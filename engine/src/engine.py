"""
Engine - 工作流引擎主类
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable

from base_engine import (
    Task, TaskFactory, TaskQueue, task_queue as _task_queue,
    Scheduler, scheduler as _default_scheduler,
    JudgmentManual, TransitionDecider, TransitionResult,
    logger as _logger, LogPoller,
)
from base_engine.config import config_registry
from .workflow import Workflow, Step, ErrorStrategy, StepStatus
from .registry import tool_registry
from .event_bus import event_bus, EventType, Event


class WorkflowEngine:
    """工作流引擎

    基于 base-engine 的 Scheduler + TaskQueue 实现。
    工作流执行流程：
    1. 解析工作流，创建任务
    2. 调度器管理任务队列和状态流转
    3. 工具适配器执行具体步骤
    4. EventBus 发布事件供监控
    """

    def __init__(
        self,
        scheduler: Scheduler = None,
        task_queue: TaskQueue = None,
        config_path: str = None,
    ):
        self.scheduler = scheduler or _default_scheduler
        self.task_queue = task_queue or _task_queue
        self._running = False

        # 加载配置（如果提供 config_path）
        if config_path:
            config_registry.load(config_path)

        # 从配置获取日志目录
        self.log_dir = config_registry.get("log.dir", "./logs")
        self.log_poller = LogPoller(self.log_dir)

    def start(self):
        """启动引擎"""
        if self._running:
            return
        self._running = True
        _logger._queue.start()  # 启动日志队列
        self.scheduler.start()
        self._running = True

    def stop(self):
        """停止引擎"""
        self._running = False
        self.scheduler.stop()

    async def run(self, workflow: Workflow, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流

        Args:
            workflow: 工作流定义
            inputs: 输入参数

        Returns:
            执行结果
        """
        # 创建工作流实例
        instance_id = f"wf_{int(time.time() * 1000)}"
        instance = {
            "id": instance_id,
            "workflow_id": workflow.id,
            "inputs": inputs,
            "outputs": {},
            "step_states": {},
            "step_outputs": {},
            "errors": [],
            "started_at": int(time.time() * 1000),
            "completed_at": None,
        }

        # 发布开始事件
        await event_bus.publish(Event(
            type=EventType.WORKFLOW_STARTED,
            data={"instance_id": instance_id, "workflow_id": workflow.id, "inputs": inputs}
        ))

        try:
            # 执行工作流
            result = await self._execute_workflow(workflow, instance, inputs)

            # 发布完成事件
            await event_bus.publish(Event(
                type=EventType.WORKFLOW_COMPLETED,
                data={"instance_id": instance_id, "result": result}
            ))

            return result

        except Exception as e:
            instance["errors"].append(str(e))
            await event_bus.publish(Event(
                type=EventType.WORKFLOW_FAILED,
                data={"instance_id": instance_id, "error": str(e)}
            ))
            raise

        finally:
            instance["completed_at"] = int(time.time() * 1000)

    async def _execute_workflow(
        self,
        workflow: Workflow,
        instance: Dict[str, Any],
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行工作流（内部）"""
        completed_steps: set = set()
        pending_steps = {step.id for step in workflow.steps}

        # 主循环
        while pending_steps:
            # 获取就绪步骤
            ready_steps = workflow.get_ready_steps(completed_steps)

            if not ready_steps:
                # 没有可执行的步骤，可能是依赖环或错误
                if pending_steps:
                    raise RuntimeError(f"Cannot proceed, stuck steps: {pending_steps}")
                break

            # 并行执行所有就绪步骤
            tasks = []
            for step in ready_steps:
                tasks.append(self._execute_step(step, workflow, instance, inputs))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for step, result in zip(ready_steps, results):
                if isinstance(result, Exception):
                    step_obj = workflow.get_step(step.id)
                    instance["step_states"][step.id] = StepStatus.FAILED.value
                    instance["errors"].append(f"Step {step.id}: {str(result)}")

                    # 错误处理
                    if step_obj.error_strategy == ErrorStrategy.SKIP:
                        instance["step_states"][step.id] = StepStatus.SKIPPED.value
                        completed_steps.add(step.id)
                        pending_steps.discard(step.id)
                    elif step_obj.error_strategy == ErrorStrategy.ABORT:
                        raise result
                    elif step_obj.error_strategy == ErrorStrategy.RETRY:
                        # TODO: 实现重试逻辑
                        raise result
                else:
                    completed_steps.add(step.id)
                    pending_steps.discard(step.id)
                    instance["step_states"][step.id] = StepStatus.COMPLETED.value
                    instance["step_outputs"][step.id] = result

        # 收集输出
        for output_name, step_output_key in self._get_output_mappings(workflow).items():
            instance["outputs"][output_name] = self._resolve_output(
                step_output_key, instance["step_outputs"], inputs
            )

        return instance["outputs"]

    async def _execute_step(
        self,
        step: Step,
        workflow: Workflow,
        instance: Dict[str, Any],
        inputs: Dict[str, Any],
    ) -> Any:
        """执行单个步骤"""
        instance["step_states"][step.id] = StepStatus.RUNNING.value

        # 发布步骤开始事件
        await event_bus.publish(Event(
            type=EventType.STEP_STARTED,
            data={
                "instance_id": instance["id"],
                "step_id": step.id,
                "tool_id": step.tool_id,
            }
        ))

        try:
            # 获取工具适配器
            adapter = tool_registry.get(step.tool_id)
            if not adapter:
                raise RuntimeError(f"Tool not found: {step.tool_id}")

            # 构建输入
            step_inputs = self._build_inputs(step, workflow, instance, inputs)

            # 执行
            result = await adapter.execute(step_inputs)

            if result.success:
                instance["step_states"][step.id] = StepStatus.COMPLETED.value

                # 发布步骤完成事件
                await event_bus.publish(Event(
                    type=EventType.STEP_COMPLETED,
                    data={
                        "instance_id": instance["id"],
                        "step_id": step.id,
                        "output": result.output,
                    }
                ))

                return result.output
            else:
                raise RuntimeError(f"Step {step.id} failed: {result.error}")

        except Exception as e:
            instance["step_states"][step.id] = StepStatus.FAILED.value

            # 发布步骤失败事件
            await event_bus.publish(Event(
                type=EventType.STEP_FAILED,
                data={
                    "instance_id": instance["id"],
                    "step_id": step.id,
                    "error": str(e),
                }
            ))

            raise

    def _build_inputs(
        self,
        step: Step,
        workflow: Workflow,
        instance: Dict[str, Any],
        workflow_inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建步骤输入"""
        inputs = {}

        for target, source in step.input_mapping.items():
            if source.startswith("$.inputs."):
                key = source.replace("$.inputs.", "")
                inputs[target] = workflow_inputs.get(key)
            elif source.startswith("$.steps."):
                parts = source.replace("$.steps.", "").split(".")
                step_id = parts[0]
                output_key = parts[1] if len(parts) > 1 else "output"
                inputs[target] = instance["step_outputs"].get(step_id, {}).get(output_key)
            else:
                inputs[target] = source

        return inputs

    def _get_output_mappings(self, workflow: Workflow) -> Dict[str, str]:
        """获取输出映射"""
        # 从工作流定义中提取输出映射
        # 这里简化处理，实际应该从工作流定义的 outputs 中读取
        mappings = {}
        for step in workflow.steps:
            for target, source in step.output_mapping.items():
                mappings[target] = f"$.steps.{step.id}.{source}"
        return mappings

    def _resolve_output(
        self,
        output_key: str,
        step_outputs: Dict[str, Any],
        workflow_inputs: Dict[str, Any],
    ) -> Any:
        """解析输出路径"""
        if output_key.startswith("$.steps."):
            parts = output_key.replace("$.steps.", "").split(".")
            step_id = parts[0]
            key = parts[1] if len(parts) > 1 else "output"
            return step_outputs.get(step_id, {}).get(key)
        elif output_key.startswith("$.inputs."):
            key = output_key.replace("$.inputs.", "")
            return workflow_inputs.get(key)
        return output_key


# 全局引擎实例
_engine: Optional[WorkflowEngine] = None


def get_engine() -> WorkflowEngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine

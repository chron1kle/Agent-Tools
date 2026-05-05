"""
Workflow Executor - 工作流执行引擎
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .workflow import (
    Workflow, WorkflowInstance, WorkflowStatus,
    Step, StepStatus, ErrorStrategy
)
from .registry import ToolRegistry


class WorkflowExecutor:
    """
    工作流执行引擎

    负责：
    - 构建 DAG
    - 拓扑排序
    - 步骤执行
    - 错误处理
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def run(self, workflow: Workflow, inputs: Dict[str, Any]) -> WorkflowInstance:
        """
        执行工作流

        Args:
            workflow: 工作流定义
            inputs: 输入参数

        Returns:
            WorkflowInstance: 工作流实例
        """
        # 创建实例
        instance = WorkflowInstance(
            id=f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            workflow_id=workflow.id,
            inputs=inputs,
            started_at=datetime.now().isoformat()
        )

        # 构建依赖图
        dag = self._build_dag(workflow, instance)

        # 初始化步骤状态
        for step in workflow.steps:
            instance.step_states[step.id] = StepStatus.PENDING

        instance.status = WorkflowStatus.RUNNING

        # 执行 DAG
        try:
            await self._execute_dag(workflow, instance, dag)
            instance.status = WorkflowStatus.COMPLETED
        except Exception as e:
            instance.status = WorkflowStatus.FAILED
            instance.errors.append(str(e))

        instance.completed_at = datetime.now().isoformat()
        return instance

    def _build_dag(self, workflow: Workflow, instance: WorkflowInstance) -> Dict[str, List[str]]:
        """
        构建依赖图

        Returns:
            Dict[step_id, List[依赖step_id]]
        """
        dag = {}
        for step in workflow.steps:
            dag[step.id] = step.depends_on.copy()
        return dag

    async def _execute_dag(self, workflow: Workflow, instance: WorkflowInstance, dag: Dict[str, List[str]]):
        """执行 DAG"""
        completed = set()
        pending = {step.id for step in workflow.steps}

        while pending:
            # 找到所有可执行的步骤（依赖都已完成）
            ready = []
            for step_id in pending:
                deps = dag.get(step_id, [])
                if all(dep in completed for dep in deps):
                    ready.append(step_id)

            if not ready:
                # 没有可执行的步骤，可能是依赖环或错误
                if pending:
                    raise RuntimeError(f"Cannot proceed: {pending}")
                break

            # 并行执行所有就绪的步骤
            tasks = []
            for step_id in ready:
                step = next(s for s in workflow.steps if s.id == step_id)
                tasks.append(self._execute_step(step, instance))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查结果
            for step_id, result in zip(ready, results):
                if isinstance(result, Exception):
                    step = next(s for s in workflow.steps if s.id == step_id)
                    await self._handle_error(step, result, workflow, instance)
                else:
                    completed.add(step_id)
                    pending.remove(step_id)

    async def _execute_step(self, step: Step, instance: WorkflowInstance) -> Any:
        """执行单个步骤"""
        # 更新状态
        instance.step_states[step.id] = StepStatus.RUNNING

        # 获取工具
        tool = self.registry.get(step.tool)
        if not tool:
            raise RuntimeError(f"Tool not found: {step.tool}")

        # 构建输入
        inputs = self._build_inputs(step, instance)

        # 验证输入
        if not await tool.validate_inputs(inputs):
            raise ValueError(f"Invalid inputs for step {step.id}")

        # 执行
        result = await tool.execute(inputs)

        if result.success:
            instance.step_states[step.id] = StepStatus.COMPLETED
            instance.step_outputs[step.id] = result.output
        else:
            raise RuntimeError(f"Step {step.id} failed: {result.error}")

        return result.output

    def _build_inputs(self, step: Step, instance: WorkflowInstance) -> Dict[str, Any]:
        """根据映射构建输入"""
        inputs = {}

        for target, source in step.input_mapping.items():
            if source.startswith("$.inputs."):
                key = source.replace("$.inputs.", "")
                inputs[target] = instance.inputs.get(key)
            elif source.startswith("$.steps."):
                # 从上一步获取
                parts = source.replace("$.steps.", "").split(".")
                step_id = parts[0]
                output_key = parts[1] if len(parts) > 1 else "output"
                inputs[target] = instance.step_outputs.get(step_id, {}).get(output_key)

        return inputs

    async def _handle_error(self, step: Step, error: Exception, workflow: Workflow, instance: WorkflowInstance):
        """处理错误"""
        if step.error_strategy == ErrorStrategy.RETRY:
            # 重试
            for attempt in range(step.retry.max_attempts):
                try:
                    await self._execute_step(step, instance)
                    return
                except Exception as e:
                    if attempt == step.retry.max_attempts - 1:
                        raise
                    await asyncio.sleep(step.retry.initial_delay * (step.retry.backoff_factor ** attempt))

        elif step.error_strategy == ErrorStrategy.SKIP:
            instance.step_states[step.id] = StepStatus.SKIPPED

        elif step.error_strategy == ErrorStrategy.ABORT:
            raise error

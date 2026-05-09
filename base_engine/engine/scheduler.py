"""Scheduler - 调度中心，单轮询线程 + 执行线程池"""

import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any

from ..task.task import Task
from ..task.task_factory import TaskFactory
from .task_queue import task_queue
from .transition_decider import TransitionDecider
from .judgment_manual import JudgmentManual


class Scheduler:
    """调度中心

    线程结构：
    - 轮询线程（1个）：从 exec_queue 取出任务，统一处理所有状态变更（包括终止）
    - 执行线程池（N个）：并行执行任务，执行完后标记完成
    - 判断器线程（1个）：从 completion_queue 判断下一状态，但不直接处理副作用

    设计原则：
    - 所有任务统一经过 exec_queue，由轮询线程处理
    - 不存在"判断器直接处理 terminate"这种例外路径
    - state = None 表示任务终止，由轮询线程统一处理退出逻辑
    """

    def __init__(
        self,
        decider: Optional[TransitionDecider] = None,
        max_workers: int = 4,
    ):
        self.task_queue = task_queue  # 使用模块级单例
        self.decider = decider
        self.max_workers = max_workers  # 执行线程池上限
        self._running = False
        self._threads: List[threading.Thread] = []
        self._executor: Optional[ThreadPoolExecutor] = None

    def start(self):
        """启动调度中心"""
        self._running = True

        # 创建执行线程池
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # 启动轮询线程（单线程，统一处理所有任务）
        t = threading.Thread(target=self._polling_loop, daemon=True)
        t.start()
        self._threads.append(t)

        # 启动判断器线程（独立轮询 completion_queue）
        t = threading.Thread(target=self._process_completions, daemon=True)
        t.start()
        self._threads.append(t)

    def _notify_mcp(self, task: Task):
        """任务结束时通知 MCP（预留接口）"""
        # TODO: 实现 MCP 回调通知机制
        # 目前只打印日志，实际通知由上层调用者处理
        pass

    def stop(self):
        """停止调度中心"""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True)
        for t in self._threads:
            t.join(timeout=2.0)

    def submit_task(self, tool_id: str, inputs: Dict[str, Any]):
        """提交新任务

        Args:
            tool_id: 工具/任务类型 ID
            inputs: 任务输入数据
        """
        task = TaskFactory.create(tool_id, inputs)
        self.task_queue.add_task(task)

    def _polling_loop(self):
        """轮询线程：统一处理所有任务状态变更

        设计原则：
        - 轮询线程不执行任务，只负责分发
        - 任务按 FIFO 顺序被分发，保证公平性
        - 执行线程池负责真正的并行执行

        任务流转：
        - task.state == "pending_exec" → 新任务，等待 decider 分配第一步
        - task.state is None → 终止处理（通知 MCP + 移除任务）
        - task.state is not None and != "pending_exec" → 提交给执行线程池

        未来扩展：
        - 当前实现为简单 FIFO 策略
        - 未来可引入负载均衡算法（如：任务优先级、资源需求、依赖关系等），
          在 _exec_queue 中选择"最适合当前执行"的任务，而非简单FIFO
        - 扩展时需注意：负载均衡逻辑应在轮询线程中完成，保持单线程避免竞争
        """
        while self._running:
            try:
                task = self.task_queue._exec_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # state = None 表示任务终止，统一由此处理
            if task.state is None:
                self._notify_mcp(task)
                self.task_queue.remove_task(task.id)
                continue

            # task.state == "pending_exec" 表示新任务，等待 decider 分配第一步
            if task.state == "pending_exec":
                # 记录到 _state_queue（如果尚未记录）
                self.task_queue._state_queue[task.id] = task
                # 通知 decider 分配第一步
                self.task_queue.put(task.id)
                # 不执行，等待 decider 决策
                continue

            # 记录当前任务（移入 _state_queue）
            self.task_queue._state_queue[task.id] = task

            # 提交给执行线程池
            self._executor.submit(self._exec_task, task)

    def _exec_task(self, task: Task):
        """执行任务（运行于执行线程池中）

        执行完后自动标记完成，由判断器处理后续流转

        TODO: 若出现异常情况，可能需要特殊的标记或处理。待实现。
        """
        try:
            self.task_queue.exec(task)
        except Exception:
            # 执行异常，仍标记完成让判断器处理
            pass

    def _process_completions(self):
        """判断器循环：轮询 completion_queue

        从 completion_queue 按 FIFO 顺序弹出任务 ID，
        决定下一状态后，将任务写回 exec_queue
        """
        while self._running:
            try:
                task_id = self.task_queue.pop_completion(timeout=0.1)
            except queue.Empty:
                continue

            task = self.task_queue.get_task(task_id)
            if not task:
                continue

            if not self.decider:
                # 没有判断器，任务结束
                task.state = None
                self.task_queue.move_to_exec(task.id)
                continue

            # 判断下一状态
            try:
                result = self.decider.decide(task, event="state_completed")
            except Exception:
                # 判断失败，任务结束
                task.state = None
                self.task_queue.move_to_exec(task.id)
                continue

            # 将判断结果写入 task，统一由轮询线程处理
            # decide() 返回下一状态，None 表示终止
            task.state = result
            self.task_queue.move_to_exec(task.id)


# 模块级单例（默认判断手册）
_default_manual = JudgmentManual.create_default()
scheduler = Scheduler(decider=TransitionDecider(_default_manual))

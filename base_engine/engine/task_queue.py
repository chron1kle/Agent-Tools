"""Task queue - 任务队列，维护双队列 + completion_queue"""

import queue
import threading
from typing import Dict, Optional

from .._queue.base_queue import BaseQueue
from ..task.task import Task


class TaskQueue(BaseQueue):
    """任务队列

    维护两个队列和一个 completion_queue：
    - _state_queue: 执行中的任务（Dict[str, Task]，需锁保护）
    - _exec_queue: 待执行队列（queue.Queue，线程安全）
    - completion_queue: 通知 decider 的 FIFO 队列（BaseQueue._q）

    流程：
    1. add_task → task.state = "pending_exec"，同时进入 _state_queue 和 _exec_queue
    2. 轮询线程发现 pending_exec → 通知 decider（放入 completion_queue）
    3. decider 分配第一步状态 → move_to_exec 移回 _exec_queue
    4. 轮询线程提交给执行线程池 → exec → _mark_complete → completion_queue
    5. decider 判断下一状态 → 循环步骤 3-5
    """

    def __init__(self):
        super().__init__()
        # Queue 1: executing 状态的任务
        self._state_queue: Dict[str, Task] = {}
        # Queue 2: pending_exec 状态的任务（queue.Queue 天然线程安全）
        self._exec_queue: queue.Queue[Task] = queue.Queue()
        # 保护 _state_queue 的锁
        self._state_lock = threading.Lock()

    def start(self):
        """禁用默认消费器"""
        pass

    def _handle(self):
        """消费 _exec_queue 中的任务（负载均衡）

        由调度中心的 worker 线程直接调用
        """
        try:
            task = self._exec_queue.get(timeout=0.1)
            self._state_lock.acquire()
            self._state_queue[task.id] = task
            self._state_lock.release()
            self.exec(task)
        except queue.Empty:
            pass

    def exec(self, task: Task):
        """执行任务（由调度中心调用）

        任务完成一个状态后，调用 _mark_complete 加入 completion_queue
        """
        # TODO: 实际执行逻辑由调度中心或工具实现
        # 这里只是占位，表示任务执行完成
        self._mark_complete(task.id)

    def _mark_complete(self, task_id: str):
        """内部方法：标记任务完成"""
        self.put(task_id)  # 加入 completion_queue

    def add_task(self, task: Task):
        """添加新任务

        任务同时进入两个队列：
        - _state_queue: 记录任务执行状态
        - _exec_queue: 待执行队列
        """
        task.state = "pending_exec"
        self._state_queue[task.id] = task
        self._exec_queue.put(task)
        # completion_queue.put(task.id) 不需要，polling_loop 会处理

    def pop_completion(self, timeout: float = None) -> str:
        """按 FIFO 获取下一个待处理的任务 ID"""
        return self._q.get(timeout=timeout)

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务对象（从 _state_queue）"""
        with self._state_lock:
            return self._state_queue.get(task_id)

    def move_to_exec(self, task_id: str):
        """将任务移入 Queue 2（待执行）

        从 _state_queue 取出，加入 _exec_queue
        """
        with self._state_lock:
            task = self._state_queue.pop(task_id, None)
        if task:
            self._exec_queue.put(task)

    def move_to_state(self, task_id: str, state: Optional[str]):
        """将任务移入 Queue 1（状态管理）

        从 _exec_queue 取出，加入 _state_queue
        """
        found_task = None
        temp_tasks = []
        try:
            while True:
                t = self._exec_queue.get_nowait()
                if t.id == task_id:
                    found_task = t
                else:
                    temp_tasks.append(t)
        except queue.Empty:
            pass
        # 将非目标任务放回队列
        for t in temp_tasks:
            self._exec_queue.put(t)

        if found_task:
            found_task.state = state
            with self._state_lock:
                self._state_queue[task_id] = found_task

    def remove_task(self, task_id: str):
        """
        移除任务（任务结束）
        
        TODO: 这里后续需要考虑是否把任务写入历史记录里。待实现。
        """
        with self._state_lock:
            self._state_queue.pop(task_id, None)
        # 从 _exec_queue 移除（通过临时重建队列）
        temp_tasks = []
        try:
            while True:
                t = self._exec_queue.get_nowait()
                if t.id != task_id:
                    temp_tasks.append(t)
        except queue.Empty:
            pass
        for t in temp_tasks:
            self._exec_queue.put(t)


# 模块级单例
task_queue = TaskQueue()

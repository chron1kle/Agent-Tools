"""
TaskQueue - 通用任务队列实现
支持并发执行、进度追踪、回调通知
"""

import asyncio
import json
import uuid
from typing import List, Optional, Callable, Any
from datetime import datetime

from .task import Task, TaskStatus
from .config import TaskQueueConfig, get_queue_config


class TaskQueue:
    """
    异步任务队列

    特性:
        - 并发控制
        - 进度追踪
        - 回调通知
        - 配置外部化

    使用示例:
        queue = TaskQueue(config=get_queue_config("MYTOOL"))

        # 添加进度回调
        def on_progress(task):
            print(f"Progress: {task.progress}%")

        queue.add_progress_callback(on_progress)

        # 提交任务
        task_id = await queue.submit(["--input", "file.pdf"])

        # 查询状态
        task = await queue.get_task(task_id)
    """

    def __init__(
        self,
        config: Optional[TaskQueueConfig] = None,
        prefix: str = "TASKQUEUE"
    ):
        """
        初始化任务队列

        Args:
            config: 任务队列配置
            prefix: 环境变量前缀
        """
        self.config = config or get_queue_config(prefix)
        self.tasks: dict[str, Task] = {}
        self.running: int = 0
        self._lock = asyncio.Lock()
        self._progress_callbacks: List[Callable] = []

    def add_progress_callback(self, callback: Callable[[Task], None]):
        """
        添加进度回调

        Args:
            callback: 回调函数，接收 Task 对象
        """
        self._progress_callbacks.append(callback)

    async def _notify_progress(self, task: Task):
        """通知进度变化"""
        for callback in self._progress_callbacks:
            try:
                callback(task)
            except Exception:
                pass

    async def submit(self, args: List[str]) -> str:
        """
        提交任务

        Args:
            args: 命令行参数列表

        Returns:
            str: 任务 ID
        """
        # 检查队列是否已满
        async with self._lock:
            if len(self.tasks) >= self.config.queue_max_size:
                raise RuntimeError(f"Queue is full (max {self.config.queue_max_size})")

            task_id = str(uuid.uuid4())[:8]
            task = Task(id=task_id, args=args)
            self.tasks[task_id] = task

        # 异步执行任务
        asyncio.create_task(self._execute(task))

        return task_id

    async def _execute(self, task: Task):
        """执行任务（子类重写）"""
        # 默认实现：子类应该重写这个方法
        # 这里只是一个占位实现
        pass

    async def _do_execute(self, task: Task, executor: Callable):
        """
        执行任务的标准流程

        Args:
            task: 任务对象
            executor: 执行器函数，应该是异步函数
        """
        async with self._lock:
            if self.running >= self.config.max_workers:
                # 等待有空位
                while self.running >= self.config.max_workers:
                    await asyncio.sleep(0.1)

            self.running += 1
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()

        try:
            # 执行任务
            result = await executor(task)

            async with self._lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0
                task.message = "完成"

        except Exception as e:
            async with self._lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.message = f"失败: {e}"

        finally:
            async with self._lock:
                self.running -= 1
                task.completed_at = datetime.now().isoformat()

            await self._notify_progress(task)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        async with self._lock:
            return self.tasks.get(task_id)

    async def list_tasks(self) -> List[Task]:
        """列出所有任务"""
        async with self._lock:
            return list(self.tasks.values())

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False

    async def clear_completed(self):
        """清除已完成的任务"""
        async with self._lock:
            self.tasks = {
                tid: task for tid, task in self.tasks.items()
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            }

    async def get_stats(self) -> dict:
        """获取统计信息"""
        async with self._lock:
            stats = {
                "total": len(self.tasks),
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "running_workers": self.running,
                "max_workers": self.config.max_workers
            }
            for task in self.tasks.values():
                stats[task.status.value] += 1
            return stats

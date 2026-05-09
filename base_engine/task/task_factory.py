"""Task factory - 任务工厂"""

from task.task import Task
from task.task_id import TaskIDGenerator


class TaskFactory:
    """任务工厂"""

    @classmethod
    def create(
        cls,
        tool_id: str,
        inputs: dict,
        metadata: dict = None,
        timestamp: int = None,
    ) -> Task:
        """创建新任务

        Args:
            tool_id: 工具/任务类型 ID
            inputs: 任务输入数据
            metadata: 额外元数据
            timestamp: 毫秒时间戳（默认自动生成）
        """
        import time
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        return Task(
            id=TaskIDGenerator.generate(),
            tool_id=tool_id,
            created_at=timestamp,
            state="pending_exec",  # 初始为待执行状态
            timeline=[],
            data={"inputs": inputs},  # 输入存入 data
            call_stack=[],
            metadata=metadata or {},
            error=None,
        )

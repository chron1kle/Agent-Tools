"""
Task 数据结构定义
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any, Dict, Optional, List


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """
    任务定义

    属性:
        id: 任务唯一标识
        args: 命令行参数
        status: 任务状态
        progress: 进度 (0-100)
        message: 进度消息
        result: 执行结果
        error: 错误信息
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    args: list = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "args": self.args,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }

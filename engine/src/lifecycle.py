"""
Lifecycle Manager - 生命周期管理
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .workflow import Workflow, WorkflowInstance, WorkflowStatus
from .executor import WorkflowExecutor
from .registry import ToolRegistry


class LifecycleManager:
    """
    工作流生命周期管理器

    负责：
    - 工作流实例管理
    - 状态追踪
    - 启动/停止/监控
    """

    def __init__(self, executor: WorkflowExecutor, registry: ToolRegistry):
        self.executor = executor
        self.registry = registry
        self.instances: Dict[str, WorkflowInstance] = {}
        self._lock = asyncio.Lock()

    async def create_workflow(self, workflow: Workflow, inputs: Dict[str, Any]) -> str:
        """
        创建并启动工作流

        Returns:
            str: 工作流实例 ID
        """
        async with self._lock:
            instance = await self.executor.run(workflow, inputs)
            self.instances[instance.id] = instance
            return instance.id

    async def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取工作流实例"""
        async with self._lock:
            return self.instances.get(instance_id)

    async def list_instances(self) -> list:
        """列出所有工作流实例"""
        async with self._lock:
            return list(self.instances.values())

    async def cancel_instance(self, instance_id: str) -> bool:
        """取消工作流"""
        async with self._lock:
            instance = self.instances.get(instance_id)
            if instance and instance.status == WorkflowStatus.RUNNING:
                instance.status = WorkflowStatus.CANCELLED
                return True
        return False

    async def get_status(self) -> Dict[str, Any]:
        """获取整体状态"""
        async with self._lock:
            stats = {
                "total": len(self.instances),
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            for instance in self.instances.values():
                stats[instance.status.value] += 1

            # 工具状态
            tool_status = await self.registry.get_all_status()

            return {
                "workflows": stats,
                "tools": {k: v.value for k, v in tool_status.items()}
            }

    async def cleanup_completed(self, max_age_seconds: int = 3600):
        """清理已完成的实例"""
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for id, instance in self.instances.items():
                if instance.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
                    if instance.completed_at:
                        completed_time = datetime.fromisoformat(instance.completed_at)
                        age = (now - completed_time).total_seconds()
                        if age > max_age_seconds:
                            to_remove.append(id)

            for id in to_remove:
                del self.instances[id]

            return len(to_remove)

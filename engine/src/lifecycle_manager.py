"""
Lifecycle Manager - 生命周期管理
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .engine import WorkflowEngine, get_engine
from .workflow import Workflow, WorkflowStatus
from .registry import tool_registry


class LifecycleManager:
    """工作流生命周期管理器

    负责：
    - 工作流实例管理
    - 状态追踪
    - 启动/停止/监控
    """

    def __init__(self, engine: WorkflowEngine = None):
        self.engine = engine or get_engine()
        self.instances: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_workflow(
        self,
        workflow: Workflow,
        inputs: Dict[str, Any],
    ) -> str:
        """创建并启动工作流

        Returns:
            str: 工作流实例 ID
        """
        async with self._lock:
            # 确保引擎已启动
            if not hasattr(self.engine, "_running") or not self.engine._running:
                self.engine.start()

            # 创建工作流
            instance_id = f"wf_{int(datetime.now().timestamp() * 1000)}"

            # 保存实例信息
            self.instances[instance_id] = {
                "id": instance_id,
                "workflow_id": workflow.id,
                "workflow": workflow,
                "inputs": inputs,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }

            # 异步执行
            asyncio.create_task(self._run_workflow(instance_id, workflow, inputs))

            return instance_id

    async def _run_workflow(
        self,
        instance_id: str,
        workflow: Workflow,
        inputs: Dict[str, Any],
    ):
        """后台执行工作流"""
        try:
            self.instances[instance_id]["status"] = "running"
            result = await self.engine.run(workflow, inputs)
            self.instances[instance_id]["status"] = "completed"
            self.instances[instance_id]["result"] = result
        except Exception as e:
            self.instances[instance_id]["status"] = "failed"
            self.instances[instance_id]["error"] = str(e)

    async def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
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
            if instance and instance["status"] == "running":
                instance["status"] = "cancelled"
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
                "cancelled": 0,
            }
            for instance in self.instances.values():
                status = instance.get("status", "unknown")
                if status in stats:
                    stats[status] += 1

            # 工具状态
            tool_status = await tool_registry.get_all_status()

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
                status = instance.get("status")
                if status in ("completed", "failed", "cancelled"):
                    created_at = datetime.fromisoformat(instance["created_at"])
                    age = (now - created_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(id)

            for id in to_remove:
                del self.instances[id]

            return len(to_remove)

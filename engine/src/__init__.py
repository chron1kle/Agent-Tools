"""
Agent Tools Workflow Engine

工作流引擎 - 统一的任务编排与执行系统
"""

from .workflow import (
    Workflow, WorkflowInstance, Step, StepStatus, WorkflowStatus,
    Input, Output, ErrorStrategy, RetryConfig
)
from .adapter import ToolAdapter, ToolStatus, ToolResult, SubprocessToolAdapter
from .registry import ToolRegistry, registry, register_tool
from .executor import WorkflowExecutor
from .lifecycle import LifecycleManager
from .state import StateStore
from .events import EventBus, Event, EventType, event_bus

__version__ = "1.0.0"

__all__ = [
    # 工作流
    "Workflow",
    "WorkflowInstance",
    "Step",
    "StepStatus",
    "WorkflowStatus",
    "Input",
    "Output",
    "ErrorStrategy",
    "RetryConfig",
    # 工具适配器
    "ToolAdapter",
    "ToolStatus",
    "ToolResult",
    "SubprocessToolAdapter",
    # 注册表
    "ToolRegistry",
    "registry",
    "register_tool",
    # 执行引擎
    "WorkflowExecutor",
    # 生命周期管理
    "LifecycleManager",
    # 状态存储
    "StateStore",
    # 事件系统
    "EventBus",
    "Event",
    "EventType",
    "event_bus",
]


class WorkflowEngine:
    """
    工作流引擎主类

    使用示例:
        from engine import WorkflowEngine

        engine = WorkflowEngine()
        result = await engine.run("workflow_id", inputs={})
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # 初始化组件
        self.registry = ToolRegistry()
        self.executor = WorkflowExecutor(self.registry)
        self.lifecycle = LifecycleManager(self.executor, self.registry)
        self.state = StateStore()
        self.event_bus = EventBus()

    def register_tool(self, name: str, adapter: ToolAdapter):
        """注册工具"""
        self.registry.register(name, adapter)

    async def run(self, workflow: Workflow, inputs: dict) -> WorkflowInstance:
        """运行工作流"""
        return await self.lifecycle.create_workflow(workflow, inputs)

    async def get_instance(self, instance_id: str) -> WorkflowInstance:
        """获取工作流实例"""
        return await self.lifecycle.get_instance(instance_id)

    async def list_instances(self) -> list:
        """列出所有实例"""
        return await self.lifecycle.list_instances()

    async def get_status(self) -> dict:
        """获取状态"""
        return await self.lifecycle.get_status()

    async def start(self):
        """启动引擎"""
        await self.registry.start_all()

    async def stop(self):
        """停止引擎"""
        await self.registry.stop_all()

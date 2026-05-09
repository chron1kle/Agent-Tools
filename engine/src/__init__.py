"""
Workflow Engine - 基于 base-engine 的工作流引擎

主要组件：
- WorkflowEngine: 主引擎类
- LifecycleManager: 实例生命周期管理
- EventBus: 事件总线
- ToolRegistry: 工具注册表
- ToolAdapter: 工具适配器基类
- ConfigRegistry: 配置注册中心
"""

from base_engine.config import ConfigRegistry, config_registry
from .workflow import Workflow, Step, ErrorStrategy, StepStatus, RetryConfig
from .engine import WorkflowEngine, get_engine
from .lifecycle_manager import LifecycleManager
from .event_bus import EventBus, event_bus, EventType, Event
from .registry import ToolRegistry, tool_registry, register_tool
from .tool_adapter import ToolAdapter, ToolResult, ToolStatus, SubprocessToolAdapter

__all__ = [
    # config
    "ConfigRegistry", "config_registry",
    # workflow
    "Workflow", "Step", "ErrorStrategy", "StepStatus", "RetryConfig",
    # engine
    "WorkflowEngine", "get_engine",
    # lifecycle
    "LifecycleManager",
    # event
    "EventBus", "event_bus", "EventType", "Event",
    # registry
    "ToolRegistry", "tool_registry", "register_tool",
    # adapter
    "ToolAdapter", "ToolResult", "ToolStatus", "SubprocessToolAdapter",
]

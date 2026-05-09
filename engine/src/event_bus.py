"""
Event Bus - 事件总线
"""

import asyncio
from typing import Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """事件类型"""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    TOOL_STATUS_CHANGED = "tool_status_changed"
    PROGRESS = "progress"


@dataclass
class Event:
    """事件"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


class EventBus:
    """事件总线

    支持事件发布和订阅。
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._history: List[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event: Event):
        """发布事件"""
        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # 通知订阅者
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Event callback error: {e}")

    def get_history(self, event_type: EventType = None) -> List[Event]:
        """获取事件历史"""
        if event_type:
            return [e for e in self._history if e.type == event_type]
        return self._history.copy()


# 模块级单例
event_bus = EventBus()

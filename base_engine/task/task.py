"""Task object - 保管任务的全部信息"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


EventType = Literal["state_enter", "state_exit", "api_request", "api_response"]


@dataclass
class CallFrame:
    """调用帧 - 支持跨工具回调"""
    return_state: str        # 回调目标状态（回到调用方后进入哪个状态）
    return_event: str        # 回调时触发的事件
    snapshot: Dict[str, Any] = field(default_factory=dict)  # 调用时的上下文快照
    tool_name: str = ""       # 被调用的工具名（可选）


@dataclass
class ErrorInfo:
    """错误信息"""
    exception_type: str
    message: str
    timestamp: int


@dataclass
class Task:
    """任务对象"""

    # ─── 身份信息 ───
    id: str                          # 唯一标识
    tool_id: str                     # 任务类型/工具 ID
    created_at: int                  # 创建时间（毫秒时间戳）

    # ─── 运行时数据 ───
    # 任务状态：直接存储状态名（字符串）
    # None 表示生命周期结束（由 decider 判断 action=terminate 时设置）
    state: Optional[str] = None

    # ─── 时间线 ───
    timeline: List[Dict[str, Any]] = field(default_factory=list)

    # ─── 数据存储 ───
    # 所有运行时数据（输入+中间产出+输出）
    data: Dict[str, Any] = field(default_factory=dict)

    # ─── 调用栈（支持回调） ───
    call_stack: List[CallFrame] = field(default_factory=list)

    # ─── 元数据 ───
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ─── 错误信息 ───
    error: Optional[ErrorInfo] = None

    def add_timeline(self, event_type: EventType, event_name: str, timestamp: int, **data):
        """添加时间线条目"""
        self.timeline.append({
            "timestamp": timestamp,
            "event_type": event_type,
            "event_name": event_name,
            "data": data,
        })

    def push_call_frame(self, frame: CallFrame):
        """压入调用帧"""
        self.call_stack.append(frame)

    def pop_call_frame(self) -> Optional[CallFrame]:
        """弹出调用帧"""
        if self.call_stack:
            return self.call_stack.pop()
        return None

    def get_data(self, key: str, default: Any = None) -> Any:
        """获取数据（支持嵌套 key 如 "extracting.pages"）"""
        if "." not in key:
            return self.data.get(key, default)

        parts = key.split(".")
        value = self.data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
        return value if value is not None else default

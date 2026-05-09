"""Judgment manual - 判断手册，定义流转规则"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TransitionRule:
    """流转规则"""
    from_state: str       # 从哪个状态
    event: str           # 触发事件
    to_state: str        # 目标状态
    condition: Optional[str] = None  # 条件（可选）


@dataclass
class ErrorHandler:
    """异常处理器"""
    state: str           # 在哪个状态
    exception_type: str  # 异常类型（* 表示所有）
    strategy: str        # 处理策略：retry/skip/fallback/abort
    max_attempts: int   # 最大重试次数
    fallback_state: Optional[str] = None  # 降级状态（可选）


class JudgmentManual:
    """判断手册 - 定义所有流转规则"""

    def __init__(self):
        self.transition_rules: List[TransitionRule] = []
        self.error_handlers: List[ErrorHandler] = []

    def add_rule(self, rule: TransitionRule):
        """添加流转规则"""
        self.transition_rules.append(rule)

    def add_error_handler(self, handler: ErrorHandler):
        """添加异常处理器"""
        self.error_handlers.append(handler)

    def get_rule(self, from_state: str, event: str) -> Optional[TransitionRule]:
        """查找匹配的流转规则"""
        for rule in self.transition_rules:
            if rule.from_state == from_state and rule.event == event:
                return rule
        return None

    def get_error_handler(self, state: str, exception_type: str) -> Optional[ErrorHandler]:
        """查找匹配的异常处理器"""
        for handler in self.error_handlers:
            if handler.state == state and (handler.exception_type == "*" or handler.exception_type == exception_type):
                return handler
        return None

    @classmethod
    def create_default(cls) -> "JudgmentManual":
        """创建默认判断手册（示例）"""
        manual = cls()

        # 正常流转
        manual.add_rule(TransitionRule("idle", "start", to_state="pending"))
        manual.add_rule(TransitionRule("pending", "execute", to_state="executing"))
        manual.add_rule(TransitionRule("executing", "done", to_state="completed"))

        # 错误流转
        manual.add_rule(TransitionRule("executing", "error", to_state="failed"))

        # 重试
        manual.add_rule(TransitionRule("failed", "retry", to_state="pending"))

        # 异常处理示例
        manual.add_error_handler(ErrorHandler(
            state="executing",
            exception_type="NetworkError",
            strategy="retry",
            max_attempts=3,
        ))
        manual.add_error_handler(ErrorHandler(
            state="executing",
            exception_type="*",
            strategy="abort",
            max_attempts=0,
        ))

        return manual

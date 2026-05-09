"""Transition decider - 流转判断执行器"""

from typing import Optional
from ..task.task import Task
from .judgment_manual import JudgmentManual, TransitionRule, ErrorHandler


class TransitionDecider:
    """状态流转判断器

    decide() 直接返回下一状态（字符串），None 表示任务终止。
    所有副作用（如 retry_count、error）写入 task.metadata。
    """

    def __init__(self, manual: JudgmentManual):
        self.manual = manual

    def decide(self, task: Task, event: str, exception: Optional[Exception] = None) -> Optional[str]:
        """决定下一个状态

        Args:
            task: 当前任务对象
            event: 触发事件
            exception: 异常（如果有）

        Returns:
            下一状态名，None 表示任务终止
        """
        # 1. 如果有异常，优先处理异常
        if exception:
            return self._handle_exception(task, exception)

        # 2. 查找匹配的流转规则
        rule = self.manual.get_rule(task.state, event)

        if rule:
            # 3. 检查条件
            if rule.condition and not self._evaluate_condition(rule.condition, task):
                return task.state  # 条件不满足，保持当前状态

            # 4. 执行流转
            return rule.to_state

        # 5. 没有匹配规则 → 检查调用栈
        return self._handle_no_rule(task, event)

    def _handle_no_rule(self, task: Task, event: str) -> Optional[str]:
        """处理无匹配规则的情况：检查调用栈决定下一步"""
        # 调用栈非空 → 弹出栈顶帧，进入回调状态
        if task.call_stack:
            frame = task.pop_call_frame()
            return frame.return_state

        # 调用栈为空 → 无下一状态，任务结束
        return None

    def _handle_exception(self, task: Task, exception: Exception) -> Optional[str]:
        """处理异常"""
        handler = self.manual.get_error_handler(task.state, type(exception).__name__)

        if not handler:
            # 没有匹配的处理器，默认 abort
            task.metadata["error"] = str(exception)
            return "failed"

        if handler.strategy == "retry":
            task.metadata["retry_count"] = task.metadata.get("retry_count", 0) + 1
            return task.state  # 保持在当前状态重试

        elif handler.strategy == "skip":
            task.metadata["error"] = str(exception)
            return handler.fallback_state or self._find_next_state(task.state)

        elif handler.strategy == "fallback":
            task.metadata["error"] = str(exception)
            return handler.fallback_state

        elif handler.strategy == "abort":
            task.metadata["error"] = str(exception)
            return "failed"

        task.metadata["error"] = f"Unknown strategy: {handler.strategy}"
        return "failed"

    def _evaluate_condition(self, condition: str, task: Task) -> bool:
        """评估条件表达式（简单实现）"""
        # TODO: 实现更复杂的条件评估
        # 目前支持简单的 key == value 格式
        if "==" in condition:
            key, value = condition.split("==", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            return task.get_data(key) == value
        return True

    def _find_next_state(self, current_state: str) -> Optional[str]:
        """查找当前状态的下一个状态（无匹配规则时的默认行为）"""
        for rule in self.manual.transition_rules:
            if rule.from_state == current_state and rule.event == "done":
                return rule.to_state
        return None


class TransitionError(Exception):
    """流转错误"""
    pass

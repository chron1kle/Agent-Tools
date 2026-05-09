"""Context assembler - 上下文组装，按状态组装提示词"""

from typing import List, Dict, Any, Optional

from task.task import Task


class ContextAssembler:
    """上下文组装系统"""

    def __init__(self):
        # 系统提示词配置：tool_id -> state -> prompt
        self._prompts: Dict[str, Dict[str, str]] = {}

    def register_prompt(self, tool_id: str, state: str, prompt: str):
        """注册系统提示词"""
        if tool_id not in self._prompts:
            self._prompts[tool_id] = {}
        self._prompts[tool_id][state] = prompt

    def assemble(
        self,
        task: Task,
        state: str,
        goal: str,
    ) -> List[Dict[str, str]]:
        """组装上下文

        Args:
            task: 当前任务对象
            state: 当前状态
            goal: 本次调用的目标

        Returns:
            消息列表
        """
        messages: List[Dict[str, str]] = []

        # 1. 获取系统提示词（基于工具和状态）
        system_prompt = self._get_system_prompt(task.tool_id, state)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. 获取历史上下文（基于状态历史）
        history = self._get_history_context(task, state)
        if history:
            messages.append({"role": "system", "content": f"历史上下文:\n{history}"})

        # 3. 获取当前输入（基于状态）
        current_input = self._get_current_input(task, state)

        # 4. 组合用户消息
        user_content = self._format_goal(goal, current_input)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _get_system_prompt(self, tool_id: str, state: str) -> str:
        """获取系统提示词"""
        return self._prompts.get(tool_id, {}).get(state, "")

    def _get_history_context(self, task: Task, state: str) -> Optional[str]:
        """获取历史上下文

        只返回同一状态的历史记录
        """
        history_entries = []
        for entry in task.timeline:
            if entry.get("event_name") == state and entry.get("event_type") in ("state_enter", "state_exit"):
                history_entries.append(entry)

        if not history_entries:
            return None

        lines = []
        for entry in history_entries:
            event_type = entry.get("event_type", "")
            data = entry.get("data", {})
            lines.append(f"[{event_type}] {data}")

        return "\n".join(lines)

    def _get_current_input(self, task: Task, state: str) -> Dict[str, Any]:
        """获取当前状态的输入

        默认返回 task.data，可根据状态过滤
        """
        # 返回整个 data 作为输入
        return task.data

    def _format_goal(self, goal: str, current_input: Dict[str, Any]) -> str:
        """格式化目标描述"""
        parts = [f"目标: {goal}"]

        if current_input:
            parts.append(f"\n当前数据:")
            for key, value in current_input.items():
                if isinstance(value, (str, int, float, bool)):
                    parts.append(f"  {key}: {value}")
                elif isinstance(value, list) and len(value) <= 3:
                    parts.append(f"  {key}: {value}")

        return "\n".join(parts)


# 模块级单例
context_assembler = ContextAssembler()

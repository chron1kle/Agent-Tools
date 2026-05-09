"""
Rewriting Tool - MCP 测试工具

功能：
- State 1 (rewriting): 接收用户指令，通过 LLM 以另一种方式/口吻/角度重新表达
- State 2 (executing): 将新指令发给 LLM 执行，得到执行结果
- 返回: rewritten_instruction + execution_result

这是一个状态机工具，内部管理自己的状态流转。
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from base_engine import (
    Task, TaskFactory, TaskIDGenerator,
    LLMClient, CallOptions, llm_client,
    logger,
)
from base_engine.engine import JudgmentManual, TransitionDecider, TransitionResult
from base_engine.engine import TransitionRule, ErrorHandler
from tool_adapter import ToolAdapter, ToolResult


# ─── 状态定义 ───

class RewritingState:
    """重写工具状态"""
    IDLE = "idle"
    REWRITING = "rewriting"      # 正在重写指令
    EXECUTING = "executing"      # 正在执行指令
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败


# ─── 判断手册 ───

rewriting_manual = JudgmentManual()


def setup_rewriting_manual():
    """设置重写工具的判断手册"""

    # 正常流转
    rewriting_manual.add_rule(TransitionRule(
        from_state=RewritingState.IDLE,
        event="start",
        to_state=RewritingState.REWRITING,
    ))
    rewriting_manual.add_rule(TransitionRule(
        from_state=RewritingState.REWRITING,
        event="done",
        to_state=RewritingState.EXECUTING,
    ))
    rewriting_manual.add_rule(TransitionRule(
        from_state=RewritingState.EXECUTING,
        event="done",
        to_state=RewritingState.COMPLETED,
    ))

    # 错误流转
    rewriting_manual.add_rule(TransitionRule(
        from_state=RewritingState.REWRITING,
        event="error",
        to_state=RewritingState.FAILED,
    ))
    rewriting_manual.add_rule(TransitionRule(
        from_state=RewritingState.EXECUTING,
        event="error",
        to_state=RewritingState.FAILED,
    ))

    # 异常处理
    rewriting_manual.add_error_handler(ErrorHandler(
        state=RewritingState.REWRITING,
        exception_type="*",
        strategy="abort",
        max_attempts=0,
    ))
    rewriting_manual.add_error_handler(ErrorHandler(
        state=RewritingState.EXECUTING,
        exception_type="*",
        strategy="abort",
        max_attempts=0,
    ))


setup_rewriting_manual()


# ─── LLM Prompt ───

REWRITE_SYSTEM_PROMPT = """你是一个指令改写专家。你的任务是将用户给出的指令以不同的方式、口吻、角度重新表达。

要求：
1. 保持原指令的核心意图不变
2. 改变表达方式、口吻或角度（如：正式->口语化、简略->详细、第一人称->第三人称等）
3. 输出只包含改写后的指令，不要有其他解释
"""

EXECUTE_SYSTEM_PROMPT = """你是一个任务执行助手。你需要执行用户给出的指令，并返回执行结果。

要求：
1. 认真理解指令内容
2. 提供详细、有用的执行结果
3. 如果指令不明确，说明需要什么信息才能执行
4. 输出只包含执行结果，不要有其他解释
"""


# ─── 工具适配器 ───

class RewritingToolAdapter(ToolAdapter):
    """重写工具适配器

    这是一个状态机工具，内部管理重写和执行两个状态。
    """

    name = "rewriting_tool"
    version = "1.0"

    def __init__(
        self,
        llm_client: LLMClient = None,
        rewrite_model: str = "general",
        execute_model: str = "general",
    ):
        super().__init__()
        self.llm_client = llm_client
        self.rewrite_model = rewrite_model
        self.execute_model = execute_model
        self.decider = TransitionDecider(rewriting_manual)

    async def execute(self, inputs: Dict[str, Any]) -> ToolResult:
        """执行工具

        Args:
            inputs: 包含 user_instruction 的字典

        Returns:
            ToolResult: 包含 rewritten_instruction 和 execution_result
        """
        user_instruction = inputs.get("user_instruction", "")

        if not user_instruction:
            return ToolResult(
                success=False,
                output={},
                error="Missing required input: user_instruction",
            )

        # 创建内部任务对象来管理状态
        task = Task(
            id=TaskIDGenerator.generate(),
            tool_id=self.name,
            created_at=int(asyncio.get_event_loop().time() * 1000),
            state=RewritingState.IDLE,
        )

        try:
            # 记录日志
            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="tool_start",
                timestamp=task.created_at,
                input=user_instruction,
            )

            # ─── State 1: Rewriting ───
            task.state = RewritingState.REWRITING
            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="state_enter",
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                state=RewritingState.REWRITING,
            )

            rewritten_instruction = await self._rewrite_instruction(user_instruction)

            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="state_exit",
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                state=RewritingState.REWRITING,
                result=rewritten_instruction,
            )

            # ─── State 2: Executing ───
            task.state = RewritingState.EXECUTING
            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="state_enter",
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                state=RewritingState.EXECUTING,
            )

            execution_result = await self._execute_instruction(rewritten_instruction)

            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="state_exit",
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                state=RewritingState.EXECUTING,
                result=execution_result,
            )

            # ─── 完成 ───
            task.state = RewritingState.COMPLETED
            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="tool_complete",
                timestamp=int(asyncio.get_event_loop().time() * 1000),
            )

            return ToolResult(
                success=True,
                output={
                    "original_instruction": user_instruction,
                    "rewritten_instruction": rewritten_instruction,
                    "execution_result": execution_result,
                },
            )

        except Exception as e:
            logger.enqueue(
                log_dir="./logs",
                task_id=task.id,
                event="tool_error",
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                error=str(e),
            )

            return ToolResult(
                success=False,
                output={},
                error=str(e),
            )

    async def _rewrite_instruction(self, instruction: str) -> str:
        """调用 LLM 重写指令"""
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": f"请将以下指令以不同的方式重新表达：\n\n{instruction}"},
        ]

        opts = CallOptions(
            model_type=self.rewrite_model,
            max_retries=2,
            temperature=0.8,
        )

        response = await self.llm_client.chat(messages, opts)
        return response.content.strip()

    async def _execute_instruction(self, instruction: str) -> str:
        """调用 LLM 执行指令"""
        messages = [
            {"role": "system", "content": EXECUTE_SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]

        opts = CallOptions(
            model_type=self.execute_model,
            max_retries=2,
            temperature=0.7,
        )

        response = await self.llm_client.chat(messages, opts)
        return response.content.strip()

    async def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """验证输入"""
        return "user_instruction" in inputs and bool(inputs["user_instruction"])

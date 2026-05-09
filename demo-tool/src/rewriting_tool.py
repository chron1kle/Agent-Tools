"""
指令重写与执行工具

配置驱动：通过 config.json 定义工具行为（状态、提示词、模型）
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, Optional

# 路径：demo-tool/src/ -> project_root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, os.path.join(project_root, "base_engine"))
sys.path.insert(0, os.path.join(project_root, "engine", "src"))


@dataclass
class StateConfig:
    """状态配置"""
    description: str
    system_prompt: Optional[str] = None
    transition_to: Optional[str] = None
    on_start: Optional[str] = None


class ConfigDrivenTool:
    """配置驱动的工具基类"""

    def __init__(self, config_path: str, llm_client=None):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.description = self.config.get("description", "")
        self.model_type = self.config.get("model_type", "general")
        self.states: Dict[str, StateConfig] = {}

        # 解析状态配置
        states_config = self.config.get("states", {})
        for state_name, state_data in states_config.items():
            self.states[state_name] = StateConfig(
                description=state_data.get("description", ""),
                system_prompt=state_data.get("system_prompt"),
                transition_to=state_data.get("transition_to"),
                on_start=state_data.get("on_start"),
            )

        # LLM 客户端
        if llm_client is None:
            from llm import llm_client as _llm_client, CallOptions
            self.llm_client = _llm_client
            self.CallOptions = CallOptions
        else:
            self.llm_client = llm_client

        # 加载模型配置
        self._load_model_config()

    def _load_model_config(self):
        """从 engine/config.json 加载模型配置"""
        engine_config_path = os.path.join(project_root, "engine", "config.json")
        if os.path.exists(engine_config_path):
            with open(engine_config_path, "r", encoding="utf-8") as f:
                engine_config = json.load(f)
            llm_config = engine_config.get("llm", {})
            self.llm_client.load_config(llm_config)

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """调用 LLM"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        opts = self.CallOptions(
            model_type=self.model_type,
            max_retries=2,
            temperature=0.7,
        )

        response = await self.llm_client.chat(messages, opts)
        return response.content.strip()

    def _get_initial_state(self) -> str:
        """获取初始状态"""
        for state_name, state_config in self.states.items():
            if state_config.on_start:
                return state_config.on_start
        return "IDLE"


class RewritingTool(ConfigDrivenTool):
    """指令重写与执行工具"""

    name = "rewriting_tool"
    version = "1.0"

    async def execute(self, user_instruction: str) -> Dict[str, Any]:
        """执行工具

        Args:
            user_instruction: 用户输入的指令

        Returns:
            包含 original_instruction, rewritten_instruction, execution_result
        """
        if not user_instruction:
            return {
                "success": False,
                "output": {},
                "error": "Missing required input: user_instruction",
            }

        try:
            # 状态 1: 重写指令
            rewriting_state = self.states.get("REWRITING")
            if not rewriting_state or not rewriting_state.system_prompt:
                return {
                    "success": False,
                    "output": {},
                    "error": "REWRITING state not configured",
                }

            rewritten_instruction = await self._call_llm(
                rewriting_state.system_prompt,
                f"请将以下指令以不同的方式重新表达：\n\n{user_instruction}"
            )

            # 状态 2: 执行指令
            executing_state = self.states.get("EXECUTING")
            if not executing_state or not executing_state.system_prompt:
                return {
                    "success": False,
                    "output": {},
                    "error": "EXECUTING state not configured",
                }

            execution_result = await self._call_llm(
                executing_state.system_prompt,
                rewritten_instruction
            )

            return {
                "success": True,
                "output": {
                    "original_instruction": user_instruction,
                    "rewritten_instruction": rewritten_instruction,
                    "execution_result": execution_result,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "output": {},
                "error": str(e),
            }


# 便捷函数
async def run(user_instruction: str, config_path: str = None) -> Dict[str, Any]:
    """运行工具"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")

    tool = RewritingTool(config_path)
    return await tool.execute(user_instruction)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="指令重写与执行工具")
    parser.add_argument("--input", "-i", help="输入指令")
    parser.add_argument("--config", "-c", help="配置文件路径")
    args = parser.parse_args()

    instruction = args.input or "帮我写一封请假邮件，因为今天身体不舒服"

    result = asyncio.run(run(instruction, args.config))

    if result["success"]:
        print("=" * 60)
        print("原始指令:", result["output"]["original_instruction"])
        print("-" * 60)
        print("重新表达:", result["output"]["rewritten_instruction"])
        print("-" * 60)
        print("执行结果:", result["output"]["execution_result"])
        print("=" * 60)
    else:
        print(f"执行失败: {result['error']}")

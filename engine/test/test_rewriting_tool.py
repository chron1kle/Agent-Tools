"""
Rewriting Tool 测试脚本

使用说明：
1. 设置环境变量 OPENAI_API_KEY（或其他 provider 的 key）
2. 运行脚本

示例：
    export OPENAI_API_KEY=sk-xxx
    python test_rewriting_tool.py
"""

import asyncio
import json
import os
import sys

# Add paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, os.path.join(project_root, "base_engine"))
sys.path.insert(0, os.path.join(project_root, "engine", "src"))

from rewriting_tool import RewritingToolAdapter
from tool_adapter import ToolResult
from llm import llm_client


def load_engine_config():
    """加载 engine/config.json 并初始化 llm_client"""
    config_path = os.path.join(project_root, "engine", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    # 加载 LLM 配置到全局 llm_client
    llm_config = config.get("llm", {})
    llm_client.load_config(llm_config)
    print(f"[配置加载] 已注册 models: {list(llm_client.registry._models.keys())}")


async def main():
    print("=" * 60)
    print("Rewriting Tool MCP Test")
    print("=" * 60)

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nERROR: Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        print("\nExample:")
        print("  export OPENAI_API_KEY=sk-xxx")
        print("  python test/test_rewriting_tool.py")
        return

    # 加载配置文件
    print("\n[初始化] 加载配置文件...")
    load_engine_config()

    # Create tool adapter
    tool = RewritingToolAdapter()

    # Test instruction
    test_instruction = input("\n请输入一个指令（直接回车使用默认测试指令）: ").strip()
    if not test_instruction:
        test_instruction = "帮我写一封请假邮件，因为今天身体不舒服"

    print(f"\n原始指令: {test_instruction}")
    print("\n正在处理...\n")

    # Execute
    result: ToolResult = await tool.execute({
        "user_instruction": test_instruction
    })

    # Output
    if result.success:
        print("=" * 60)
        print("结果")
        print("=" * 60)
        print(f"\n[原始指令]\n{result.output.get('original_instruction', '')}")
        print(f"\n[重新表达后的指令]\n{result.output.get('rewritten_instruction', '')}")
        print(f"\n[执行结果]\n{result.output.get('execution_result', '')}")
        print("\n" + "=" * 60)
    else:
        print(f"\n执行失败: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())

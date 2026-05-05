"""
{{TOOL_NAME}} - 统一入口
{{ONE_LINE_DESCRIPTION}}

============================================
使用前请阅读：
============================================
1. 在 src/ 目录下创建你的实现文件（见下方列表）
2. 编辑本文件顶部的 {{TOOL_NAME}} 和 {{ONE_LINE_DESCRIPTION}} 占位符
3. 根据需要修改 LANGUAGE_PRIORITY 和 LANGUAGE_ENTRY
4. 编辑 TOOL_SCHEMA 中的 inputSchema，定义 MCP 暴露的参数
5. 编辑 TOOL_CLASS 指向你的工具类

支持的实现文件：
  - Python: 创建 main.py
  - Node.js: 创建 index.js
  - Go: 创建 main.go（需编译为可执行文件）
  - Rust: 创建 main（需编译为可执行文件）

调用方式：
  # MCP 模式（强烈推荐 - 生产环境使用）
  python -m {{TOOL_NAME}}.src --mcp

  # 生命周期管理
  python -m {{TOOL_NAME}}.src --start    # 启动工具进程
  python -m {{TOOL_NAME}}.src --stop     # 停止工具进程
  python -m {{TOOL_NAME}}.src --status   # 查询状态
============================================
"""

import sys
import os
import subprocess
import argparse
import json
import signal
import time
import threading
import asyncio
from pathlib import Path
from typing import Optional, List

# ============ 配置加载 ============

# 获取工具根目录
TOOL_ROOT = Path(__file__).parent.parent.resolve()

# 添加公共组件路径
AGENT_TOOLS_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(AGENT_TOOLS_ROOT))

# 加载配置到环境变量
try:
    from common.conf_env_reg.python import setup_env_from_config

    config_path = TOOL_ROOT / "config.json"
    if config_path.exists():
        setup_env_from_config(str(config_path), prefix="{{TOOL_NAME|upper}}")
except ImportError:
    # 如果没有 conf-env-reg 组件，跳过自动配置加载
    pass

# ============ 语言实现配置 ============
# TODO: 根据你的工具支持的编程语言，修改以下配置

# 语言优先级（按顺序检测，排在前的优先）
LANGUAGE_PRIORITY = [
    "python",
    # "nodejs",  # 取消注释以启用
    # "go",       # 取消注释以启用
    # "rust",    # 取消注释以启用
]

# 各语言对应的入口文件（相对于 src/ 目录）
# TODO: 确保你创建的文件名与这里配置的一致
LANGUAGE_ENTRY = {
    "python": "main.py",      # 必须创建此文件
    "nodejs": "index.js",    # 可选：创建此文件以启用 Node.js
    "go": "main.go",         # 可选：需编译为可执行文件
    "rust": "main",          # 可选：需编译为可执行文件
}

# ============ MCP 配置 ============
# TODO: 修改此 schema 定义 MCP 暴露的参数
# LLM 将根据此 schema 知道如何调用工具

TOOL_SCHEMA = {
    "name": "run",
    "description": "{{ONE_LINE_DESCRIPTION}}",
    "inputSchema": {
        "type": "object",
        "properties": {
            "input": {
                "type": "string",
                "description": "输入文件路径"
            },
            "output": {
                "type": "string",
                "description": "输出目录"
            },
            "mode": {
                "type": "string",
                "enum": ["convert", "extract"],
                "description": "运行模式"
            }
        },
        "required": ["input"]
    }
}

# ============ 任务队列 ============

# 使用通用任务队列组件
try:
    from common.task_queue.python import TaskQueue, get_queue_config

    # 从环境变量读取配置
    task_config = get_queue_config("{{TOOL_NAME|upper}}")
    task_queue = TaskQueue(config=task_config)
except ImportError:
    # 如果没有通用组件，设为 None
    task_queue = None

# ============ 工具类 ============
# TODO: 定义你的工具类，用于单例模式
# 示例：
# class MyTool:
#     def __init__(self):
#         self.running = False
#     def start(self):
#         self.running = True
#     def stop(self):
#         self.running = False
#     def execute(self, args):
#         return {"result": "done"}

class ToolPlaceholder:
    """占位符工具类 - 请替换为你的实现"""
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True
        print("Tool started")

    def stop(self):
        self.running = False
        print("Tool stopped")

    def status(self) -> dict:
        return {"running": self.running}

    def execute(self, args: List[str]) -> dict:
        print(f"Executing: {args}")
        return {"result": "success", "args": args}

# TODO: 替换为你的工具类
TOOL_CLASS = ToolPlaceholder

# ============ 工具管理器（单例） ============

class ToolManager:
    """
    工具生命周期管理器

    使用单例模式确保只有一个工具实例运行。
    Claude 可以通过 MCP 调用来管理工具生命周期。
    """
    _instance = None
    _tool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tool = TOOL_CLASS()
        return cls._instance

    @classmethod
    def start(cls):
        if cls._tool is None:
            cls._tool = TOOL_CLASS()
        cls._tool.start()
        return {"status": "started"}

    @classmethod
    def stop(cls):
        if cls._tool:
            cls._tool.stop()
        return {"status": "stopped"}

    @classmethod
    def status(cls) -> dict:
        if cls._tool:
            return cls._tool.status()
        return {"running": False}

    @classmethod
    def execute(cls, args: List[str]) -> dict:
        if cls._tool is None:
            cls._tool = TOOL_CLASS()
        return cls._tool.execute(args)

    @classmethod
    def restart(cls):
        cls.stop()
        time.sleep(0.5)
        cls.start()
        return {"status": "restarted"}


# ============ 核心功能 ============

def get_implementation() -> Optional[str]:
    src_dir = Path(__file__).parent
    for lang in LANGUAGE_PRIORITY:
        entry_file = src_dir / LANGUAGE_ENTRY[lang]
        if entry_file.exists():
            return lang
    print(f"Error: No implementation found in src/", file=sys.stderr)
    return None


def run_command(lang: str, args: List[str]) -> int:
    src_dir = Path(__file__).parent
    entry_file = src_dir / LANGUAGE_ENTRY[lang]
    if lang == "python":
        cmd = [sys.executable, str(entry_file)] + args
        return subprocess.call(cmd, cwd=str(src_dir))
    elif lang == "nodejs":
        cmd = ["node", str(entry_file)] + args
        return subprocess.call(cmd, cwd=str(src_dir))
    elif lang == "go":
        return subprocess.call([str(entry_file)] + args, cwd=str(src_dir))
    elif lang == "rust":
        return subprocess.call([str(entry_file)] + args, cwd=str(src_dir))
    else:
        raise ValueError(f"Unsupported language: {lang}")


def run(*args, lang: Optional[str] = None, config_path: Optional[str] = None):
    if lang is None:
        lang = get_implementation()
        if lang is None:
            return 1
    args_list = list(args) if args else []
    return run_command(lang, args_list)


def _convert_mcp_args(mcp_args: dict) -> List[str]:
    args = []
    for key, value in mcp_args.items():
        if value is not None:
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            else:
                args.extend([f"--{key}", str(value)])
    return args


# ============ MCP Server ============

def create_mcp_server():
    try:
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        from mcp.server.stdio import stdio_server
        import asyncio
    except ImportError:
        print("Error: mcp package not installed", file=sys.stderr)
        print("Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    app = Server("{{TOOL_NAME}}")

    @app.list_tools()
    async def list_tools():
        return [
            Tool(
                name=TOOL_SCHEMA["name"],
                description=TOOL_SCHEMA["description"],
                inputSchema=TOOL_SCHEMA["inputSchema"]
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "run":
            # 生命周期管理
            if arguments.get("_action") == "start":
                result = ToolManager.start()
                return [TextContent(type="text", json.dumps(result))]
            elif arguments.get("_action") == "stop":
                result = ToolManager.stop()
                return [TextContent(type="text", json.dumps(result))]
            elif arguments.get("_action") == "status":
                result = ToolManager.status()
                return [TextContent(type="text", json.dumps(result))]
            elif arguments.get("_action") == "restart":
                result = ToolManager.restart()
                return [TextContent(type="text", json.dumps(result))]
            elif arguments.get("_action") == "tasks":
                # 列出所有任务
                if task_queue:
                    tasks = await task_queue.list_tasks()
                    result = {"tasks": [t.to_dict() for t in tasks]}
                else:
                    result = {"tasks": []}
                return [TextContent(type="text", json.dumps(result))]
            else:
                cli_args = _convert_mcp_args(arguments)
                result = ToolManager.execute(cli_args)
                return [TextContent(type="text", json.dumps(result))]
        raise ValueError(f"Unknown tool: {name}")

    return app, stdio_server


async def run_mcp_server():
    app, stdio_server = create_mcp_server()

    # 添加进度日志回调
    if task_queue:
        async def progress_callback(task):
            print(json.dumps({
                "type": "progress",
                "task_id": task.id,
                "progress": task.progress,
                "message": task.message
            }))
        task_queue.add_progress_callback(progress_callback)

    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )


def main():
    parser = argparse.ArgumentParser(description="{{TOOL_NAME}} - {{ONE_LINE_DESCRIPTION}}")

    parser.add_argument("--start", action="store_true", help="启动工具进程")
    parser.add_argument("--stop", action="store_true", help="停止工具进程")
    parser.add_argument("--status", action="store_true", help="查询工具状态")
    parser.add_argument("--restart", action="store_true", help="重启工具进程")

    parser.add_argument("--mcp", action="store_true", help="启动 MCP 服务器模式")
    parser.add_argument("--lang", "-l", choices=LANGUAGE_PRIORITY, help="指定实现语言")
    parser.add_argument("--config", "-c", help="指定配置文件路径")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="传递给底层实现的参数")

    parsed = parser.parse_args()

    if parsed.start:
        result = ToolManager.start()
        print(json.dumps(result))
        return

    if parsed.stop:
        result = ToolManager.stop()
        print(json.dumps(result))
        return

    if parsed.status:
        result = ToolManager.status()
        print(json.dumps(result, indent=2))
        return

    if parsed.restart:
        result = ToolManager.restart()
        print(json.dumps(result))
        return

    if parsed.mcp:
        import asyncio
        asyncio.run(run_mcp_server())
        return

    exit_code = run(*parsed.args, lang=parsed.lang, config_path=parsed.config)
    sys.exit(exit_code)


__all__ = ["run", "main", "get_implementation", "ToolManager"]

"""
pdf2epub - 统一入口
PDF 转 EPUB 工具，支持 OCR 纠错和 LLM 校正

============================================
使用说明：
============================================
1. 本工具支持 Python 实现
2. 使用前请确保已安装依赖：pip install -r requirements.txt

调用方式：
  # 生命周期管理
  python -m pdf2epub.src --start    # 启动工具进程
  python -m pdf2epub.src --stop     # 停止工具进程
  python -m pdf2epub.src --status   # 查询状态
  python -m pdf2epub.src --restart  # 重启工具进程

  # MCP 模式（强烈推荐 - 生产环境使用）
  python -m pdf2epub.src --mcp

  # 普通模式（仅开发调试用）
  python -m pdf2epub.src input.pdf --output out/
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
        setup_env_from_config(str(config_path), prefix="PDF2EPUB")
except ImportError:
    pass

# ============ 语言实现配置 ============

LANGUAGE_PRIORITY = ["python"]

LANGUAGE_ENTRY = {
    "python": "pdf2epub.py",
}

# ============ MCP 配置 ============

TOOL_SCHEMA = {
    "name": "run",
    "description": "将 PDF 文件转换为 EPUB 格式，支持 OCR 纠错和 LLM 校正",
    "inputSchema": {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "输入 PDF 文件路径"},
            "output": {"type": "string", "description": "输出目录"},
            "title": {"type": "string", "description": "书籍标题"},
            "author": {"type": "string", "description": "书籍作者"},
            "no_correction": {"type": "boolean", "description": "跳过 OCR 纠错"},
            "no_page_markers": {"type": "boolean", "description": "不添加页码标注"},
            "use_llm": {"type": "boolean", "description": "使用 LLM 校正"},
            "llm_provider": {"type": "string", "enum": ["anthropic", "ollama"], "description": "LLM 提供商"},
            "llm_model": {"type": "string", "description": "LLM 模型名称"},
            "step": {"type": "string", "enum": ["1", "2", "3"], "description": "执行步骤"}
        },
        "required": ["input"]
    }
}

# ============ 任务队列 ============

# 使用通用任务队列组件
try:
    from common.task_queue.python import TaskQueue, get_queue_config, Task, TaskStatus

    # 从环境变量读取配置
    task_config = get_queue_config("PDF2EPUB")
    task_queue = TaskQueue(config=task_config)
except ImportError:
    # 如果没有通用组件，使用简化版本
    task_queue = None


# ============ 工具类 ============

class PDF2EPUBTool:
    """PDF2EPUB 工具类"""

    def __init__(self):
        self.running = False
        self.process = None

    def start(self):
        """启动工具"""
        self.running = True
        print("PDF2EPUB tool started")

    def stop(self):
        """停止工具"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process = None
        print("PDF2EPUB tool stopped")

    def status(self) -> dict:
        """查询状态"""
        return {"running": self.running}

    def execute(self, args: List[str]) -> dict:
        """执行转换（同步）"""
        src_dir = Path(__file__).parent
        entry_file = src_dir / "pdf2epub.py"

        cmd = [sys.executable, str(entry_file)] + args
        result = subprocess.run(cmd, cwd=str(src_dir), capture_output=True, text=True)

        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    async def execute_async(self, args: List[str]) -> str:
        """异步执行转换 - 返回任务 ID"""
        if task_queue:
            return await task_queue.submit(args)
        else:
            # 简化版本：直接执行
            task_id = f"task_{int(time.time())}"
            return task_id


TOOL_CLASS = PDF2EPUBTool


# ============ 工具管理器（单例） ============

class ToolManager:
    """工具生命周期管理器"""
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
    async def execute_async(cls, args: List[str]) -> str:
        if cls._tool is None:
            cls._tool = TOOL_CLASS()
        return await cls._tool.execute_async(args)

    @classmethod
    def execute(cls, args: List[str]) -> dict:
        if cls._tool is None:
            cls._tool = TOOL_CLASS()
        return cls._tool.execute(args)

    @classmethod
    async def get_task_status(cls, task_id: str):
        if task_queue:
            return await task_queue.get_task(task_id)
        return None

    @classmethod
    async def list_tasks(cls):
        if task_queue:
            return await task_queue.list_tasks()
        return []

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
    return None


def run_command(lang: str, args: List[str]) -> int:
    src_dir = Path(__file__).parent
    entry_file = src_dir / LANGUAGE_ENTRY[lang]
    if lang == "python":
        cmd = [sys.executable, str(entry_file)] + args
        return subprocess.call(cmd, cwd=str(src_dir))
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
                    args.append(f"--{key.replace('_', '-')}")
            else:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
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

    app = Server("pdf2epub")

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
                tasks = await ToolManager.list_tasks()
                result = {
                    "tasks": [t.to_dict() for t in tasks]
                }
                return [TextContent(type="text", json.dumps(result))]
            elif arguments.get("_action") == "task_status":
                task_id = arguments.get("task_id")
                if not task_id:
                    return [TextContent(type="text", json.dumps({"error": "task_id required"}))]
                task = await ToolManager.get_task_status(task_id)
                if not task:
                    return [TextContent(type="text", json.dumps({"error": "task not found"}))]
                result = task.to_dict()
                return [TextContent(type="text", json.dumps(result))]
            else:
                # 异步执行任务
                cli_args = _convert_mcp_args(arguments)
                task_id = await ToolManager.execute_async(cli_args)
                return [TextContent(type="text", json.dumps({"task_id": task_id, "status": "submitted"}))]
        raise ValueError(f"Unknown tool: {name}")

    return app, stdio_server


async def run_mcp_server():
    app, stdio_server = create_mcp_server()

    # 添加进度日志回调
    async def progress_callback(task):
        print(json.dumps({
            "type": "progress",
            "task_id": task.id,
            "progress": task.progress,
            "message": task.message
        }))

    if task_queue:
        task_queue.add_progress_callback(progress_callback)

    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )


def main():
    parser = argparse.ArgumentParser(description="pdf2epub - PDF to EPUB Converter")

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

"""
Tool Adapter - 工具适配器基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ToolStatus(Enum):
    """工具状态"""
    STOPPED = "stopped"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    logs: str = ""


class ToolAdapter(ABC):
    """工具适配器基类"""

    name: str = "base_tool"
    version: str = "1.0"

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> ToolResult:
        """
        执行工具

        Args:
            inputs: 输入参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    async def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        验证输入

        Args:
            inputs: 输入参数

        Returns:
            bool: 是否有效
        """
        return True

    async def get_status(self) -> ToolStatus:
        """获取工具状态"""
        return ToolStatus.READY

    async def start(self):
        """启动工具"""
        pass

    async def stop(self):
        """停止工具"""
        pass

    async def get_capabilities(self) -> Dict[str, Any]:
        """获取工具能力"""
        return {}


class SubprocessToolAdapter(ToolAdapter):
    """子进程工具适配器 - 用于调用现有工具"""

    def __init__(self, name: str, command: list):
        self.name = name
        self.command = command
        self.process = None

    async def execute(self, inputs: Dict[str, Any]) -> ToolResult:
        import subprocess
        import asyncio

        # 构建命令
        cmd = self.command.copy()
        for key, value in inputs.items():
            if value is not None:
                cmd.extend([f"--{key}", str(value)])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            return ToolResult(
                success=process.returncode == 0,
                output={"stdout": stdout.decode(), "returncode": process.returncode},
                error=stderr.decode() if process.returncode != 0 else None,
                logs=stdout.decode()
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output={},
                error=str(e)
            )

    async def get_status(self) -> ToolStatus:
        return ToolStatus.READY

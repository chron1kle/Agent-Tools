"""
Tool Registry - 工具注册表
"""

from typing import Dict, Optional, Type
from .adapter import ToolAdapter, ToolStatus


class ToolRegistry:
    """
    工具注册表

    用于注册和管理工具适配器。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, name: str, adapter: ToolAdapter):
        """
        注册工具

        Args:
            name: 工具名称
            adapter: 工具适配器实例
        """
        self._tools[name] = adapter

    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[ToolAdapter]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, ToolAdapter]:
        """列出所有工具"""
        return self._tools.copy()

    def exists(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    async def start_all(self):
        """启动所有工具"""
        for tool in self._tools.values():
            try:
                await tool.start()
            except Exception as e:
                print(f"Failed to start tool {tool.name}: {e}")

    async def stop_all(self):
        """停止所有工具"""
        for tool in self._tools.values():
            try:
                await tool.stop()
            except Exception as e:
                print(f"Failed to stop tool {tool.name}: {e}")

    async def get_all_status(self) -> Dict[str, ToolStatus]:
        """获取所有工具状态"""
        result = {}
        for name, tool in self._tools.items():
            try:
                result[name] = await tool.get_status()
            except Exception:
                result[name] = ToolStatus.ERROR
        return result


# 全局注册表
registry = ToolRegistry()


def register_tool(name: str):
    """装饰器：注册工具"""
    def decorator(cls: Type[ToolAdapter]):
        registry.register(name, cls())
        return cls
    return decorator

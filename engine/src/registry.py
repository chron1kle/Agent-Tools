"""
Tool Registry - 工具注册表
"""

from typing import Dict, Optional, Type

from .tool_adapter import ToolAdapter, ToolStatus


class ToolRegistry:
    """工具注册表

    管理所有工具适配器。
    使用模块级单例模式。
    """

    def __init__(self):
        self._tools: Dict[str, ToolAdapter] = {}

    def register(self, name: str, adapter: ToolAdapter):
        """注册工具"""
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


# 模块级单例
tool_registry = ToolRegistry()


def register_tool(name: str):
    """装饰器：注册工具"""
    def decorator(cls: Type[ToolAdapter]):
        tool_registry.register(name, cls())
        return cls
    return decorator

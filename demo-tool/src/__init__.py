"""
demo-tool - 指令重写与执行工具

配置驱动工具示例：通过 config.json 定义状态机行为
"""

from .rewriting_tool import RewritingTool, run, ConfigDrivenTool

__all__ = ["RewritingTool", "run", "ConfigDrivenTool"]

"""
Config to Environment Registry
将 config.json 配置注册为环境变量的工具组件
"""

from .conf_env_reg import setup_env_from_config

__all__ = ["setup_env_from_config"]

"""Config to Environment Registry - 配置注册中心"""

import json
import os
from typing import Optional, Dict, Any


class ConfigRegistry:
    """配置注册中心

    将 config.json 配置扁平化注册为环境变量，提供统一的配置访问接口。
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._loaded = False

    def load(
        self,
        config_path: str = "config.json",
        prefix: str = "AGENT",
        verbose: bool = True,
    ) -> dict:
        """从 config.json 加载配置并注册为环境变量

        Args:
            config_path: config.json 文件路径
            prefix: 环境变量前缀，默认 "AGENT_"
            verbose: 是否打印加载信息

        Returns:
            加载的配置（用于调试）
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        except FileNotFoundError:
            if verbose:
                print(f"[Config] Config file not found: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            if verbose:
                print(f"[Config] Invalid JSON in {config_path}: {e}")
            return {}

        # 扁平化注册所有配置为环境变量
        def register_recursive(obj: dict, prefix_parts: list):
            count = 0
            for key, value in obj.items():
                env_key = prefix + "_".join(prefix_parts + [key.upper()])

                if isinstance(value, dict):
                    count += register_recursive(value, prefix_parts + [key])
                elif isinstance(value, bool):
                    os.environ[env_key] = str(value).lower()
                    count += 1
                elif isinstance(value, (int, float)):
                    os.environ[env_key] = str(value)
                    count += 1
                elif isinstance(value, str):
                    os.environ[env_key] = value
                    count += 1

                return count

        count = register_recursive(self._config, [])

        if verbose:
            print(f"[Config] Loaded {count} config values from {config_path}")
            print(f"[Config] Sections: {list(self._config.keys())}")

        self._loaded = True
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（从内存缓存）

        Args:
            key: 配置键名（支持嵌套格式，如 "engine.max_concurrent"）
            default: 默认值
        """
        if not self._loaded:
            return default

        # 支持嵌套 key
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default

        return value

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """读取配置值（从环境变量）

        Args:
            key: 配置键名（格式：SECTION_KEY 或 KEY）
            default: 默认值
        """
        return os.environ.get(key, default)

    def is_loaded(self) -> bool:
        """检查配置是否已加载"""
        return self._loaded


# 模块级单例
config_registry = ConfigRegistry()

"""
Config to Environment Registry
将 config.json 配置扁平化注册为环境变量
"""

import json
import os
from typing import Optional


def setup_env_from_config(
    config_path: str = "config.json",
    prefix: str = "AGENT",
    verbose: bool = True
) -> dict:
    """
    从 config.json 加载所有配置并注册为环境变量

    Args:
        config_path: config.json 文件路径（相对于当前工作目录）
        prefix: 环境变量前缀，默认 "AGENT_"
        verbose: 是否打印加载信息

    Returns:
        dict: 加载的配置（用于调试）
    """
    config = {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
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
                # 嵌套对象递归处理
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

    count = register_recursive(config, [])

    if verbose:
        print(f"[Config] Loaded {count} config values from {config_path}")
        print(f"[Config] Sections: {list(config.keys())}")

    return config


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    读取配置值（从环境变量）

    Args:
        key: 配置键名（格式：SECTION_KEY 或 KEY）
        default: 默认值

    Returns:
        str or None: 配置值
    """
    return os.environ.get(key, default)

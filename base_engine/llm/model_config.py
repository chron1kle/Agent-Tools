"""Model configuration system - 以 model_type 为索引的模型注册中心"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ModelConfig:
    """单个模型配置"""
    model_type: str           # 标识：text_rewrite / text_execute / anthropic_sonnet
    provider: str            # openai / anthropic / deepseek
    model_name: str         # 实际模型名
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: float = 60.0
    active: int = 1         # 0=禁用，1=启用


class ConfigLoader:
    """配置加载器，支持环境变量替换"""

    @staticmethod
    def substitute_env_vars(value: Any) -> Any:
        """替换 ${ENV_VAR} 格式的环境变量"""
        if isinstance(value, str):
            # 匹配 ${VAR_NAME} 格式
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for match in matches:
                env_value = os.environ.get(match, "")
                value = value.replace(f"${{{match}}}", env_value)
            return value
        elif isinstance(value, dict):
            return {k: ConfigLoader.substitute_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [ConfigLoader.substitute_env_vars(item) for item in value]
        return value


class ModelRegistry:
    """模型注册中心"""

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}

    def load_from_dict(self, config: Dict[str, Any]):
        """从字典加载配置（model-centric 结构）

        Args:
            config: 配置字典，包含 model_types（不再区分 providers/models）
        """
        # 加载 model_types（model-centric: 每个模型自己包含 provider、api_key 等）
        model_types_config = config.get("model_types", {})
        for model_type, model_data in model_types_config.items():
            # 替换环境变量
            model_data = ConfigLoader.substitute_env_vars(model_data)
            self._models[model_type] = ModelConfig(
                model_type=model_type,
                provider=model_data.get("provider", ""),
                model_name=model_data.get("model_name", ""),
                api_key=model_data.get("api_key"),
                base_url=model_data.get("base_url"),
                max_tokens=model_data.get("max_tokens", 8192),
                temperature=model_data.get("temperature", 0.7),
                timeout=model_data.get("timeout", 60.0),
                active=model_data.get("active", 0),
            )

    def set_default_api_key(self, api_key: str):
        """设置全局默认 API key（向后兼容）"""
        for model in self._models.values():
            if not model.api_key:
                model.api_key = api_key

    def register(self, model_type: str, config: ModelConfig):
        """注册模型"""
        self._models[model_type] = config

    def resolve(self, model_type: str) -> ModelConfig:
        """解析模型配置"""
        config = self._models.get(model_type)
        if not config:
            raise ValueError(f"Unknown model_type: {model_type}")
        if not config.active:
            raise ValueError(f"model_type [{model_type}] is disabled (active=0)")
        return config

    def get(self, model_type: str) -> Optional[ModelConfig]:
        """获取模型配置（不合并默认 api_key）"""
        return self._models.get(model_type)


# 模块级单例
model_registry = ModelRegistry()

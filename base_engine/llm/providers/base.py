"""LLM Provider 接口定义"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from llm.model_config import ModelConfig


class BaseProvider(ABC):
    """LLM Provider 基类"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        **kwargs,
    ) -> "LLMResponse":
        """调用 LLM API

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            config: 模型配置
            **kwargs: 其他参数

        Returns:
            LLMResponse: 响应对象
        """
        pass

    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass


class LLMResponse:
    """LLM 响应"""

    def __init__(
        self,
        content: str,
        model: str,
        usage: Dict[str, int] = None,
        raw: Dict[str, Any] = None,
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.raw = raw or {}

    def __repr__(self):
        return f"LLMResponse(content={self.content[:50]}..., model={self.model})"

"""OpenAI API Provider"""

import httpx
from typing import List, Dict, Any

from .base import BaseProvider, LLMResponse
from llm.model_config import ModelConfig


class OpenAIProvider(BaseProvider):
    """OpenAI API Provider"""

    def __init__(self):
        self._client: httpx.AsyncClient = None

    def _get_client(self, config: ModelConfig) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=config.base_url or "https://api.openai.com/v1",
                timeout=config.timeout or 60.0,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        **kwargs,
    ) -> LLMResponse:
        """调用 OpenAI Chat API"""
        client = self._get_client(config)

        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
        }

        # 添加可选参数
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stream" in kwargs:
            payload["stream"] = kwargs["stream"]

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
                raw=data,
            )
        except httpx.HTTPStatusError as e:
            raise Exception(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

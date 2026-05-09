"""Anthropic API Provider"""

import httpx
from typing import List, Dict, Any

from .base import BaseProvider, LLMResponse
from llm.model_config import ModelConfig


class AnthropicProvider(BaseProvider):
    """Anthropic API Provider"""

    def __init__(self):
        self._client: httpx.AsyncClient = None

    def _get_client(self, config: ModelConfig) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=config.base_url or "https://api.anthropic.com",
                timeout=config.timeout or 60.0,
                headers={
                    "x-api-key": config.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
            )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        **kwargs,
    ) -> LLMResponse:
        """调用 Anthropic Messages API"""
        client = self._get_client(config)

        # Anthropic 使用不同的消息格式
        # 需要将 role 转换为 anthropic 格式
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                anthropic_messages.append({
                    "role": "user",
                    "content": f"<system>{msg['content']}</system>"
                })
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        payload = {
            "model": config.model_name,
            "messages": anthropic_messages,
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens) or 8192,
        }

        try:
            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()
            data = response.json()

            # 提取文本内容（兼容标准 Anthropic 和第三方代理格式）
            content = data.get("content", [])
            text_content = ""
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content = block.get("text", "")
                    break
                elif isinstance(block, dict) and block.get("type") == "thinking":
                    # 跳过 thinking 块
                    continue

            return LLMResponse(
                content=text_content,
                model=data.get("model", config.model_name),
                usage={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
                raw=data,
            )
        except httpx.HTTPStatusError as e:
            raise Exception(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

"""LLM API client - LLM API 调用封装，含重试策略"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from llm.model_config import ModelRegistry, model_registry
from llm.providers import OpenAIProvider, AnthropicProvider, BaseProvider


@dataclass
class CallOptions:
    """调用选项"""
    model_type: Optional[str] = None     # 模型类型
    max_retries: int = 3
    auto_truncate: bool = True            # 上下文超限时自动截断
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)                 # token 使用量
    raw: Dict[str, Any] = field(default_factory=dict)                   # 原始响应


class LLMError(Exception):
    """LLM 错误基类"""
    pass


class ContextWindowError(LLMError):
    """上下文超限"""
    pass


class RateLimitError(LLMError):
    """速率限制"""
    pass


class NetworkError(LLMError):
    """网络错误"""
    pass


class ServerError(LLMError):
    """服务器错误"""
    pass


class AuthError(LLMError):
    """认证错误"""
    pass


class InvalidRequestError(LLMError):
    """无效请求"""
    pass


class LLMClient:
    """LLM API 组件"""

    def __init__(self, registry: ModelRegistry = None):
        self.registry = registry or model_registry
        self.providers: Dict[str, BaseProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        """注册默认 provider"""
        self.providers["openai"] = OpenAIProvider()
        self.providers["anthropic"] = AnthropicProvider()
        # 其他 provider 可按需注册

    def register_provider(self, name: str, provider: BaseProvider):
        """注册 provider"""
        self.providers[name] = provider

    def load_config(self, config: Dict[str, Any]):
        """从配置加载

        Args:
            config: 包含 providers 和 models 的配置字典
        """
        self.registry.load_from_dict(config)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        opts: CallOptions,
    ) -> LLMResponse:
        """调用 LLM API"""

        # 1. 解析模型配置
        model_type = opts.model_type or "default"
        config = self.registry.resolve(model_type)

        # 2. 获取 provider
        provider = self.providers.get(config.provider)
        if not provider:
            raise LLMError(f"Unknown provider: {config.provider}")

        # 3. 重试循环
        attempt = 0
        last_error = None

        while attempt < opts.max_retries:
            try:
                response = await provider.chat(
                    messages,
                    config,
                    temperature=opts.temperature or config.temperature,
                    max_tokens=opts.max_tokens or config.max_tokens,
                )
                return response

            except ContextWindowError as e:
                if opts.auto_truncate and attempt < opts.max_retries - 1:
                    messages = self._truncate_messages(messages)
                    attempt += 1
                else:
                    raise

            except RateLimitError as e:
                wait_time = self._calculate_backoff(attempt)
                await asyncio.sleep(wait_time)
                attempt += 1
                last_error = e

            except NetworkError as e:
                wait_time = self._calculate_backoff(attempt)
                await asyncio.sleep(wait_time)
                attempt += 1
                last_error = e

            except ServerError as e:
                wait_time = self._calculate_backoff(attempt)
                await asyncio.sleep(wait_time)
                attempt += 1
                last_error = e

            except Exception as e:
                # 其他错误（如认证错误）直接失败
                error_str = str(e).lower()
                if "auth" in error_str or "401" in error_str or "403" in error_str:
                    raise AuthError(str(e))
                elif "400" in error_str or "invalid" in error_str:
                    raise InvalidRequestError(str(e))
                else:
                    wait_time = self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    attempt += 1
                    last_error = e

        raise last_error

    def _truncate_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """截断消息列表（保留 system 和最后一条 user）"""
        if len(messages) <= 2:
            return messages

        system = [m for m in messages if m.get("role") == "system"]
        others = [m for m in messages if m.get("role") != "system"]

        # 保留 system + 最后一条 user
        result = system + others[-1:]
        return result

    def _calculate_backoff(self, attempt: int) -> float:
        """计算退避时间"""
        return min(2 ** attempt + 0.1, 30.0)

    async def close(self):
        """关闭所有 provider 连接"""
        for provider in self.providers.values():
            await provider.close()


# 模块级单例
llm_client = LLMClient()

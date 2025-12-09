"""模块名称: llm
主要功能: LLM 客户端实现

提供 OpenAI 兼容的 LLM 客户端，支持多提供商和自动故障转移。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 数据结构 ====================

@dataclass
class LLMConfig:
    """LLM 配置

    Attributes:
        provider: 提供商名称
        model: 模型名称
        base_url: API 基础 URL
        api_key: API 密钥
    """
    provider: str
    model: str
    base_url: str
    api_key: str


@dataclass
class LLMResponse:
    """LLM 响应结构

    Attributes:
        content: 响应文本内容
        tool_calls: 工具调用列表 (如果有)
        finish_reason: 完成原因
        usage: Token 使用统计
    """
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)


# ==================== LLM 客户端 ====================

class LLMClient:
    """OpenAI 兼容的 LLM 客户端

    支持多提供商配置和自动故障转移。

    Attributes:
        _primary_config: 主提供商配置
        _fallback_config: 备用提供商配置
    """

    def __init__(self):
        """初始化 LLM 客户端"""
        # 主提供商配置
        self._primary_config = LLMConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
        )

        # 备用提供商配置
        self._fallback_config = LLMConfig(
            provider=config.llm_fallback_provider,
            model=config.llm_fallback_model,
            base_url=config.llm_fallback_base_url,
            api_key=config.llm_fallback_api_key,
        )

        # 初始化客户端
        self._primary_client = self._create_client(self._primary_config)
        self._fallback_client = self._create_client(self._fallback_config)

        logger.info(
            f"LLM 客户端已初始化: {self._primary_config.provider}/{self._primary_config.model}"
        )

    def _create_client(self, cfg: LLMConfig) -> AsyncOpenAI:
        """创建 OpenAI 客户端

        Args:
            cfg: LLM 配置

        Returns:
            AsyncOpenAI: 异步 OpenAI 客户端
        """
        return AsyncOpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
        )

    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """发送聊天请求

        Args:
            messages: 消息列表
            tools: 工具定义列表
            tool_choice: 工具选择策略
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            LLMResponse: LLM 响应
        """
        # 尝试主提供商
        try:
            return await self._call_completion(
                self._primary_client,
                self._primary_config,
                messages,
                tools,
                tool_choice,
                temperature,
                max_tokens,
            )
        except Exception as e:
            logger.warning(
                f"主提供商调用失败: {self._primary_config.provider}, 错误: {e}"
            )

            # 尝试备用提供商
            if self._fallback_config.api_key:
                logger.info(f"切换到备用提供商: {self._fallback_config.provider}")
                return await self._call_completion(
                    self._fallback_client,
                    self._fallback_config,
                    messages,
                    tools,
                    tool_choice,
                    temperature,
                    max_tokens,
                )
            raise

    async def _call_completion(
        self,
        client: AsyncOpenAI,
        cfg: LLMConfig,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """调用 LLM API

        Args:
            client: OpenAI 客户端
            cfg: LLM 配置
            messages: 消息列表
            tools: 工具定义列表
            tool_choice: 工具选择策略
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            LLMResponse: LLM 响应
        """
        kwargs: Dict[str, Any] = {
            "model": cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = await client.chat.completions.create(**kwargs)

        message = response.choices[0].message

        # 解析工具调用
        tool_calls_parsed = None
        if message.tool_calls:
            tool_calls_parsed = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls_parsed,
            finish_reason=response.choices[0].finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

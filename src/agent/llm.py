"""模块名称: llm
主要功能: LLM 客户端实现
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.config import config
from src.logger import get_logger
from src.agent.pipeline.router import get_router

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
        self._clients: Dict[str, AsyncOpenAI] = {}
        logger.info("LLM 客户端已初始化")

    @property
    def current_config(self) -> LLMConfig:
        """获取当前主 LLM 配置 (公开 API)"""
        primary, _ = self._get_config()
        return primary

    def _get_config(self) -> tuple[LLMConfig, LLMConfig]:
        """获取当前配置 (主, 备)"""
        # 1. 确定主配置
        if (
            config.ai.current_model_group
            and config.ai.current_model_group in config.config.ai.model_groups
        ):
            group_name = config.ai.current_model_group
            group_config = config.config.ai.model_groups[group_name]

            primary = LLMConfig(
                provider=group_config.provider,
                model=group_config.model,
                base_url=group_config.base_url,
                api_key=group_config.api_key,
            )
        else:
            primary = LLMConfig(
                provider=config.llm_provider,
                model=config.llm_model,
                base_url=config.llm_base_url,
                api_key=config.llm_api_key,
            )

        # 2. 备用配置 (目前暂不支持备用配置动态化，仍使用全局配置)
        fallback = LLMConfig(
            provider=config.llm_fallback_provider,
            model=config.llm_fallback_model,
            base_url=config.llm_fallback_base_url,
            api_key=config.llm_fallback_api_key,
        )

        return primary, fallback

    def _get_client(self, cfg: LLMConfig) -> AsyncOpenAI:
        """获取或创建 client 实例 (带有简单的缓存)"""
        # 使用 base_url + api_key 作为缓存键
        cache_key = f"{cfg.base_url}:{cfg.api_key[-6:] if len(cfg.api_key) > 6 else cfg.api_key}"

        if cache_key not in self._clients:
            logger.debug("创建新的 OpenAI Client: %s", cfg.base_url)
            self._clients[cache_key] = AsyncOpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
            )

        return self._clients[cache_key]

    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """发送聊天请求

        集成 LLMRouter 进行性能指标追踪。
        """

        primary_conf, fallback_conf = self._get_config()
        router = get_router()

        # 尝试主提供商
        start_time = time.time()
        try:
            client = self._get_client(primary_conf)
            response = await self._call_completion(
                client,
                primary_conf,
                messages,
                tools,
                tool_choice,
                temperature,
                max_tokens,
            )
            # 记录成功调用指标
            latency_ms = (time.time() - start_time) * 1000
            router.record_call(primary_conf.model, latency_ms, success=True)
            return response

        except Exception as e:
            # 记录失败调用指标
            latency_ms = (time.time() - start_time) * 1000
            router.record_call(primary_conf.model, latency_ms, success=False)
            logger.warning("主提供商调用失败: %s, 错误: %s", primary_conf.provider, e)

            # 尝试备用提供商
            logger.info("尝试使用备用提供商...")
            start_time = time.time()
            try:
                client = self._get_client(fallback_conf)
                response = await self._call_completion(
                    client,
                    fallback_conf,
                    messages,
                    tools,
                    tool_choice,
                    temperature,
                    max_tokens,
                )
                # 记录备用调用成功
                latency_ms = (time.time() - start_time) * 1000
                router.record_call(fallback_conf.model, latency_ms, success=True)
                return response

            except Exception as e2:
                latency_ms = (time.time() - start_time) * 1000
                router.record_call(fallback_conf.model, latency_ms, success=False)
                logger.error("备用提供商调用失败: %s", e2)

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
                "completion_tokens": response.usage.completion_tokens
                if response.usage
                else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

"""
AI Engine Core: LLM Client Wrapper
Provides a unified interface for LLM interactions with fallback support,
streaming (future), and cost tracking.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""
    api_key: str
    base_url: str
    model: str
    provider_name: str


class LLMResponse(BaseModel):
    """Unified response from LLM."""
    content: str
    tool_calls: List[Dict[str, Any]] = []
    raw_response: Any = None
    provider: str
    model: str
    latency_ms: float
    usage: Dict[str, int] = {}


class LLMClient:
    """
    Robust LLM Client with fallback mechanisms.
    """

    def __init__(self):
        self._primary_config = self._get_primary_config()
        self._fallback_config = self._get_fallback_config()
        
        self._primary_client = self._build_client(self._primary_config)
        self._fallback_client = self._build_client(self._fallback_config)

    def _get_primary_config(self) -> LLMConfig:
        return LLMConfig(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
            provider_name=config.llm_provider
        )

    def _get_fallback_config(self) -> LLMConfig:
        return LLMConfig(
            api_key=config.llm_fallback_api_key,
            base_url=config.llm_fallback_base_url,
            model=config.llm_fallback_model,
            provider_name=config.llm_fallback_provider
        )

    def _build_client(self, cfg: LLMConfig) -> Optional[AsyncOpenAI]:
        if not cfg.api_key:
            return None
        return AsyncOpenAI(api_key=cfg.api_key, base_url=cfg.base_url)

    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Union[str, Dict[str, Any]] = "auto",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Execute a chat completion with automatic fallback.
        """
        start_time = time.time()
        
        # Try Primary
        if self._primary_client:
            try:
                return await self._execute_call(
                    self._primary_client,
                    self._primary_config,
                    messages,
                    tools,
                    tool_choice,
                    temperature,
                    max_tokens,
                    json_mode,
                    start_time
                )
            except Exception as e:
                logger.warning(f"Primary LLM ({self._primary_config.provider_name}) failed: {e}")
        
        # Try Fallback
        if self._fallback_client:
            try:
                logger.info(f"Switching to fallback LLM ({self._fallback_config.provider_name})")
                return await self._execute_call(
                    self._fallback_client,
                    self._fallback_config,
                    messages,
                    tools,
                    tool_choice,
                    temperature,
                    max_tokens,
                    json_mode,
                    start_time
                )
            except Exception as e:
                logger.error(f"Fallback LLM failed: {e}")
                raise RuntimeError(f"All LLM providers failed. Last error: {e}")
        
        raise RuntimeError("No LLM clients configured or available.")

    async def _execute_call(
        self,
        client: AsyncOpenAI,
        cfg: LLMConfig,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Any,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        start_time: float
    ) -> LLMResponse:
        
        kwargs = {
            "model": cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response: ChatCompletion = await client.chat.completions.create(**kwargs)
        
        latency = (time.time() - start_time) * 1000
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    },
                    "type": tc.type
                })

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            raw_response=response,
            provider=cfg.provider_name,
            model=cfg.model,
            latency_ms=latency,
            usage=response.usage.model_dump() if response.usage else {}
        )

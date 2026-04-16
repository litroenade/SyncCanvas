"""OpenAI-compatible LLM client with provider failover."""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.infra.ai.circuit_breaker import ai_circuit_registry
from src.infra.config import config
from src.infra.logging import get_logger
from src.infra.metrics import inc_counter, observe_ms

logger = get_logger(__name__)


def _preview_text(value: Any, limit: int = 400) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _preview_content(content: Any, limit: int = 400) -> str:
    if isinstance(content, str):
        return _preview_text(content, limit)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                item_type = item.get("type") or "part"
                if item_type == "text":
                    parts.append(str(item.get("text") or ""))
                else:
                    parts.append(f"<{item_type}>")
            else:
                parts.append(str(item))
        return _preview_text(" | ".join(parts), limit)
    return _preview_text(content, limit)


def _preview_messages(messages: List[ChatCompletionMessageParam], limit: int = 1200) -> str:
    previews: list[str] = []
    for index, message in enumerate(messages, start=1):
        if isinstance(message, dict):
            role = str(message.get("role") or "unknown")
            previews.append(
                f"{index}:{role}:{_preview_content(message.get('content'), 240)}"
            )
        else:
            previews.append(f"{index}:raw:{_preview_text(message, 240)}")
    return _preview_text(" || ".join(previews), limit)


def _preview_tool_calls(tool_calls: Optional[List[Dict[str, Any]]], limit: int = 400) -> str:
    if not tool_calls:
        return "-"
    preview = " | ".join(
        f"{call.get('function', {}).get('name', 'unknown')}("
        f"{_preview_text(call.get('function', {}).get('arguments', ''), 120)})"
        for call in tool_calls
    )
    return _preview_text(preview, limit)


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str
    api_key: str


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)


class LLMRuntimeError(RuntimeError):
    """LLM runtime exception with provider context."""

    def __init__(self, message: str, *, provider: str) -> None:
        super().__init__(message)
        self.provider = provider


class LLMClient:
    """Small wrapper around OpenAI-compatible completion calls."""

    def __init__(self) -> None:
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._timeout_seconds = 90.0
        logger.info("LLM client initialized")

    @property
    def current_config(self) -> LLMConfig:
        primary, _ = self._get_config()
        return primary

    def _get_config(self) -> tuple[LLMConfig, LLMConfig]:
        if (
            config.ai.current_model_group
            and config.ai.current_model_group in config.config.ai.model_groups
        ):
            group_name = config.ai.current_model_group
            group_config = config.config.ai.model_groups[group_name]
            chat_model = group_config.chat_model
            primary = LLMConfig(
                provider=chat_model.provider,
                model=chat_model.model,
                base_url=chat_model.base_url,
                api_key=chat_model.api_key,
            )
        else:
            primary = LLMConfig(
                provider=config.llm_provider,
                model=config.llm_model,
                base_url=config.llm_base_url,
                api_key=config.llm_api_key,
            )

        fallback = LLMConfig(
            provider=config.llm_fallback_provider,
            model=config.llm_fallback_model,
            base_url=config.llm_fallback_base_url,
            api_key=config.llm_fallback_api_key,
        )
        return primary, fallback

    def _get_client(self, cfg: LLMConfig) -> AsyncOpenAI:
        cache_key = f"{cfg.base_url}:{cfg.api_key[-6:] if len(cfg.api_key) > 6 else cfg.api_key}"
        if cache_key not in self._clients:
            logger.debug("Create OpenAI client: %s", cfg.base_url)
            self._clients[cache_key] = AsyncOpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
            )
        return self._clients[cache_key]

    def _is_config_enabled(self, cfg: LLMConfig) -> bool:
        return bool(cfg.provider and cfg.model and cfg.base_url and cfg.api_key.strip())

    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
    ) -> LLMResponse:
        primary_conf, fallback_conf = self._get_config()
        start_time = time.time()
        effective_timeout = timeout if timeout is not None else self._timeout_seconds
        enabled_configs: list[LLMConfig] = []

        for conf in (primary_conf, fallback_conf):
            if self._is_config_enabled(conf):
                enabled_configs.append(conf)
                continue
            logger.warning(
                "LLM provider skipped: provider=%s model=%s reason=missing_configuration",
                conf.provider,
                conf.model,
            )

        if not enabled_configs:
            raise LLMRuntimeError(
                "AI_CIRCUIT_OPEN: no configured LLM provider",
                provider=primary_conf.provider,
            )

        for index, conf in enumerate(enabled_configs):
            provider = conf.provider
            breaker = ai_circuit_registry.get(provider)
            attempt = index + 1

            logger.debug(
                "LLM call start: provider=%s model=%s attempt=%s timeout=%.1fs temperature=%.2f max_tokens=%s tools=%s tool_choice=%s messages=%s",
                provider,
                conf.model,
                attempt,
                effective_timeout,
                temperature,
                max_tokens,
                len(tools or []),
                tool_choice,
                _preview_messages(messages),
            )

            if not await breaker.before_request():
                logger.warning(
                    "LLM provider blocked by circuit: provider=%s model=%s attempt=%s",
                    provider,
                    conf.model,
                    attempt,
                )
                inc_counter("llm_provider_blocked_total", labels={"provider": provider})
                continue

            attempt_start = time.time()
            try:
                response = await asyncio.wait_for(
                    self._call_completion(
                        self._get_client(conf),
                        conf,
                        messages,
                        tools,
                        tool_choice,
                        temperature,
                        max_tokens,
                    ),
                    timeout=effective_timeout,
                )
                await breaker.on_success()
                latency_ms = (time.time() - start_time) * 1000
                attempt_ms = (time.time() - attempt_start) * 1000
                logger.debug(
                    "LLM call success: provider=%s model=%s attempt=%s total_ms=%.2f attempt_ms=%.2f finish_reason=%s usage=%s content=%s tool_calls=%s",
                    provider,
                    conf.model,
                    attempt,
                    latency_ms,
                    attempt_ms,
                    response.finish_reason,
                    response.usage,
                    _preview_text(response.content, 600),
                    _preview_tool_calls(response.tool_calls),
                )
                inc_counter(
                    "llm_requests_total",
                    labels={"provider": provider, "status": "success"},
                )
                observe_ms(
                    "llm_call_duration_ms",
                    attempt_ms,
                    {"provider": provider, "status": "success"},
                )
                return response
            except asyncio.TimeoutError as exc:
                await breaker.on_failure()
                attempt_ms = (time.time() - attempt_start) * 1000
                observe_ms(
                    "llm_call_duration_ms",
                    attempt_ms,
                    {"provider": provider, "status": "timeout"},
                )
                inc_counter(
                    "llm_requests_total",
                    labels={"provider": provider, "status": "timeout"},
                )
                logger.warning(
                    "LLM call timeout: provider=%s model=%s attempt=%s timeout=%.1fs",
                    provider,
                    conf.model,
                    attempt,
                    effective_timeout,
                )
                if index == 0:
                    continue
                raise LLMRuntimeError(
                    "AI_CIRCUIT_OPEN: LLM request timeout",
                    provider=provider,
                ) from exc
            except Exception as exc:  # pylint: disable=broad-except
                await breaker.on_failure()
                attempt_ms = (time.time() - attempt_start) * 1000
                observe_ms(
                    "llm_call_duration_ms",
                    attempt_ms,
                    {"provider": provider, "status": "error"},
                )
                inc_counter(
                    "llm_requests_total",
                    labels={"provider": provider, "status": "error"},
                )
                logger.warning(
                    "LLM call failed: provider=%s model=%s attempt=%s error=%s",
                    provider,
                    conf.model,
                    attempt,
                    exc,
                )
                if index == 0:
                    continue
                raise LLMRuntimeError(
                    "AI_CIRCUIT_OPEN: LLM providers unavailable",
                    provider=provider,
                ) from exc

        inc_counter(
            "llm_requests_total",
            labels={"provider": enabled_configs[-1].provider, "status": "all_failed"},
        )
        raise LLMRuntimeError(
            "AI_CIRCUIT_OPEN: no available LLM provider",
            provider=enabled_configs[-1].provider,
        )

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

        tool_calls_parsed = None
        if message.tool_calls:
            tool_calls_parsed = [
                {
                    "id": tool_call.id,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls
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

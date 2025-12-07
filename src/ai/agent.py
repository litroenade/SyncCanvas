"""模块名称: agent
主要功能: 驱动 LLM 通过工具调用操控白板内容。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from src.ai.toolkit import BoardToolKit, BoardToolRegistry
from src.config import config
from src.logger import get_logger
from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)


class AIAgent:
    """AI 智能体，提供基于工具调用的白板操作。"""

    def __init__(self):
        self._toolkit = BoardToolKit()
        self._tool_registry = BoardToolRegistry(self._toolkit)
        self._client, self._model, self._provider = self._build_client(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
            provider=config.llm_provider,
        )
        self._fallback_client, self._fallback_model, self._fallback_provider = self._build_client(
            api_key=config.llm_fallback_api_key,
            base_url=config.llm_fallback_base_url,
            model=config.llm_fallback_model,
            provider=config.llm_fallback_provider,
        )
        self._max_tool_calls = config.llm_max_tool_calls
        self._tool_choice = config.llm_tool_choice

    @property
    def model(self) -> str:
        """Expose current model name."""

        return self._model or ""

    def _build_client(
        self, api_key: str, base_url: str, model: str, provider: str
    ) -> Tuple[Optional[AsyncOpenAI], Optional[str], Optional[str]]:
        """创建 LLM 客户端，缺少 key 时返回 None。"""

        if not api_key:
            logger.warning("LLM API Key 未配置，已禁用该 provider", extra={"provider": provider})
            return None, None, None

        return AsyncOpenAI(api_key=api_key, base_url=base_url), model, provider

    async def _get_board_snapshot(self, room_id: str) -> str:
        """获取白板概要，帮助模型少走弯路。"""

        try:
            snapshot = await self._toolkit.list_shapes(room_id, limit=20)
        except Exception:  # pragma: no cover - 非核心路径
            return "- board context unavailable"

        sample = snapshot.get("sample", [])
        if not sample:
            return "- board is empty"

        lines = [
            f"- id={item.get('id')} type={item.get('type')} text={item.get('text','')[:20]} x={item.get('x')} y={item.get('y')}"
            for item in sample
        ]
        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """构造系统提示词，约束模型使用工具。"""

        return (
            "You are the Teacher agent orchestrating a painter-like toolkit on a collaborative board. "
            "Always operate via tools, never invent shapes."
            "Workflow: (1) inspect board state; (2) plan briefly; (3) apply add_shapes / update_shape / remove_shapes / clear_board; "
            "(4) finish with a concise English summary of changes."
            "Shape fields: type, x, y, width, height, text, fill, strokeColor, id."
            "If the canvas should reset, call clear_board before adding new items. Use list_shapes when more context is required."
        )

    def _build_user_prompt(self, prompt: str, room_id: str, board_context: str) -> str:
        """拼接用户提示，传递房间和当前画布概况。"""

        return (
            f"Room ID: {room_id}\n"
            "Board snapshot (partial):\n"
            f"{board_context}\n"
            "Respond by using tools to meet the request.\n"
            f"User request: {prompt}"
        )

    def _parse_tool_arguments(self, arguments: str) -> Dict[str, Any]:
        """解析工具调用参数，容错空字符串。"""

        if not arguments:
            return {}
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            logger.warning("工具参数解析失败，将返回空参数: %s", arguments)
            return {}

    async def _call_llm(self, **kwargs) -> Tuple[Any, str, str]:
        """调用主模型，失败时尝试回退模型。"""

        last_error: Optional[Exception] = None
        if self._client and self._model:
            try:
                resp = await self._client.chat.completions.create(**kwargs, model=self._model)
                return resp, self._provider or "primary", self._model
            except Exception as exc:  # pragma: no cover - 依赖外部服务
                last_error = exc
                logger.warning("Primary LLM failed, trying fallback", extra={"error": str(exc)})

        if self._fallback_client and self._fallback_model:
            resp = await self._fallback_client.chat.completions.create(
                **kwargs, model=self._fallback_model
            )
            return resp, self._fallback_provider or "fallback", self._fallback_model

        raise last_error or RuntimeError("No available LLM client")

    async def generate_with_tools(
        self,
        prompt: str,
        room_id: str,
        run_logger: Optional[AgentRunService] = None,
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """驱动模型完成带工具的绘图流程，并可记录 agent 行为。"""

        if not self._client and not self._fallback_client:
            raise ValueError("LLM 服务未配置，请先设置 API Key")

        board_context = await self._get_board_snapshot(room_id)
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(prompt, room_id, board_context)},
        ]

        actions: List[Dict[str, Any]] = []
        provider_used = None
        model_used = None

        for _ in range(self._max_tool_calls):
            response, provider_used, model_used = await self._call_llm(
                messages=messages,
                tools=self._tool_registry.tools_schema,
                tool_choice=self._tool_choice,
                temperature=0.35,
                max_tokens=1200,
            )

            choice = response.choices[0].message
            tool_calls = choice.tool_calls or []

            if tool_calls:
                assistant_msg = {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [],
                }
                messages.append(assistant_msg)
                for call in tool_calls:
                    assistant_msg["tool_calls"].append(
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                    )

                    args = self._parse_tool_arguments(call.function.arguments)
                    result = await self._tool_registry.run(
                        call.function.name, args, room_id
                    )
                    action_payload = {
                        "tool": call.function.name,
                        "args": args,
                        "result": result,
                    }
                    actions.append(action_payload)

                    if run_logger and run_id:
                        run_logger.log_action(run_id, call.function.name, args, result)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue

            final_message = choice.content or "Done"
            return {
                "message": final_message,
                "actions": actions,
                "run_id": run_id,
                "provider": provider_used,
                "model": model_used,
            }

        raise RuntimeError("已达到最大工具调用次数，生成流程被中断")


# 全局实例
ai_agent = AIAgent()

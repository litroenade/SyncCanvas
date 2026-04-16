"""AI application service orchestration."""


import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from src.api.policy import PolicyErrorCode
from src.application.ai.memory.service import memory_service
from src.application.ai.managed_policy import ensure_managed_request_supported
from src.application.ai.runtime.runs import AgentRunService
from src.application.diagrams.service import diagram_service
from src.infra.ai.llm import LLMClient, LLMRuntimeError
from src.infra.metrics import inc_counter, observe_ms
from src.infra.logging import get_logger
from src.persistence.db.engine import engine, sqlite_write_transaction
from src.persistence.db.models.ai import AgentRequest
from src.persistence.db.repositories import ai_runs as request_repo

logger = get_logger(__name__)


def _preview_text(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


@dataclass
class ServiceStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tool_calls: int = 0
    total_elements_created: int = 0
    avg_response_time_ms: float = 0.0
    _response_times: List[float] = field(default_factory=list)

    def record_request(self, success: bool, duration_ms: float, tool_calls: int, elements: int) -> None:
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_tool_calls += tool_calls
        self.total_elements_created += elements
        self._response_times.append(duration_ms)
        if len(self._response_times) > 100:
            self._response_times.pop(0)
        if self._response_times:
            self.avg_response_time_ms = sum(self._response_times) / len(self._response_times)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.successful_requests / max(1, self.total_requests) * 100, 1),
            "total_tool_calls": self.total_tool_calls,
            "total_elements_created": self.total_elements_created,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
        }


class AIService:
    """Application-level AI service with idempotency and unified failure handling."""

    def __init__(self) -> None:
        self.llm_client = LLMClient()
        self._stats = ServiceStats()
        self._active_runs: Dict[int, str] = {}
        logger.info("AI service initialized")

    @property
    def stats(self) -> ServiceStats:
        return self._stats

    async def process_request(
        self,
        user_input: str,
        session_id: str,
        step_callback: Optional[Callable] = None,
        user_id: Optional[str] = None,
        theme: str = "light",
        virtual_mode: bool = False,
        conversation_id: Optional[int] = None,
        mode: str = "agent",
        target_diagram_id: Optional[str] = None,
        target_semantic_id: Optional[str] = None,
        edit_scope: str = "create_new",
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        explain: bool = False,
        source: str = "api",
    ) -> Dict[str, Any]:
        request_id = request_id or str(uuid.uuid4())
        idempotency_key = idempotency_key or request_id
        start_time = time.time()
        timeout_seconds = timeout_ms / 1000.0 if timeout_ms else None

        logger.debug(
            "AI request received: room=%s request_id=%s mode=%s virtual_mode=%s target_diagram_id=%s target_semantic_id=%s edit_scope=%s explain=%s timeout_ms=%s prompt=%s",
            session_id,
            request_id,
            mode,
            virtual_mode,
            target_diagram_id,
            target_semantic_id,
            edit_scope,
            explain,
            timeout_ms,
            _preview_text(user_input, 500),
        )

        existing = self._get_cached_request(session_id, idempotency_key)
        if existing:
            logger.debug(
                "AI request cache hit: room=%s request_id=%s idempotency_key=%s",
                session_id,
                request_id,
                idempotency_key,
            )
            return existing

        active_request_id = request_id
        run_id: Optional[int] = None
        request_record: Optional[AgentRequest] = None

        run_service = AgentRunService(Session(engine))
        session = run_service.session

        try:
            with sqlite_write_transaction():
                run = run_service.create_run(
                    room_id=session_id,
                    prompt=user_input,
                    model=self.llm_client.current_config.model,
                    auto_commit=False,
                )
                run_id = run.id
                if run_id is None:
                    raise RuntimeError("run id should exist after creation")
                request_record = request_repo.create_agent_request(
                    session,
                    request_id=active_request_id,
                    room_id=session_id,
                    user_id=None if user_id is None else _safe_int(user_id),
                    idempotency_key=idempotency_key,
                    source=source,
                    status="processing",
                    explain_requested=explain,
                    timeout_ms=timeout_ms,
                    auto_commit=False,
                )
                request_record.run_id = run_id
                session.add(request_record)
                request_record.updated_at = int(time.time() * 1000)
                session.flush()
                run_id = int(request_record.run_id or run_id)
                session.commit()
            self._active_runs[run_id] = session_id

            try:
                ensure_managed_request_supported(
                    user_input=user_input,
                    mode=mode,
                    target_diagram_id=target_diagram_id,
                    prompt_supports=diagram_service.supports_prompt,
                )
                logger.info(
                    "Resolved AI request pipeline: room=%s run=%s pipeline=managed_diagram",
                    session_id,
                    run_id,
                )
                logger.debug(
                    "Dispatching managed diagram request: room=%s run=%s mode=%s virtual_mode=%s target_diagram_id=%s target_semantic_id=%s edit_scope=%s",
                    session_id,
                    run_id,
                    mode,
                    virtual_mode,
                    target_diagram_id,
                    target_semantic_id,
                    edit_scope,
                )
                result = await self._run_with_timeout(
                    self._process_diagram_request(
                        user_input=user_input,
                        session_id=session_id,
                        theme=theme,
                        virtual_mode=virtual_mode,
                        run_id=run_id,
                        target_diagram_id=target_diagram_id,
                        target_semantic_id=target_semantic_id,
                        edit_scope=edit_scope,
                        request_timeout_seconds=timeout_seconds,
                    ),
                    timeout_seconds,
                )

                response_payload = self._with_explain(
                    payload=result,
                    explain=explain,
                    request_id=active_request_id,
                    idempotency_key=idempotency_key,
                )
                run_service.complete_run(
                    run_id,
                    message=str(response_payload.get("response", "")),
                    auto_commit=False,
                )
                request_record.status = "success"
                request_record.response = response_payload
                request_record.updated_at = int(time.time() * 1000)
                request_record.error = None
                request_record.run_id = run_id
                request_record.status = "success"
                session.add(request_record)

                with sqlite_write_transaction():
                    session.commit()
                await self._persist_conversation_turn(
                    conversation_id=conversation_id,
                    room_id=session_id,
                    mode=mode,
                    request_id=active_request_id,
                    run_id=run_id,
                    user_input=user_input,
                    assistant_content=str(response_payload.get("response", "")),
                    assistant_status="completed",
                    assistant_payload=response_payload,
                )

                duration_ms = (time.time() - start_time) * 1000
                self._stats.record_request(
                    True,
                    duration_ms,
                    len(result.get("tools_used", [])),
                    len(result.get("elements_created", [])),
                )
                observe_ms("ai_request_duration_ms", duration_ms, {"status": "success"})
                inc_counter("ai_requests_total", labels={"status": "success"})
                return response_payload

            except LLMRuntimeError as exc:
                # LLM failover open or call failure
                logger.warning(
                    "AI request failed with LLM runtime error: room=%s request_id=%s run=%s error=%s",
                    session_id,
                    active_request_id,
                    run_id,
                    exc,
                )
                raise
            except Exception:
                raise

        except LLMRuntimeError as exc:
            error_message = str(exc)
            session.rollback()
            payload = self._fail_request(
                session_id=session_id,
                session=session,
                request_id=active_request_id,
                idempotency_key=idempotency_key,
                run_id=run_id,
                status=PolicyErrorCode.AI_CIRCUIT_OPEN,
                error=self._normalize_failure_message(error_message),
            )
            duration_ms = (time.time() - start_time) * 1000
            self._stats.record_request(False, duration_ms, 0, 0)
            inc_counter("ai_requests_total", labels={"status": "fail"})
            inc_counter(
                "ai_request_failures_total",
                labels={"reason": PolicyErrorCode.AI_CIRCUIT_OPEN},
            )
            observe_ms("ai_request_duration_ms", duration_ms, {"status": "error"})
            await self._persist_conversation_turn(
                conversation_id=conversation_id,
                room_id=session_id,
                mode=mode,
                request_id=active_request_id,
                run_id=run_id,
                user_input=user_input,
                assistant_content=str(payload.get("message", error_message)),
                assistant_status="error",
                assistant_payload=payload,
            )
            return payload

        except IntegrityError as exc:
            # concurrent duplicate idempotency handling
            logger.warning("AI idempotency conflict: %s", exc)
            session.rollback()
            duplicate = self._get_cached_request(session_id, idempotency_key)
            if duplicate:
                return duplicate
            duration_ms = (time.time() - start_time) * 1000
            self._stats.record_request(False, duration_ms, 0, 0)
            inc_counter("ai_requests_total", labels={"status": "fail"})
            inc_counter(
                "ai_request_failures_total",
                labels={"reason": PolicyErrorCode.TXN_ROLLBACK},
            )
            observe_ms("ai_request_duration_ms", duration_ms, {"status": "error"})
            payload = self._build_error_payload(
                code=PolicyErrorCode.TXN_ROLLBACK,
                message="AI request idempotency conflict",
                request_id=active_request_id,
                idempotency_key=idempotency_key,
                run_id=run_id,
            )
            await self._persist_conversation_turn(
                conversation_id=conversation_id,
                room_id=session_id,
                mode=mode,
                request_id=active_request_id,
                run_id=run_id,
                user_input=user_input,
                assistant_content=str(payload.get("message", "AI request idempotency conflict")),
                assistant_status="error",
                assistant_payload=payload,
            )
            return payload

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("AI request failed: %s", exc)
            session.rollback()
            payload = self._fail_request(
                session_id=session_id,
                session=session,
                request_id=active_request_id,
                idempotency_key=idempotency_key,
                run_id=run_id,
                status=PolicyErrorCode.TXN_ROLLBACK,
                error=self._normalize_failure_message(str(exc)),
            )
            duration_ms = (time.time() - start_time) * 1000
            self._stats.record_request(False, duration_ms, 0, 0)
            inc_counter("ai_requests_total", labels={"status": "fail"})
            inc_counter(
                "ai_request_failures_total",
                labels={"reason": "unhandled"},
            )
            observe_ms("ai_request_duration_ms", duration_ms, {"status": "error"})
            await self._persist_conversation_turn(
                conversation_id=conversation_id,
                room_id=session_id,
                mode=mode,
                request_id=active_request_id,
                run_id=run_id,
                user_input=user_input,
                assistant_content=str(payload.get("message", exc)),
                assistant_status="error",
                assistant_payload=payload,
            )
            return payload
        finally:
            if run_id is not None:
                self._active_runs.pop(run_id, None)
            try:
                session.close()
            except Exception:
                pass

    async def _run_with_timeout(self, coro: Any, timeout_seconds: Optional[float]) -> Any:
        if timeout_seconds is None:
            return await coro
        return await asyncio.wait_for(coro, timeout=timeout_seconds)

    def _resolve_llm_timeout_seconds(self, request_timeout_seconds: Optional[float]) -> float:
        if request_timeout_seconds is None:
            return 90.0
        return max(30.0, min(90.0, request_timeout_seconds * 0.75))

    async def _save_memory_safe(
        self,
        conversation_id: Optional[int],
        room_id: str,
        role: str,
        content: str,
        *,
        run_id: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not conversation_id or not content or not content.strip():
            return
        try:
            safe_content = content[:10000]
            await memory_service.save_message(
                conversation_id,
                role,
                safe_content,
                run_id=run_id,
                extra_data=extra_data,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to save memory (room=%s, role=%s): %s",
                room_id,
                role,
                exc,
            )

    async def _persist_conversation_turn(
        self,
        *,
        conversation_id: Optional[int],
        room_id: str,
        mode: str,
        request_id: str,
        run_id: Optional[int],
        user_input: str,
        assistant_content: str,
        assistant_status: str,
        assistant_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        user_metadata = {
            "mode": mode,
            "used_mode": mode,
            "request_id": request_id,
        }
        assistant_metadata = self._build_conversation_message_metadata(
            mode=mode,
            request_id=request_id,
            status=assistant_status,
            payload=assistant_payload,
        )
        await self._save_memory_safe(
            conversation_id,
            room_id,
            "user",
            user_input,
            run_id=run_id,
            extra_data=user_metadata,
        )
        await self._save_memory_safe(
            conversation_id,
            room_id,
            "assistant",
            assistant_content,
            run_id=run_id,
            extra_data=assistant_metadata,
        )

    def _build_conversation_message_metadata(
        self,
        *,
        mode: str,
        request_id: str,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "mode": mode,
            "used_mode": mode,
            "request_id": request_id,
            "status": status,
        }
        if not payload:
            return metadata

        for key in (
            "run_id",
            "code",
            "virtual_elements",
            "diagram_bundle",
            "diagram_family",
            "generation_mode",
            "managed_scope",
            "patch_summary",
            "unmanaged_warnings",
            "sources",
            "change_reasoning",
            "affected_node_ids",
            "risk_notes",
        ):
            value = payload.get(key)
            if value not in (None, [], {}):
                metadata[key] = value
        return metadata

    async def _process_diagram_request(
        self,
        *,
        user_input: str,
        session_id: str,
        theme: str,
        virtual_mode: bool,
        run_id: int,
        target_diagram_id: Optional[str],
        target_semantic_id: Optional[str],
        edit_scope: str,
        request_timeout_seconds: Optional[float],
    ) -> Dict[str, Any]:
        start_time = time.time()
        llm_timeout_seconds = self._resolve_llm_timeout_seconds(request_timeout_seconds)
        logger.debug(
            "Managed diagram request start: room=%s run=%s target_diagram_id=%s target_semantic_id=%s edit_scope=%s virtual_mode=%s llm_timeout_seconds=%.1f prompt=%s",
            session_id,
            run_id,
            target_diagram_id,
            target_semantic_id,
            edit_scope,
            virtual_mode,
            llm_timeout_seconds,
            _preview_text(user_input, 500),
        )
        if target_diagram_id:
            diagram_result = await diagram_service.update_from_prompt_result(
                session_id,
                target_diagram_id,
                user_input,
                target_semantic_id=target_semantic_id,
                edit_scope=edit_scope,
                llm_client=self.llm_client,
                llm_timeout_seconds=llm_timeout_seconds,
                persist=not virtual_mode,
            )
        else:
            diagram_result = await diagram_service.create_from_prompt_result(
                user_input,
                session_id=session_id,
                theme=theme,
                llm_client=self.llm_client,
                llm_timeout_seconds=llm_timeout_seconds,
                persist=not virtual_mode,
            )
        bundle = diagram_result.bundle

        duration_ms = (time.time() - start_time) * 1000
        action = "Updated" if target_diagram_id else "Created"
        message = (
            f"{action} a managed {bundle.summary.family} diagram with "
            f"{bundle.summary.component_count} components."
        )
        logger.debug(
            "Managed diagram request complete: room=%s run=%s action=%s generation_mode=%s diagram_id=%s family=%s components=%s connectors=%s preview_elements=%s managed_scope=%s duration_ms=%.2f",
            session_id,
            run_id,
            action.lower(),
            diagram_result.generation_mode,
            bundle.spec.diagram_id,
            bundle.summary.family,
            bundle.summary.component_count,
            bundle.summary.connector_count,
            len(bundle.preview_elements),
            bundle.state.managed_scope,
            duration_ms,
        )
        return {
            "status": "success",
            "response": message,
            "run_id": run_id,
            "elements_created": [element["id"] for element in bundle.preview_elements],
            "tools_used": [
                "update_diagram_by_prompt"
                if target_diagram_id
                else "create_diagram_from_prompt"
            ],
            "metrics": {
                "duration_ms": round(duration_ms, 2),
                "iterations": 1,
                "diagram_family": bundle.summary.family,
            },
            "virtual_elements": bundle.preview_elements if virtual_mode else [],
            "diagram_bundle": bundle.model_dump(by_alias=True),
            "diagram_family": bundle.summary.family,
            "generation_mode": diagram_result.generation_mode,
            "managed_scope": bundle.state.managed_scope,
            "patch_summary": bundle.state.last_patch_summary,
            "unmanaged_warnings": bundle.state.warnings,
        }

    async def cancel_request(self, run_id: int) -> Dict[str, Any]:
        if run_id not in self._active_runs:
            return {
                "status": "error",
                "message": f"Run {run_id} does not exist or already completed",
            }
        return {
            "status": "error",
            "message": "Managed diagram requests cannot be cancelled once execution starts",
        }

    async def get_run_history(self, session_id: str, db: Session, limit: int = 20) -> Dict[str, Any]:
        runs = AgentRunService(db).get_room_runs(session_id, limit)
        return {
            "status": "success",
            "runs": [
                {
                    "id": run.id,
                    "prompt": run.prompt[:100] + "..." if len(run.prompt) > 100 else run.prompt,
                    "status": run.status,
                    "created_at": run.created_at,
                    "finished_at": run.finished_at,
                }
                for run in runs
            ],
        }

    async def get_run_detail(self, run_id: int, db: Session) -> Dict[str, Any]:
        detail = AgentRunService(db).get_run_detail(run_id)
        if not detail:
            return {"status": "error", "message": f"Run {run_id} not found"}
        return {"status": "success", "run": detail}

    def get_service_status(self) -> Dict[str, Any]:
        active_rooms = sorted(set(self._active_runs.values()))
        return {
            "status": "healthy",
            "llm": {
                "provider": self.llm_client.current_config.provider,
                "model": self.llm_client.current_config.model,
            },
            "stats": self._stats.to_dict(),
            "active_requests": len(self._active_runs),
            "busy_rooms": active_rooms,
            "pipeline": {
                "mode": "managed_diagrams_only",
                "freeform_canvas_mode": False,
            },
            "tools": {
                "total": 0,
                "enabled": 0,
                "by_category": {},
            },
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        return []

    def disable_tool(self, name: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "message": "Legacy agent tools have been removed",
        }

    def enable_tool(self, name: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "message": "Legacy agent tools have been removed",
        }

    def is_room_busy(self, room_id: str) -> bool:
        return room_id in self._active_runs.values()

    def _with_explain(
        self,
        payload: Dict[str, Any],
        *,
        explain: bool,
        request_id: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        payload["request_id"] = request_id
        payload["idempotency_key"] = idempotency_key
        if explain:
            affected_node_ids = list(payload.get("elements_created", []))
            generation_mode = str(payload.get("generation_mode") or "llm")
            diagram_family = str(payload.get("diagram_family") or "layered_architecture")
            if generation_mode == "deterministic_seed":
                payload["sources"] = [
                    {
                        "type": "deterministic_seed",
                        "role": "system",
                    }
                ]
                payload["change_reasoning"] = [
                    {
                        "step": "deterministic_seed",
                        "explanation": (
                            f"LLM spec generation was unavailable, so SyncCanvas used the "
                            f"deterministic {diagram_family} seed and re-rendered the scene."
                        ),
                    }
                ]
                payload["risk_notes"] = [
                    "This preview used a deterministic family seed because the LLM did not return a usable diagram spec.",
                ]
            elif generation_mode == "heuristic_patch":
                payload["sources"] = [
                    {
                        "type": "heuristic_patch",
                        "role": "system",
                    }
                ]
                payload["change_reasoning"] = [
                    {
                        "step": "heuristic_patch",
                        "explanation": (
                            "LLM patch generation was unavailable, so SyncCanvas applied "
                            "heuristic semantic edits to the existing diagram and re-rendered the scene."
                        ),
                    }
                ]
                payload["risk_notes"] = [
                    "This update used heuristic patching because the LLM did not return a usable diagram edit payload.",
                ]
            else:
                payload["sources"] = [
                    {
                        "type": "llm",
                        "provider": self.llm_client.current_config.provider,
                        "model": self.llm_client.current_config.model,
                        "role": "assistant",
                    }
                ]
                payload["change_reasoning"] = [
                    {
                        "step": "managed_diagram",
                        "explanation": "LLM generated or updated a managed diagram spec and re-rendered the scene.",
                    }
                ]
                payload["risk_notes"] = []
            payload["affected_node_ids"] = affected_node_ids
        return payload

    def _get_cached_request(self, room_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
        with Session(engine) as db:
            req = request_repo.get_agent_request_by_idempotency_key(db, idempotency_key)
            if not req:
                return None
            if req.room_id != room_id:
                return {
                    "status": "error",
                    "code": PolicyErrorCode.AUTHZ_DENIED,
                    "message": "request room mismatch",
                    "request_id": req.request_id,
                    "idempotency_key": req.idempotency_key,
                    "run_id": req.run_id,
                }
            if req.status != "processing" and isinstance(req.response, dict):
                return dict(req.response)
            if req.status == "processing":
                return {
                    "status": "processing",
                    "message": "AI request is processing",
                    "request_id": req.request_id,
                    "idempotency_key": req.idempotency_key,
                    "run_id": req.run_id,
                }
            if req.status == "success" and req.response:
                return dict(req.response)
            if req.status == "failed":
                return {
                    "status": "error",
                    "code": PolicyErrorCode.TXN_ROLLBACK,
                    "message": req.error or "AI request failed",
                    "run_id": req.run_id,
                    "request_id": req.request_id,
                    "idempotency_key": req.idempotency_key,
                }
            return {
                "status": req.status,
                "request_id": req.request_id,
                "idempotency_key": req.idempotency_key,
                "run_id": req.run_id,
            }

    def _build_error_payload(
        self,
        *,
        code: str,
        message: str,
        request_id: str,
        idempotency_key: str,
        run_id: Optional[int],
    ) -> Dict[str, Any]:
        return {
            "status": "error",
            "code": code,
            "message": message,
            "run_id": run_id or 0,
            "request_id": request_id,
            "idempotency_key": idempotency_key,
        }

    def _normalize_failure_message(self, message: str) -> str:
        if not message:
            return "AI request failed"
        return message

    def _fail_request(
        self,
        *,
        session_id: str,
        session: Optional[Session] = None,
        request_id: str,
        idempotency_key: str,
        run_id: Optional[int],
        status: str,
        error: str,
    ) -> Dict[str, Any]:
        owner_session = session or Session(engine)
        close_session = session is None
        run_service = AgentRunService(owner_session)
        payload = self._build_error_payload(
            code=status,
            message=error,
            request_id=request_id,
            idempotency_key=idempotency_key,
            run_id=run_id,
        )
        try:
            req = request_repo.get_agent_request_by_idempotency_key(owner_session, idempotency_key)
            if req is None:
                req = request_repo.create_agent_request(
                    owner_session,
                    request_id=request_id,
                    room_id=session_id,
                    user_id=None,
                    idempotency_key=idempotency_key,
                    status=status,
                    explain_requested=False,
                    timeout_ms=None,
                    auto_commit=False,
                )
            req.status = status
            req.run_id = run_id
            req.error = error
            req.response = payload
            req.updated_at = int(time.time() * 1000)
            owner_session.add(req)

            if run_id:
                try:
                    run_service.fail_run(run_id, error=error, auto_commit=False)
                except Exception:
                    # Keep request error log even if run record diverges.
                    pass

            with sqlite_write_transaction():
                owner_session.commit()
            logger.error(
                "AI request failed",
                extra={
                    "status": status,
                    "request_id": request_id,
                    "run_id": run_id,
                    "error": error,
                },
            )
            return payload
        except IntegrityError:
            owner_session.rollback()
            raise
        except Exception:
            owner_session.rollback()
            return self._build_error_payload(
                code=PolicyErrorCode.TXN_ROLLBACK,
                message=self._normalize_failure_message(error),
                request_id=request_id,
                idempotency_key=idempotency_key,
                run_id=run_id,
            )
        finally:
            if close_session:
                try:
                    owner_session.close()
                except Exception:
                    pass


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


ai_service = AIService()

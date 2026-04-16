
import json
import time
from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.application.ai.service import ai_service
from src.application.ai.memory.service import memory_service
from src.application.ai.prompts.manager import prompt_manager
from src.application.ai.tools.mermaid import generate_mermaid_code
from src.auth.utils import get_current_user
from src.infra.ai.circuit_breaker import ai_circuit_registry
from src.infra.ai.llm import LLMClient
from src.infra.logging import get_logger
from src.middleware.rate_limit import check_rate_limit_for_room
from src.persistence.db.engine import engine, get_session
from src.persistence.db.models.ai import Conversation
from src.persistence.db.models.rooms import Room
from src.persistence.db.models.users import User
from src.api.policy import PolicyErrorCode, build_error_payload
from src.application.rooms.access import (
    WS_AUTHENTICATION_REQUIRED,
    WS_INVALID_TOKEN,
    WS_ROOM_MEMBERSHIP_REQUIRED,
    WS_ROOM_NOT_FOUND,
    ensure_room_member_access,
    resolve_websocket_room_user,
)
from src.infra.metrics import inc_counter, observe_ms, set_gauge

router = APIRouter(prefix="/ai", tags=["AI"])
logger = get_logger(__name__)


def _is_transport_disconnect_error(exception: BaseException) -> bool:
    """Identify transport-layer websocket disconnect noise."""

    if isinstance(exception, WebSocketDisconnect):
        return True
    error_text = str(exception).lower()
    disconnect_keywords = [
        "clientdisconnected",
        "websocket is not connected",
        "need to call \"accept\" first",
        "cannot call receive once a disconnect message has been received",
        "cannot call send once a close message has been sent",
        "websocket disconnected",
    ]
    return any(keyword in error_text for keyword in disconnect_keywords)


class GenerateRequest(BaseModel):
    """AI request payload."""

    prompt: str = Field(..., description="User input", min_length=1, max_length=2000)
    room_id: str = Field(..., description="Room id")
    theme: str = Field("light", description="Canvas theme (light/dark)")
    request_id: Optional[str] = Field(default=None, max_length=64)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    timeout_ms: Optional[int] = Field(default=None, ge=1000, le=300000)
    explain: bool = Field(default=False)


class GenerateResponse(BaseModel):
    """AI response payload."""

    status: str
    response: str = ""
    run_id: int
    elements_created: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    code: Optional[str] = None
    generation_mode: Optional[str] = None
    sources: Optional[list[dict[str, object]]] = None
    change_reasoning: Optional[list[dict[str, object]]] = None
    affected_node_ids: Optional[list[str]] = None
    risk_notes: Optional[list[str]] = None


class MermaidRequest(BaseModel):
    """Mermaid generation payload."""

    prompt: str = Field(..., description="Mermaid input", min_length=1, max_length=2000)
    room_id: Optional[str] = Field(default=None, description="Room id")
    conversation_id: Optional[int] = Field(default=None, ge=1)


class MermaidResponse(BaseModel):
    """Mermaid response."""

    code: str
    status: str = "success"


class SummarizeRequest(BaseModel):
    """Summary payload."""

    message: str = Field(..., description="Original user text", min_length=1, max_length=500)


class SummarizeResponse(BaseModel):
    """Summary response."""

    title: str = Field(..., description="Summary title")
    status: str = "success"


class ConversationInfo(BaseModel):
    """Conversation metadata."""

    id: int
    room_id: str
    title: str
    mode: str
    is_active: bool
    message_count: int
    created_at: int
    updated_at: int


class ConversationsListResponse(BaseModel):
    """Conversation list response."""

    conversations: list[ConversationInfo]
    total: int


class CreateConversationRequest(BaseModel):
    """Conversation creation payload."""

    title: str = Field(default="New conversation", max_length=100)
    mode: str = Field(default="planning", max_length=20)


class UpdateConversationRequest(BaseModel):
    """Update conversation payload."""

    title: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = Field(default=None)


class ConversationMessageInfo(BaseModel):
    """Conversation message payload."""

    role: str
    content: str
    created_at: int
    extra_data: dict[str, object] = Field(default_factory=dict)


class ConversationMessagesResponse(BaseModel):
    """Conversation messages response."""

    messages: list[ConversationMessageInfo]
    total: int


class AIWebSocketManager:
    """Manages AI websocket connections and event replay."""

    def __init__(self, history_limit: int = 200):
        self._connections: dict[str, list[WebSocket]] = {}
        self._room_seq: dict[str, int] = {}
        self._connection_sessions: dict[int, str] = {}
        self._room_history: dict[str, Deque[dict[str, Any]]] = {}
        self._history_limit = history_limit

    def _next_seq(self, room_id: str) -> int:
        current = self._room_seq.get(room_id, 0) + 1
        self._room_seq[room_id] = current
        return current

    def _append_history(self, room_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        payload = payload.copy()
        payload["seq"] = self._next_seq(room_id)
        payload.setdefault("room_id", room_id)
        payload.setdefault("timestamp", int(time.time() * 1000))
        history = self._room_history.setdefault(room_id, deque(maxlen=self._history_limit))
        history.append(payload)
        set_gauge("ws_ai_room_buffer_size", len(history), {"room_id": room_id})
        return payload

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        client_session_id: Optional[str] = None,
    ) -> None:
        await websocket.accept()
        if client_session_id:
            self._connection_sessions[id(websocket)] = client_session_id
        self._connections.setdefault(room_id, [])
        if websocket not in self._connections[room_id]:
            self._connections[room_id].append(websocket)
        set_gauge("ws_ai_active_connections", len(self._connections[room_id]), {"room_id": room_id})
        inc_counter("ws_ai_connection_total", labels={"room_id": room_id, "outcome": "connected"})
        logger.info("AI websocket connected: room=%s", room_id)

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        if room_id not in self._connections:
            return
        if websocket in self._connections[room_id]:
            self._connections[room_id].remove(websocket)
        self._connection_sessions.pop(id(websocket), None)
        if not self._connections[room_id]:
            del self._connections[room_id]
            set_gauge("ws_ai_active_connections", 0, {"room_id": room_id})
        else:
            set_gauge("ws_ai_active_connections", len(self._connections[room_id]), {"room_id": room_id})
        logger.info("AI websocket disconnected: room=%s", room_id)
        inc_counter("ws_ai_connection_total", labels={"room_id": room_id, "outcome": "disconnected"})

    def get_missing_messages(
        self,
        room_id: str,
        resume_from_seq: Optional[int],
    ) -> Tuple[bool, list[dict[str, Any]]]:
        if resume_from_seq is None:
            return True, []
        if resume_from_seq < 0:
            inc_counter("ws_ai_reconnect_total", labels={"room_id": room_id, "outcome": "invalid_resume_seq"})
            return False, []

        history = self._room_history.get(room_id, deque())
        if not history:
            return True, []

        latest_seq = self._room_seq.get(room_id, 0)
        if resume_from_seq >= latest_seq:
            inc_counter("ws_ai_reconnect_total", labels={"room_id": room_id, "outcome": "resume_no_gap"})
            return True, []

        min_seq = history[0].get("seq", 0)
        if resume_from_seq < min_seq - 1:
            inc_counter("ws_ai_reconnect_total", labels={"room_id": room_id, "outcome": "gap_too_large"})
            return False, []

        events = [item for item in history if item.get("seq", 0) > resume_from_seq]
        if events:
            inc_counter("ws_ai_gap_recovered_total", value=len(events), labels={"room_id": room_id})
        inc_counter("ws_ai_reconnect_total", labels={"room_id": room_id, "outcome": "resume_recovered"})
        return True, events

    async def broadcast_to_room(self, room_id: str, payload: dict[str, Any]) -> None:
        payload = self._append_history(room_id, payload)
        inc_counter("ws_ai_broadcast_total", labels={"room_id": room_id, "message_type": payload.get("type", "unknown")})
        if room_id not in self._connections:
            return
        disconnected: list[WebSocket] = []
        for ws in self._connections[room_id]:
            try:
                await ws.send_json(payload)
            except Exception as exc:  # pylint: disable=broad-except
                disconnected.append(ws)
                if _is_transport_disconnect_error(exc):
                    logger.debug("AI WS transport disconnected: %s", exc)
                else:
                    logger.debug("AI WS send failed: %s", exc)
        for ws in disconnected:
            self.disconnect(ws, room_id)


def _policy_http_error(
    *,
    code: str,
    message: str,
    request_id: Optional[str] = None,
) -> HTTPException:
    payload = build_error_payload(
        code=code,
        message=message,
        trace_id=request_id,
        reason=message,
    )

    if code == PolicyErrorCode.AUTHZ_DENIED:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=payload)
    if code == PolicyErrorCode.RATE_LIMIT_EXCEEDED:
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=payload)
    if code == PolicyErrorCode.AI_CIRCUIT_OPEN:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    if code == PolicyErrorCode.ROOM_NOT_FOUND:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    if code.endswith("_not_found"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=payload)


def _extract_ws_token(
    token: Optional[str],
    authorization: Optional[str],
) -> Optional[str]:
    if token:
        return token
    if not authorization:
        return None
    scheme, _, raw_token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return raw_token


def _room_head_version(room_id: str) -> int:
    with Session(engine) as session:
        room = session.get(Room, room_id)
        return room.head_commit_id or 0 if room else 0


ai_ws_manager = AIWebSocketManager()


def _build_complete_payload(
    *,
    result: dict[str, Any],
    request_id: str,
    idempotency_key: str,
    room_version: int,
    client_session_id: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "type": "complete",
        "status": result.get("status", "success"),
        "code": result.get("code") if result.get("status") != "success" else "SUCCESS",
        "response": result.get("response", ""),
        "run_id": result.get("run_id", 0),
        "elements_created": result.get("elements_created", []),
        "tools_used": result.get("tools_used", []),
        "metrics": result.get("metrics", {}),
        "virtual_elements": result.get("virtual_elements", []),
        "diagram_bundle": result.get("diagram_bundle"),
        "diagram_family": result.get("diagram_family"),
        "generation_mode": result.get("generation_mode"),
        "managed_scope": result.get("managed_scope", []),
        "patch_summary": result.get("patch_summary"),
        "unmanaged_warnings": result.get("unmanaged_warnings", []),
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "sources": result.get("sources"),
        "change_reasoning": result.get("change_reasoning"),
        "affected_node_ids": result.get("affected_node_ids"),
        "risk_notes": result.get("risk_notes"),
        "room_version": room_version,
        "client_session_id": client_session_id,
    }


@router.post("/mermaid", response_model=MermaidResponse)
async def generate_mermaid(
    request: MermaidRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate mermaid source code."""
    logger.info("received mermaid request", extra={"prompt_length": len(request.prompt)})
    if request.room_id:
        ensure_room_member_access(session, request.room_id, current_user)

    if request.conversation_id is not None:
        conversation = session.get(Conversation, request.conversation_id)
        if not conversation or (
            request.room_id is not None and conversation.room_id != request.room_id
        ):
            raise _policy_http_error(
                code="conversation_not_found",
                message="conversation_not_found",
            )
        ensure_room_member_access(session, conversation.room_id, current_user)

    result = await generate_mermaid_code(request.prompt)
    if request.conversation_id is not None:
        await memory_service.save_message(
            request.conversation_id,
            "user",
            request.prompt[:10000],
            extra_data={
                "mode": "mermaid",
                "used_mode": "mermaid",
            },
        )
        await memory_service.save_message(
            request.conversation_id,
            "assistant",
            f"```mermaid\n{result['code'].strip()}\n```",
            extra_data={
                "mode": "mermaid",
                "used_mode": "mermaid",
                "status": "completed",
            },
        )
    return MermaidResponse(code=result["code"], status=result["status"])


@router.post("/summarize", response_model=SummarizeResponse)
async def generate_summary(request: SummarizeRequest):
    """Generate a short title for given message."""
    prompt = (
        "Generate a short title for the following message with no extra text.\n\n"
        f"Message: {request.message[:200]}\n\n"
        "Title:"
    )
    try:
        client = LLMClient()
        response = await client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        title = (response.content or "").strip().strip("\"'")
        if not title:
            title = request.message[:15] + ("..." if len(request.message) > 15 else "")
        return SummarizeResponse(title=title[:30])
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("summary failed: %s", exc)
        fallback = request.message[:15] + ("..." if len(request.message) > 15 else "")
        return SummarizeResponse(title=fallback)


@router.post("/generate", response_model=GenerateResponse)
async def generate_shapes(
    request: GenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate AI content with room permission checks."""
    ensure_room_member_access(session, request.room_id, current_user)
    result = await ai_service.process_request(
        user_input=request.prompt,
        session_id=request.room_id,
        theme=request.theme,
        user_id=str(current_user.id) if current_user.id is not None else None,
        request_id=request.request_id,
        idempotency_key=request.idempotency_key,
        timeout_ms=request.timeout_ms,
        explain=request.explain,
        source="api",
    )
    return GenerateResponse(
        status=result.get("status", "success"),
        response=result.get("response", ""),
        run_id=int(result.get("run_id", 0)),
        elements_created=list(result.get("elements_created", [])),
        tools_used=list(result.get("tools_used", [])),
        request_id=result.get("request_id"),
        idempotency_key=result.get("idempotency_key"),
        code=result.get("code"),
        generation_mode=result.get("generation_mode"),
        sources=result.get("sources"),
        change_reasoning=result.get("change_reasoning"),
        affected_node_ids=result.get("affected_node_ids"),
        risk_notes=result.get("risk_notes"),
    )


@router.get("/runs/{room_id}")
async def get_room_runs(
    room_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get room run history."""
    ensure_room_member_access(session, room_id, current_user)
    return await ai_service.get_run_history(session_id=room_id, db=session, limit=limit)


@router.get("/run/{run_id}")
async def get_run_detail(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get one AI run detail."""
    from src.application.rooms.access import ensure_run_room_access

    result = await ai_service.get_run_detail(run_id, session)
    if result.get("status") == "error":
        raise _policy_http_error(code="run_not_found", message="run_not_found")
    run_room = result.get("room_id")
    if run_room:
        ensure_room_member_access(session, str(run_room), current_user)
    return result


@router.get("/tools")
async def list_tools():
    """List managed-diagram capabilities."""
    tools = ai_service.list_tools()
    return {"status": "success", "count": len(tools), "tools": tools}


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Tool detail endpoint retained as a managed-only no-op."""
    raise _policy_http_error(
        code="tool_not_found",
        message=f"tool {tool_name} not found",
    )


@router.get("/status")
async def get_agent_status():
    """System status."""
    payload = ai_service.get_service_status()
    payload["circuit_breakers"] = ai_circuit_registry.snapshot()
    payload["agent"] = {
        "active_rooms": payload.get("busy_rooms", []),
        "active_count": len(payload.get("busy_rooms", [])),
    }
    return payload


@router.get("/status/{room_id}")
async def get_room_agent_status(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Room agent status."""
    ensure_room_member_access(session, room_id, current_user)
    is_busy = ai_service.is_room_busy(room_id)
    return {
        "status": "success",
        "room_id": room_id,
        "is_busy": is_busy,
        "message": "room busy" if is_busy else "room idle",
    }


@router.post("/cancel/{run_id}")
async def cancel_run(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Cancel run."""
    from src.application.rooms.access import ensure_run_room_access

    ensure_run_room_access(session, run_id, current_user)
    return await ai_service.cancel_request(run_id)


@router.get("/stats")
async def get_service_stats():
    """Service stats."""
    return ai_service.get_service_status()


@router.post("/tools/{tool_name}/disable")
async def disable_tool(tool_name: str):
    """Disable tool."""
    return ai_service.disable_tool(tool_name)


@router.post("/tools/{tool_name}/enable")
async def enable_tool(tool_name: str):
    """Enable tool."""
    return ai_service.enable_tool(tool_name)


@router.get("/templates")
async def list_templates():
    """List prompt templates."""
    templates = prompt_manager.list_templates()
    return {"status": "success", "count": len(templates), "templates": templates}


@router.get("/templates/{template_name}")
async def get_template(template_name: str):
    """Get one prompt template."""
    source = prompt_manager.get_template_source(template_name)
    if source is None:
        raise _policy_http_error(
            code="template_not_found",
            message=f"template {template_name} not found",
        )
    return {"status": "success", "name": template_name, "source": source, "length": len(source)}


@router.get("/conversations/{room_id}")
async def list_conversations(
    room_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List room conversations."""
    ensure_room_member_access(session, room_id, current_user)
    conversations = await memory_service.get_conversations(room_id, limit)
    return ConversationsListResponse(
        conversations=[
            ConversationInfo(
                id=c.id or 0,
                room_id=c.room_id,
                title=c.title,
                mode=c.mode,
                is_active=c.is_active,
                message_count=c.message_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
            if c.id is not None
        ],
        total=len(conversations),
    )


@router.post("/conversations/{room_id}")
async def create_conversation(
    room_id: str,
    request: CreateConversationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create one conversation."""
    ensure_room_member_access(session, room_id, current_user)
    conv = await memory_service.create_conversation(
        room_id=room_id,
        title=request.title,
        mode=request.mode,
    )
    return {"status": "created", "conversation_id": conv.id, "title": conv.title}


@router.get(
    "/conversations/{room_id}/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def get_conversation_messages(
    room_id: str,
    conversation_id: int,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get room messages."""
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.room_id != room_id:
        raise _policy_http_error(code="conversation_not_found", message="conversation_not_found")
    ensure_room_member_access(session, room_id, current_user)
    messages = await memory_service.get_messages(conversation_id, limit)
    return ConversationMessagesResponse(
        messages=[
            ConversationMessageInfo(
                role=message["role"],
                content=message["content"],
                created_at=message["created_at"],
                extra_data=message.get("extra_data") or {},
            )
            for message in messages
        ],
        total=len(messages),
    )


@router.patch("/conversations/{room_id}/{conversation_id}")
async def update_conversation(
    room_id: str,
    conversation_id: int,
    request: UpdateConversationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update conversation title."""
    ensure_room_member_access(session, room_id, current_user)
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.room_id != room_id:
        raise _policy_http_error(code="conversation_not_found", message="conversation_not_found")

    if request.title is not None:
        await memory_service.update_conversation_title(conversation_id, request.title)

    if request.is_active:
        activated = await memory_service.activate_conversation(room_id, conversation_id)
        if activated is None:
            raise _policy_http_error(
                code="conversation_not_found",
                message="conversation_not_found",
            )

    return {
        "status": "updated",
        "title": request.title if request.title is not None else conversation.title,
        "is_active": bool(request.is_active),
    }


@router.delete("/conversations/{room_id}/{conversation_id}")
async def delete_conversation(
    room_id: str,
    conversation_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete conversation."""
    ensure_room_member_access(session, room_id, current_user)
    deleted_count = await memory_service.delete_conversation(conversation_id)
    return {"status": "deleted", "messages_deleted": deleted_count}


@router.websocket("/stream/{room_id}")
async def ai_stream_websocket(
    websocket: WebSocket,
    room_id: str,
    token: Optional[str] = Query(default=None),
    client_session_id: Optional[str] = Query(default=None),
    resume_from_seq: Optional[int] = Query(default=None),
    room_version: Optional[int] = Query(default=None),
):
    """Streaming AI websocket with resumable delivery."""
    authorization = websocket.headers.get("authorization")
    ws_token = _extract_ws_token(token, authorization)
    rate_limited, rate_headers = check_rate_limit_for_room(
        path=f"/api/ai/stream/{room_id}",
        room_id=room_id,
        token=ws_token,
        client_host=websocket.client.host if websocket.client else None,
    )
    if not rate_limited:
        inc_counter("ws_rate_limit_total", labels={"room_id": room_id, "outcome": "handshake_blocked"})
        logger.warning("AI WS rate limit exceeded", extra={"room_id": room_id, "peer": websocket.client})
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "reconnect_required",
                "code": PolicyErrorCode.RATE_LIMIT_EXCEEDED,
                "message": "rate limit exceeded",
                "room_version": _room_head_version(room_id),
            },
        )
        await websocket.close(code=1013, reason=PolicyErrorCode.RATE_LIMIT_EXCEEDED)
        return

    try:
        current_user = resolve_websocket_room_user(
            room_id,
            token=ws_token,
            authorization=authorization,
        )
    except Exception as exc:  # pylint: disable=broad-except
        inc_counter("ws_ai_handshake_total", labels={"room_id": room_id, "outcome": "auth_failed"})
        detail = getattr(exc, "detail", str(exc))
        if isinstance(detail, dict):
            reason = str(
                detail.get("reason")
                or detail.get("message")
                or detail.get("code")
                or PolicyErrorCode.AUTHZ_DENIED
            )
        else:
            reason = str(detail)

        await websocket.accept()
        if reason not in {
            WS_AUTHENTICATION_REQUIRED,
            WS_INVALID_TOKEN,
            WS_ROOM_NOT_FOUND,
            WS_ROOM_MEMBERSHIP_REQUIRED,
            PolicyErrorCode.AUTHZ_DENIED,
            PolicyErrorCode.ROOM_NOT_FOUND,
            PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED,
            PolicyErrorCode.RATE_LIMIT_EXCEEDED,
        }:
            reason = "AUTHZ_DENIED"
        await websocket.close(code=1008, reason=reason)
        logger.warning(
            "ai ws auth failed: room=%s reason=%s headers=%s",
            room_id,
            reason,
            rate_headers,
        )
        return

    room_version_server = _room_head_version(room_id)
    if room_version is not None and room_version != room_version_server:
        inc_counter("ws_ai_reconnect_total", labels={"room_id": room_id, "outcome": "version_mismatch"})
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "reconnect_required",
                "code": PolicyErrorCode.RECONNECT_REQUIRES_SNAPSHOT,
                "message": "room_version mismatch, request latest snapshot",
                "room_version": room_version_server,
                "snapshot_required": True,
            },
        )
        await websocket.close(code=1008, reason=PolicyErrorCode.RECONNECT_REQUIRES_SNAPSHOT)
        return

    await ai_ws_manager.connect(
        websocket,
        room_id,
        client_session_id=client_session_id,
    )
    inc_counter("ws_ai_handshake_total", labels={"room_id": room_id, "outcome": "connected"})
    if client_session_id:
        logger.debug(
            "AI WS client session: room=%s user=%s session=%s",
            room_id,
            current_user.id,
            client_session_id,
        )

    if resume_from_seq is not None:
        inc_counter("ws_ai_reconnect_total", labels={"room_id": room_id, "outcome": "resume_requested"})
        ok, missed = ai_ws_manager.get_missing_messages(room_id, resume_from_seq)
        if not ok:
            await websocket.send_json(
                {
                    "type": "reconnect_required",
                    "code": PolicyErrorCode.RECONNECT_REQUIRES_SNAPSHOT,
                    "message": "resume window expired, request room snapshot",
                    "room_version": room_version_server,
                    "snapshot_required": True,
                },
            )
            await websocket.close(code=1008, reason=PolicyErrorCode.RECONNECT_REQUIRES_SNAPSHOT)
            return

        if missed:
            await websocket.send_json(
                {
                    "type": "resume",
                    "room_id": room_id,
                    "room_version": room_version_server,
                    "events": missed,
                    "event_count": len(missed),
                }
            )
            inc_counter(
                "ws_ai_reconnect_total",
                labels={"room_id": room_id, "outcome": "resume_recovered"},
            )
        else:
            inc_counter(
                "ws_ai_reconnect_total",
                labels={"room_id": room_id, "outcome": "resume_no_events"},
            )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                inc_counter("ws_ai_message_total", labels={"room_id": room_id, "outcome": "json_ok"})
            except json.JSONDecodeError:
                inc_counter("ws_ai_message_total", labels={"room_id": room_id, "outcome": "json_error"})
                await ai_ws_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "error",
                        "code": "INVALID_MESSAGE",
                        "message": "invalid JSON",
                        "request_id": None,
                        "idempotency_key": None,
                        "client_session_id": client_session_id,
                    },
                )
                continue

            if data.get("type") == "ack" and data.get("last_seq") is not None:
                # Client side ack is used for future fine-grained replay control.
                continue

            if data.get("type") != "request":
                inc_counter(
                    "ws_ai_message_total",
                    labels={"room_id": room_id, "outcome": "invalid_type"},
                )
                await ai_ws_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "error",
                        "code": "INVALID_MESSAGE_TYPE",
                        "message": "invalid message type, expect {type: 'request'}",
                        "request_id": data.get("request_id"),
                        "idempotency_key": data.get("idempotency_key"),
                        "client_session_id": client_session_id,
                    },
                )
                continue

            request_id = str(data.get("request_id") or int(time.time() * 1000))
            idempotency_key = str(data.get("idempotency_key") or request_id)

            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                inc_counter(
                    "ws_ai_message_total",
                    labels={"room_id": room_id, "outcome": "empty_prompt"},
                )
                await ai_ws_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "error",
                        "code": "INVALID_REQUEST",
                        "message": "prompt is required",
                        "request_id": request_id,
                        "idempotency_key": idempotency_key,
                        "client_session_id": client_session_id,
                    },
                )
                continue

            processed_prompt = prompt
            mode = str(data.get("mode", "agent"))
            if mode == "mermaid" and "mermaid" not in prompt.lower():
                processed_prompt = f"Please use mermaid syntax to implement: {prompt}"

            timeout_ms = data.get("timeout_ms")
            explain = bool(data.get("explain", False))
            current_room_version = _room_head_version(room_id)
            request_start = time.time()

            await ai_ws_manager.broadcast_to_room(
                room_id,
                {
                    "type": "started",
                    "code": "IN_PROGRESS",
                    "request_id": request_id,
                    "idempotency_key": idempotency_key,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "room_version": current_room_version,
                    "user_id": current_user.id,
                    "client_session_id": client_session_id,
                },
            )

            async def _broadcast_step(step: Any) -> None:
                await ai_ws_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "step",
                        "code": "STEP",
                        "request_id": request_id,
                        "idempotency_key": idempotency_key,
                        "step_number": step.step_number,
                        "thought": step.thought,
                        "action": step.action,
                        "action_input": step.action_input,
                        "observation": (
                            step.observation[:500]
                            if (step.observation and len(step.observation) > 500)
                            else step.observation
                        ),
                        "success": step.success,
                        "latency_ms": round(step.latency_ms, 2),
                        "room_version": _room_head_version(room_id),
                        "client_session_id": client_session_id,
                    },
                )

            try:
                inc_counter(
                    "ws_ai_request_total",
                    labels={"room_id": room_id, "outcome": "started"},
                )
                result = await ai_service.process_request(
                    user_input=processed_prompt,
                    session_id=room_id,
                    step_callback=_broadcast_step,
                    theme=str(data.get("theme", "light")),
                    virtual_mode=bool(data.get("virtual_mode", False)),
                    conversation_id=data.get("conversation_id"),
                    target_diagram_id=data.get("target_diagram_id"),
                    target_semantic_id=data.get("target_semantic_id"),
                    edit_scope=data.get("edit_scope", "create_new"),
                    mode=mode,
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                    timeout_ms=timeout_ms,
                    explain=explain,
                    source="ws",
                    user_id=str(current_user.id) if current_user.id is not None else None,
                )
                request_ms = (time.time() - request_start) * 1000
                observe_ms(
                    "ws_ai_request_duration_ms",
                    request_ms,
                    {"room_id": room_id, "status": "success"},
                )
                inc_counter("ws_ai_request_total", labels={"room_id": room_id, "outcome": "success"})

                await ai_ws_manager.broadcast_to_room(
                    room_id,
                    _build_complete_payload(
                        result=result,
                        request_id=request_id,
                        idempotency_key=idempotency_key,
                        room_version=_room_head_version(room_id),
                        client_session_id=client_session_id,
                    ),
                )
            except Exception as exc:  # pylint: disable=broad-except
                request_ms = (time.time() - request_start) * 1000
                observe_ms(
                    "ws_ai_request_duration_ms",
                    request_ms,
                    {"room_id": room_id, "status": "error"},
                )
                inc_counter("ws_ai_request_total", labels={"room_id": room_id, "outcome": "error"})
                logger.error("AI websocket processing error: %s", exc)
                await ai_ws_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "error",
                        "status": "error",
                        "request_id": request_id,
                        "idempotency_key": idempotency_key,
                        "message": str(exc),
                        "code": PolicyErrorCode.TXN_ROLLBACK,
                        "client_session_id": client_session_id,
                    },
                )

    except WebSocketDisconnect:
        inc_counter("ws_ai_handshake_total", labels={"room_id": room_id, "outcome": "disconnect"})
        ai_ws_manager.disconnect(websocket, room_id)
    except Exception as exc:  # pylint: disable=broad-except
        if _is_transport_disconnect_error(exc):
            inc_counter("ws_ai_handshake_total", labels={"room_id": room_id, "outcome": "disconnect"})
            logger.info("AI websocket disconnected during transport cleanup: room=%s", room_id)
        else:
            inc_counter("ws_ai_handshake_total", labels={"room_id": room_id, "outcome": "error"})
            logger.error("AI websocket failed: %s", exc)
        ai_ws_manager.disconnect(websocket, room_id)

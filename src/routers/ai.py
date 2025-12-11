"""模块名称: ai
主要功能: AI Agent API 路由

提供 AI Agent 的 HTTP API 接口，包括:
- 生成/绘图请求
- 流式响应 (WebSocket)
- 运行历史查询
- 运行详情查询
- 工具列表
- Agent 状态监控
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.agent.core.agent import RoomLockManager, ReActStep
from src.agent.core.tools import registry
from src.agent.prompts import prompt_manager
from src.db.database import get_session
from src.logger import get_logger
from src.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI"])
logger = get_logger(__name__)


# ==================== 请求/响应模型 ====================


class GenerateRequest(BaseModel):
    """AI 生成请求模型

    Attributes:
        prompt: 用户输入的提示词
        room_id: 目标房间 ID
    """

    prompt: str = Field(
        ..., description="用户输入的提示词", min_length=1, max_length=2000
    )
    room_id: str = Field(..., description="目标房间 ID")


class GenerateResponse(BaseModel):
    """AI 生成响应模型

    Attributes:
        status: 请求状态 (success/error)
        response: AI 响应文本
        run_id: 运行记录 ID
        elements_created: 创建的元素 ID 列表
        tools_used: 使用的工具列表
    """

    status: str
    response: str
    run_id: int
    elements_created: list = []
    tools_used: list = []


class RunHistoryRequest(BaseModel):
    """运行历史查询请求

    Attributes:
        room_id: 房间 ID
        limit: 返回数量限制
    """

    room_id: str = Field(..., description="房间 ID")
    limit: int = Field(20, description="返回数量限制", ge=1, le=100)


# ==================== API 路由 ====================


@router.post("/generate", response_model=GenerateResponse)
async def generate_shapes(
    request: GenerateRequest, session: Session = Depends(get_session)
):
    """使用 AI Agent 根据用户描述在白板上绘制图形

    支持:
    - 流程图绘制
    - 数据流图绘制
    - 架构图绘制
    - 一般的图形创建

    Args:
        request: AI 生成请求对象
        session: 数据库会话

    Returns:
        GenerateResponse: AI 处理结果

    Raises:
        HTTPException: 处理失败时抛出 500 错误
    """
    logger.info(
        "收到 AI 生成请求",
        extra={"room_id": request.room_id, "prompt_length": len(request.prompt)},
    )

    try:
        result = await ai_service.process_request(
            user_input=request.prompt, session_id=request.room_id, db=session
        )

        return GenerateResponse(
            status=result.get("status", "success"),
            response=result.get("response", ""),
            run_id=result.get("run_id", 0),
            elements_created=result.get("elements_created", []),
            tools_used=result.get("tools_used", []),
        )

    except Exception as e:  # pylint: disable=broad-except
        logger.error("AI 生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/runs/{room_id}")
async def get_room_runs(
    room_id: str, limit: int = 20, session: Session = Depends(get_session)
):
    """获取房间的 AI 运行历史

    Args:
        room_id: 房间 ID
        limit: 返回数量限制
        session: 数据库会话

    Returns:
        dict: 运行历史列表
    """
    result = await ai_service.get_run_history(
        session_id=room_id, db=session, limit=limit
    )
    return result


@router.get("/run/{run_id}")
async def get_run_detail(run_id: int, session: Session = Depends(get_session)):
    """获取指定运行的详情

    包含运行的所有工具调用记录。

    Args:
        run_id: 运行记录 ID
        session: 数据库会话

    Returns:
        dict: 运行详情

    Raises:
        HTTPException: 运行记录不存在时抛出 404 错误
    """
    result = await ai_service.get_run_detail(run_id, session)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=404, detail=result.get("message", "run_not_found")
        )

    return result


# ==================== 管理 API ====================


@router.get("/tools")
async def list_tools():
    """获取所有可用工具列表

    返回 AI Agent 可以使用的所有工具及其元数据。

    Returns:
        dict: 工具列表
    """
    tools = registry.list_tools()
    return {"status": "success", "count": len(tools), "tools": tools}


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """获取单个工具的详细信息

    Args:
        tool_name: 工具名称

    Returns:
        dict: 工具详情

    Raises:
        HTTPException: 工具不存在时抛出 404 错误
    """
    meta = registry.get_metadata(tool_name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    schema = registry.get_schema(tool_name) or {}

    return {
        "status": "success",
        "tool": {
            "name": meta.name,
            "description": meta.description,
            "category": meta.category.value,
            "requires_room": meta.requires_room,
            "timeout": meta.timeout,
            "retries": meta.retries,
            "dangerous": meta.dangerous,
            "schema": schema.get("function", {}).get("parameters", {}),
        },
    }


@router.get("/status")
async def get_agent_status():
    """获取 Agent 系统状态

    返回当前活跃房间、工具数量等状态信息。

    Returns:
        dict: 系统状态
    """
    # 获取活跃房间列表
    active_rooms = list(RoomLockManager._active_rooms)

    # 统计工具
    tools = registry.list_tools()
    enabled_tools = [t for t in tools if t.get("enabled")]

    # 按分类统计
    category_counts = {}
    for tool in tools:
        cat = tool.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "status": "success",
        "agent": {
            "active_rooms": active_rooms,
            "active_count": len(active_rooms),
        },
        "tools": {
            "total": len(tools),
            "enabled": len(enabled_tools),
            "by_category": category_counts,
        },
    }


@router.get("/status/{room_id}")
async def get_room_agent_status(room_id: str):
    """检查指定房间的 Agent 状态

    Args:
        room_id: 房间 ID

    Returns:
        dict: 房间 Agent 状态
    """
    is_busy = RoomLockManager.is_room_busy(room_id)

    return {
        "status": "success",
        "room_id": room_id,
        "is_busy": is_busy,
        "message": "房间正在处理 AI 任务" if is_busy else "房间空闲",
    }


@router.post("/cancel/{run_id}")
async def cancel_run(run_id: int):
    """取消正在进行的 AI 请求

    Args:
        run_id: 运行记录 ID

    Returns:
        dict: 操作结果
    """
    result = await ai_service.cancel_request(run_id)
    return result


@router.get("/stats")
async def get_service_stats():
    """获取 AI 服务统计信息

    返回请求总数、成功率、平均响应时间等统计数据。

    Returns:
        dict: 服务统计信息
    """
    return ai_service.get_service_status()


@router.post("/tools/{tool_name}/disable")
async def disable_tool(tool_name: str):
    """禁用指定工具

    Args:
        tool_name: 工具名称

    Returns:
        dict: 操作结果
    """
    return ai_service.disable_tool(tool_name)


@router.post("/tools/{tool_name}/enable")
async def enable_tool(tool_name: str):
    """启用指定工具

    Args:
        tool_name: 工具名称

    Returns:
        dict: 操作结果
    """
    return ai_service.enable_tool(tool_name)


# ==================== 模板 API ====================


@router.get("/templates")
async def list_templates():
    """列出所有可用的 Prompt 模板

    Returns:
        dict: 模板列表
    """
    templates = prompt_manager.list_templates()
    return {"status": "success", "count": len(templates), "templates": templates}


@router.get("/templates/{template_name}")
async def get_template(template_name: str):
    """获取模板源码

    Args:
        template_name: 模板名称

    Returns:
        dict: 模板源码
    """
    source = prompt_manager.get_template_source(template_name)
    if source is None:
        raise HTTPException(status_code=404, detail=f"模板 {template_name} 不存在")

    return {
        "status": "success",
        "name": template_name,
        "source": source,
        "length": len(source),
    }


class RenderTemplateRequest(BaseModel):
    """渲染模板请求"""

    template_name: str = Field(..., description="模板名称")
    variables: dict = Field(default_factory=dict, description="模板变量")


# ==================== WebSocket 流式响应 ====================


class AIWebSocketManager:
    """AI WebSocket 连接管理器

    管理每个房间的 WebSocket 连接，支持向多个连接广播消息。
    """

    def __init__(self):
        # room_id -> list of active websockets
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """接受 WebSocket 连接"""
        await websocket.accept()
        if room_id not in self._connections:
            self._connections[room_id] = []
        self._connections[room_id].append(websocket)
        logger.info("AI WebSocket 连接: room=%s", room_id)

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """断开连接"""
        if room_id in self._connections:
            if websocket in self._connections[room_id]:
                self._connections[room_id].remove(websocket)
            if not self._connections[room_id]:
                del self._connections[room_id]
        logger.info("AI WebSocket 断开: room=%s", room_id)

    async def broadcast_to_room(self, room_id: str, message: dict) -> None:
        """向房间所有连接广播消息"""
        if room_id not in self._connections:
            return

        disconnected = []
        for ws in self._connections[room_id]:
            try:
                await ws.send_json(message)
            except Exception:  # pylint: disable=broad-except
                disconnected.append(ws)

        # 清理断开的连接
        for ws in disconnected:
            self._connections[room_id].remove(ws)


# 全局 WebSocket 管理器
ai_ws_manager = AIWebSocketManager()


@router.websocket("/stream/{room_id}")
async def ai_stream_websocket(
    websocket: WebSocket,
    room_id: str,
):
    """WebSocket 流式 AI 响应

    连接后发送 JSON 消息开始请求:
    {"type": "request", "prompt": "画一个流程图"}

    接收实时步骤消息:
    {"type": "step", "step_number": 1, "thought": "...", "action": "create_flowchart_node", ...}
    {"type": "tool_result", "tool": "create_flowchart_node", "result": {...}}
    {"type": "complete", "response": "已完成绘制", "elements_created": [...]}
    {"type": "error", "message": "..."}
    """
    await ai_ws_manager.connect(websocket, room_id)

    try:
        while True:
            # 接收请求
            data = await websocket.receive_json()

            if data.get("type") != "request":
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "无效消息类型，请发送 {type: 'request', prompt: '...'}",
                    }
                )
                continue

            prompt = data.get("prompt", "")
            if not prompt:
                await websocket.send_json(
                    {"type": "error", "message": "prompt 不能为空"}
                )
                continue

            # 发送开始消息
            await websocket.send_json(
                {
                    "type": "started",
                    "room_id": room_id,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                }
            )

            # 处理请求
            try:
                result = await ai_service.process_request_with_stream(
                    user_input=prompt,
                    session_id=room_id,
                    step_callback=lambda step: _broadcast_step(
                        websocket, room_id, step
                    ),
                )

                # 发送完成消息
                await websocket.send_json(
                    {
                        "type": "complete",
                        "status": result.get("status", "success"),
                        "response": result.get("response", ""),
                        "run_id": result.get("run_id", 0),
                        "elements_created": result.get("elements_created", []),
                        "tools_used": result.get("tools_used", []),
                        "metrics": result.get("metrics", {}),
                    }
                )

            except Exception as e:  # pylint: disable=broad-except
                logger.error("AI WebSocket 处理错误: %s", e)
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        ai_ws_manager.disconnect(websocket, room_id)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("AI WebSocket 异常: %s", e)
        ai_ws_manager.disconnect(websocket, room_id)


async def _broadcast_step(websocket: WebSocket, _room_id: str, step: ReActStep) -> None:
    """广播 Agent 步骤"""
    try:
        message = {
            "type": "step",
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
        }
        await websocket.send_json(message)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("广播步骤失败: %s", e)

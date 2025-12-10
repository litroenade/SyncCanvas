"""模块名称: config_router
主要功能: 配置管理 API 路由

提供前端配置页面所需的 REST API 接口。
"""

from typing import Any, Dict

from fastapi import APIRouter

from src.config import config as config_manager
from src.agent.core.agent import AgentConfig
from src.services.config_service import config_to_list

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/list")
async def get_all_configs() -> Dict[str, Any]:
    """获取所有配置列表
    
    Returns:
        包含各配置分组的字典
    """
    return {
        "status": "success",
        "data": {
            "ai": config_to_list(config_manager.config.ai),
            "server": config_to_list(config_manager.config.server),
            "database": config_to_list(config_manager.config.database),
            "security": config_to_list(config_manager.config.security),
            "agent": config_to_list(AgentConfig()),
        }
    }


@router.get("/ai")
async def get_ai_config() -> Dict[str, Any]:
    """获取 AI 配置列表"""
    return {
        "status": "success",
        "data": config_to_list(config_manager.config.ai)
    }


@router.get("/server")
async def get_server_config() -> Dict[str, Any]:
    """获取服务器配置列表"""
    return {
        "status": "success",
        "data": config_to_list(config_manager.config.server)
    }


@router.get("/agent")
async def get_agent_config() -> Dict[str, Any]:
    """获取 Agent 默认配置列表"""
    return {
        "status": "success",
        "data": config_to_list(AgentConfig())
    }

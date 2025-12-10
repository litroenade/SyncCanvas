"""模块名称: settings
主要功能: 设置管理 API 路由

提供 AI 配置的查询和更新接口。
"""

from typing import Dict, List, Optional
import httpx

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import config as config_manager
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["设置"])


# ==================== 请求/响应模型 ====================

class AIConfigResponse(BaseModel):
    """AI 配置响应"""
    provider: str = Field(description="当前提供商")
    model: str = Field(description="当前模型")
    base_url: str = Field(description="API 地址")
    has_api_key: bool = Field(description="是否配置了 API Key")
    tool_choice: str = Field(description="工具调用模式")
    max_tool_calls: int = Field(description="最大工具调用次数")
    # 备用配置
    fallback_provider: str = Field(description="备用提供商")
    fallback_model: str = Field(description="备用模型")
    fallback_base_url: str = Field(description="备用 API 地址")
    has_fallback_api_key: bool = Field(description="是否配置了备用 API Key")


class AIConfigUpdate(BaseModel):
    """AI 配置更新请求"""
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    tool_choice: Optional[str] = None
    max_tool_calls: Optional[int] = None
    # 备用配置
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    fallback_base_url: Optional[str] = None
    fallback_api_key: Optional[str] = None


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    object: str = "model"
    owned_by: Optional[str] = None


class ModelsResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelInfo]
    total: int


# ==================== 常用供应商 ====================

COMMON_PROVIDERS = [
    {"name": "SiliconFlow", "url": "https://api.siliconflow.cn/v1"},
    {"name": "OpenAI", "url": "https://api.openai.com/v1"},
    {"name": "DeepSeek", "url": "https://api.deepseek.com/v1"},
    {"name": "通义千问", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"name": "豆包", "url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"name": "智谱清言", "url": "https://open.bigmodel.cn/api/paas/v4"},
    {"name": "Kimi", "url": "https://api.moonshot.cn/v1"},
    {"name": "Google Gemini", "url": "https://generativelanguage.googleapis.com/v1beta/openai"},
]


# ==================== API 路由 ====================

@router.get("/ai", response_model=AIConfigResponse)
async def get_ai_config() -> AIConfigResponse:
    """获取当前 AI 配置
    
    返回当前 AI 配置（API Key 只返回是否存在）
    """
    ai_config = config_manager.config.ai
    return AIConfigResponse(
        provider=ai_config.provider,
        model=ai_config.model,
        base_url=ai_config.base_url,
        has_api_key=bool(ai_config.api_key),
        tool_choice=ai_config.tool_choice,
        max_tool_calls=ai_config.max_tool_calls,
        fallback_provider=ai_config.fallback_provider,
        fallback_model=ai_config.fallback_model,
        fallback_base_url=ai_config.fallback_base_url,
        has_fallback_api_key=bool(ai_config.fallback_api_key),
    )


@router.put("/ai", response_model=AIConfigResponse)
async def update_ai_config(update: AIConfigUpdate) -> AIConfigResponse:
    """更新 AI 配置
    
    只更新提供的字段，未提供的字段保持不变。
    更新后配置会保存到 config.toml。
    """
    ai_config = config_manager.config.ai

    # 更新提供的字段
    if update.provider is not None:
        ai_config.provider = update.provider
    if update.model is not None:
        ai_config.model = update.model
    if update.base_url is not None:
        ai_config.base_url = update.base_url
    if update.api_key is not None:
        ai_config.api_key = update.api_key
    if update.tool_choice is not None:
        ai_config.tool_choice = update.tool_choice
    if update.max_tool_calls is not None:
        ai_config.max_tool_calls = update.max_tool_calls
    if update.fallback_provider is not None:
        ai_config.fallback_provider = update.fallback_provider
    if update.fallback_model is not None:
        ai_config.fallback_model = update.fallback_model
    if update.fallback_base_url is not None:
        ai_config.fallback_base_url = update.fallback_base_url
    if update.fallback_api_key is not None:
        ai_config.fallback_api_key = update.fallback_api_key

    # 保存配置
    config_manager._save()

    logger.info("AI 配置已更新", extra={
        "provider": ai_config.provider,
        "model": ai_config.model,
    })

    return await get_ai_config()


@router.get("/ai/providers")
async def get_common_providers() -> List[Dict[str, str]]:
    """获取常用 AI 供应商列表"""
    return COMMON_PROVIDERS


@router.get("/ai/models", response_model=ModelsResponse)
async def get_available_models(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ModelsResponse:
    """获取可用模型列表
    
    从指定的 API 获取可用模型列表。
    如果不提供参数，使用当前配置的 API。
    
    Args:
        base_url: API 基础 URL (可选，默认使用当前配置)
        api_key: API Key (可选，默认使用当前配置)
    """
    # 使用提供的参数或默认配置
    url = base_url or config_manager.llm_base_url
    key = api_key or config_manager.llm_api_key

    if not url:
        raise HTTPException(400, "未配置 API 地址")
    if not key:
        raise HTTPException(400, "未配置 API Key")

    # 构建 models 端点 URL
    models_url = url.rstrip("/") + "/models"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                models_url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

            # 解析模型列表 (支持 OpenAI 格式)
            models = []
            raw_models = data.get("data", []) or data.get("models", [])

            for m in raw_models:
                if isinstance(m, str):
                    models.append(ModelInfo(id=m))
                elif isinstance(m, dict):
                    models.append(ModelInfo(
                        id=m.get("id", "unknown"),
                        object=m.get("object", "model"),
                        owned_by=m.get("owned_by"),
                    ))

            # 按 ID 排序
            models.sort(key=lambda x: x.id)

            logger.info(f"获取到 {len(models)} 个可用模型", extra={
                "base_url": url,
            })

            return ModelsResponse(models=models, total=len(models))

    except httpx.HTTPStatusError as e:
        logger.error(f"获取模型列表失败: HTTP {e.response.status_code}")
        raise HTTPException(e.response.status_code, f"获取模型失败: {e.response.text[:200]}")
    except httpx.RequestError as e:
        logger.error(f"获取模型列表请求错误: {e}")
        raise HTTPException(502, f"请求失败: {str(e)}")
    except Exception as e:
        logger.error(f"获取模型列表异常: {e}")
        raise HTTPException(500, f"获取模型失败: {str(e)}")

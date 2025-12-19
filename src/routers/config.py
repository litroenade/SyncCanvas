from typing import Dict, Any, List, Optional
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from src.config import config, ModelConfig
from src.deps import get_current_user
from src.db.user import User
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["Config"])


class UpdateConfigRequest(BaseModel):
    value: Any


class UpdateModelGroupRequest(BaseModel):
    name: str
    config: ModelConfig


class AIConfigResponse(BaseModel):
    """AI 配置响应"""

    provider: str = Field(description="当前提供商")
    model: str = Field(description="当前模型")
    base_url: str = Field(description="API 地址")
    has_api_key: bool = Field(description="是否配置了 API Key")
    tool_choice: str = Field(description="工具调用模式")
    max_tool_calls: int = Field(description="最大工具调用次数")
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
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    fallback_base_url: Optional[str] = None
    fallback_api_key: Optional[str] = None


class ModelInfo(BaseModel):
    """
    模型信息
    """

    id: str
    object: str = "model"
    owned_by: Optional[str] = None


class ModelsResponse(BaseModel):
    """模型列表响应"""

    models: List[ModelInfo]
    total: int


COMMON_PROVIDERS = [
    {"name": "SiliconFlow", "url": "https://api.siliconflow.cn/v1"},
    {"name": "OpenAI", "url": "https://api.openai.com/v1"},
    {"name": "DeepSeek", "url": "https://api.deepseek.com/v1"},
    {"name": "通义千问", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"name": "豆包", "url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"name": "智谱清言", "url": "https://open.bigmodel.cn/api/paas/v4"},
    {"name": "Kimi", "url": "https://api.moonshot.cn/v1"},
    {
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
]


@router.get("/list")
async def get_all_configs(current_user: User = Depends(get_current_user)):
    """获取所有配置"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return {
        "status": "success",
        "data": {
            "ai": _get_config_items(config.config.ai),
            "server": _get_config_items(config.config.server),
            "database": _get_config_items(config.config.database),
            "security": _get_config_items(config.config.security),
        },
    }


@router.put("/{group}/{key}")
async def update_config(
    group: str,
    key: str,
    req: UpdateConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """更新配置项"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    group_obj = getattr(config.config, group, None)
    if not group_obj:
        raise HTTPException(status_code=404, detail=f"配置组 {group} 不存在")

    if not hasattr(group_obj, key):
        raise HTTPException(status_code=404, detail=f"配置项 {key} 不存在")

    setattr(group_obj, key, req.value)
    config._save()

    return {"status": "success"}


@router.get("/models")
async def get_model_groups(current_user: User = Depends(get_current_user)):
    """获取所有模型组"""
    # TODO: 暂时移除管理员权限检查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="需要管理员权限")
    return config.config.ai.model_groups


@router.post("/models")
async def update_model_group(
    req: UpdateModelGroupRequest, current_user: User = Depends(get_current_user)
):
    """创建或更新模型组"""
    # TODO: 暂时移除管理员权限检查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="需要管理员权限")

    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="模型组名称不能为空")

    config.config.ai.model_groups[name] = req.config
    config._save()
    return {"status": "success", "message": f"模型组 {name} 已保存"}


@router.delete("/models/{name}")
async def delete_model_group(name: str, current_user: User = Depends(get_current_user)):
    """删除模型组"""
    # TODO: 暂时移除管理员权限检查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="需要管理员权限")

    if name in config.config.ai.model_groups:
        del config.config.ai.model_groups[name]
        config._save()
        return {"status": "success", "message": f"模型组 {name} 已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"模型组 {name} 不存在")


@router.get("/models/types")
async def get_model_types():
    """获取支持的模型类型"""
    return [
        {
            "value": "chat",
            "label": "对话模型",
            "icon": "Chat",
            "description": "标准对话模型 (如 GPT-4, Qwen)",
            "color": "primary",
        },
        {
            "value": "code",
            "label": "代码模型",
            "icon": "Code",
            "description": "代码生成专用模型 (如 DeepSeek Coder)",
            "color": "info",
        },
        {
            "value": "vision",
            "label": "视觉模型",
            "icon": "Image",
            "description": "支持图片理解的模型 (如 GPT-4V)",
            "color": "warning",
        },
    ]


@router.get("/ai", response_model=AIConfigResponse)
async def get_ai_config(
    current_user: User = Depends(get_current_user),
) -> AIConfigResponse:
    """获取当前 AI 配置"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    ai_config = config.config.ai
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
async def update_ai_config(
    update: AIConfigUpdate, current_user: User = Depends(get_current_user)
) -> AIConfigResponse:
    """更新 AI 配置"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    ai_config = config.config.ai

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

    config._save()
    logger.info(
        "AI 配置已更新",
        extra={"provider": ai_config.provider, "model": ai_config.model},
    )

    return await get_ai_config(current_user)


@router.get("/ai/providers")
async def get_common_providers() -> List[Dict[str, str]]:
    """获取常用 AI 供应商列表"""
    return COMMON_PROVIDERS


@router.get("/ai/models", response_model=ModelsResponse)
async def get_available_models(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ModelsResponse:
    """获取可用模型列表"""
    url = base_url or config.llm_base_url
    key = api_key or config.llm_api_key

    if not url:
        raise HTTPException(400, "未配置 API 地址")
    if not key:
        raise HTTPException(400, "未配置 API Key")

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

            models = []
            raw_models = data.get("data", []) or data.get("models", [])

            for m in raw_models:
                if isinstance(m, str):
                    models.append(ModelInfo(id=m))
                elif isinstance(m, dict):
                    models.append(
                        ModelInfo(
                            id=m.get("id", "unknown"),
                            object=m.get("object", "model"),
                            owned_by=m.get("owned_by"),
                        )
                    )

            models.sort(key=lambda x: x.id)
            logger.info("获取到 %d 个可用模型", len(models), extra={"base_url": url})

            return ModelsResponse(models=models, total=len(models))

    except httpx.HTTPStatusError as e:
        logger.error("获取模型列表失败: HTTP %d", e.response.status_code)
        raise HTTPException(
            e.response.status_code, f"获取模型失败: {e.response.text[:200]}"
        ) from e
    except httpx.RequestError as e:
        logger.error("获取模型列表请求错误: %s", e)
        raise HTTPException(502, f"请求失败: {str(e)}") from e
    except Exception as e:  # pylint: disable=broad-except
        logger.error("获取模型列表异常: %s", e)
        raise HTTPException(500, f"获取模型失败: {str(e)}") from e


def _get_config_items(model: BaseModel) -> List[Dict[str, Any]]:
    """将 Pydantic 模型转换为前端可用的配置项列表"""
    items = []
    for name, field in model.model_fields.items():
        value = getattr(model, name)

        if name == "model_groups":
            continue

        _extra = field.json_schema_extra
        extra = _extra if isinstance(_extra, dict) else {}
        if extra.get("is_hidden"):
            continue

        type_str = "str"
        if isinstance(value, bool):
            type_str = "bool"
        elif isinstance(value, int):
            type_str = "int"
        elif isinstance(value, float):
            type_str = "float"
        elif isinstance(value, list):
            type_str = "list"
        elif isinstance(value, dict):
            type_str = "dict"

        items.append(
            {
                "key": name,
                "value": value,
                "type": type_str,
                "title": field.title or name,
                "description": field.description or "",
                "is_secret": extra.get("is_secret", False),
                "is_textarea": extra.get("is_textarea", False),
                "placeholder": extra.get("placeholder", ""),
                "overridable": extra.get("overridable", False),
                "required": field.is_required(),
                "ref_model_groups": extra.get("ref_model_groups", False),
                "model_type": extra.get("model_type", ""),
                "enable_toggle": extra.get("enable_toggle", ""),
            }
        )
    return items

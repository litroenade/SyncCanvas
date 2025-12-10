from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.config import config, ModelConfig
from src.deps import get_current_user
from src.db.user import User

router = APIRouter(prefix="/config", tags=["Config"])


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


@router.get("/ai")
async def get_ai_config(current_user: User = Depends(get_current_user)):
    """获取 AI 配置"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return {"status": "success", "data": _get_config_items(config.config.ai)}


class UpdateConfigRequest(BaseModel):
    value: Any


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

    # 立即保存
    config._save()

    return {"status": "success"}


# ==================== 模型组 API ====================


@router.get("/models")
async def get_model_groups(current_user: User = Depends(get_current_user)):
    """获取所有模型组"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return config.config.ai.model_groups


class UpdateModelGroupRequest(BaseModel):
    name: str
    config: ModelConfig


@router.post("/models")
async def update_model_group(
    req: UpdateModelGroupRequest, current_user: User = Depends(get_current_user)
):
    """创建或更新模型组"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    # 清理名称
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="模型组名称不能为空")

    config.config.ai.model_groups[name] = req.config
    config._save()
    return {"status": "success", "message": f"模型组 {name} 已保存"}


@router.delete("/models/{name}")
async def delete_model_group(name: str, current_user: User = Depends(get_current_user)):
    """删除模型组"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

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


def _get_config_items(model: BaseModel) -> List[Dict[str, Any]]:
    """将 Pydantic 模型转换为前端可用的配置项列表"""
    items = []
    # 遍历字段定义
    for name, field in model.model_fields.items():
        # 获取当前值
        value = getattr(model, name)

        # 排除模型组字典自身
        if name == "model_groups":
            continue

        # 获取元数据
        extra = field.json_schema_extra or {}
        if extra.get("is_hidden"):
            continue

        # 确定类型
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

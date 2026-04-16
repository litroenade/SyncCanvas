"""Configuration management routes."""

from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.deps import get_current_user
from src.infra.config import ModelGroup, config
from src.infra.logging import get_logger
from src.persistence.db.models.users import User

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["Config"])


class UpdateConfigRequest(BaseModel):
    value: Any


class UpdateModelGroupRequest(BaseModel):
    name: str
    config: ModelGroup


class AIConfigResponse(BaseModel):
    """Current AI configuration exposed to the UI."""

    provider: str = Field(description="Current primary provider name.")
    model: str = Field(description="Current primary model name.")
    base_url: str = Field(description="Primary API base URL.")
    has_api_key: bool = Field(description="Whether the primary API key is configured.")
    tool_choice: str = Field(description="Tool call selection mode.")
    max_tool_calls: int = Field(description="Maximum tool calls per run.")
    fallback_provider: str = Field(description="Fallback provider name.")
    fallback_model: str = Field(description="Fallback model name.")
    fallback_base_url: str = Field(description="Fallback API base URL.")
    has_fallback_api_key: bool = Field(
        description="Whether the fallback API key is configured."
    )


class AIConfigUpdate(BaseModel):
    """Patch payload for AI configuration updates."""

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
    """Minimal model descriptor returned by upstream providers."""

    id: str
    object: str = "model"
    owned_by: Optional[str] = None


class ModelsResponse(BaseModel):
    """Collection of available upstream models."""

    models: List[ModelInfo]
    total: int


class SwitchModelGroupRequest(BaseModel):
    """Select the active model group for future requests."""

    group_name: str


COMMON_PROVIDERS = [
    {"name": "SiliconFlow", "url": "https://api.siliconflow.cn/v1"},
    {"name": "OpenAI", "url": "https://api.openai.com/v1"},
    {"name": "DeepSeek", "url": "https://api.deepseek.com/v1"},
    {
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
]


def _require_admin(current_user: User) -> None:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")


def _normalize_provider_base_url(url: str) -> str:
    """Normalize and validate provider base URLs before probing upstream APIs."""

    candidate = (url or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="API base URL is not configured")

    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid API base URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(status_code=400, detail="Invalid API base URL")

    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _iter_configured_model_credentials() -> Dict[str, str]:
    """Collect configured model probe targets keyed by normalized base URL."""

    credentials: Dict[str, str] = {}

    def register(url: Optional[str], api_key: Optional[str]) -> None:
        if not url:
            return
        try:
            normalized = _normalize_provider_base_url(url)
        except HTTPException:
            logger.warning("Skipping invalid configured model base URL", extra={"base_url": url})
            return
        if api_key and normalized not in credentials:
            credentials[normalized] = api_key

    ai_config = config.config.ai
    register(ai_config.base_url, ai_config.api_key)
    register(ai_config.fallback_base_url, ai_config.fallback_api_key)

    for group in ai_config.model_groups.values():
        register(group.chat_model.base_url, group.chat_model.api_key)
        if group.embedding_model:
            register(group.embedding_model.base_url, group.embedding_model.api_key)

    return credentials


def _iter_allowed_model_base_urls() -> set[str]:
    """Return normalized provider URLs that the model probe route may access."""

    allowed = set(_iter_configured_model_credentials().keys())
    for provider in COMMON_PROVIDERS:
        url = provider.get("url")
        if not url:
            continue
        try:
            allowed.add(_normalize_provider_base_url(url))
        except HTTPException:
            logger.warning("Skipping invalid common provider URL", extra={"base_url": url})
    return allowed


def _resolve_models_probe_base_url(base_url: Optional[str]) -> str:
    """Resolve the requested base URL and enforce the probe allowlist."""

    requested_url = base_url or config.llm_base_url
    normalized = _normalize_provider_base_url(requested_url)
    if normalized not in _iter_allowed_model_base_urls():
        logger.warning(
            "Rejected model probe for non-allowlisted base URL",
            extra={"base_url": normalized},
        )
        raise HTTPException(status_code=403, detail="API base URL is not allowlisted")
    return normalized


@router.get("/list")
async def get_all_configs(current_user: User = Depends(get_current_user)):
    """Return all editable configuration groups for the settings UI."""

    _require_admin(current_user)
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
    """Update one scalar config field and persist it."""

    _require_admin(current_user)

    group_obj = getattr(config.config, group, None)
    if not group_obj:
        raise HTTPException(status_code=404, detail=f"Config group '{group}' not found")

    if not hasattr(group_obj, key):
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    setattr(group_obj, key, req.value)
    config._save()
    return {"status": "success"}


@router.get("/models")
async def get_model_groups(current_user: User = Depends(get_current_user)):
    """Return all configured model groups for authenticated users."""

    return config.config.ai.model_groups


@router.post("/models")
async def update_model_group(
    req: UpdateModelGroupRequest,
    current_user: User = Depends(get_current_user),
):
    """Create or replace one model group."""

    _require_admin(current_user)

    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Model group name cannot be empty")

    config.config.ai.model_groups[name] = req.config.model_copy(update={"name": name})
    config._save()
    return {"status": "success", "message": f"Model group '{name}' saved"}


@router.delete("/models/{name}")
async def delete_model_group(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """Delete one configured model group."""

    _require_admin(current_user)

    if name not in config.config.ai.model_groups:
        raise HTTPException(status_code=404, detail=f"Model group '{name}' not found")

    del config.config.ai.model_groups[name]
    config._save()
    return {"status": "success", "message": f"Model group '{name}' deleted"}


@router.get("/models/current")
async def get_current_model_groups(current_user: User = Depends(get_current_user)):
    """Return the active model group name for authenticated users."""

    return {"current": config.config.ai.current_model_group}


@router.post("/models/switch")
async def switch_model_group(
    req: SwitchModelGroupRequest,
    current_user: User = Depends(get_current_user),
):
    """Switch the active model group used by the backend."""

    _require_admin(current_user)
    group_name = req.group_name.strip()

    if group_name and group_name not in config.config.ai.model_groups:
        raise HTTPException(status_code=404, detail=f"Model group '{group_name}' not found")

    config.config.ai.current_model_group = group_name
    config._save()
    return {
        "status": "success",
        "message": f"Switched model group to '{group_name or 'default'}'",
    }


@router.get("/models/types")
async def get_model_types(current_user: User = Depends(get_current_user)):
    """Return supported model categories for the settings UI."""

    return [
        {
            "value": "chat",
            "label": "Chat Model",
            "icon": "Chat",
            "description": "Standard dialogue models such as GPT-4 or Qwen.",
            "color": "primary",
        },
        {
            "value": "code",
            "label": "Code Model",
            "icon": "Code",
            "description": "Models specialized for code generation.",
            "color": "info",
        },
    ]


@router.get("/ai", response_model=AIConfigResponse)
async def get_ai_config(
    current_user: User = Depends(get_current_user),
) -> AIConfigResponse:
    """Return the current AI config for administrators."""

    _require_admin(current_user)
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
    update: AIConfigUpdate,
    current_user: User = Depends(get_current_user),
) -> AIConfigResponse:
    """Update the AI provider configuration."""

    _require_admin(current_user)
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
        "AI configuration updated",
        extra={"provider": ai_config.provider, "model": ai_config.model},
    )
    return await get_ai_config(current_user)


@router.get("/ai/providers")
async def get_common_providers(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, str]]:
    """Return common provider presets for authenticated users."""

    return COMMON_PROVIDERS


@router.get("/ai/models", response_model=ModelsResponse)
async def get_available_models(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> ModelsResponse:
    """Proxy the upstream /models endpoint for provider introspection."""

    _require_admin(current_user)

    url = _resolve_models_probe_base_url(base_url)
    key = api_key or _iter_configured_model_credentials().get(url) or config.llm_api_key

    if not key:
        raise HTTPException(status_code=400, detail="API key is not configured")

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
            payload = response.json()

        models: List[ModelInfo] = []
        raw_models = payload.get("data", []) or payload.get("models", [])
        for item in raw_models:
            if isinstance(item, str):
                models.append(ModelInfo(id=item))
            elif isinstance(item, dict):
                models.append(
                    ModelInfo(
                        id=item.get("id", "unknown"),
                        object=item.get("object", "model"),
                        owned_by=item.get("owned_by"),
                    )
                )

        models.sort(key=lambda model: model.id)
        logger.info(
            "Fetched %d upstream models",
            len(models),
            extra={"base_url": url},
        )
        return ModelsResponse(models=models, total=len(models))
    except httpx.HTTPStatusError as exc:
        logger.error("Failed to fetch models: HTTP %d", exc.response.status_code)
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Failed to fetch models: {exc.response.text[:200]}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Failed to fetch models: request error %s", exc)
        raise HTTPException(status_code=502, detail=f"Request failed: {exc}") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to fetch models: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {exc}") from exc


def _get_config_items(model: BaseModel) -> List[Dict[str, Any]]:
    """Convert a Pydantic model into UI-friendly config item metadata."""

    items: List[Dict[str, Any]] = []
    for name, field in type(model).model_fields.items():
        value = getattr(model, name)

        if name == "model_groups":
            continue

        extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
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


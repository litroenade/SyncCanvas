"""Config manager and singleton."""


import tomllib
from pathlib import Path
from typing import Any, Dict, Optional

import tomli_w

from src.infra.config.loader import CONFIG_DIR, CONFIG_FILE
from src.infra.config.schema import (
    AIProviderConfig,
    AppConfig,
    CanvasConfig,
    DatabaseConfig,
    LoggingConfig,
    SecurityConfig,
    ServerConfig,
)
from src.infra.logging import get_logger

logger = get_logger(__name__)


class ConfigManager:
    def __init__(self, config_file: Path = CONFIG_FILE):
        self._config_file = config_file
        self._config: Optional[AppConfig] = None
        self._last_mtime = 0.0
        self._ensure_config_dir()
        self._load()

    def _ensure_config_dir(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        default_config = AppConfig()
        code_version = default_config.version

        if not self._config_file.exists():
            self._config = default_config
            self._save()
            logger.info("Created default config file: %s", self._config_file)
            return

        try:
            mtime = self._config_file.stat().st_mtime
            if mtime <= self._last_mtime and self._config is not None:
                return

            with self._config_file.open("rb") as file_obj:
                raw = tomllib.load(file_obj)

            if "version" in raw and isinstance(raw["version"], int):
                raw["version"] = f"{raw['version']}.0.0"

            file_version = raw.get("version", "0.0.0")
            if self._version_compare(file_version, code_version) < 0:
                raw = self._migrate_config(raw, default_config)
                raw["version"] = code_version
            else:
                raw, _ = self._migrate_model_groups_if_needed(raw)

            self._config = AppConfig(**raw)
            if self._config.model_dump() != raw:
                self._save()

            self._last_mtime = self._config_file.stat().st_mtime
            logger.info("Loaded config version %s", self._config.version)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to load config: %s", exc)
            self._config = default_config

    def _version_compare(self, left: str, right: str) -> int:
        try:
            left_parts = [int(part) for part in left.split(".")]
            right_parts = [int(part) for part in right.split(".")]
        except (TypeError, ValueError, AttributeError):
            return -1

        for left_part, right_part in zip(left_parts, right_parts):
            if left_part < right_part:
                return -1
            if left_part > right_part:
                return 1
        return 0

    def _migrate_model_groups_if_needed(self, raw: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        if "ai" not in raw or "model_groups" not in raw["ai"]:
            return raw, False

        migrated = False
        old_groups = raw["ai"]["model_groups"]
        new_groups: Dict[str, Any] = {}
        for name, group_data in old_groups.items():
            if isinstance(group_data, dict) and "provider" in group_data and "chat_model" not in group_data:
                new_groups[name] = {
                    "name": name,
                    "chat_model": group_data,
                    "embedding_model": None,
                }
                migrated = True
            elif isinstance(group_data, dict) and "vision_model" in group_data:
                sanitized_group = dict(group_data)
                sanitized_group.pop("vision_model", None)
                new_groups[name] = sanitized_group
                migrated = True
            else:
                new_groups[name] = group_data

        if migrated:
            raw["ai"]["model_groups"] = new_groups
            for deprecated_field in ("current_vision_model", "current_embedding_model"):
                raw["ai"].pop(deprecated_field, None)
        return raw, migrated

    def _migrate_config(self, raw: Dict[str, Any], default: AppConfig) -> Dict[str, Any]:
        default_dict = default.model_dump()

        def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(base)
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        merged = deep_merge(default_dict, raw)

        if "security" in merged:
            merged["security"].pop("admin_key", None)
        if "logging" in merged:
            merged["logging"].pop("format", None)
        if "ai" in merged:
            for deprecated_field in ("current_vision_model", "current_embedding_model"):
                merged["ai"].pop(deprecated_field, None)

        merged, _ = self._migrate_model_groups_if_needed(merged)
        return merged

    def _save(self) -> None:
        if self._config is None:
            return
        try:
            data = self._config.model_dump(exclude_none=True)
            with self._config_file.open("wb") as file_obj:
                tomli_w.dump(data, file_obj)
            self._last_mtime = self._config_file.stat().st_mtime
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to save config: %s", exc)

    def reload(self) -> None:
        self._last_mtime = 0.0
        self._load()

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self._load()
        return self._config  # type: ignore[return-value]

    @property
    def security(self) -> SecurityConfig:
        return self.config.security

    @property
    def server(self) -> ServerConfig:
        return self.config.server

    @property
    def database(self) -> DatabaseConfig:
        return self.config.database

    @property
    def ai(self) -> AIProviderConfig:
        return self.config.ai

    @property
    def logging(self) -> LoggingConfig:
        return self.config.logging

    @property
    def canvas(self) -> CanvasConfig:
        return self.config.canvas

    @property
    def version(self) -> str:
        return self.config.version

    @property
    def secret_key(self) -> str:
        return self.config.security.secret_key

    @property
    def host(self) -> str:
        return self.config.server.host

    @property
    def port(self) -> int:
        return self.config.server.port

    @property
    def allowed_origins(self) -> list[str]:
        return self.config.server.allowed_origins

    @property
    def database_url(self) -> str:
        return self.config.database.url

    @property
    def db_echo(self) -> bool:
        return self.config.database.echo

    @property
    def llm_provider(self) -> str:
        return self.config.ai.provider

    @property
    def llm_model(self) -> str:
        return self.config.ai.model

    @property
    def llm_base_url(self) -> str:
        return self.config.ai.base_url

    @property
    def llm_api_key(self) -> str:
        key = self.config.ai.api_key
        if not key:
            key = self.config.ai.fallback_api_key
        return key

    @property
    def llm_fallback_provider(self) -> str:
        return self.config.ai.fallback_provider

    @property
    def llm_fallback_model(self) -> str:
        return self.config.ai.fallback_model

    @property
    def llm_fallback_base_url(self) -> str:
        return self.config.ai.fallback_base_url

    @property
    def llm_fallback_api_key(self) -> str:
        return self.config.ai.fallback_api_key

    @property
    def llm_tool_choice(self) -> str:
        return self.config.ai.tool_choice

    @property
    def llm_max_tool_calls(self) -> int:
        return self.config.ai.max_tool_calls


config = ConfigManager()

__all__ = ["ConfigManager", "config"]


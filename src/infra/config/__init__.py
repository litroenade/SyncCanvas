"""Canonical configuration exports."""

from src.infra.config.loader import CONFIG_DIR, CONFIG_FILE
from src.infra.config.manager import ConfigManager, config
from src.infra.config.schema import AppConfig, ExtraField, ModelConfig, ModelGroup

__all__ = [
    "AppConfig",
    "CONFIG_DIR",
    "CONFIG_FILE",
    "ConfigManager",
    "ExtraField",
    "ModelConfig",
    "ModelGroup",
    "config",
]

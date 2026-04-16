"""Config file path helpers."""

from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
CONFIG_FILE = CONFIG_DIR / "config.toml"

__all__ = ["CONFIG_DIR", "CONFIG_FILE"]

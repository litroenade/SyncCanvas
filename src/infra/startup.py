"""Startup helpers for local development server execution."""


import os
import socket

from src.infra.config import config

HOST_ENV_VAR = "SYNC_CANVAS_HOST"
PORT_ENV_VAR = "SYNC_CANVAS_PORT"
PORT_FALLBACK_ENV_VAR = "PORT"
RELOAD_ENV_VAR = "SYNC_CANVAS_RELOAD"


def resolve_server_host() -> str:
    return (os.getenv(HOST_ENV_VAR) or config.host).strip()


def resolve_server_port() -> int:
    raw_port = os.getenv(PORT_ENV_VAR) or os.getenv(PORT_FALLBACK_ENV_VAR)
    if raw_port is None:
        return config.port

    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid port override '{raw_port}'. Set {PORT_ENV_VAR} to an integer between 1 and 65535."
        ) from exc

    if port < 1 or port > 65535:
        raise RuntimeError(
            f"Invalid port override '{raw_port}'. Set {PORT_ENV_VAR} to an integer between 1 and 65535."
        )
    return port


def resolve_server_reload() -> bool:
    raw_reload = os.getenv(RELOAD_ENV_VAR)
    if raw_reload is None:
        return False

    normalized = raw_reload.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(
        f"Invalid reload override '{raw_reload}'. "
        f"Set {RELOAD_ENV_VAR} to one of: 1, true, yes, on, 0, false, no, off."
    )


def ensure_bind_available(host: str, port: int) -> None:
    probe_host = host.strip()
    if probe_host in {"", "0.0.0.0"}:
        probe_host = "127.0.0.1"
    elif probe_host == "::":
        probe_host = "::1"

    try:
        family = socket.AF_INET6 if ":" in probe_host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.25)
            status = probe.connect_ex((probe_host, port))
    except OSError as exc:
        winerror = getattr(exc, "winerror", None)
        if winerror in {10013, 10048} or exc.errno in {13, 48, 98}:
            raise RuntimeError(
                f"Cannot bind development server to {host}:{port}. "
                f"The port is already occupied or blocked by local policy. "
                f"Try `Get-NetTCPConnection -LocalPort {port}` in an elevated shell, "
                f"or start with `$env:{PORT_ENV_VAR}='8001'; uv run python main.py`."
            ) from exc
        raise RuntimeError(f"Cannot bind development server to {host}:{port}: {exc}") from exc

    if status == 0:
        raise RuntimeError(
            f"Cannot bind development server to {host}:{port}. "
            f"The port is already occupied or blocked by local policy. "
            f"Try `Get-NetTCPConnection -LocalPort {port}` in an elevated shell, "
            f"or start with `$env:{PORT_ENV_VAR}='8001'; uv run python main.py`."
        )


__all__ = [
    "HOST_ENV_VAR",
    "PORT_ENV_VAR",
    "PORT_FALLBACK_ENV_VAR",
    "RELOAD_ENV_VAR",
    "ensure_bind_available",
    "resolve_server_host",
    "resolve_server_port",
    "resolve_server_reload",
]

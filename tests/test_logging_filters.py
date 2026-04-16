import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infra.logging import ModuleLevelFilter


def _record(name: str, level: int) -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg="test",
        args=(),
        exc_info=None,
    )


def test_module_level_filter_applies_default_level_to_nonmatching_modules() -> None:
    log_filter = ModuleLevelFilter(
        {"src.application.ai": logging.DEBUG},
        default_level=logging.INFO,
    )

    assert log_filter.filter(_record("src.other", logging.INFO))
    assert not log_filter.filter(_record("src.other", logging.DEBUG))


def test_module_level_filter_respects_module_override() -> None:
    log_filter = ModuleLevelFilter(
        {
            "src.application.ai": logging.DEBUG,
            "uvicorn": logging.WARNING,
        },
        default_level=logging.INFO,
    )

    assert log_filter.filter(_record("src.application.ai.service", logging.DEBUG))
    assert not log_filter.filter(_record("uvicorn.access", logging.INFO))

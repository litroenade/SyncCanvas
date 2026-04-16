"""Rendered-element semantic refs."""

from typing import Any, Dict

from src.domain.diagrams.models import ManagedElementRef


def custom_data(ref: ManagedElementRef) -> Dict[str, Any]:
    return {"syncCanvas": ref.model_dump(by_alias=True)}


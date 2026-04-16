"""Managed-diagram-only request admission checks."""

from typing import Callable, Optional


MANAGED_ONLY_MESSAGE = (
    "Freeform canvas generation has been removed. "
    "Use a managed diagram prompt or select an existing managed diagram."
)


def ensure_managed_request_supported(
    *,
    user_input: str,
    mode: str,
    target_diagram_id: Optional[str],
    prompt_supports: Callable[[str, str], bool],
) -> None:
    """Reject prompts that no longer map to the managed-diagram pipeline."""

    if target_diagram_id:
        return
    if prompt_supports(user_input, mode):
        return
    raise ValueError(MANAGED_ONLY_MESSAGE)

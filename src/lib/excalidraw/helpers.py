"""Shared Excalidraw helper utilities."""

import random
import uuid
from typing import Any, Dict, Optional, Tuple

from pycrdt import Array, Map

from src.infra.config import config
from src.infra.logging import get_logger

logger = get_logger(__name__)


def get_theme_colors(theme: str = "light") -> Dict[str, str]:
    """Return the canvas palette for the active theme."""

    return config.canvas.get_theme_colors(theme)


def require_room_id(context: Optional[Any]) -> str:
    """Extract a room id from an execution context that carries session_id."""

    if not context or not context.session_id:
        raise ValueError("room_id (session_id) is required in AgentContext")
    return context.session_id


def generate_element_id(prefix: str = "el") -> str:
    """Generate a stable-enough element identifier for programmatic writes."""

    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def base_excalidraw_element(
    element_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: Optional[str] = None,
    bg_color: Optional[str] = None,
    theme: str = "light",
) -> Dict[str, Any]:
    """Build a baseline Excalidraw element payload."""

    colors = get_theme_colors(theme)
    final_stroke = stroke_color if stroke_color else colors["stroke"]
    final_bg = bg_color if bg_color else colors["background"]

    def safe_float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            result = float(value)
        except (TypeError, ValueError):
            logger.warning("[safe_float] failed to parse %s, using %s", value, default)
            return default
        if result != result or result == float("inf") or result == float("-inf"):
            logger.warning("[safe_float] invalid numeric value %s, using %s", value, default)
            return default
        return result

    safe_x = safe_float(x, 100.0)
    safe_y = safe_float(y, 100.0)
    safe_width = safe_float(width, 100.0)
    safe_height = safe_float(height, 100.0)

    base = {
        "id": generate_element_id(element_type),
        "type": element_type,
        "x": safe_x,
        "y": safe_y,
        "width": safe_width,
        "height": safe_height,
        "frameId": None,
        "angle": 0,
        "strokeColor": final_stroke,
        "backgroundColor": final_bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }

    if element_type in ("rectangle", "diamond", "ellipse"):
        base["roundness"] = {"type": 3}
    elif element_type in ("arrow", "line"):
        base["points"] = [[0, 0], [safe_width, safe_height]]
        base["startBinding"] = None
        base["endBinding"] = None
        base["startArrowhead"] = None
        base["endArrowhead"] = "arrow" if element_type == "arrow" else None
        base["roundness"] = {"type": 2}
        base["backgroundColor"] = "transparent"
    elif element_type == "freedraw":
        base["points"] = []
        base["pressures"] = []
        base["simulatePressure"] = True
        base["roundness"] = None
    elif element_type == "text":
        base["roundness"] = None
    elif element_type == "image":
        base["fileId"] = None
        base["status"] = "pending"
        base["scale"] = [1, 1]
        base["roundness"] = None
    elif element_type in ("frame", "magicframe"):
        base["name"] = None
        base["roundness"] = None
    else:
        base["roundness"] = {"type": 3}

    return base


def get_elements_array(doc: Any) -> Array:
    """Return the shared elements array from a Y.Doc."""

    return doc.get("elements", type=Array)


def find_element_by_id(elements_array: Array, element_id: str) -> Tuple[int, Any]:
    """Find one element inside a Y.Array."""

    for index, element in enumerate(elements_array):
        if isinstance(element, Map):
            if element.get("id") == element_id:
                return index, dict(element)
        elif isinstance(element, dict):
            if element.get("id") == element_id:
                return index, element
    return -1, None


def append_element_as_ymap(elements_array: Array, element: Dict[str, Any]) -> None:
    """Append one element into a Y.Array using a fresh Y.Map container."""

    ymap = Map()
    elements_array.append(ymap)
    for key, value in element.items():
        ymap[key] = value


def update_element_in_array(
    elements_array: Array,
    element_id: str,
    updates: Dict[str, Any],
) -> bool:
    """Update an existing Y.Array element in-place."""

    for element in elements_array:
        if isinstance(element, Map) and element.get("id") == element_id:
            for key, value in updates.items():
                element[key] = value
            return True
    return False

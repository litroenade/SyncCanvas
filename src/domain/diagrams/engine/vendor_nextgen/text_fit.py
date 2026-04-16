
from typing import List, Tuple

from src.lib.math.text import estimate_text_size

from .semantic_ir import GeomNode, SemanticDiagram
from .symbol_grammar import rule_for

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    Image = None
    ImageDraw = None
    ImageFont = None
    _FONT = None
else:
    _FONT = ImageFont.load_default()


def text_size(text: str) -> Tuple[int, int]:
    if Image is None or ImageDraw is None or _FONT is None:
        width, height = estimate_text_size(
            text,
            font_size=18,
            font_family=1,
            line_height=1.25,
        )
        return int(width), int(height)
    img = Image.new("RGB", (1, 1), "white")
    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), text, font=_FONT, spacing=4)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(text: str, max_width: int) -> str:
    if not text:
        return text
    parts = text.split("\n")
    wrapped_lines: List[str] = []
    for part in parts:
        words = part.split(" ")
        if len(words) == 1:
            token = words[0]
            if text_size(token)[0] <= max_width:
                wrapped_lines.append(token)
                continue
            current = ""
            for ch in token:
                trial = current + ch
                if current and text_size(trial)[0] > max_width:
                    wrapped_lines.append(current)
                    current = ch
                else:
                    current = trial
            if current:
                wrapped_lines.append(current)
            continue
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if current and text_size(trial)[0] > max_width:
                wrapped_lines.append(current)
                current = word
            else:
                current = trial
        if current:
            wrapped_lines.append(current)
    return "\n".join(wrapped_lines)


def _wrap_width(diagram: SemanticDiagram, node: GeomNode) -> int:
    if diagram.family == "workflow":
        role = str(node.meta.get("role", ""))
        if node.kind == "decision":
            return 108
        if node.kind == "process":
            if role == "validate":
                return 94
            if role in {"approve", "post", "reject"}:
                return 90
            return 98
        if node.kind == "terminator":
            return 98
    if diagram.family == "technical_blueprint" and node.kind == "device":
        return 118
    if diagram.family == "architecture_flow":
        if node.kind == "network":
            return 108
        if node.kind == "process":
            return 118
    return 180 if node.kind != "title_block" else 220


def fit_diagram(diagram: SemanticDiagram) -> List[GeomNode]:
    out: List[GeomNode] = []
    for node in diagram.nodes:
        rule = rule_for(node.kind)
        if node.kind in {"class", "interface"}:
            header = ("<<interface>>\n" if node.kind == "interface" else "") + node.label
            body = []
            body.extend(node.attrs)
            if node.methods:
                if body:
                    body.append("")
                body.extend(node.methods)
            text = header + ("\n" + "\n".join(body) if body else "")
            wrapped = wrap_text(text, 220)
        else:
            probe = GeomNode(
                id=node.id,
                label=node.label,
                kind=node.kind,
                family=node.family,
                x=0.0,
                y=0.0,
                w=0.0,
                h=0.0,
                row=node.row_hint,
                col=node.col_hint,
                attrs=node.attrs,
                methods=node.methods,
                group=node.group,
                style_role=node.style_role,
                meta=node.meta.copy(),
            )
            wrapped = wrap_text(node.label, _wrap_width(diagram, probe))
        text_w, text_h = text_size(wrapped)
        width = max(rule.min_w, text_w + 2 * rule.px)
        height = max(rule.min_h, text_h + 2 * rule.py)
        if diagram.family == "workflow":
            width += 28.0
            height += 12.0
            if node.kind == "process":
                width += 12.0
            if node.kind == "decision":
                width += 24.0
                height += 18.0
            if node.kind == "terminator":
                width += 10.0
        if diagram.family == "istar":
            width += 18.0
            height += 6.0
        out.append(
            GeomNode(
                id=node.id,
                label=wrapped,
                kind=node.kind,
                family=node.family,
                x=0.0,
                y=0.0,
                w=float(width),
                h=float(height),
                row=node.row_hint,
                col=node.col_hint,
                attrs=node.attrs,
                methods=node.methods,
                group=node.group,
                style_role=node.style_role,
                meta=node.meta.copy(),
            )
        )
    return out

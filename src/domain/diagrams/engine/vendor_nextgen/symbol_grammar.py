
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SymbolRule:
    min_w: float
    min_h: float
    px: float
    py: float
    line_height: float
    shape: str


FAMILY_COLORS: Dict[str, Dict[str, str]] = {
    "workflow": {"fill": "#f4fbff", "stroke": "#2f6189", "accent": "#6d9dc5", "label_bg": "#ffffff"},
    "static_structure": {"fill": "#f7f7ff", "stroke": "#4b4a77", "accent": "#7c7bc0", "label_bg": "#ffffff"},
    "component_cluster": {"fill": "#f6fff7", "stroke": "#3f6a42", "accent": "#7aad73", "label_bg": "#ffffff"},
    "technical_blueprint": {"fill": "#fffdf7", "stroke": "#745a3a", "accent": "#b08b49", "label_bg": "#fffefb"},
    "istar": {"fill": "#fff7fc", "stroke": "#7a3e63", "accent": "#bc78a1", "label_bg": "#ffffff"},
    "architecture_flow": {"fill": "#59c8c1", "stroke": "#4c9d98", "accent": "#5abdb7", "label_bg": "#f8fffe"},
    "layered_architecture": {"fill": "#f8fbff", "stroke": "#3d5f86", "accent": "#87a7c9", "label_bg": "#ffffff"},
    "transformer_stack": {"fill": "#fffaf4", "stroke": "#8a5f2d", "accent": "#c89c63", "label_bg": "#fffdf8"},
    "react_loop": {"fill": "#f8fff8", "stroke": "#426e47", "accent": "#85b58b", "label_bg": "#ffffff"},
    "rag_pipeline": {"fill": "#f8fbff", "stroke": "#325d89", "accent": "#7aa0c9", "label_bg": "#ffffff"},
}


SYMBOL_RULES: Dict[str, SymbolRule] = {
    "process": SymbolRule(160, 64, 18, 12, 18, "roundrect"),
    "terminator": SymbolRule(150, 60, 18, 12, 18, "ellipse"),
    "decision": SymbolRule(160, 104, 16, 16, 18, "diamond"),
    "class": SymbolRule(190, 120, 18, 14, 18, "classbox"),
    "interface": SymbolRule(180, 106, 18, 14, 18, "classbox"),
    "component": SymbolRule(180, 84, 18, 12, 18, "component"),
    "database": SymbolRule(160, 84, 16, 12, 18, "database"),
    "device": SymbolRule(165, 82, 18, 12, 18, "device"),
    "title_block": SymbolRule(230, 90, 16, 12, 18, "title_block"),
    "goal": SymbolRule(140, 72, 16, 12, 18, "ellipse"),
    "task": SymbolRule(150, 70, 18, 12, 18, "roundrect"),
    "resource": SymbolRule(150, 70, 18, 12, 18, "rect"),
    "softgoal": SymbolRule(170, 86, 18, 14, 18, "softgoal"),
    "network": SymbolRule(170, 96, 18, 14, 18, "network"),
}


def rule_for(kind: str) -> SymbolRule:
    return SYMBOL_RULES[kind]


def colors_for(family: str) -> Dict[str, str]:
    return FAMILY_COLORS[family]

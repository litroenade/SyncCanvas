import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.diagrams.engine.vendor_nextgen.fallbacks import build_seed_spec
from src.domain.diagrams.rendering.render import render_spec


def test_technical_blueprint_seed_prefers_industrial_layout_for_plc_prompt() -> None:
    prompt = (
        "生成一张设备/系统布置图风格的 blueprint，包含 Main PLC、Remote IO、Servo Drive、"
        "Axis Motor、Inspection PLC、Camera、HMI Panel、Safety Relay、Quality Bus、"
        "Fieldbus、Power Trunk，并预留 title block 和 keepout 区域。"
    )
    spec = build_seed_spec(prompt, "technical_blueprint", diagram_id="diagram_blueprint_industrial")

    assert spec.family == "technical_blueprint"
    assert any(component.id == "plc" for component in spec.components)
    bundle = render_spec(spec)
    assert bundle.summary.component_count > 0
    assert len(bundle.preview_elements) > 0


def test_technical_blueprint_seed_llm_variant_still_renders_without_crashing() -> None:
    prompt = "Create an LLM infrastructure blueprint with gateway rack, retrieval node, inference runtime, and storage array."
    spec = build_seed_spec(prompt, "technical_blueprint", diagram_id="diagram_blueprint_llm")

    assert spec.family == "technical_blueprint"
    bundle = render_spec(spec)
    assert bundle.summary.component_count > 0
    assert len(bundle.preview_elements) > 0

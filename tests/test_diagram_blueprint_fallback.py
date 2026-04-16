import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.diagrams.engine.vendor_bridge import build_vendor_layout
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


def test_technical_blueprint_llm_variant_skips_incompatible_fixed_id_engine(caplog) -> None:
    prompt = "Create an LLM infrastructure blueprint with gateway rack, retrieval node, inference runtime, and storage array."
    spec = build_seed_spec(prompt, "technical_blueprint", diagram_id="diagram_blueprint_llm_skip")

    caplog.set_level("INFO")
    layout = build_vendor_layout(spec)

    assert "Vendored family engine failed" not in caplog.text
    assert "Skipping vendored family engine" in caplog.text
    assert any(node.id == "gateway" for node in layout.nodes)


def test_transformer_seed_renders_family_group_frames() -> None:
    spec = build_seed_spec(
        "Create a transformer-style architecture diagram",
        "transformer_stack",
        diagram_id="diagram_transformer_groups",
    )

    bundle = render_spec(spec)
    group_ids = {
        entry.semantic_id
        for entry in bundle.manifest.entries
        if entry.role == "group"
    }

    assert "Encoder Stack" in group_ids
    assert "Decoder Stack" in group_ids

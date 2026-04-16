import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.diagrams.prompting import DiagramPromptService
from src.domain.diagrams.families import route_family
from src.infra.ai.llm import LLMResponse


class FakeLLMClient:
    def __init__(self, content: str) -> None:
        self._content = content

    async def chat_completion(self, **_kwargs) -> LLMResponse:  # type: ignore[no-untyped-def]
        return LLMResponse(content=self._content)


def test_route_family_skips_negated_workflow_prompt() -> None:
    prompt = "画一张大模型应用平台拓扑，不是流程图，要求像论文里的系统总览图，分层、分区、可扩展。"
    assert route_family(prompt) == "layered_architecture"


def test_route_family_keeps_blueprint_prompt_on_technical_blueprint() -> None:
    prompt = (
        "生成一张设备/系统布置图风格的 blueprint，包含 Main PLC、Remote IO、Servo Drive、"
        "Axis Motor、Inspection PLC、Camera、HMI Panel、Safety Relay。"
    )
    assert route_family(prompt) == "technical_blueprint"


def test_spec_from_llm_normalizes_blueprint_style_strings() -> None:
    service = DiagramPromptService()
    payload = """
{
  "diagramId": "device_layout_blueprint",
  "diagramType": "technical_blueprint",
  "family": "technical_blueprint",
  "version": "1.0",
  "title": "Device/System Layout Blueprint",
  "prompt": "生成一张设备/系统布置图风格的 blueprint",
  "style": "blueprint",
  "layout": "top-down",
  "components": [
    {"id": "main_plc", "componentType": "plc", "label": "Main PLC", "text": "Main PLC", "shape": "rectangle", "style": "blueprint", "data": {}},
    {"id": "quality_bus", "componentType": "bus", "label": "Quality Bus", "text": "Quality Bus", "shape": "line", "style": "blueprint", "data": {}},
    {"id": "hmi_panel", "componentType": "panel", "label": "HMI Panel", "text": "HMI Panel", "shape": "rectangle", "style": "blueprint", "data": {}}
  ],
  "connectors": [
    {"id": "conn_quality_bus", "fromComponent": "main_plc", "toComponent": "quality_bus", "connectorType": "bus", "style": "blueprint", "data": {}}
  ],
  "annotations": [
    {"id": "note.keepout", "annotationType": "caption", "text": "KEEP OUT", "style": "blueprint"}
  ],
  "layoutConstraints": {"keepouts": [[760, 340, 1180, 510]]},
  "overrides": {}
}
"""

    spec = asyncio.run(
        service.spec_from_llm(
            "生成一张设备/系统布置图风格的 blueprint",
            "technical_blueprint",
            FakeLLMClient(payload),  # type: ignore[arg-type]
        )
    )

    assert spec is not None
    assert spec.family == "technical_blueprint"
    assert spec.layout == {"mode": "top-down"}
    assert spec.style["preset"] == "handdrawn-paper"
    assert spec.components[0].component_type == "device"
    assert spec.components[1].component_type == "network"
    assert spec.components[0].style["preset"] == "handdrawn-paper"
    assert spec.connectors[0].connector_type == "line"
    assert spec.connectors[0].style["preset"] == "handdrawn-paper"

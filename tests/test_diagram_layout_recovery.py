import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.diagrams.engine.render import render_spec
from src.domain.diagrams.models import DiagramBundle, DiagramSpec


def _build_transformer_detail_spec(*, use_family_engine: bool | None = None) -> DiagramSpec:
    layout_constraints = {"type": "vertical_stack", "align": "center", "gap": 60}
    if use_family_engine is not None:
        layout_constraints["vendorUseFamilyEngine"] = use_family_engine

    return DiagramSpec.model_validate(
        {
            "diagramId": "transformer_stack_001",
            "diagramType": "transformer_stack",
            "family": "transformer_stack",
            "version": 1,
            "title": "Transformer Stack",
            "prompt": "Create a transformer stack diagram with encoder, decoder, and attention flow.",
            "style": {},
            "layout": {},
            "layoutConstraints": layout_constraints,
            "components": [
                {"id": "embedding.input", "componentType": "container", "label": "Input Embedding", "text": "Input Embedding", "shape": "rectangle"},
                {"id": "positional.encoding", "componentType": "block", "label": "Positional Encoding", "text": "Positional Encoding", "shape": "rectangle"},
                {"id": "encoder.stack", "componentType": "block", "label": "Encoder Stack", "text": "Encoder Stack", "shape": "rectangle"},
                {"id": "encoder.layer", "componentType": "container", "label": "Encoder Layer", "text": "Encoder Layer", "shape": "rectangle"},
                {"id": "attention.self.encoder", "componentType": "block", "label": "Encoder Self Attention", "text": "Encoder Self Attention", "shape": "rectangle"},
                {"id": "feed.forward.encoder", "componentType": "block", "label": "Encoder Feed Forward", "text": "Encoder Feed Forward", "shape": "rectangle"},
                {"id": "encoder.output", "componentType": "block", "label": "Encoder Output", "text": "Encoder Output", "shape": "rectangle"},
                {"id": "decoder.stack", "componentType": "block", "label": "Decoder Stack", "text": "Decoder Stack", "shape": "rectangle"},
                {"id": "decoder.layer", "componentType": "container", "label": "Decoder Layer", "text": "Decoder Layer", "shape": "rectangle"},
                {"id": "attention.self.decoder", "componentType": "block", "label": "Decoder Self Attention", "text": "Masked Decoder Self Attention", "shape": "rectangle"},
                {"id": "attention.cross", "componentType": "block", "label": "Cross Attention", "text": "Cross Attention", "shape": "rectangle"},
                {"id": "feed.forward.decoder", "componentType": "block", "label": "Decoder Feed Forward", "text": "Decoder Feed Forward", "shape": "rectangle"},
                {"id": "decoder.output", "componentType": "block", "label": "Decoder Output", "text": "Decoder Output", "shape": "rectangle"},
                {"id": "output.projection", "componentType": "block", "label": "Output Projection", "text": "Linear and Softmax", "shape": "rectangle"},
            ],
            "connectors": [
                {"id": "conn.embedding.positional", "fromComponent": "embedding.input", "toComponent": "positional.encoding", "connectorType": "arrow", "label": "tokens"},
                {"id": "conn.positional.encoder", "fromComponent": "positional.encoding", "toComponent": "encoder.stack", "connectorType": "arrow", "label": "embedded"},
                {"id": "conn.encoder.layer", "fromComponent": "encoder.stack", "toComponent": "encoder.layer", "connectorType": "arrow"},
                {"id": "conn.encoder.self_attention", "fromComponent": "encoder.layer", "toComponent": "attention.self.encoder", "connectorType": "arrow"},
                {"id": "conn.encoder.ffn", "fromComponent": "attention.self.encoder", "toComponent": "feed.forward.encoder", "connectorType": "arrow"},
                {"id": "conn.encoder.output", "fromComponent": "feed.forward.encoder", "toComponent": "encoder.output", "connectorType": "arrow", "label": "encoded"},
                {"id": "conn.encoder.to.decoder", "fromComponent": "encoder.output", "toComponent": "decoder.stack", "connectorType": "arrow", "label": "memory"},
                {"id": "conn.decoder.layer", "fromComponent": "decoder.stack", "toComponent": "decoder.layer", "connectorType": "arrow"},
                {"id": "conn.decoder.self_attention", "fromComponent": "decoder.layer", "toComponent": "attention.self.decoder", "connectorType": "arrow"},
                {"id": "conn.decoder.cross_attention", "fromComponent": "attention.self.decoder", "toComponent": "attention.cross", "connectorType": "arrow", "label": "query"},
                {"id": "conn.cross.to.ffn", "fromComponent": "attention.cross", "toComponent": "feed.forward.decoder", "connectorType": "arrow", "label": "context"},
                {"id": "conn.decoder.output", "fromComponent": "feed.forward.decoder", "toComponent": "decoder.output", "connectorType": "arrow", "label": "decoded"},
                {"id": "conn.decoder.to.projection", "fromComponent": "decoder.output", "toComponent": "output.projection", "connectorType": "arrow", "label": "logits"},
            ],
            "groups": [],
            "annotations": [],
            "assets": [],
            "overrides": {},
        }
    )


def _build_react_loop_spec() -> DiagramSpec:
    return DiagramSpec.model_validate(
        {
            "diagramId": "react_loop_001",
            "diagramType": "react_loop",
            "family": "react_loop",
            "version": 1,
            "title": "ReAct Loop",
            "prompt": "Draw a ReAct loop with an LM, environment, action, and observation.",
            "style": {},
            "layout": {},
            "layoutConstraints": {},
            "components": [
                {"id": "query", "componentType": "block", "label": "User Query", "text": "User Query", "shape": "rectangle"},
                {"id": "lm", "componentType": "block", "label": "Language Model", "text": "LM", "shape": "rectangle"},
                {"id": "reasoning", "componentType": "block", "label": "Reasoning", "text": "Reasoning", "shape": "rectangle"},
                {"id": "action", "componentType": "block", "label": "Action", "text": "Action", "shape": "rectangle"},
                {"id": "environment", "componentType": "block", "label": "Environment", "text": "Environment", "shape": "rectangle"},
                {"id": "observation", "componentType": "block", "label": "Observation", "text": "Observation", "shape": "rectangle"},
                {"id": "answer", "componentType": "block", "label": "Final Answer", "text": "Final Answer", "shape": "rectangle"},
            ],
            "connectors": [
                {"id": "conn.query.lm", "fromComponent": "query", "toComponent": "lm", "connectorType": "arrow"},
                {"id": "conn.lm.reasoning", "fromComponent": "lm", "toComponent": "reasoning", "connectorType": "arrow"},
                {"id": "conn.reasoning.action", "fromComponent": "reasoning", "toComponent": "action", "connectorType": "arrow"},
                {"id": "conn.action.environment", "fromComponent": "action", "toComponent": "environment", "connectorType": "arrow"},
                {"id": "conn.environment.observation", "fromComponent": "environment", "toComponent": "observation", "connectorType": "arrow"},
                {"id": "conn.observation.answer", "fromComponent": "observation", "toComponent": "answer", "connectorType": "arrow"},
            ],
            "groups": [],
            "annotations": [],
            "assets": [],
            "overrides": {},
        }
    )


def _coords(bundle: DiagramBundle) -> dict[str, tuple[float, float]]:
    return {
        component.id: (float(component.x), float(component.y))
        for component in bundle.spec.components
    }


def _assert_row_col_hints(bundle: DiagramBundle) -> None:
    for component in bundle.spec.components:
        assert isinstance(component.data.get("rowHint"), int)
        assert isinstance(component.data.get("colHint"), int)


def _assert_non_degenerate_routes(bundle: DiagramBundle) -> None:
    for connector in bundle.spec.connectors:
        points = connector.data.get("routePoints")
        assert isinstance(points, list)
        assert len(points) >= 2
        start = tuple(points[0])
        end = tuple(points[-1])
        assert start != end


def test_hintless_transformer_layout_uses_family_engine_and_recovers_routes() -> None:
    bundle = render_spec(_build_transformer_detail_spec())
    coords = _coords(bundle)

    assert len(set(coords.values())) == len(coords)
    assert coords["embedding.input"][0] < coords["encoder.output"][0]
    assert coords["encoder.output"][0] < coords["decoder.output"][0]
    assert coords["decoder.output"][0] < coords["output.projection"][0]
    assert coords["encoder.stack"][0] < coords["feed.forward.encoder"][0] < coords["encoder.output"][0]
    assert coords["attention.cross"][0] <= coords["feed.forward.decoder"][0] < coords["decoder.output"][0]
    assert coords["positional.encoding"][1] < coords["embedding.input"][1]
    assert coords["attention.self.encoder"][1] < coords["feed.forward.encoder"][1]
    assert coords["attention.self.decoder"][1] < coords["feed.forward.decoder"][1]
    assert any(
        entry.semantic_id == "Encoder Stack"
        for entry in bundle.manifest.entries
        if entry.role == "group"
    )
    assert any(
        entry.semantic_id == "Decoder Stack"
        for entry in bundle.manifest.entries
        if entry.role == "group"
    )
    _assert_row_col_hints(bundle)
    _assert_non_degenerate_routes(bundle)


def test_hintless_transformer_layout_recovers_when_family_engine_is_disabled() -> None:
    bundle = render_spec(_build_transformer_detail_spec(use_family_engine=False))
    coords = _coords(bundle)

    assert len(set(coords.values())) == len(coords)
    assert len({x for x, _y in coords.values()}) >= 4
    assert coords["embedding.input"][0] < coords["output.projection"][0]
    _assert_row_col_hints(bundle)
    _assert_non_degenerate_routes(bundle)


def test_hintless_react_layout_assigns_distinct_slots() -> None:
    bundle = render_spec(_build_react_loop_spec())
    coords = _coords(bundle)

    assert coords["query"][0] < coords["lm"][0] < coords["answer"][0]
    assert coords["environment"] != coords["observation"]
    assert coords["reasoning"][1] < coords["observation"][1]
    _assert_row_col_hints(bundle)
    _assert_non_degenerate_routes(bundle)

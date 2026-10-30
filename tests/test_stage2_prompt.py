"""Offline checks for prompts/stage2_v1.md (draft awaiting anchor approval). No LLM calls."""
import json
import re

from ti.llm import load_prompt
from ti.schemas import Stage2Out, TurnLabel, Trajectory

NAME = "stage2_v1"


def _prompt() -> str:
    return load_prompt(NAME)[1]


def test_markers_present_once_and_prompt_parses():
    from ti import PROMPT_DIR

    raw = (PROMPT_DIR / f"{NAME}.md").read_text()
    assert raw.count("<!-- PROMPT START -->") == 1 and raw.count("<!-- PROMPT END -->") == 1
    version, text = load_prompt(NAME)
    assert version == NAME and len(text.split()) > 500
    assert "Version: stage2_v1" in raw


def _format_block(text: str) -> str:
    tail = text.split("Return only JSON, nothing else:", 1)[1]
    return tail.strip()


def test_output_format_fields_match_schema():
    block = _format_block(_prompt())
    top = set(re.findall(r'^  "(\w+)":', block, flags=re.M))
    assert top == set(Stage2Out.model_fields), (top, set(Stage2Out.model_fields))
    # nested keys named in the format block
    assert '"index"' in block and '"label"' in block
    assert set(TurnLabel.model_fields) == {"index", "label"}
    assert '"start"' in block and '"end"' in block
    assert set(Trajectory.model_fields) == {"start", "end"}
    for label in ("negative", "neutral", "positive"):
        assert label in block
    for conf in ("low", "medium", "high"):
        assert f'"{conf}"' in block


def test_worked_examples_validate_against_schema():
    text = _prompt()
    outs = re.findall(r"^Output:\n(\{.*\})$", text, flags=re.M)
    assert len(outs) == 2
    parsed = [Stage2Out.model_validate(json.loads(o)) for o in outs]
    assert parsed[0].customer_score == 3 and parsed[1].customer_score is None  # internal example has no customer
    assert all(len(p.per_turn) == 6 for p in parsed)
    assert "invented for this prompt; not dataset content" in text


def test_prompt_never_asks_for_or_mentions_provided_inputs():
    text = _prompt()
    for banned in ("sentimentScore", "sentimentType", "overallSentiment", "summary.json", "topics:", "call_type"):
        assert banned not in text
    assert "no title, no call type" in text


def test_anchor_levels_complete():
    text = _prompt()
    for lvl in ("5", "4", "3", "2", "1"):
        # one whole-call and one customer-side anchor line per level
        assert len(re.findall(rf"^- {lvl} \(", text, flags=re.M)) == 2
    assert "half step" in text.lower()


def test_stage2_view_has_no_provided_or_call_type_fields(meetings):
    """The view the prompt is paired with: turns only; no title, call type or provided data, for all 100 meetings."""
    for m in meetings:
        v = m.view_for("stage2")
        assert set(v) == {"turns"}
        flat = json.dumps(v)
        assert m.title not in flat
        assert m.provided.summary not in flat
        for banned in ("call_type", "sentimentScore", "sentimentType", "overallSentiment", "title"):
            assert banned not in set(v) and banned not in {k for t in v["turns"] for k in t}

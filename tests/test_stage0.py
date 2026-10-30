import pandas as pd

from ti import stage0
from ti.llm import LLMClient


def test_stage0_end_to_end_on_five_calls_with_mock(meetings, mock_openai, tmp_path):
    customer_calls = [m for m in meetings if not m.is_internal_by_metadata][:4]
    internal = [m for m in meetings if m.is_internal_by_metadata][:1]
    sample = customer_calls + internal
    client = LLMClient(mode="live", cache_dir=tmp_path / "cache", openai_client=mock_openai, min_interval=0)
    df = stage0.run(sample, client, model="mock/model", out_dir=tmp_path / "out")

    assert len(df) == 5
    row_internal = df[df.meeting_id == internal[0].meeting_id].iloc[0]
    assert row_internal.label == "internal" and row_internal.source == "metadata"
    assert mock_openai.calls == 4  # the internal call never reached the model
    assert set(df[df.source == "llm"].label) <= {"support", "external"}
    assert {"disagree", "title_rule_label", "confidence", "evidence_quote"} <= set(df.columns)
    assert (tmp_path / "out" / "stage0.csv").exists()
    q = pd.read_csv(tmp_path / "out" / "stage0_review_queue.csv")
    assert {"meeting_id", "reason"} <= set(q.columns)

    # second run is served entirely from the cache
    stage0.run(sample, client, model="mock/model", out_dir=tmp_path / "out")
    assert mock_openai.calls == 4


def test_prompt_loads_and_has_definitions():
    from ti.llm import load_prompt

    version, text = load_prompt("stage0_v1")
    assert version == "stage0_v1"
    assert "support:" in text and "external:" in text and "meeting name" in text and "title:" not in text


def test_stage0_request_never_contains_the_meeting_title(meetings):
    """D1 revision note 2: the model must not see the title, for any of the 100 meetings."""
    for m in meetings:
        v = m.view_for("stage0")
        assert "title" not in v
        assert m.title not in stage0.build_user_message(m)
        assert "title:" not in stage0.build_user_message(m)

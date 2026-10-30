import json

from ti.load import Meeting


def test_loads_100(meetings):
    assert len(meetings) == 100
    assert len({m.meeting_id for m in meetings}) == 100


def test_internal_by_metadata_is_30(meetings):
    assert sum(m.is_internal_by_metadata for m in meetings) == 30


def test_title_rule_matches_exploration(meetings):
    counts = {k: sum(m.title_rule_label == k for m in meetings) for k in ("support", "external", "internal")}
    assert counts == {"support": 27, "external": 43, "internal": 30}


def test_speaker_sides(meetings):
    for m in meetings:
        sides = set(m.speaker_sides().values())
        if m.is_internal_by_metadata:
            assert sides == {"aegis_staff"}
        else:
            assert "customer" in sides  # every customer call has a customer speaking


def test_stage2_view_is_exactly_the_transcript(meetings):
    """Structural check: the view is built only from turns + sides. Nothing else can be in it."""
    for m in meetings:
        v = m.view_for("stage2")
        assert set(v) == {"turns"}
        assert len(v["turns"]) == len(m.turns)
        for t, src in zip(v["turns"], m.turns):
            assert set(t) == {"index", "speaker", "side", "sentence"}
            assert t["sentence"] == src.sentence and t["speaker"] == src.speaker


def test_stage1_view_same_shape_and_stage0_view_keys(meetings):
    m = next(x for x in meetings if not x.is_internal_by_metadata)
    assert m.view_for("stage1") == m.view_for("stage2")
    v0 = m.view_for("stage0")
    assert set(v0) == {"n_attendees", "n_aegis_attendees", "n_outside_attendees", "opening"}
    assert len(v0["opening"]) == 8
    assert all(set(t) == {"speaker", "sentence"} for t in v0["opening"])  # no sides, no provided labels


def test_provided_object_is_separate_and_never_in_a_view(meetings):
    m = meetings[0]
    assert m.provided.summary and m.provided.topics  # present for baseline comparison
    for stage in ("stage0", "stage1", "stage2"):
        flat = json.dumps(m.view_for(stage))
        assert m.provided.summary not in flat
        assert str(m.provided.sentiment_score) not in {k for k in m.view_for(stage)}
    # stage 1 and 2 views never carry the title (a baseline-only field per D3a) or a call type
    assert "title" not in m.view_for("stage1") and "title" not in m.view_for("stage2")
    assert "call_type" not in json.dumps(m.view_for("stage2"))


def test_transcript_hash_stable(meetings):
    assert meetings[0].transcript_hash() == meetings[0].transcript_hash()
    assert meetings[0].transcript_hash() != meetings[1].transcript_hash()


def test_unknown_stage_raises(meetings):
    import pytest

    with pytest.raises(ValueError):
        meetings[0].view_for("stage9")

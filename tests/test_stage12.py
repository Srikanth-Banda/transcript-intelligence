"""Offline tests for the production Stage 1 and Stage 2 (D8): schemas, validation, retry, taxonomy/prompt sync, metrics."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ti import stage1, stage2
from ti.common import Guard, quote_exact, stability_sample
from ti.llm import LLMClient, load_prompt
from ti.schemas import Stage1Out, Stage2Out, Trajectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
import stage12_report as rep  # noqa: E402


# ---- schemas ---------------------------------------------------------------------------------
def test_stage1_schema_is_additive_and_old_payload_still_valid():
    old = {"primary_theme": "x", "tags": [], "product_area": "Detect", "evidence_quote": "q", "confidence": "high",
           "taxonomy_version": "v0"}
    out = Stage1Out.model_validate(old)
    assert out.incident is None and out.other_description == ""
    new = Stage1Out.model_validate({**old, "incident": "2026-03-detect-outage"})
    assert new.incident == "2026-03-detect-outage"


@pytest.mark.parametrize("v,ok", [(3.0, True), (3.5, True), (3.33, False), (0.5, False), (5.5, False)])
def test_trajectory_must_be_half_steps(v, ok):
    if ok:
        assert Trajectory(start=v, end=v).start == v
    else:
        with pytest.raises(ValueError):
            Trajectory(start=v, end=v)


# ---- taxonomy and prompt stay in sync -------------------------------------------------------------
def test_taxonomy_v1_matches_d8_and_prompt():
    tax = json.loads((stage1.OUT / "taxonomy_v1.json").read_text())
    assert tax["version"] == "v1" and len(tax["themes"]) == 8
    assert [a["name"] for a in tax["product_areas"]] == ["Detect", "Comply", "Protect", "Identity", "Platform/General"]
    _, prompt = load_prompt("stage1_v1")
    for t in tax["themes"]:
        assert t["name"] in prompt and t["definition"] in prompt
    assert tax["incident"]["id"] in prompt
    # no answer leakage: example quotes live in the taxonomy file, not in the prompt
    for t in tax["themes"]:
        for ex in t["examples"]:
            assert ex["quote"] not in prompt


def test_taxonomy_example_quotes_are_verbatim(meetings):
    tax = json.loads((stage1.OUT / "taxonomy_v1.json").read_text())
    by_label = {m.meeting_id[-6:]: m for m in meetings}
    for t in tax["themes"]:
        assert t["examples"], t["name"]
        for ex in t["examples"]:
            assert quote_exact(ex["quote"], [x.sentence for x in by_label[ex["call"]].turns])


def test_stage_views_hide_title_and_provided_fields(meetings):
    m = meetings[0]
    for stage in ("stage1", "stage2"):
        text = (stage1.build_user_message(m) if stage == "stage1" else stage2.build_user_message(m)).lower()
        assert m.title.lower() not in text
        assert m.provided.summary[:40].lower() not in text


# ---- validation logic ----------------------------------------------------------------------------
def _s1(**kw):
    base = dict(primary_theme="A", tags=[], product_area="Detect", evidence_quote="hello world", confidence="high",
                taxonomy_version="v1", incident=None)
    return Stage1Out(**{**base, **kw})


def test_stage1_check_flags():
    themes, areas = {"A", "B", "C"}, {"Detect", "Comply"}
    sent = ["say hello world now"]
    assert stage1.check(_s1(), sent, themes, areas)["membership_ok"]
    assert not stage1.check(_s1(primary_theme="Z"), sent, themes, areas)["primary_in_list"]
    assert not stage1.check(_s1(tags=["A"]), sent, themes, areas)["tags_ok"]  # tag equals primary
    assert not stage1.check(_s1(tags=["B", "B"]), sent, themes, areas)["tags_ok"]
    assert not stage1.check(_s1(product_area="Nope"), sent, themes, areas)["product_ok"]
    assert not stage1.check(_s1(incident="other-incident"), sent, themes, areas)["incident_ok"]
    assert stage1.check(_s1(primary_theme="Other / new theme"), sent, themes, areas)["primary_in_list"]
    q = stage1.check(_s1(evidence_quote="not in transcript"), sent, themes, areas)
    assert not q["quote_exact"] and not q["quote_loose"]


def _s2(n, **kw):
    base = dict(call_score=3.0, customer_score=None, per_turn=[{"index": i, "label": "neutral"} for i in range(n)],
                trajectory={"start": 3.0, "end": 3.5}, evidence_quote="hello", confidence="high")
    return Stage2Out.model_validate({**base, **kw})


def test_stage2_validate_checks_per_turn_and_customer():
    s = ["hello there"]
    assert stage2.validate(_s2(3), 3, False, s)["per_turn_ok"]
    assert not stage2.validate(_s2(2), 3, False, s)["per_turn_ok"]  # a turn is missing
    bad = _s2(3, per_turn=[{"index": 0, "label": "neutral"}, {"index": 2, "label": "neutral"}, {"index": 1, "label": "neutral"}])
    assert not stage2.validate(bad, 3, False, s)["per_turn_ok"]  # out of order
    assert not stage2.validate(_s2(3), 3, True, s)["customer_null_ok"]  # customer present but score null
    assert not stage2.validate(_s2(3, customer_score=3.0), 3, False, s)["customer_null_ok"]
    assert not stage2.validate(_s2(3, evidence_quote="nope"), 3, False, s)["quote_exact"]


# ---- retry-once behaviour with a mock model ----------------------------------------------------------
class RetryMock:
    """First answer per transcript is bad, the second is good. Counts calls."""

    def __init__(self, kind):
        self.kind, self.calls, self.seen = kind, 0, {}
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls += 1
        user = kw["messages"][-1]["content"]
        n_prev = self.seen.get(user[:60], 0)
        self.seen[user[:60]] = n_prev + 1
        lines = [ln for ln in user.splitlines() if ln.startswith("[")]
        n = len(lines)
        first_sentence = lines[0].split("): ", 1)[1]
        if self.kind == "s1":
            body = {"primary_theme": "Not a theme" if self.calls == 1 else "Billing and Usage Disputes", "tags": [],
                    "product_area": "Detect", "evidence_quote": first_sentence, "confidence": "high",
                    "taxonomy_version": "v1", "incident": None, "other_description": ""}
        else:
            k = n - 1 if self.calls == 1 else n  # first answer is one turn short
            body = {"call_score": 3.0, "customer_score": None if "(customer)" not in user else 3.0,
                    "per_turn": [{"index": i, "label": "neutral"} for i in range(k)],
                    "trajectory": {"start": 3.0, "end": 3.0}, "evidence_quote": first_sentence, "confidence": "high"}
        msg = SimpleNamespace(content=json.dumps(body))
        usage = SimpleNamespace(model_dump=lambda: {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.001})
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], model="mock/m", usage=usage,
                               model_extra={})


def test_stage1_retries_once_on_bad_membership(meetings, tmp_path):
    mock = RetryMock("s1")
    client = LLMClient(mode="live", cache_dir=tmp_path, openai_client=mock, min_interval=0)
    rec = stage1.classify(meetings[0], client, Guard(refresh=False), model="mock/m")
    assert rec["attempts"] == 2 and rec["status"] == "ok" and mock.calls == 2


def test_stage2_retries_once_then_ok_and_second_failure_is_recorded(meetings, tmp_path):
    m = next(x for x in meetings if not x.has_external)  # internal: no customer turn
    mock = RetryMock("s2")
    client = LLMClient(mode="live", cache_dir=tmp_path, openai_client=mock, min_interval=0)
    rec = stage2.classify(m, client, Guard(refresh=False), model="mock/m")
    assert rec["attempts"] == 2 and rec["status"] == "ok" and rec["per_turn_ok"] and mock.calls == 2

    class AlwaysShort(RetryMock):
        def _create(self, **kw):
            self.calls = 0  # super() increments it to 1, so every answer is the short one
            return super()._create(**kw)

    bad = AlwaysShort("s2")
    client2 = LLMClient(mode="live", cache_dir=tmp_path / "b", openai_client=bad, min_interval=0)
    rec2 = stage2.classify(m, client2, Guard(refresh=False), model="mock/m")
    assert rec2["status"] == "failed_validation" and rec2["attempts"] == 2 and not rec2["per_turn_ok"]


# ---- stability sample and metrics ---------------------------------------------------------------------
def test_stability_sample_is_seeded_and_stratified():
    types = {f"id{i}": ("support" if i < 30 else "external" if i < 70 else "internal") for i in range(100)}
    a, b = stability_sample(types), stability_sample(types)
    assert a == b and len(a) == 20
    counts = {t: sum(types[i] == t for i in a) for t in ("support", "external", "internal")}
    assert counts == {"support": 6, "external": 8, "internal": 6}


def test_metric_helpers():
    assert rep.mad([1, 2], [1, 3]) == 0.5
    assert rep.agree(["a", "b"], ["a", "c"]) == 0.5
    c = rep.confusion(["negative", "neutral"], ["negative", "negative"])
    assert c["negative"]["negative"] == 1 and c["negative"]["neutral"] == 1 and c["positive"]["positive"] == 0
    assert rep.is_half_step(2.5) and not rep.is_half_step(3.0) and not rep.is_half_step(3.25)
    assert rep.jaccard({"a"}, {"a", "b"}) == 0.5 and rep.jaccard(set(), set()) == 1.0
    assert rep.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert rep.spearman([1, 2, 3], [1, 8, 27]) == pytest.approx(1.0)

"""Offline tests for the bake-off scoring functions (eval/bakeoff.py). No network, no key."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
import bakeoff as B  # noqa: E402


def test_quote_valid_exact_and_loose():
    hay = ["Thank you for calling Aegis — how can I help?"]
    assert B.quote_valid("Thank you for calling Aegis", hay)
    assert not B.quote_valid("thank you for calling aegis", hay)  # exact is case sensitive
    assert not B.quote_valid("Thank you for calling Aegis - how can I help?", hay)  # dash differs
    assert B.quote_valid("thank you for calling Aegis - how can I help?", hay, loose=True)
    assert not B.quote_valid("", hay) and not B.quote_valid("   ", hay)
    assert not B.quote_valid("something invented", hay, loose=True)


def test_rates_and_agreement():
    assert B.rate([True, True, False, True]) == 75.0
    assert math.isnan(B.rate([]))
    assert B.agreement(["a", "b", "c"], ["a", "x", "c"]) == pytest.approx(66.666, abs=0.01)
    assert B.mad([1, 2, 3], [1, 3, 5]) == pytest.approx(1.0)


def test_pearson_perfect_and_degenerate():
    assert B.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert B.pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)
    assert math.isnan(B.pearson([1, 1, 1], [1, 2, 3]))  # no variance
    assert math.isnan(B.pearson([1], [1]))


def test_per_turn_agreement_uses_shared_indices_only():
    a = B.per_turn_map([{"index": 0, "label": "neutral"}, {"index": 1, "label": "negative"}, {"index": 2, "label": "positive"}])
    b = B.per_turn_map([{"index": 0, "label": "neutral"}, {"index": 1, "label": "neutral"}])
    assert B.per_turn_agreement(a, b) == 50.0


def test_check_stage1_membership():
    ok = {"primary_theme": "Compliance & audit", "tags": ["Renewal, pricing & billing"], "product_area": "Comply"}
    assert all(B.check_stage1(ok).values())
    assert not B.check_stage1({**ok, "primary_theme": "Compliance"})["primary_in_list"]
    assert not B.check_stage1({**ok, "tags": ["Compliance & audit"]})["tags_ok"]  # repeats primary
    assert not B.check_stage1({**ok, "tags": ["a", "b", "c"]})["tags_ok"]
    assert not B.check_stage1({**ok, "product_area": "Everything"})["product_ok"]
    other = {"primary_theme": "Other / new theme", "tags": ["a free-text description"], "product_area": "Detect"}
    assert B.check_stage1(other)["tags_ok"]


def test_check_stage2_coverage_and_customer_null():
    out = {"per_turn": [{"index": i, "label": "neutral"} for i in range(3)], "customer_score": None}
    assert B.check_stage2(out, 3, has_customer=False) == {"per_turn_complete": True, "customer_null_ok": True}
    assert not B.check_stage2(out, 4, has_customer=False)["per_turn_complete"]
    assert not B.check_stage2(out, 3, has_customer=True)["customer_null_ok"]  # customer present but score null
    dup = {"per_turn": [{"index": 0, "label": "neutral"}, {"index": 0, "label": "neutral"}], "customer_score": 3.0}
    assert not B.check_stage2(dup, 2, has_customer=True)["per_turn_complete"]


def test_cost_of_prefers_billed_cost_then_tokens():
    assert B.cost_of({"cost": 0.01, "prompt_tokens": 10**6}, (1.0, 5.0)) == 0.01
    assert B.cost_of({"prompt_tokens": 1_000_000, "completion_tokens": 100_000}, (1.0, 5.0)) == pytest.approx(1.5)
    assert B.cost_of(None, (1.0, 5.0)) == 0.0


def test_decide_disqualifies_below_thresholds():
    stats = {
        "a": dict(schema=97.0, quote=100.0, stability=100.0, cost=0.1),  # schema too low
        "b": dict(schema=100.0, quote=97.5, stability=100.0, cost=0.2),  # quote too low
        "c": dict(schema=100.0, quote=100.0, stability=100.0, cost=0.9, mad=0.5),  # mad too high
        "d": dict(schema=100.0, quote=99.0, stability=95.0, cost=0.5, mad=0.1),
    }
    r = B.decide(stats, max_mad=0.3)
    assert r["winner"] == "d"
    assert set(k for k, v in r["disqualified"].items() if v) == {"a", "b", "c"}
    assert B.decide({"a": stats["a"]})["winner"] is None


def test_decide_picks_cheapest_within_two_points_and_breaks_ties():
    stats = {
        "best": dict(schema=100.0, quote=100.0, stability=100.0, cost=1.0),
        "near": dict(schema=100.0, quote=99.0, stability=99.0, cost=0.4),  # quality 99.33, within 2
        "far": dict(schema=100.0, quote=98.0, stability=90.0, cost=0.1),  # quality 96.0, outside 2 points
        "tie": dict(schema=100.0, quote=99.0, stability=99.0, cost=0.4),
    }
    r = B.decide(stats, tie_prefer=["tie", "near"])
    assert r["winner"] == "tie" and "far" not in r["eligible"]
    assert B.decide(stats, tie_prefer=["near", "tie"])["winner"] == "near"


def test_sample_is_deterministic_balanced_and_contains_escalations():
    from ti.load import load_meetings

    ms = load_meetings()
    s1, s2 = B.select_sample(ms), B.select_sample(ms)
    assert s1["ids"] == s2["ids"] and len(s1["ids"]) == 15
    types = list(s1["title_rule_type"].values())
    assert {t: types.count(t) for t in ("support", "external", "internal")} == {"support": 5, "external": 5, "internal": 5}
    titles = [s1["titles"][i] for i in s1["ids"]]
    for prefix in B.ESCALATION_PREFIXES:
        assert any(t.startswith(prefix) for t in titles)


def test_models_are_pinned_to_single_providers():
    for cfg in B.MODELS.values():
        assert len(cfg["provider"]) == 1 and cfg["slug"].count("/") == 1

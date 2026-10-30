"""Offline tests for the Task 2 analysis helpers (no network, no LLM)."""
from datetime import date

import numpy as np

from ti.analysis.stats import (band, bootstrap_ci, bootstrap_diff_ci, perm_test_diff, share, standardized_mean, thirds, verdict,
                               week_start)


def test_bootstrap_ci_contains_mean_and_is_seeded():
    v = [1, 2, 3, 4, 5, 3, 3, 4]
    lo, hi = bootstrap_ci(v)
    assert lo < np.mean(v) < hi
    assert bootstrap_ci(v) == (lo, hi)  # deterministic with the fixed seed


def test_bootstrap_diff_ci_sign_and_width():
    lo, hi = bootstrap_diff_ci([5, 5, 4, 5, 4, 5], [1, 2, 1, 2, 1, 2])
    assert lo > 0 and hi > lo


def test_perm_test_separated_vs_identical():
    assert perm_test_diff([5, 5, 5, 4, 5, 5, 4, 5], [1, 1, 2, 1, 1, 2, 1, 1], n=2000) < 0.01
    assert perm_test_diff([1, 2, 3, 4], [1, 2, 3, 4], n=2000) > 0.9
    assert perm_test_diff([1, 2], [3, 4], n=500) > 0  # add-one smoothing: never exactly 0


def test_week_start_is_monday():
    assert week_start(date(2026, 3, 10)) == date(2026, 3, 9)
    assert week_start(date(2026, 3, 9)) == date(2026, 3, 9)
    assert week_start(date(2026, 3, 15)).weekday() == 0


def test_band_thresholds():
    assert [band(x) for x in (1.0, 2.4, 2.5, 3.4, 3.5, 5.0)] == ["low", "low", "mid", "mid", "high", "high"]


def test_share_and_nan():
    assert share(["negative", "neutral", "negative", "positive"], "negative") == 0.5
    assert np.isnan(share([], "negative"))


def test_thirds_matches_stage2_definition():
    first, last = thirds(10)  # ceil(10/3) = 4
    assert list(first) == [0, 1, 2, 3] and list(last) == [6, 7, 8, 9]
    first, last = thirds(3)
    assert list(first) == [0] and list(last) == [2]


def test_standardized_mean_removes_mix_effect():
    # same within-group means, different group mix -> identical standardized mean
    means = {"a": 2.0, "b": 4.0}
    assert standardized_mean(means, {"a": 1, "b": 1}) == 3.0
    assert standardized_mean(means, {"a": 10, "b": 10}) == 3.0


def test_verdict_rules():
    assert verdict((0.1, 0.9), 40) .startswith("supported")
    assert verdict((-0.1, 0.9), 40) == "directional only"
    assert verdict((0.1, 0.9), 5) == "directional only"


def test_calls_table_matches_frozen_stage_outputs():
    from ti.analysis.sentiment import build_calls
    df = build_calls()
    assert len(df) == 100
    assert df.type.value_counts().to_dict() == {"external": 40, "support": 30, "internal": 30}
    assert int(df.touches_incident.sum()) == 42 and int(df.core_incident.sum()) == 18
    assert (df.type != df.title_rule).sum() == 3

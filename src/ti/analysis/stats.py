"""Small, dependency-light statistics helpers for the Task 2 analysis (offline, seeded)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Sequence

import numpy as np

SEED = 20261029
N_RESAMPLES = 10_000


def bootstrap_ci(values: Sequence[float], stat: Callable = np.mean, n: int = N_RESAMPLES, seed: int = SEED,
                 level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap CI of `stat` over calls (resampling calls with replacement)."""
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n, len(v)))
    stats = np.apply_along_axis(stat, 1, v[idx]) if stat is not np.mean else v[idx].mean(axis=1)
    lo, hi = np.quantile(stats, [(1 - level) / 2, 1 - (1 - level) / 2])
    return (float(lo), float(hi))


def bootstrap_diff_ci(a: Sequence[float], b: Sequence[float], n: int = N_RESAMPLES, seed: int = SEED,
                      level: float = 0.95) -> tuple[float, float]:
    """CI of mean(a) - mean(b) with independent resampling of each group."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    ma = a[rng.integers(0, len(a), size=(n, len(a)))].mean(axis=1)
    mb = b[rng.integers(0, len(b), size=(n, len(b)))].mean(axis=1)
    lo, hi = np.quantile(ma - mb, [(1 - level) / 2, 1 - (1 - level) / 2])
    return (float(lo), float(hi))


def perm_test_diff(a: Sequence[float], b: Sequence[float], n: int = N_RESAMPLES, seed: int = SEED) -> float:
    """Two-sided permutation p-value for the difference in means (add-one smoothing, never exactly 0)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    obs = abs(a.mean() - b.mean())
    pool = np.concatenate([a, b])
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(pool[: len(a)].mean() - pool[len(a):].mean()) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (n + 1)


def week_start(d: date) -> date:
    """Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def band(x: float) -> str:
    """Coarse band used only to flag disagreements: low < 2.5 <= mid < 3.5 <= high."""
    return "low" if x < 2.5 else ("mid" if x < 3.5 else "high")


def share(labels: Sequence[str], target: str) -> float:
    return float("nan") if len(labels) == 0 else sum(1 for x in labels if x == target) / len(labels)


def thirds(n: int) -> tuple[range, range]:
    """First and last ceil(n/3) turn indices (the Stage 2 trajectory definition)."""
    k = -(-n // 3)
    return range(0, k), range(n - k, n)


def standardized_mean(group_means: dict[str, float], weights: dict[str, float]) -> float:
    """Mean of within-group means under fixed weights (removes composition effects)."""
    tot = sum(weights[g] for g in group_means)
    return sum(group_means[g] * weights[g] for g in group_means) / tot


def verdict(ci: tuple[float, float], n: int, min_n: int = 10) -> str:
    """'supported' when the CI of a difference excludes 0 and n is adequate, else 'directional only'."""
    lo, hi = ci
    if n < min_n or (lo <= 0 <= hi):
        return "directional only"
    return "supported (n adequate, CI excludes 0)"

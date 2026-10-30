"""Shared helpers for the production runs of Stage 1 and Stage 2 (D7, D8).

- one pinned model and provider for every call (D7), settings fixed here and recorded in each cache entry;
- a spend guard that stops (never works around) a low balance or a payment / limit error;
- a seeded, stratified stability sample;
- quote checks that the schemas cannot express.
"""

from __future__ import annotations

import csv
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from . import OUTPUT_DIR
from .llm import LLMClient
from .load import Meeting
from .stage1_discovery import Guard, SpendStop, cost_of, is_limit_error, quote_exact, quote_loose  # re-exported

__all__ = ["Guard", "SpendStop", "cost_of", "is_limit_error", "quote_exact", "quote_loose", "BASE_PARAMS",
           "stage0_types", "stability_sample", "transcript_lines", "run_parallel", "word_count", "STABILITY_SEED"]

BASE_PARAMS = {"reasoning_effort": "low", "seed": 7}  # D7
STABILITY_SEED = 11
STABILITY_N = {"support": 6, "external": 8, "internal": 6}  # 20 calls, stratified by Stage 0 type


def stage0_types() -> dict[str, str]:
    """meeting_id -> frozen Stage 0 label (outputs/stage0_final.csv)."""
    with open(OUTPUT_DIR / "stage0_final.csv") as f:
        return {r["meeting_id"]: r["label"] for r in csv.DictReader(f)}


def stability_sample(types: dict[str, str], seed: int = STABILITY_SEED) -> list[str]:
    ids = []
    for t, n in STABILITY_N.items():
        pool = sorted(i for i, lab in types.items() if lab == t)
        ids += random.Random(seed).sample(pool, n)
    return sorted(ids)


def transcript_lines(meeting: Meeting, stage: str) -> list[str]:
    turns = meeting.view_for(stage)["turns"]
    return [f"[{t['index']}] {t['speaker']} ({t['side']}): {t['sentence']}" for t in turns]


def word_count(s: str) -> int:
    return len(s.split())


def model_for(stage_env: str) -> str:
    m = os.getenv(stage_env, "")
    if not m:
        raise RuntimeError(f"{stage_env} is not set in .env (D7)")
    return m


def run_parallel(fn: Callable[[Meeting], dict], meetings: list[Meeting], guard: Guard, workers: int = 4) -> list[dict]:
    """Run fn over meetings. Stops cleanly (keeps finished results) when the guard trips."""
    results: list[dict] = []

    def wrapped(m: Meeting) -> dict | None:
        if guard.stopped:
            return None
        try:
            return fn(m)
        except SpendStop:
            return None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(wrapped, meetings):
            if r is not None:
                results.append(r)
    return results


def write_json(path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))

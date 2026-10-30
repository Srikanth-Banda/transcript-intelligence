"""Model bake-off harness (docs/model-selection.md section 7).

Reproducible: every live call goes through src/ti/llm.py (cached, provider pinned), every run is logged to
outputs/bakeoff/results.jsonl, and every metric is computed from that log by `report`. The scoring functions at
the top are pure and tested offline (tests/test_bakeoff.py).

Usage (from the project root):
    uv run python eval/bakeoff.py sample
    uv run python eval/bakeoff.py stage0  --models haiku,gemini --runs 1,2 [--limit N]
    uv run python eval/bakeoff.py stage12 --models sonnet,terra,gemini --runs 1,2 [--limit N]
    uv run python eval/bakeoff.py probe
    uv run python eval/bakeoff.py report

Spend guard: stops (no retries, no tricks) when the key's remaining balance is below MIN_BALANCE, or when a call
returns a payment / limit error. Partial results are kept; a re-run resumes from the log and the cache.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics as st
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs" / "bakeoff"
RESULTS = OUT / "results.jsonl"
MIN_BALANCE = 0.75
SAMPLE_SEED = 42
THEMES = [
    "Outage & incident response", "Compliance & audit", "Renewal, pricing & billing", "Churn & competitive risk",
    "Onboarding & rollout", "Identity & access", "Product roadmap & planning", "Integrations, backup & data",
    "Other / new theme",
]
PRODUCT_AREAS = ["Detect", "Comply", "Identity", "Protect", "Backup", "Platform/General"]
ESCALATION_PREFIXES = ("URGENT: Blackridge", "URGENT: Cobalt", "ESCALATION: Northstar")

# slug, pinned provider (OpenRouter provider tag, standard tier, no fallbacks), reasoning effort for models whose
# reasoning is mandatory, seed for models that list it, USD per million tokens (input, output).
MODELS = {
    "haiku": dict(slug="anthropic/claude-haiku-5.5", provider=["anthropic"], effort=None, seed=None, price=(0.10, 0.50)),
    "sonnet": dict(slug="anthropic/claude-sonnet-5.5", provider=["anthropic"], effort="low", seed=None, price=(2.0, 10.0)),
    "terra": dict(slug="openai/gpt-6.1-terra", provider=["openai"], effort=None, seed=7, price=(1.0, 5.0)),
    "gemini": dict(slug="google/gemini-3.8-flash", provider=["google-ai-studio"], effort="low", seed=7, price=(0.75, 3.75)),
}
MAX_TOKENS = {"stage0": 3000, "stage1": 4000, "stage2": 10000}


# ======================================================================================================
# Pure scoring functions (tested offline)
# ======================================================================================================
def _norm(s: str) -> str:
    table = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}
    return " ".join("".join(table.get(c, c) for c in s).split()).lower()


def quote_valid(quote: str, haystacks: list[str], loose: bool = False) -> bool:
    """Exact substring of at least one haystack (a turn, or the formatted opening). Empty quote is invalid."""
    if not quote or not quote.strip():
        return False
    if loose:
        q = _norm(quote)
        return any(q in _norm(h) for h in haystacks)
    return any(quote in h for h in haystacks)


def rate(flags: list[bool]) -> float:
    return 100.0 * sum(flags) / len(flags) if flags else float("nan")


def agreement(a: list, b: list) -> float:
    """Percent of positions where two equal-length label lists agree."""
    assert len(a) == len(b)
    return rate([x == y for x, y in zip(a, b)])


def mad(a: list[float], b: list[float]) -> float:
    assert len(a) == len(b) and a
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 2 or len(set(x)) < 2 or len(set(y)) < 2:
        return float("nan")
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den


def per_turn_map(per_turn: list[dict]) -> dict[int, str]:
    return {t["index"]: t["label"] for t in per_turn}


def per_turn_agreement(a: dict[int, str], b: dict[int, str]) -> float:
    keys = sorted(set(a) & set(b))
    return rate([a[k] == b[k] for k in keys])


def check_stage1(out: dict) -> dict:
    """List membership checks the schema cannot enforce."""
    primary_ok = out["primary_theme"] in THEMES
    if out["primary_theme"] == "Other / new theme":
        tags_ok = len(out["tags"]) <= 2
    else:
        tags_ok = all(t in THEMES and t != out["primary_theme"] for t in out["tags"]) and len(out["tags"]) <= 2
    return {"primary_in_list": primary_ok, "tags_ok": tags_ok, "product_ok": out["product_area"] in PRODUCT_AREAS}


def check_stage2(out: dict, n_turns: int, has_customer: bool) -> dict:
    idx = [t["index"] for t in out["per_turn"]]
    return {
        "per_turn_complete": sorted(idx) == list(range(n_turns)),
        "customer_null_ok": (out.get("customer_score") is None) == (not has_customer),
    }


def cost_of(usage: dict | None, price: tuple[float, float]) -> float:
    """Billed cost if OpenRouter returned it, else tokens times listed price."""
    if not usage:
        return 0.0
    if usage.get("cost") is not None:
        return float(usage["cost"])
    return (usage.get("prompt_tokens", 0) * price[0] + usage.get("completion_tokens", 0) * price[1]) / 1e6


def quality_score(schema_valid: float, quote_valid_rate: float, stability: float) -> float:
    """Mean of the three percentage metrics the decision rule compares ('points')."""
    return (schema_valid + quote_valid_rate + stability) / 3.0


def decide(stats: dict[str, dict], min_schema=98.0, min_quote=98.0, max_mad=None, tie_prefer: list[str] | None = None) -> dict:
    """Decision rule (model-selection.md section 7).

    stats[model] = {schema, quote, stability, cost, mad (optional)}. Disqualify below the thresholds (or above
    max_mad when given); among the rest pick the cheapest whose quality score is within 2 points of the best;
    ties (same cost) go to the first model in tie_prefer.
    """
    ok, dq = {}, {}
    for m, s in stats.items():
        why = []
        if s["schema"] < min_schema:
            why.append(f"schema-valid {s['schema']:.1f}% < {min_schema}")
        if s["quote"] < min_quote:
            why.append(f"quote validity {s['quote']:.1f}% < {min_quote}")
        if max_mad is not None and s.get("mad") is not None and s["mad"] > max_mad:
            why.append(f"run-to-run MAD {s['mad']:.2f} > {max_mad}")
        (dq if why else ok)[m] = why or None
    if not ok:
        return {"winner": None, "disqualified": dq, "reason": "all models disqualified"}
    q = {m: quality_score(stats[m]["schema"], stats[m]["quote"], stats[m]["stability"]) for m in ok}
    best = max(q.values())
    eligible = [m for m in ok if q[m] >= best - 2.0]
    prefer = tie_prefer or []
    winner = sorted(eligible, key=lambda m: (stats[m]["cost"], prefer.index(m) if m in prefer else 99))[0]
    return {"winner": winner, "disqualified": dq, "quality": q, "eligible": eligible}


# ======================================================================================================
# Sample selection
# ======================================================================================================
def select_sample(meetings, seed: int = SAMPLE_SEED) -> dict:
    """15 calls: 3 escalations, plus hard picks, plus seeded random fill; 5 per title-rule call type (escalations
    count as external). Hard picks: longest transcript, shortest transcript, and the call where the provided score
    and the provided sentence-label balance disagree most (all are selection aids, never stage inputs)."""
    by_id = {m.meeting_id: m for m in meetings}
    quota = {"support": 5, "external": 5, "internal": 5}
    chosen: dict[str, str] = {}
    counts = {"support": 0, "external": 0, "internal": 0}

    def add(m, why: str) -> bool:
        t = m.title_rule_label
        if m.meeting_id in chosen or counts[t] >= quota[t]:
            return False
        chosen[m.meeting_id] = why
        counts[t] += 1
        return True

    for m in meetings:
        if m.title.startswith(ESCALATION_PREFIXES):
            add(m, "escalation call (title says external, opens like support)")
    words = {m.meeting_id: sum(len(t.sentence.split()) for t in m.turns) for m in meetings}

    def balance(m):
        ts = m.provided.turn_sentiments
        return (ts.count("positive") - ts.count("negative")) / len(ts)

    zs = lambda xs: [(x - st.mean(xs)) / (st.pstdev(xs) or 1) for x in xs]
    zscore = dict(zip([m.meeting_id for m in meetings], zs([m.provided.sentiment_score for m in meetings])))
    zbal = dict(zip([m.meeting_id for m in meetings], zs([balance(m) for m in meetings])))
    resid = {i: abs(zscore[i] - zbal[i]) for i in zscore}
    hard_orders = [
        ("longest transcript", sorted(meetings, key=lambda m: -words[m.meeting_id])),
        ("shortest transcript", sorted(meetings, key=lambda m: words[m.meeting_id])),
        ("provided score and sentence-label balance disagree most", sorted(meetings, key=lambda m: -resid[m.meeting_id])),
    ]
    for why, order in hard_orders:
        for m in order:
            if add(m, f"known-hard: {why}"):
                break
    rng = random.Random(seed)
    for t in ("support", "external", "internal"):
        pool = sorted([m for m in meetings if m.title_rule_label == t and m.meeting_id not in chosen], key=lambda m: m.meeting_id)
        rng.shuffle(pool)
        for m in pool:
            if counts[t] >= quota[t]:
                break
            add(m, f"seeded random ({seed})")
    ids = sorted(chosen, key=lambda i: (by_id[i].start_time, i))
    return {
        "seed": seed,
        "ids": ids,
        "why": chosen,
        "titles": {i: by_id[i].title for i in ids},
        "title_rule_type": {i: by_id[i].title_rule_label for i in ids},
        "has_customer": {i: by_id[i].has_external for i in ids},
    }


# ======================================================================================================
# Spend guard and key info
# ======================================================================================================
def key_info() -> dict:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    req = urllib.request.Request("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": "Bearer " + key})
    return json.load(urllib.request.urlopen(req, timeout=30))["data"]


class Guard:
    """Stops the run when the balance is low or a payment / limit error appears. Never retries around it."""

    def __init__(self):
        self.stop = threading.Event()
        self.reason = ""
        self.session_cost = 0.0
        self.remaining = None
        self.lock = threading.Lock()
        self.calls = 0

    def refresh(self) -> None:
        d = key_info()
        self.remaining = d.get("limit_remaining")
        if self.remaining is not None and self.remaining < MIN_BALANCE:
            self.trip(f"remaining balance ${self.remaining:.2f} < ${MIN_BALANCE}")

    def trip(self, reason: str) -> None:
        with self.lock:
            if not self.stop.is_set():
                self.reason = reason
                self.stop.set()

    def note(self, cost: float) -> None:
        with self.lock:
            self.session_cost += cost
            self.calls += 1
            n = self.calls
        if self.remaining is not None and self.remaining - self.session_cost < MIN_BALANCE:
            self.trip(f"estimated remaining ${self.remaining - self.session_cost:.2f} < ${MIN_BALANCE}")
        elif n % 25 == 0:
            self.refresh()


def is_limit_error(e: Exception) -> bool:
    code = getattr(e, "status_code", None)
    msg = str(e).lower()
    return code == 402 or (code in (403, 429) and any(w in msg for w in ("limit", "credit", "insufficient", "balance")))


# ======================================================================================================
# Runner
# ======================================================================================================
def load_results() -> list[dict]:
    if not RESULTS.exists():
        return []
    return [json.loads(line) for line in RESULTS.read_text().splitlines() if line.strip()]


_write_lock = threading.Lock()


def append_result(rec: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with _write_lock, RESULTS.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def user_message(stage: str, meeting) -> str:
    if stage == "stage0":
        from ti.stage0 import build_user_message

        return build_user_message(meeting)
    turns = meeting.view_for(stage)["turns"]
    return "transcript:\n" + "\n".join(f"[{t['index']}] {t['speaker']} ({t['side']}): {t['sentence']}" for t in turns)


def prompt_for(stage: str) -> tuple[str, str]:
    from ti.llm import load_prompt

    return load_prompt({"stage0": "stage0_v1", "stage1": "stage1_bakeoff_v0", "stage2": "stage2_bakeoff_v0"}[stage])


def schema_for(stage: str):
    from ti import schemas

    return {"stage0": schemas.Stage0LLMOut, "stage1": schemas.Stage1Out, "stage2": schemas.Stage2Out}[stage]


def one_call(client, guard: Guard, stage: str, model_key: str, run: int, meeting) -> dict | None:
    from ti.llm import InvalidOutput, sha256

    if guard.stop.is_set():
        return None
    cfg = MODELS[model_key]
    version, system = prompt_for(stage)
    params = {"max_tokens": MAX_TOKENS[stage], "provider_order": cfg["provider"], "run": run}
    if cfg["effort"]:
        params["reasoning_effort"] = cfg["effort"]
    if cfg["seed"] is not None:
        params["seed"] = cfg["seed"]
    user = user_message(stage, meeting)
    rec = {"stage": stage, "model": model_key, "run": run, "meeting_id": meeting.meeting_id, "prompt_version": version,
           "prompt_sha": sha256(system)[:12]}
    t0 = time.monotonic()
    try:
        out, meta = client.complete(stage=stage, prompt_version=version, model=cfg["slug"], system=system, user=user,
                                    schema=schema_for(stage), params=params)
        usage = meta.get("usage") or {}
        rec.update(ok=True, first_attempt_ok=not meta.get("retried"), retried=bool(meta.get("retried")),
                   cache_hit=meta["cache_hit"], latency_s=meta.get("latency_s"), finish_reason=meta.get("finish_reason"),
                   cost=cost_of(usage, cfg["price"]), prompt_tokens=usage.get("prompt_tokens"),
                   completion_tokens=usage.get("completion_tokens"), model_returned=meta.get("model_returned"),
                   provider_returned=meta.get("provider_returned"), structured_mode=meta.get("structured_mode"),
                   parsed=out.model_dump())
        if not meta["cache_hit"]:
            guard.note(rec["cost"])
    except InvalidOutput as e:
        usage = e.usage or {}
        rec.update(ok=False, first_attempt_ok=False, retried=True, error="invalid_output_twice", error_detail=str(e)[:300],
                   raw_text=e.text[:2000], latency_s=round(e.latency_s, 3), cost=cost_of(usage, cfg["price"]),
                   completion_tokens=usage.get("completion_tokens"), prompt_tokens=usage.get("prompt_tokens"))
        guard.note(rec["cost"])
    except Exception as e:  # noqa: BLE001 - API errors are data in a bake-off
        if is_limit_error(e):
            guard.trip(f"payment / limit error: {type(e).__name__} {getattr(e, 'status_code', '')}")
            return None
        rec.update(ok=False, first_attempt_ok=False, error=type(e).__name__, error_detail=str(e)[:300],
                   latency_s=round(time.monotonic() - t0, 3), cost=0.0)
    append_result(rec)
    return rec


def run_batch(stage: str, models: list[str], runs: list[int], meetings: list, limit: int | None = None, workers: int = 4) -> Guard:
    from ti.llm import LLMClient

    guard = Guard()
    guard.refresh()
    print(f"balance before: ${guard.remaining:.4f} remaining; guard stops below ${MIN_BALANCE}")
    if guard.stop.is_set():
        print("STOP:", guard.reason)
        return guard
    done = {(r["stage"], r["model"], r["run"], r["meeting_id"]) for r in load_results()}
    jobs = [(m, r, mt) for m in models for r in runs for mt in (meetings[:limit] if limit else meetings)
            if (stage, m, r, mt.meeting_id) not in done]
    print(f"{stage}: {len(jobs)} calls to run ({len(done)} already logged)")
    client = LLMClient(min_interval=0.1)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda j: one_call(client, guard, stage, j[0], j[1], j[2]), jobs))
    guard.refresh() if not guard.stop.is_set() else None
    print(f"session cost (billed, live calls): ${guard.session_cost:.4f}; remaining: ${guard.remaining}")
    if guard.stop.is_set():
        print("STOPPED:", guard.reason)
    return guard


# ======================================================================================================
# CLI
# ======================================================================================================
def customer_meetings(meetings):
    return [m for m in meetings if not m.is_internal_by_metadata]


def main() -> None:
    from ti.load import load_meetings

    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "stage0", "stage12", "probe", "report"])
    ap.add_argument("--models", default="")
    ap.add_argument("--runs", default="1,2")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    meetings = load_meetings()
    OUT.mkdir(parents=True, exist_ok=True)
    sample_path = OUT / "sample.json"
    if a.cmd == "sample":
        s = select_sample(meetings)
        sample_path.write_text(json.dumps(s, indent=2, ensure_ascii=False))
        for i in s["ids"]:
            print(i[-6:], s["title_rule_type"][i], "|", s["titles"][i], "|", s["why"][i])
        return
    if a.cmd == "report":
        from bakeoff_report import build_report  # noqa: F401  (kept separate to keep this file readable)

        build_report(meetings)
        return
    models = [m for m in a.models.split(",") if m]
    runs = [int(r) for r in a.runs.split(",") if r]
    if a.cmd == "stage0":
        run_batch("stage0", models, runs, customer_meetings(meetings), a.limit)
        return
    sample = json.loads(sample_path.read_text())
    sm = [m for m in meetings if m.meeting_id in set(sample["ids"])]
    if a.cmd == "stage12":
        for stage in ("stage1", "stage2"):
            g = run_batch(stage, models, runs, sm, a.limit)
            if g.stop.is_set():
                break
        return
    if a.cmd == "probe":
        # third identical call on 3 transcripts per model: runs 1 and 2 already exist, run 3 completes the probe
        first3 = [m for m in sm if m.has_external][:3]
        run_batch("stage0", models or ["haiku", "gemini"], [3], first3)
        run_batch("stage2", models or ["sonnet", "terra", "gemini"], [3], first3)


if __name__ == "__main__":
    main()

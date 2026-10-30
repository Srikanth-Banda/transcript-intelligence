"""Stage 1, part 1: one-time taxonomy DISCOVERY (D3, D3a). Not the recurring classification stage.

Flow (all calls use the model pinned in D7; the only transcript input is `view_for("stage1")`):
  1. split the 100 calls into 4 batches of 25 (seeded shuffle), one discovery call per batch
  2. consolidation call merges the 4 batch outputs into <= 12 candidate themes (code takes the union of call ids
     and evidence, so the model can not invent evidence at this step)
  3. repeat 1 and 2 with a different split seed ("run 2") to measure stability
  4. scripted overlap between the two runs (Jaccard on the sets of calls each theme covers)
  5. proposal call: draft taxonomy v0 of 6 to 8 themes (NOT frozen, the candidate approves it)
  6. pilot assignment of all 100 calls to v0, to see counts, examples and the split by Stage 0 call type

Pure functions are tested offline in tests/test_stage1_discovery.py. Live calls go through ti.llm.LLMClient, so
every response is cached and committed.
"""

from __future__ import annotations

import json
import os
import random
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import OUTPUT_DIR, ROOT
from .llm import InvalidOutput, LLMClient, load_prompt, sha256
from .load import Meeting

OUT = OUTPUT_DIR / "stage1"
MIN_BALANCE = 0.75
N_BATCHES = 4
OWNERS = ("support lead", "sales / account manager", "product manager", "engineering lead")
OTHER = "Other / new theme"
PRICE = (0.75, 3.75)  # google/gemini-3.8-flash, USD per million tokens (input, output); used only if billed cost is absent
RUN_SPLIT_SEEDS = {1: 11, 2: 23}
PILOT_SPLIT_SEED = 37
PARAMS_BASE = {"reasoning_effort": "low", "seed": 7}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


Owner = Literal["support lead", "sales / account manager", "product manager", "engineering lead"]


# ---- schemas -------------------------------------------------------------------------------------
class Evidence(_Strict):
    meeting_id: str
    quote: str


class BatchTheme(_Strict):
    name: str
    definition: str
    distinguishing: str
    owner: Owner
    actionable_because: str
    meeting_ids: list[str]
    evidence: list[Evidence]


class BatchProduct(_Strict):
    name: str
    meeting_ids: list[str]
    evidence: list[Evidence]


class BatchDiscovery(_Strict):
    themes: list[BatchTheme]
    product_areas: list[BatchProduct]
    other_note: str


class MergedTheme(_Strict):
    name: str
    definition: str
    distinguishing: str
    owner: Owner
    actionable_because: str
    merged_from: list[str]


class MergedProduct(_Strict):
    name: str
    merged_from: list[str]


class Dropped(_Strict):
    source: str
    reason: str


class Consolidation(_Strict):
    themes: list[MergedTheme]
    product_areas: list[MergedProduct]
    dropped: list[Dropped]
    other_note: str


class ProposedTheme(_Strict):
    name: str
    definition: str
    boundary_note: str
    owner: Owner
    sources: list[str]
    note: str


class ProposedProduct(_Strict):
    name: str
    note: str


class Proposal(_Strict):
    themes: list[ProposedTheme]
    product_areas: list[ProposedProduct]
    dropped_candidates: list[Dropped]
    other_policy: str
    rationale: str


class PilotRecord(_Strict):
    meeting_id: str
    primary_theme: str
    tags: list[str] = Field(max_length=2)
    product_area: str
    other_description: str
    evidence_quote: str
    confidence: Literal["low", "medium", "high"]


class PilotBatch(_Strict):
    records: list[PilotRecord]


# ---- pure helpers (unit-tested) ------------------------------------------------------------------
def call_label(meeting_id: str) -> str:
    """Short call id shown to the model: the last 6 characters of the meeting id."""
    return meeting_id[-6:]


def label_map(meetings: list[Meeting]) -> dict[str, Meeting]:
    m = {call_label(x.meeting_id): x for x in meetings}
    if len(m) != len(meetings):
        raise ValueError("short call ids are not unique; use a longer suffix")
    return m


def split_batches(ids: list[str], n_batches: int, seed: int) -> list[list[str]]:
    """Seeded shuffle, then n near-equal batches (sizes differ by at most 1). Deterministic."""
    ids = sorted(ids)
    random.Random(seed).shuffle(ids)
    return [sorted(ids[i::n_batches]) for i in range(n_batches)]


def render_batch(meetings: list[Meeting], labels: list[str], by_label: dict[str, Meeting]) -> str:
    """Model input: id header, then 'Speaker (side): sentence' lines. Nothing else leaves load.view_for('stage1')."""
    parts = []
    for lab in labels:
        view = by_label[lab].view_for("stage1")
        lines = "\n".join(f"{t['speaker']} ({t['side']}): {t['sentence']}" for t in view["turns"])
        parts.append(f"=== call {lab} ===\n{lines}")
    return f"calls in this batch: {len(labels)}\n\n" + "\n\n".join(parts)


def quote_exact(quote: str, sentences: list[str]) -> bool:
    q = quote.strip()
    return bool(q) and any(q in s for s in sentences)


def _norm(s: str) -> str:
    return " ".join(s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
                    .replace("—", "-").replace("–", "-").split()).lower()


def quote_loose(quote: str, sentences: list[str]) -> bool:
    q = _norm(quote)
    return bool(q) and any(q in _norm(s) for s in sentences)


def validate_evidence(items: list[Evidence], allowed: set[str], sentences_by_id: dict[str, list[str]]) -> dict:
    """Counts: how many evidence items cite a known id, have an exact quote, and a loose quote."""
    n = len(items)
    known = [e for e in items if e.meeting_id in allowed]
    exact = sum(quote_exact(e.quote, sentences_by_id[e.meeting_id]) for e in known)
    loose = sum(quote_loose(e.quote, sentences_by_id[e.meeting_id]) for e in known)
    return {"n": n, "known_id": len(known), "exact": exact, "loose": loose}


def validate_batch(out: BatchDiscovery, batch_labels: list[str], sentences_by_id: dict[str, list[str]]) -> dict:
    allowed = set(batch_labels)
    ev = [e for t in out.themes for e in t.evidence] + [e for p in out.product_areas for e in p.evidence]
    stats = validate_evidence(ev, allowed, sentences_by_id)
    ids = [i for t in out.themes for i in t.meeting_ids] + [i for p in out.product_areas for i in p.meeting_ids]
    stats["ids_total"] = len(ids)
    stats["ids_unknown"] = sum(i not in allowed for i in ids)
    stats["n_themes"] = len(out.themes)
    stats["n_products"] = len(out.product_areas)
    return stats


def source_table(batches: list[BatchDiscovery]) -> tuple[dict, dict]:
    """Source ids 'b{batch}.t{n}' and 'b{batch}.p{n}' (1-based) -> the source theme/product."""
    themes, products = {}, {}
    for b, out in enumerate(batches, 1):
        for i, t in enumerate(out.themes, 1):
            themes[f"b{b}.t{i}"] = t
        for i, p in enumerate(out.product_areas, 1):
            products[f"b{b}.p{i}"] = p
    return themes, products


def consolidation_input(batches: list[BatchDiscovery]) -> str:
    themes, products = source_table(batches)
    payload = {
        "themes": [
            {"source": sid, "name": t.name, "definition": t.definition, "distinguishing": t.distinguishing,
             "owner": t.owner, "actionable_because": t.actionable_because, "calls": len(set(t.meeting_ids))}
            for sid, t in themes.items()
        ],
        "product_areas": [{"source": sid, "name": p.name, "calls": len(set(p.meeting_ids))}
                          for sid, p in products.items()],
    }
    return json.dumps(payload, ensure_ascii=False, indent=1)


def check_consolidation(c: Consolidation, batches: list[BatchDiscovery]) -> dict:
    """Every source id appears exactly once across merged_from + dropped; no invented ids."""
    themes, products = source_table(batches)
    used = [s for t in c.themes for s in t.merged_from] + [d.source for d in c.dropped]
    pused = [s for p in c.product_areas for s in p.merged_from]
    return {
        "themes_unknown": sorted(set(used) - set(themes) - set(products)),
        "themes_missing": sorted(set(themes) - set(used)),
        "themes_duplicated": sorted({s for s in used if used.count(s) > 1}),
        "products_unknown": sorted(set(pused) - set(products)),
        "products_missing": sorted(set(products) - set(pused)),
        "products_duplicated": sorted({s for s in pused if pused.count(s) > 1}),
        "n_themes": len(c.themes),
    }


def materialize(c: Consolidation, batches: list[BatchDiscovery], max_evidence: int = 6) -> dict:
    """Consolidated candidates with call ids and evidence taken by code (union of the source themes)."""
    themes, products = source_table(batches)
    out_t = []
    for i, t in enumerate(c.themes, 1):
        srcs = [themes[s] for s in t.merged_from if s in themes]
        ids = sorted({m for s in srcs for m in s.meeting_ids})
        ev, seen = [], set()
        for s in srcs:
            for e in s.evidence:
                if (e.meeting_id, e.quote) not in seen:
                    seen.add((e.meeting_id, e.quote))
                    ev.append(e.model_dump())
        out_t.append({**t.model_dump(), "id": f"c{i}", "meeting_ids": ids, "n_calls": len(ids),
                      "evidence": ev[:max_evidence]})
    out_p = []
    for i, p in enumerate(c.product_areas, 1):
        srcs = [products[s] for s in p.merged_from if s in products]
        ids = sorted({m for s in srcs for m in s.meeting_ids})
        out_p.append({**p.model_dump(), "id": f"p{i}", "meeting_ids": ids, "n_calls": len(ids)})
    return {"themes": out_t, "product_areas": out_p, "dropped": [d.model_dump() for d in c.dropped],
            "other_note": c.other_note}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def best_matches(a: list[dict], b: list[dict]) -> list[dict]:
    """For each theme in a, the theme in b covering the most similar set of calls (Jaccard on call ids)."""
    rows = []
    for ta in a:
        sa = set(ta["meeting_ids"])
        best = max(b, key=lambda tb: jaccard(sa, set(tb["meeting_ids"])), default=None)
        j = jaccard(sa, set(best["meeting_ids"])) if best else 0.0
        rows.append({"a_id": ta["id"], "a_name": ta["name"], "a_calls": len(sa),
                     "b_id": best["id"] if best else None, "b_name": best["name"] if best else None,
                     "b_calls": len(best["meeting_ids"]) if best else 0, "jaccard": round(j, 3)})
    return rows


def stability_summary(run1: list[dict], run2: list[dict], threshold: float = 0.5) -> dict:
    ab, ba = best_matches(run1, run2), best_matches(run2, run1)
    mean = lambda rows: round(sum(r["jaccard"] for r in rows) / len(rows), 3) if rows else 0.0  # noqa: E731
    return {
        "run1_to_run2_mean_best_jaccard": mean(ab),
        "run2_to_run1_mean_best_jaccard": mean(ba),
        "run1_themes_with_match_ge_threshold": sum(r["jaccard"] >= threshold for r in ab),
        "run2_themes_with_match_ge_threshold": sum(r["jaccard"] >= threshold for r in ba),
        "n_run1": len(run1), "n_run2": len(run2), "threshold": threshold,
        "run1_to_run2": ab, "run2_to_run1": ba,
    }


def check_pilot(batch_labels: list[str], recs: list[PilotRecord], theme_names: set[str], product_names: set[str],
                sentences_by_id: dict[str, list[str]]) -> dict:
    ids = [r.meeting_id for r in recs]
    allowed_themes = theme_names | {OTHER}
    bad_theme = [r.meeting_id for r in recs if r.primary_theme not in allowed_themes]
    bad_tag = [r.meeting_id for r in recs if any(t not in theme_names for t in r.tags) or r.primary_theme in r.tags]
    bad_prod = [r.meeting_id for r in recs if r.product_area not in product_names | {"Platform/General"}]
    known = [r for r in recs if r.meeting_id in sentences_by_id]
    exact = sum(quote_exact(r.evidence_quote, sentences_by_id[r.meeting_id]) for r in known)
    loose = sum(quote_loose(r.evidence_quote, sentences_by_id[r.meeting_id]) for r in known)
    return {
        "expected": len(batch_labels), "returned": len(recs),
        "missing": sorted(set(batch_labels) - set(ids)), "extra": sorted(set(ids) - set(batch_labels)),
        "duplicates": sorted({i for i in ids if ids.count(i) > 1}),
        "bad_theme": bad_theme, "bad_tag": bad_tag, "bad_product": bad_prod,
        "quotes": len(known), "quote_exact": exact, "quote_loose": loose,
    }


def theme_by_type(assignments: list[dict], types: dict[str, str]) -> dict:
    """{theme: {'support': n, 'external': n, 'internal': n, 'total': n}} using the primary theme only."""
    table: dict[str, dict] = {}
    for a in assignments:
        row = table.setdefault(a["primary_theme"], {"support": 0, "external": 0, "internal": 0, "total": 0})
        row[types[a["meeting_id"]]] += 1
        row["total"] += 1
    return table


# ---- spend guard ---------------------------------------------------------------------------------
def key_info() -> dict:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    req = urllib.request.Request("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": "Bearer " + key})
    return json.load(urllib.request.urlopen(req, timeout=30))["data"]


def cost_of(usage: dict | None) -> float:
    if not usage:
        return 0.0
    if usage.get("cost") is not None:
        return float(usage["cost"])
    return (usage.get("prompt_tokens", 0) * PRICE[0] + usage.get("completion_tokens", 0) * PRICE[1]) / 1e6


class SpendStop(RuntimeError):
    pass


class Guard:
    """Stops when the balance is low or a payment / limit error appears. Never retries around it."""

    def __init__(self, min_balance: float = MIN_BALANCE, refresh: bool = True):
        self.min_balance, self.cost, self.calls, self.lock = min_balance, 0.0, 0, threading.Lock()
        self.remaining = None
        self.stopped = ""
        if refresh:
            self.refresh()

    def refresh(self) -> None:
        self.remaining = key_info().get("limit_remaining")
        self.check()

    def check(self) -> None:
        if self.remaining is not None and self.remaining - self.cost < self.min_balance:
            self.stopped = f"remaining ${self.remaining - self.cost:.2f} < ${self.min_balance}"
        if self.stopped:
            raise SpendStop(self.stopped)

    def note(self, cost: float) -> None:
        with self.lock:
            self.cost += cost
            self.calls += 1
        self.check()

    def trip(self, reason: str) -> None:
        self.stopped = reason
        raise SpendStop(reason)


def is_limit_error(e: Exception) -> bool:
    code = getattr(e, "status_code", None)
    msg = str(e).lower()
    return code == 402 or (code in (403, 429) and any(w in msg for w in ("limit", "credit", "insufficient", "balance")))


# ---- live steps ----------------------------------------------------------------------------------
def _model() -> str:
    m = os.getenv("TI_MODEL_STAGE1", "")
    if not m:
        raise RuntimeError("TI_MODEL_STAGE1 is not set in .env")
    return m


def _call(client: LLMClient, guard: Guard, stage: str, prompt_name: str, user: str, schema, params: dict,
          max_tokens: int):
    version, system = load_prompt(prompt_name)
    p = {**PARAMS_BASE, "max_tokens": max_tokens, **params}
    try:
        out, meta = client.complete(stage=stage, prompt_version=version, model=_model(), system=system, user=user,
                                    schema=schema, params=p)
    except InvalidOutput as e:
        guard.note(cost_of(e.usage))
        raise
    except Exception as e:  # noqa: BLE001
        if is_limit_error(e):
            guard.trip(f"payment / limit error {getattr(e, 'status_code', '')}")
        raise
    if not meta["cache_hit"]:
        guard.note(cost_of(meta.get("usage")))
    return out, meta


def run_discovery(meetings: list[Meeting], run: int, client: LLMClient, guard: Guard) -> dict:
    by_label = label_map(meetings)
    sentences = {lab: [t.sentence for t in m.turns] for lab, m in by_label.items()}
    batches_ids = split_batches(list(by_label), N_BATCHES, RUN_SPLIT_SEEDS[run])
    params = {"run": run, "split_seed": RUN_SPLIT_SEEDS[run]}

    def one(batch):
        out, meta = _call(client, guard, "stage1_discovery", "stage1_discovery_v1",
                          render_batch(meetings, batch, by_label), BatchDiscovery, params, 24000)
        return out, meta

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(one, batches_ids))
    outs = [r[0] for r in results]
    val = [validate_batch(o, ids, sentences) for o, ids in zip(outs, batches_ids)]
    cons, cmeta = _call(client, guard, "stage1_consolidate", "stage1_consolidate_v1", consolidation_input(outs),
                        Consolidation, params, 16000)
    checks = check_consolidation(cons, outs)
    mat = materialize(cons, outs)
    record = {
        "run": run, "split_seed": RUN_SPLIT_SEEDS[run], "batches": batches_ids,
        "batch_outputs": [o.model_dump() for o in outs], "batch_validation": val,
        "batch_usage": [r[1].get("usage") for r in results], "consolidation": cons.model_dump(),
        "consolidation_checks": checks, "consolidated": mat, "consolidation_usage": cmeta.get("usage"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"candidate_themes_run{run}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return record


def proposal_input(r1: dict, r2: dict, stab: dict) -> str:
    def side(tag, rec):
        return {
            "themes": [{"source": f"{tag}.{t['id']}", "name": t["name"], "definition": t["definition"],
                        "distinguishing": t["distinguishing"], "owner": t["owner"], "calls": t["n_calls"]}
                       for t in rec["consolidated"]["themes"]],
            "product_areas": [{"source": f"{tag}.{p['id']}", "name": p["name"], "calls": p["n_calls"]}
                              for p in rec["consolidated"]["product_areas"]],
            "other_note": rec["consolidated"]["other_note"],
        }

    overlap = [{"run1": f"r1.{r['a_id']}", "best_match_in_run2": f"r2.{r['b_id']}", "jaccard": r["jaccard"]}
               for r in stab["run1_to_run2"]]
    overlap += [{"run2": f"r2.{r['a_id']}", "best_match_in_run1": f"r1.{r['b_id']}", "jaccard": r["jaccard"]}
                for r in stab["run2_to_run1"]]
    return json.dumps({"run1": side("r1", r1), "run2": side("r2", r2), "overlap_by_calls": overlap},
                      ensure_ascii=False, indent=1)


def run_proposal(r1: dict, r2: dict, stab: dict, client: LLMClient, guard: Guard) -> Proposal:
    out, _ = _call(client, guard, "stage1_proposal", "stage1_proposal_v1", proposal_input(r1, r2, stab), Proposal,
                   {}, 16000)
    return out


def taxonomy_text(p: Proposal) -> str:
    lines = ["THEMES:"]
    for t in p.themes:
        lines.append(f"- {t.name}: {t.definition} Boundary: {t.boundary_note}")
    lines.append("\nPRODUCT AREAS (separate field):")
    lines += [f"- {a.name}" for a in p.product_areas]
    lines.append("- Platform/General (when no single product dominates)")
    lines.append(f"\nOther / new theme: {p.other_policy}")
    return "\n".join(lines)


def run_pilot(meetings: list[Meeting], p: Proposal, client: LLMClient, guard: Guard, *,
              prompt: str = "stage1_pilot_assign_v1", stage: str = "stage1_pilot", out_name: str = "pilot_assignment.json") -> dict:
    by_label = label_map(meetings)
    sentences = {lab: [t.sentence for t in m.turns] for lab, m in by_label.items()}
    batches_ids = split_batches(list(by_label), N_BATCHES, PILOT_SPLIT_SEED)
    tax = taxonomy_text(p)
    names, products = {t.name for t in p.themes}, {a.name for a in p.product_areas}

    def one(batch):
        user = tax + "\n\n---\n\n" + render_batch(meetings, batch, by_label)
        out, meta = _call(client, guard, stage, prompt, user, PilotBatch, {"split_seed": PILOT_SPLIT_SEED}, 24000)
        return out, meta

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(one, batches_ids))
    checks, recs = [], []
    for (out, _), ids in zip(results, batches_ids):
        checks.append(check_pilot(ids, out.records, names, products, sentences))
        recs += [r.model_dump() for r in out.records]
    record = {"prompt": prompt, "split_seed": PILOT_SPLIT_SEED, "batches": batches_ids, "checks": checks,
              "assignments": recs, "usage": [r[1].get("usage") for r in results]}
    (OUT / out_name).write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return record


def revision_input(prop0: dict, pilot: dict, r1: dict, r2: dict) -> str:
    """Pilot feedback for the revision round: counts per theme (not by call type) and the Other calls' descriptions."""
    counts: dict[str, int] = {}
    for a in pilot["assignments"]:
        counts[a["primary_theme"]] = counts.get(a["primary_theme"], 0) + 1
    others = [a["other_description"] for a in pilot["assignments"] if a["primary_theme"] == OTHER]

    def cand(tag, rec):
        return [{"source": f"{tag}.{t['id']}", "name": t["name"], "definition": t["definition"], "owner": t["owner"],
                 "calls": t["n_calls"]} for t in rec["consolidated"]["themes"]]

    return json.dumps({
        "draft_themes": [{"name": t["name"], "definition": t["definition"], "owner": t["owner"],
                          "calls_in_pilot": counts.get(t["name"], 0)} for t in prop0["themes"]],
        "calls_in_other": len(others), "total_calls": len(pilot["assignments"]),
        "other_call_descriptions": others,
        "candidates_run1": cand("r1", r1), "candidates_run2": cand("r2", r2),
        "dropped_by_first_proposal": prop0["dropped_candidates"],
        "draft_product_areas": [a["name"] for a in prop0["product_areas"]],
    }, ensure_ascii=False, indent=1)


def run_revision(prop0: dict, pilot: dict, r1: dict, r2: dict, client: LLMClient, guard: Guard) -> Proposal:
    out, _ = _call(client, guard, "stage1_revise", "stage1_revise_v1", revision_input(prop0, pilot, r1, r2), Proposal,
                   {}, 16000)
    return out


# ---- driver --------------------------------------------------------------------------------------
def _stage0_types() -> dict[str, str]:
    import pandas as pd

    df = pd.read_csv(OUTPUT_DIR / "stage0_gemini.csv")
    return dict(zip(df["meeting_id"].map(call_label), df["label"]))


def main() -> None:
    """Run discovery (2 runs), stability, proposal and pilot. Resumable: every call is cached."""
    from .load import load_meetings

    meetings = load_meetings()
    client = LLMClient()
    guard = Guard(refresh=client.mode == "live")  # replay mode never touches the network
    if client.mode == "live":
        print(f"balance: ${guard.remaining} remaining; guard stops below ${MIN_BALANCE}")
    try:
        recs = {r: run_discovery(meetings, r, client, guard) for r in (1, 2)}
        stab = stability_summary(recs[1]["consolidated"]["themes"], recs[2]["consolidated"]["themes"])
        (OUT / "stability.json").write_text(json.dumps(stab, indent=2, ensure_ascii=False))
        prop = run_proposal(recs[1], recs[2], stab, client, guard)
        (OUT / "taxonomy_v0_proposal.json").write_text(json.dumps(prop.model_dump(), indent=2, ensure_ascii=False))
        pilot = run_pilot(meetings, prop, client, guard)
        types = _stage0_types()
        table = theme_by_type(pilot["assignments"], types)
        (OUT / "theme_by_type.json").write_text(json.dumps(table, indent=2, ensure_ascii=False))
        prods: dict[str, int] = {}
        for a in pilot["assignments"]:
            prods[a["product_area"]] = prods.get(a["product_area"], 0) + 1
        (OUT / "product_area_counts.json").write_text(json.dumps(prods, indent=2, ensure_ascii=False))
        # one revision round, triggered because Other exceeded the 10% the proposal itself set (see docs/stage1-discovery.md)
        rev = run_revision(json.loads((OUT / "taxonomy_v0_proposal.json").read_text()), pilot, recs[1], recs[2], client, guard)
        (OUT / "taxonomy_v0_2_proposal.json").write_text(json.dumps(rev.model_dump(), indent=2, ensure_ascii=False))
        pilot2 = run_pilot(meetings, rev, client, guard, prompt="stage1_pilot_assign_v2", stage="stage1_pilot2",
                           out_name="pilot_assignment_v2.json")
        (OUT / "theme_by_type_v2.json").write_text(json.dumps(theme_by_type(pilot2["assignments"], types), indent=2, ensure_ascii=False))
        prods2: dict[str, int] = {}
        for a in pilot2["assignments"]:
            prods2[a["product_area"]] = prods2.get(a["product_area"], 0) + 1
        (OUT / "product_area_counts_v2.json").write_text(json.dumps(prods2, indent=2, ensure_ascii=False))
    except SpendStop as e:
        print(f"STOPPED by spend guard: {e}. Partial results are cached; re-run to resume.")
    finally:
        print(f"session cost (billed, live calls): ${guard.cost:.4f} over {guard.calls} live calls")


if __name__ == "__main__":
    main()

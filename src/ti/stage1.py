"""Stage 1: theme, tags, product area, incident (D3, D3a, D8).

One LLM call per transcript against the frozen taxonomy v1 (`outputs/stage1/taxonomy_v1.json`, prompt
`prompts/stage1_v1.md`). The model sees only the transcript with speaker sides (`Meeting.view_for("stage1")`):
no title, no call type, no provided summary, topics or score. A call whose theme, tags or product area are not
from the lists is retried once (a different cache key); anything still invalid is recorded as invalid, never
silently fixed. Evidence quotes are checked by script against the turns (exact and loose).

Run:  uv run python -m ti.stage1 [--run 1] [--sample] [--limit N]
"""

from __future__ import annotations

import argparse
import json

from . import OUTPUT_DIR
from .common import (BASE_PARAMS, Guard, cost_of, is_limit_error, model_for, quote_exact, quote_loose,
                     run_parallel, stability_sample, stage0_types, transcript_lines, word_count, write_json)
from .llm import InvalidOutput, LLMClient, load_prompt
from .load import Meeting, load_meetings
from .schemas import Stage1Out

STAGE = "stage1"
PROMPT_NAME = "stage1_v1"
MAX_TOKENS = 4000
OTHER = "Other / new theme"
OUT = OUTPUT_DIR / "stage1"
INCIDENT_ID = "2026-03-detect-outage"


def load_taxonomy() -> dict:
    return json.loads((OUT / "taxonomy_v1.json").read_text())


def build_user_message(meeting: Meeting) -> str:
    lines = transcript_lines(meeting, "stage1")
    return f"transcript ({len(lines)} turns):\n" + "\n".join(lines)


def check(out: Stage1Out, sentences: list[str], theme_names: set[str], areas: set[str]) -> dict:
    """Validity flags the schema cannot express (list membership, tag rules, quote)."""
    primary_ok = out.primary_theme in theme_names or out.primary_theme == OTHER
    tags_ok = (len(out.tags) <= 2 and len(set(out.tags)) == len(out.tags) and all(t in theme_names for t in out.tags)
               and out.primary_theme not in out.tags)
    return {
        "primary_in_list": primary_ok,
        "tags_ok": tags_ok,
        "product_ok": out.product_area in areas,
        "incident_ok": out.incident in (None, INCIDENT_ID),
        "membership_ok": primary_ok and tags_ok and out.product_area in areas and out.incident in (None, INCIDENT_ID),
        "quote_exact": quote_exact(out.evidence_quote, sentences),
        "quote_loose": quote_loose(out.evidence_quote, sentences),
        "quote_words_ok": 0 < word_count(out.evidence_quote) <= 30,
    }


def classify(meeting: Meeting, client: LLMClient, guard: Guard, run: int = 1, model: str | None = None) -> dict:
    version, system = load_prompt(PROMPT_NAME)
    model = model or model_for("TI_MODEL_STAGE1")
    tax = load_taxonomy()
    theme_names = {t["name"] for t in tax["themes"]}
    areas = {a["name"] for a in tax["product_areas"]}
    sentences = [t.sentence for t in meeting.turns]
    user = build_user_message(meeting)
    rec: dict = {"meeting_id": meeting.meeting_id, "run": run, "prompt_version": version}
    cost = 0.0
    for attempt in (0, 1):
        params = {**BASE_PARAMS, "max_tokens": MAX_TOKENS, "run": run}
        if attempt:
            params["retry"] = 1
        try:
            out, meta = client.complete(stage=STAGE, prompt_version=version, model=model, system=system, user=user,
                                        schema=Stage1Out, params=params)
        except InvalidOutput as e:
            guard.note(cost_of(e.usage))
            rec.update(status="invalid_output", error=str(e)[:300])
            return rec
        except Exception as e:  # noqa: BLE001
            if is_limit_error(e):
                guard.trip(f"payment / limit error {getattr(e, 'status_code', '')}")
            raise
        c = 0.0 if meta["cache_hit"] else cost_of(meta.get("usage"))
        if c:
            guard.note(c)
        cost += c
        flags = check(out, sentences, theme_names, areas)
        rec.update(out.model_dump(), **flags, tags="|".join(out.tags), attempts=attempt + 1,
                   cache_hit=meta["cache_hit"], cost=round(cost, 6), model_returned=meta.get("model_returned"),
                   provider_returned=meta.get("provider_returned"), structured_mode=meta.get("structured_mode"),
                   status="ok" if flags["membership_ok"] else "invalid_membership")
        if flags["membership_ok"]:
            break
    return rec


def run(meetings: list[Meeting], client: LLMClient, guard: Guard, run: int = 1, workers: int = 4) -> list[dict]:
    from tqdm import tqdm  # noqa: F401  (progress is printed by the CLI)

    return run_parallel(lambda m: classify(m, client, guard, run=run), meetings, guard, workers=workers)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--sample", action="store_true", help="run only the seeded 20-call stability sample")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    meetings = load_meetings()
    types = stage0_types()
    if a.sample:
        ids = set(stability_sample(types))
        write_json(OUT / "stability_sample.json", {"seed": 11, "ids": sorted(ids), "strata": "6 support, 8 external, 6 internal (Stage 0 labels)"})
        meetings = [m for m in meetings if m.meeting_id in ids]
    if a.limit:
        meetings = meetings[: a.limit]
    guard = Guard()
    print(f"balance ${guard.remaining:.2f}; running {len(meetings)} calls (run {a.run})")
    recs = run(meetings, LLMClient(), guard, run=a.run)
    name = f"stage1_records_run{a.run}{'_sample' if a.sample else ''}.json"
    write_json(OUT / name, recs)
    print(f"done {len(recs)}/{len(meetings)}; session cost ${guard.cost:.4f}; stopped={guard.stopped or 'no'}")


if __name__ == "__main__":
    main()

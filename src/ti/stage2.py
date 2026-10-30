"""Stage 2: sentiment (D2, D2a, D8).

One LLM call per transcript with the frozen anchors in `prompts/stage2_v1.md`. The model sees only the transcript
with speaker sides (`Meeting.view_for("stage2")`): no title, no call type, no provided summary, topics or score.
Returns a whole-call score (1 to 5, half steps) for every call, a customer-side score for calls that have a
customer, one label per turn, a start-versus-end trajectory (half steps), an evidence quote and a confidence.

Run-time validation (D8): per_turn must hold exactly one entry per turn, in order; customer_score is null if and only
if no turn has side "customer"; trajectory values are half steps (schema). A call that fails validation is retried
once (a different cache key plus a note with the turn count); a second failure is recorded as `failed`, never fixed.

Run:  uv run python -m ti.stage2 [--run 1] [--sample] [--limit N]
"""

from __future__ import annotations

import argparse

from . import OUTPUT_DIR
from .common import (BASE_PARAMS, Guard, cost_of, is_limit_error, model_for, quote_exact, quote_loose,
                     run_parallel, stability_sample, stage0_types, transcript_lines, word_count, write_json)
from .llm import InvalidOutput, LLMClient, load_prompt
from .load import Meeting, load_meetings
from .schemas import Stage2Out

STAGE = "stage2"
PROMPT_NAME = "stage2_v1"
MAX_TOKENS = 10000
OUT = OUTPUT_DIR / "stage2"


def build_user_message(meeting: Meeting, retry: bool = False) -> str:
    lines = transcript_lines(meeting, "stage2")
    n = len(lines)
    head = f"transcript ({n} turns, indices 0 to {n - 1}; per_turn needs exactly {n} entries, one per index in order):\n"
    msg = head + "\n".join(lines)
    if retry:
        msg += (f"\n\nNote: an earlier answer did not satisfy the format. Return exactly {n} per_turn entries with "
                f"indices 0 to {n - 1} in order, and customer_score null only if no turn has side \"customer\".")
    return msg


def validate(out: Stage2Out, n_turns: int, has_customer_turn: bool, sentences: list[str]) -> dict:
    """Checks the schema cannot express."""
    idx = [t.index for t in out.per_turn]
    return {
        "per_turn_ok": idx == list(range(n_turns)),
        "customer_null_ok": (out.customer_score is None) == (not has_customer_turn),
        "quote_exact": quote_exact(out.evidence_quote, sentences),
        "quote_loose": quote_loose(out.evidence_quote, sentences),
        "quote_words_ok": 0 < word_count(out.evidence_quote) <= 25,
    }


def classify(meeting: Meeting, client: LLMClient, guard: Guard, run: int = 1, model: str | None = None) -> dict:
    version, system = load_prompt(PROMPT_NAME)
    model = model or model_for("TI_MODEL_STAGE2")
    view = meeting.view_for("stage2")["turns"]
    n = len(view)
    has_customer_turn = any(t["side"] == "customer" for t in view)
    sentences = [t["sentence"] for t in view]
    rec: dict = {"meeting_id": meeting.meeting_id, "run": run, "prompt_version": version, "n_turns": n}
    cost = 0.0
    last = None
    for attempt in (0, 1):
        params = {**BASE_PARAMS, "max_tokens": MAX_TOKENS, "run": run}
        if attempt:
            params["retry"] = 1
        try:
            out, meta = client.complete(stage=STAGE, prompt_version=version, model=model, system=system,
                                        user=build_user_message(meeting, retry=bool(attempt)), schema=Stage2Out,
                                        params=params)
        except InvalidOutput as e:
            guard.note(cost_of(e.usage))
            cost += cost_of(e.usage)
            last = {"status": "invalid_output", "error": str(e)[:300]}
            continue
        except Exception as e:  # noqa: BLE001
            if is_limit_error(e):
                guard.trip(f"payment / limit error {getattr(e, 'status_code', '')}")
            raise
        c = 0.0 if meta["cache_hit"] else cost_of(meta.get("usage"))
        if c:
            guard.note(c)
        cost += c
        flags = validate(out, n, has_customer_turn, sentences)
        ok = flags["per_turn_ok"] and flags["customer_null_ok"]
        last = dict(out.model_dump(exclude={"per_turn", "trajectory"}),
                    traj_start=out.trajectory.start, traj_end=out.trajectory.end,
                    per_turn=[t.model_dump() for t in out.per_turn],
                    n_neg=sum(t.label == "negative" for t in out.per_turn),
                    n_neu=sum(t.label == "neutral" for t in out.per_turn),
                    n_pos=sum(t.label == "positive" for t in out.per_turn),
                    **flags, attempts=attempt + 1, cache_hit=meta["cache_hit"],
                    model_returned=meta.get("model_returned"), provider_returned=meta.get("provider_returned"),
                    structured_mode=meta.get("structured_mode"), finish_reason=meta.get("finish_reason"),
                    status="ok" if ok else "failed_validation")
        if ok:
            break
    rec.update(last or {"status": "invalid_output"})
    rec["cost"] = round(cost, 6)
    rec["has_customer_turn"] = has_customer_turn
    return rec


def run(meetings: list[Meeting], client: LLMClient, guard: Guard, run: int = 1, workers: int = 4) -> list[dict]:
    return run_parallel(lambda m: classify(m, client, guard, run=run), meetings, guard, workers=workers)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--sample", action="store_true", help="run only the seeded 20-call stability sample")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    meetings = load_meetings()
    if a.sample:
        ids = set(stability_sample(stage0_types()))
        meetings = [m for m in meetings if m.meeting_id in ids]
    if a.limit:
        meetings = meetings[: a.limit]
    guard = Guard()
    print(f"balance ${guard.remaining:.2f}; running {len(meetings)} calls (run {a.run})")
    recs = run(meetings, LLMClient(), guard, run=a.run)
    name = f"stage2_records_run{a.run}{'_sample' if a.sample else ''}.json"
    write_json(OUT / name, recs)
    print(f"done {len(recs)}/{len(meetings)}; session cost ${guard.cost:.4f}; stopped={guard.stopped or 'no'}")


if __name__ == "__main__":
    main()

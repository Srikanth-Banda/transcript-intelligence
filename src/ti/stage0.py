"""Stage 0: call type (D1).

1. No outside attendee -> internal, by metadata. No model involved.
2. Calls with a customer: an LLM chooses support or external from attendee counts and the first
   8 turns (the title is withheld, D1 revision note 2), returning label, evidence quote, confidence and speaker sides.
3. The title rule runs as an independent cross-check (the model never sees the title). Disagreements, low confidence and a seeded sample of 10 agreements
   go to a review queue for the candidate.
"""

from __future__ import annotations

import json
import os
import random

import pandas as pd

from . import OUTPUT_DIR
from .llm import LLMClient, load_prompt
from .load import Meeting
from .schemas import Stage0LLMOut

STAGE = "stage0"
PROMPT_NAME = "stage0_v1"
AGREEMENT_SAMPLE = 10
SAMPLE_SEED = 7


def build_user_message(meeting: Meeting) -> str:
    v = meeting.view_for("stage0")
    opening = "\n".join(f"{t['speaker']}: {t['sentence']}" for t in v["opening"])
    return (
        f"attendees: {v['n_attendees']} total, {v['n_aegis_attendees']} from Aegis, "
        f"{v['n_outside_attendees']} from outside Aegis\n\n"
        f"opening:\n{opening}"
    )


def classify(meeting: Meeting, client: LLMClient, model: str | None = None) -> dict:
    """One meeting -> one record (a dict that becomes a row of outputs/stage0.csv)."""
    base = {
        "meeting_id": meeting.meeting_id,
        "title": meeting.title,
        "title_rule_label": meeting.title_rule_label,
        "prompt_version": PROMPT_NAME,
    }
    if meeting.is_internal_by_metadata:
        return {**base, "label": "internal", "source": "metadata", "confidence": "certain", "evidence_quote": "",
                "sides_agree": True, "model": "", "cache_hit": ""}

    version, system = load_prompt(PROMPT_NAME)
    model = model or os.getenv("TI_MODEL_STAGE0", "")
    user = build_user_message(meeting)
    out, meta = client.complete(stage=STAGE, prompt_version=version, model=model, system=system, user=user,
                                schema=Stage0LLMOut)
    det = meeting.speaker_sides()
    llm_sides = {s.speaker: s.side for s in out.speaker_sides}
    sides_agree = all(det.get(name) == side for name, side in llm_sides.items() if name in det)
    return {**base, "label": out.label, "source": "llm", "confidence": out.confidence,
            "evidence_quote": out.evidence_quote, "sides_agree": sides_agree,
            "model": meta.get("model_returned") or model, "cache_hit": meta["cache_hit"]}


def run(meetings: list[Meeting], client: LLMClient, model: str | None = None, out_dir=OUTPUT_DIR) -> pd.DataFrame:
    from tqdm import tqdm

    rows = [classify(m, client, model) for m in tqdm(meetings, desc="stage0")]
    df = pd.DataFrame(rows)
    df["disagree"] = df["label"] != df["title_rule_label"]
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "stage0.csv", index=False)
    review_queue(df).to_csv(out_dir / "stage0_review_queue.csv", index=False)
    return df


def review_queue(df: pd.DataFrame) -> pd.DataFrame:
    """Disagreements with the title rule, low confidence, speaker-side mismatches, plus a seeded sample of agreements."""
    reasons = []
    for _, r in df.iterrows():
        why = []
        if r["disagree"]:
            why.append(f"LLM says {r['label']}, title rule says {r['title_rule_label']}")
        if r["confidence"] == "low":
            why.append("low confidence")
        if not r["sides_agree"]:
            why.append("speaker sides differ from deterministic")
        reasons.append("; ".join(why))
    q = df.assign(reason=reasons)
    flagged = q[q["reason"] != ""]
    agreed = q[(q["reason"] == "") & (q["source"] == "llm")]
    k = min(AGREEMENT_SAMPLE, len(agreed))
    idx = random.Random(SAMPLE_SEED).sample(list(agreed.index), k) if k else []
    sample = q.loc[idx].assign(reason="agreement sample")
    cols = ["meeting_id", "title", "label", "title_rule_label", "confidence", "evidence_quote", "reason"]
    return pd.concat([flagged, sample])[cols].reset_index(drop=True)


def summarize(df: pd.DataFrame) -> str:
    return json.dumps(
        {"counts": df["label"].value_counts().to_dict(), "disagreements": int(df["disagree"].sum())}, indent=2
    )

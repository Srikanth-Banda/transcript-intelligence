"""Load the 100 meetings and control what each pipeline stage is allowed to see.

Design rule (DECISIONS.md D2, D3a, B2 criterion 4): fields produced by the upstream AI system
(summary, topics, sentiment score, per-sentence sentiment labels, key moments, action items) live in a
separate `Provided` object. Stages never receive it; `Meeting.view_for(stage)` is the only door.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from . import DATASET

INTERNAL_DOMAIN = "aegiscloud.com"
Side = Literal["customer", "aegis_staff"]
CallType = Literal["support", "external", "internal"]


class Turn(BaseModel):
    index: int
    speaker: str
    sentence: str
    start: float
    end: float


class Provided(BaseModel):
    """Upstream AI output shipped with the dataset. Comparison baseline only, never a stage input."""

    summary: str
    topics: list[str]
    overall_sentiment: str
    sentiment_score: float
    action_items: list[str]
    key_moments: list[dict]
    turn_sentiments: list[str]  # provided per-sentence labels, aligned with Meeting.turns


class Meeting(BaseModel):
    meeting_id: str
    title: str
    start_time: str
    duration_min: float
    emails: list[str]
    turns: list[Turn]
    provided: Provided = Field(repr=False)

    # ---- metadata facts (deterministic) -------------------------------------------------
    @property
    def external_emails(self) -> list[str]:
        return [e for e in self.emails if not e.lower().endswith("@" + INTERNAL_DOMAIN)]

    @property
    def internal_emails(self) -> list[str]:
        return [e for e in self.emails if e.lower().endswith("@" + INTERNAL_DOMAIN)]

    @property
    def has_external(self) -> bool:
        return bool(self.external_emails)

    @property
    def is_internal_by_metadata(self) -> bool:
        """D1 step 1: no attendee outside aegiscloud.com means internal. No model involved."""
        return not self.has_external

    @property
    def title_rule_label(self) -> CallType:
        """D1 step 3 baseline (cross-check only, not the pipeline's answer)."""
        if self.title.startswith("Support Case"):
            return "support"
        return "external" if self.has_external else "internal"

    # ---- speaker side (deterministic version; A8a) ---------------------------------------
    @staticmethod
    def _norm(name: str) -> str:
        return re.sub(r"[^a-z ]", "", name.lower()).strip()

    @property
    def staff_names(self) -> set[str]:
        return {self._norm(e.split("@")[0].replace(".", " ")) for e in self.internal_emails}

    def speaker_side(self, name: str) -> Side:
        """Customer if the meeting has an outside attendee and the speaker is not an Aegis invitee."""
        if self.has_external and self._norm(name) not in self.staff_names:
            return "customer"
        return "aegis_staff"

    def speaker_sides(self) -> dict[str, Side]:
        return {n: self.speaker_side(n) for n in dict.fromkeys(t.speaker for t in self.turns)}

    # ---- helpers -------------------------------------------------------------------------
    def transcript_hash(self) -> str:
        payload = json.dumps([[t.speaker, t.sentence] for t in self.turns], ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    def opening(self, n: int = 8) -> list[Turn]:
        return self.turns[:n]

    def view_for(self, stage: str) -> dict:
        """The only fields a stage may see. Anything not listed here cannot reach a prompt.

        stage0: attendee counts, first 8 turns (speaker names + sentences). No title (D1 revision note 2: keeps the
        title-rule cross-check independent), no sides, no provided data. The title stays on Meeting for the
        deterministic title rule only.
        stage1: full transcript with speaker sides. No title, no call type, no provided data.
        stage2: full transcript with speaker sides. No title, no call type, no provided data.
        Note: sides reveal whether a customer is present; that is inherent to scoring the customer side.
        """
        if stage == "stage0":
            return {
                "n_attendees": len(self.emails),
                "n_aegis_attendees": len(self.internal_emails),
                "n_outside_attendees": len(self.external_emails),
                "opening": [{"speaker": t.speaker, "sentence": t.sentence} for t in self.opening(8)],
            }
        if stage in ("stage1", "stage2"):
            sides = self.speaker_sides()
            return {
                "turns": [
                    {"index": t.index, "speaker": t.speaker, "side": sides[t.speaker], "sentence": t.sentence}
                    for t in self.turns
                ]
            }
        raise ValueError(f"unknown stage {stage!r}")


def _load_one(folder: Path) -> Meeting:
    info = json.loads((folder / "meeting-info.json").read_text())
    summ = json.loads((folder / "summary.json").read_text())
    data = json.loads((folder / "transcript.json").read_text())["data"]
    turns = [
        Turn(index=x["index"], speaker=x["speaker_name"], sentence=x["sentence"], start=x["time"], end=x["endTime"])
        for x in data
    ]
    provided = Provided(
        summary=summ["summary"],
        topics=summ["topics"],
        overall_sentiment=summ["overallSentiment"],
        sentiment_score=summ["sentimentScore"],
        action_items=summ["actionItems"],
        key_moments=summ["keyMoments"],
        turn_sentiments=[x["sentimentType"] for x in data],
    )
    return Meeting(
        meeting_id=info["meetingId"],
        title=info["title"],
        start_time=info["startTime"],
        duration_min=info["duration"],
        emails=info["allEmails"],
        turns=turns,
        provided=provided,
    )


def load_meetings(root: Path = DATASET) -> list[Meeting]:
    """All meetings, sorted by start time then id (stable order)."""
    folders = [p for p in root.iterdir() if p.is_dir()]
    ms = [_load_one(p) for p in folders]
    return sorted(ms, key=lambda m: (m.start_time, m.meeting_id))

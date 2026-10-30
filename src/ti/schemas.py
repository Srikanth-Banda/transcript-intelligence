"""Output schemas for each LLM stage (shapes fixed by D1, D2a, D3a).

Lists of small objects are used instead of dicts so the JSON schema is strict-mode friendly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Confidence = Literal["low", "medium", "high"]
Side = Literal["customer", "aegis_staff"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- Stage 0 (D1) -----------------------------------------------------------------------
class SpeakerSide(_Strict):
    speaker: str
    side: Side


class Stage0Out(_Strict):
    label: Literal["support", "external", "internal"]
    evidence_quote: str = Field(description="Verbatim quote from the opening that supports the label")
    confidence: Confidence
    speaker_sides: list[SpeakerSide] = Field(description="Side for each speaker seen in the opening")


class Stage0LLMOut(Stage0Out):
    """What the model may return: internal is decided by metadata, never by the model."""

    label: Literal["support", "external"]  # type: ignore[assignment]


# ---- Stage 1 (D3, D3a) ------------------------------------------------------------------
class Stage1Out(_Strict):
    primary_theme: str
    tags: list[str] = Field(max_length=2)
    product_area: str
    evidence_quote: str
    confidence: Confidence
    taxonomy_version: str
    # Added with taxonomy v1 (D8). Defaults keep older cached bake-off outputs valid.
    incident: str | None = Field(default=None, description="Incident id (e.g. 2026-03-detect-outage) or null")
    other_description: str = Field(default="", description="One sentence when primary_theme is Other / new theme")


# ---- Stage 2 (D2, D2a) ------------------------------------------------------------------
HALF_STEPS = {1.0 + 0.5 * i for i in range(9)}  # 1, 1.5, ..., 5


class TurnLabel(_Strict):
    index: int
    label: Literal["negative", "neutral", "positive"]


class Trajectory(_Strict):
    start: float = Field(ge=1, le=5, description="Score of the first third of the call (half steps)")
    end: float = Field(ge=1, le=5, description="Score of the last third of the call (half steps)")

    @field_validator("start", "end")
    @classmethod
    def _half_step(cls, v: float) -> float:
        # D8: tightened from 1..5 continuous; the prompt asks for half steps.
        if v not in HALF_STEPS:
            raise ValueError("trajectory values must be 1 to 5 in half steps")
        return v


class Stage2Out(_Strict):
    call_score: float = Field(description="Whole-call score 1 to 5 in half steps, per the written anchors")
    customer_score: float | None = Field(default=None, description="Customer-side score; null when no customer")
    per_turn: list[TurnLabel]
    trajectory: Trajectory
    evidence_quote: str
    confidence: Confidence

    @field_validator("call_score", "customer_score")
    @classmethod
    def _half_step(cls, v: float | None) -> float | None:
        if v is not None and v not in HALF_STEPS:
            raise ValueError("score must be 1 to 5 in half steps")
        return v

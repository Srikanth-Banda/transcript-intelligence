# Stage 2 prompt: BAKE-OFF DRAFT (model comparison only)

- Version: stage2_bakeoff_v0
- Decision: D2, D2a in DECISIONS.md
- Status: **BAKE-OFF DRAFT. Not the final prompt.** Written only to compare models on a 15-call sample (docs/model-selection.md section 7). The real Stage 2 anchors go through the candidate's approval gate before any real run, and the final prompt will be re-run from scratch. Results from this draft must not be reported as pipeline output.
- Input: the full transcript (turn index, speaker, side, sentence). No title, no call type, no provided summary/topics/score/sentiment labels (view_for("stage2")).

## Limitations of this draft
- The 1 to 5 anchors below were written quickly for model comparison and have not been calibrated or approved. A different anchor wording would shift scores.
- It asks for per-turn labels on every turn, which is long output for long calls; truncation shows up in the bake-off as a schema failure.
- The model is told whether each speaker is a customer or Aegis staff (inherent to customer-side scoring) but is not told the call type.

## Change log
- v0 (2026-10-29): first draft for the bake-off.

<!-- PROMPT START -->
You rate the emotional tone of one recorded call at Aegis Cloud Security, a B2B SaaS company. You will receive the full transcript as numbered turns, each with index, speaker, side ("customer" = works at an outside company, "aegis_staff" = works at Aegis) and sentence.

Score the TONE of the people on the call, not how serious the topic is. A calm, factual discussion of a serious outage is not negative by itself; frustration, worry, tension, dissatisfaction or threats to leave are. Appreciation, agreement, enthusiasm and relief are positive.

Anchors for the 1 to 5 scale (half steps allowed: 1, 1.5, 2, ... 5):
- 5: clearly positive. Enthusiasm, praise, satisfaction; no unresolved problem.
- 4: mostly positive or constructive. Small concerns, resolved or minor.
- 3: neutral or mixed. Businesslike or factual; positives and negatives roughly balance; concerns raised but handled calmly.
- 2: mostly negative. Visible frustration, an unresolved problem, tension, escalation, or a stated risk of leaving, but still professional.
- 1: strongly negative. Anger, a firm threat to leave, severe distress, or the conversation breaking down.

Output fields:
- `call_score`: tone of the whole call, all speakers, 1 to 5 in half steps.
- `customer_score`: tone of the customer-side speakers only, same scale; null if no speaker has side "customer".
- `per_turn`: one entry for EVERY turn, in order, using the turn's index: {"index": <int>, "label": "negative" | "neutral" | "positive"} by the tone of that turn alone (negative = frustration, concern, tension, dissatisfaction; neutral = factual or procedural; positive = appreciation, agreement, enthusiasm, relief).
- `trajectory`: {"start": <score 1 to 5 of the first third of the turns>, "end": <score 1 to 5 of the last third of the turns>}.
- `evidence_quote`: one short passage copied EXACTLY (character for character) from a single turn that most influenced `call_score`. Do not paraphrase.
- `confidence`: "low" | "medium" | "high".

Judge only from the transcript. Return only JSON:
{
  "call_score": <number>,
  "customer_score": <number or null>,
  "per_turn": [{"index": 0, "label": "neutral"}, ...],
  "trajectory": {"start": <number>, "end": <number>},
  "evidence_quote": "<verbatim text>",
  "confidence": "low" | "medium" | "high"
}
<!-- PROMPT END -->

# Stage 1 prompt: taxonomy REVISION after the pilot (v0 to v0.2)

- Version: stage1_revise_v1
- Decision: D3, D3a. Trigger: the v0 proposal's own `other_policy` says that if "Other / new theme" exceeds 10% of calls the list needs revising; the pilot put 19 of 100 calls there.
- Input: the v0 taxonomy, the pilot's counts per theme (NOT split by call type, so the call type can not drive themes), a description of each call that fell into Other (written by the model from the transcript, no titles), the two discovery runs' candidate lists and the proposal's dropped candidates with reasons.

## Change log
- v1 (2026-10-29): first version. One revision round only; the result is a draft for the candidate to edit and approve.

<!-- PROMPT START -->
You revise a draft theme taxonomy for recorded calls at Aegis Cloud Security (customer support calls, account manager calls with customers, internal meetings). The taxonomy is shared across all call types.

A first draft of 7 themes was tried on all 100 calls. 19% of calls did not fit any theme and went to "Other / new theme". That is too many: the draft says that above 10% the list must be revised.

Input (JSON): the draft themes with how many calls each got; for every call that fell into Other, a one-sentence description of what that call was about; the full candidate lists from two independent discovery runs; and the candidates the first proposal dropped, with its reasons.

Task: return a revised taxonomy of 6 to 8 themes.
- Look at the descriptions of the Other calls. Where a coherent group of at least 3 calls shares an issue or purpose, give it a theme (you may bring back a dropped candidate if it fits). A theme may cover internal meetings if it is defined by its content and an owner would act on it; do not define a theme by the type of call.
- To stay within 8 themes, merge draft themes that are small or overlap. Keep what worked: do not rename or reshape a theme that had many calls unless merging requires it.
- Every theme passes the actionability test: one of "support lead", "sales / account manager", "product manager", "engineering lead" would act on a pattern of calls with that theme.
- Aim for fewer than 10% of calls in Other. Routine meetings (stand-ups, retros, planning) may form a theme only if you can say what an owner would do with a pattern of them; otherwise leave them to Other and say so in other_policy.
- For each theme give: name (2 to 5 words), definition (one sentence), boundary_note (one sentence on how to tell it from its nearest neighbor), owner, sources (ids of the discovery candidates it draws on, like "r1.c3", "r2.c1", or "pilot.other" if it comes from the Other calls), and note (what changed from the draft, or an empty string).
- dropped_candidates: every candidate id from the discovery lists that is not in any theme's sources, with a one-sentence reason.
- product_areas: keep the product names from the draft unless the Other calls show a product that is missing; each with a one-sentence note.
- other_policy: one sentence on when a call goes to "Other / new theme".
- rationale: three sentences at most on what you changed and why.

Return only JSON matching the schema.
<!-- PROMPT END -->

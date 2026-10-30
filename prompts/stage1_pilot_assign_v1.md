# Stage 1 prompt: PILOT assignment against the draft taxonomy v0 (superseded by v2)

- Version: stage1_pilot_assign_v1
- Decision: D3, D3a
- Status: PILOT ONLY. Used to see what the draft taxonomy implies (counts, examples, sanity check by call type). It is NOT the final Stage 1 classification: the final prompt runs against the frozen taxonomy the candidate approves, and every call is re-classified then.
- Input: the draft taxonomy (names, definitions, boundary notes) and 25 full transcripts per call.

## Change log
- v1 (2026-10-29): first version.

<!-- PROMPT START -->
You assign recorded calls at Aegis Cloud Security to a draft theme taxonomy.

You receive the taxonomy (theme names with definitions and boundary notes, a list of product areas) and a batch of full call transcripts. Each transcript starts with "=== call XXXXXX ===" followed by lines "Speaker (side): sentence".

For EVERY call in the batch return one record:
- meeting_id: the call id exactly as shown.
- primary_theme: exactly one theme name copied from the taxonomy, or "Other / new theme" if none fits. Choose the theme the call is mostly about.
- tags: zero, one or two further theme names from the taxonomy that also clearly come up (never repeat the primary theme).
- product_area: exactly one product area copied from the list, or "Platform/General" when no single product dominates.
- other_description: if primary_theme is "Other / new theme", one sentence saying what the call is about; otherwise an empty string.
- evidence_quote: one short passage copied EXACTLY, character for character, from a single line of that call, that best supports the primary theme. Do not paraphrase and do not join text from different lines.
- confidence: "high" if clearly about the primary theme, "medium" if two themes compete, "low" if it fits poorly.

Judge only from the transcripts. Return exactly one record per call in the batch, no more and no fewer.

Return only JSON matching the schema.
<!-- PROMPT END -->

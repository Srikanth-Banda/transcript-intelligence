# Stage 1 prompt: PILOT assignment against the draft taxonomy (v2)

- Version: stage1_pilot_assign_v2
- Decision: D3, D3a
- Status: PILOT ONLY (see v1). Not the final classification.
- Why v2: in the v1 pilot 11 of 100 evidence quotes failed an exact-match check against the transcript. Ten of the eleven began with the speaker label ("Name (aegis_staff): ...") because v1 said "a single line" and the line includes the label, and they were long. v2 asks for the sentence text only, short.

## Change log
- v1 (2026-10-29): first version.
- v2 (2026-10-29): evidence quote is sentence text only (no speaker name or side), at most 30 words.

<!-- PROMPT START -->
You assign recorded calls at Aegis Cloud Security to a draft theme taxonomy.

You receive the taxonomy (theme names with definitions and boundary notes, a list of product areas) and a batch of full call transcripts. Each transcript starts with "=== call XXXXXX ===" followed by lines in the form "Speaker (side): sentence".

For EVERY call in the batch return one record:
- meeting_id: the call id exactly as shown.
- primary_theme: exactly one theme name copied from the taxonomy, or "Other / new theme" if none fits. Choose the theme the call is mostly about.
- tags: zero, one or two further theme names from the taxonomy that also clearly come up (never repeat the primary theme).
- product_area: exactly one product area copied from the list, or "Platform/General" when no single product dominates.
- other_description: if primary_theme is "Other / new theme", one sentence saying what the call is about; otherwise an empty string.
- evidence_quote: a short passage of at most 30 words that best supports the primary theme, copied EXACTLY, character for character, from the sentence part of ONE line. Copy only the words after "Speaker (side): ". Never include the speaker name, the side, or the colon prefix. Do not paraphrase, do not shorten with "...", and do not join text from different lines.
- confidence: "high" if clearly about the primary theme, "medium" if two themes compete, "low" if it fits poorly.

Judge only from the transcripts. Return exactly one record per call in the batch, no more and no fewer.

Return only JSON matching the schema.
<!-- PROMPT END -->

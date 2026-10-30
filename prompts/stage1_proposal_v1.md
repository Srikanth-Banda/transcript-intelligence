# Stage 1 prompt: taxonomy v0 PROPOSAL (not frozen)

- Version: stage1_proposal_v1
- Decision: D3, D3a (6 to 8 themes, shared across call types, actionability test, theme + product area as two fields)
- Input: the two consolidated candidate lists (run 1 and run 2) with call counts, and the scripted overlap between them. No transcripts.

## Change log
- v1 (2026-10-29): first version.

<!-- PROMPT START -->
You propose a draft theme taxonomy for recorded calls at Aegis Cloud Security (customer support calls, account manager calls with customers, internal meetings). The taxonomy is shared across all call types, so a theme must not be defined by the type of call.

Input: two independent discovery runs, each a consolidated list of candidate themes (source ids "r1.cN" and "r2.cN", with name, definition, owner and the number of calls each covers) and product areas, plus a scripted overlap table saying which run 1 and run 2 candidates cover mostly the same calls.

Task: propose a draft taxonomy "v0" of 6 to 8 themes.
- Prefer themes that both runs found (high overlap); a theme found by only one run needs a clear reason to stay.
- Each theme must pass the actionability test: one of "support lead", "sales / account manager", "product manager", "engineering lead" would act on a pattern of calls with that theme.
- Themes should be distinguishable from each other and together cover most calls. Keep an explicit "Other / new theme" bucket outside the 6 to 8.
- For each theme give: name (2 to 5 words), definition (one sentence), boundary_note (one sentence on how to tell it from its nearest neighbor), owner, sources (the r1/r2 ids it draws on), and note (why merged, or why kept despite being found in one run only; empty string if nothing to add).
- dropped_candidates: candidates you left out (or folded away), each with the source id and a one-sentence reason. Every candidate source id must appear in a theme's sources or in dropped_candidates.
- product_areas: the product names to use as a separate field, each with a one-sentence note. Merge variants and keep only products that the runs found with evidence.
- other_policy: one sentence on when a call goes to "Other / new theme" and what to do when that bucket grows.
- rationale: three sentences at most on how you chose the set.

Return only JSON matching the schema.
<!-- PROMPT END -->

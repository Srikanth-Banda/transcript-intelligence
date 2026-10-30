# Stage 1 taxonomy discovery: method, results, limits

Status: draft proposal for the candidate's approval. Nothing here is frozen. Decisions: D3, D3a, D7 (`DECISIONS.md`). Code: `src/ti/stage1_discovery.py`. Prompts: `prompts/stage1_discovery_v1.md`, `stage1_consolidate_v1.md`, `stage1_proposal_v1.md`, `stage1_revise_v1.md`, `stage1_pilot_assign_v1.md` and `_v2.md`. Outputs: `outputs/stage1/`. Raw model responses: `cache/stage1_*`.

## What this step is
D3 says taxonomy discovery is a one-time, offline step, followed by a frozen, versioned taxonomy and a recurring classification stage. This document covers only the discovery. The recurring classification (Stage 1 proper) runs later against the taxonomy the candidate approves in the Taxonomy Approval artifact.

## Method (as run)
Model for every call: `google/gemini-3.8-flash` through OpenRouter, provider pinned to `google-ai-studio`, temperature 0, seed 7, reasoning effort low (D7). All 20 live calls came back from Google AI Studio in `json_schema` mode with no retry.

1. **Input isolation.** Each model sees only `Meeting.view_for("stage1")`: the transcript with speaker names and sides. No title, no call type, no provided summary, topics or score. Calls are labelled with the last six characters of the meeting id (unique across the 100). Product names are not mentioned in any discovery prompt, so the product-area list is found, not led.
2. **Batches, two independent runs.** 100 calls are split into 4 batches of 25 by a seeded shuffle (seed 11 for run 1, seed 23 for run 2). One discovery call per batch returns candidate themes (name, definition, how it differs from the nearest theme, the stakeholder who would act on it, what they would do, the calls it covers, up to 3 verbatim quotes) and a separate product-area list. A consolidation call merges the 4 batch outputs into at most 12 candidate themes. Code, not the model, takes the union of call ids and evidence, and checks that every source theme is merged or dropped exactly once (all checks passed in both runs).
3. **Why batches of 25 and not one pass of all 100 (about 190k tokens).** My judgment, not a tested result: shorter contexts make exact quoting more reliable, the quote check is then simple, and using a different split in run 2 tests sensitivity to batch composition as well as run-to-run noise. I did not run a single-pass variant, so I cannot say it would be worse.
4. **Stability.** Scripted: for each theme in one run, the best-matching theme in the other run by Jaccard overlap of the sets of calls each covers (no model judge).
5. **Proposal v0.** One call turns the two consolidated lists plus the overlap table into a draft of 6 to 8 themes.
6. **Pilot.** All 100 calls are assigned to the draft (4 batches of 25, seed 37): one primary theme, up to two tags, a product area, one evidence quote. This is a preview of the draft, not the final classification.
7. **One revision round.** The v0 proposal's own policy says that above 10% in Other the list must be revised; the pilot put 19 calls in Other. A revision call saw the draft, the pilot counts per theme (not split by call type), a one-sentence description of each Other call (no titles), the candidate lists and the dropped candidates. It returned v0.2 (8 themes). The pilot prompt was also fixed (below) and the 100 calls were assigned again.

## Results
| Check | Result |
|---|---|
| Discovery output validity | 8 of 8 batch calls and 2 of 2 consolidation calls valid on the first attempt, no retries |
| Unknown call ids cited in discovery | 0 |
| Discovery evidence quotes, exact match | 193 of 208 (92.8%); 206 of 208 (99.0%) after normalising punctuation and spacing |
| Run 1 / run 2 candidate themes | 12 / 10 |
| Stability (mean best Jaccard, run 1 to 2 / run 2 to 1) | 0.362 / 0.378 |
| Themes with a match of 0.5 or more | 4 of 12 and 4 of 10: renewals (0.65), Comply (0.58), Identity (0.58), backup/Protect (0.57) |
| Outage theme | Run 2 drew it much wider (32 calls vs 15 in run 1); best overlap 0.38 |
| Product areas found (both runs) | Detect, Comply, Protect, Identity. "Backup" did not appear as a product name; the backup theme's calls were all tagged Protect |
| Pilot v1, quote exact match | 89 of 100 (90 after normalising). 10 of the 11 failures began with the speaker label ("Name (aegis_staff): ...") because the prompt said "a single line" |
| Pilot v2 (prompt fixed: sentence text only, at most 30 words), quote exact match | 98 of 100 (100 after normalising) |
| Pilot v1 (draft of 7 themes), calls in Other | 19 of 100 |
| Pilot v2 (revised draft of 8 themes), calls in Other | 15 of 100; 13 of them internal routine meetings (sprint planning, retros, stand-ups, quarterly planning, all-hands, SOC 2 prep) |
| Confidence in pilot v2 | 98 high, 2 medium |
| Cost, all 20 live calls | $0.909 (discovery $0.435, pilot v1 $0.219, pilot v2 $0.216, proposal and revision $0.018, consolidation $0.021) |

Draft v0.2 themes with pilot counts (primary theme; by Stage 0 call type: support / external / internal):
Commercial Renewals and Retention 20 (0/20/0); Compliance Product Adoption and Expansion 17 (4/9/4); Pipeline Outage Technical Remediation 17 (10/0/7); Identity Authentication and Directory Provisioning 9 (6/2/1); Customer Implementation and Architecture Scoping 8 (0/8/0); Backup Performance and Scalability 6 (5/0/1); Billing and Usage Ingestion Disputes 4 (4/0/0); Competitive Strategy and Enablement 4 (0/0/4); Other 15 (1/1/13). Source: `outputs/stage1/theme_by_type_v2.json`.

## Sanity check by call type (my reading of the pilot v2 titles and counts; judgment, not a test)
- Counts by type make sense by content: renewals are all external, billing disputes all support, competitive review all internal.
- **Owner mismatches:** Customer Implementation and Architecture Scoping is proposed for the support lead but has no support calls (all 8 are account-manager-led); Billing and Usage Ingestion Disputes is proposed for sales / account manager but all 4 calls are support cases.
- **Mixed theme:** Compliance Product Adoption and Expansion combines customer compliance reviews, internal Comply v2 launch meetings and report-related support tickets.
- **Small themes:** Billing (4) and Competitive (4).
- **Outage split:** customer-facing outage conversations (account managers) sit in Commercial Renewals, tagged Pipeline Outage; the outage theme itself is only the technical response (support and internal).
- **Gap:** 13 internal routine meetings remain in Other. The approval page offers "Internal Planning and Delivery Cadence" as a suggested theme, starting as Drop. It was written by the analysis, not proposed by the model, and is marked so.

## Limits
- The same 100 calls were used to discover the themes and to test them, and the draft was revised once after seeing the pilot. Counts are in-sample.
- Run-to-run overlap is modest (about 0.37). Core themes are stable; small themes of 2 to 5 calls are not.
- Themes are LLM-led and reflect the model's reading plus the candidate's edits. There are no gold labels.
- Evidence quotes: even after the fix 2 of 100 pilot quotes fail an exact match. The recurring stage needs a check-and-retry step on quotes.
- Titles and call types were withheld from the model by design; titles in the approval page are for the reviewer.

## What this means for the pipeline
- Discovery cost is small (about $0.9 for the whole round), so a taxonomy revision, which bumps the version and re-classifies everything, is cheap to run.
- The "Other" bucket worked as the signal D3 intended: it flagged the gap and triggered the revision. Keep the 10% rule in the pipeline.
- Add a quote check with one retry to the recurring Stage 1 and to Stage 2.

## Reproduce
`PYTHONPATH=src uv run python -m ti.stage1_discovery` replays every call from `cache/` (with `TI_MODE=replay` no key is needed). `uv run pytest tests/test_stage1_discovery.py` runs the offline checks.

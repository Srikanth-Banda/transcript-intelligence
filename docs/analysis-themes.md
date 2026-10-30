# Task 1: categories (themes) with examples and boundary cases

Source: frozen Stage 1 output (`outputs/stage1/stage1_final.csv`, taxonomy v1, prompt `stage1_v1`), Stage 0 labels, Stage 2 scores. Tables, examples and figures: `outputs/analysis/themes/` (`theme_summary.csv`, `examples.json`, `sanity_checks.csv`, `fig1` to `fig3`). Counts, the theme by call-type table and mean scores below were recomputed independently by the main session (R); other figures come from the analysis code (S).

## The categories (8 themes, 0 in Other)

| Theme | Calls | Support / external / internal (R) | Mean call score | Mean customer score | Touches the outage |
|---|---|---|---|---|---|
| Product Adoption, Feedback and Expansion | 24 | 5 / 14 / 5 | 4.33 | 4.29 | 3 |
| Incident and Outage Response | 18 | 7 / 3 / 8 | 2.47 | 2.10 | 18 |
| Technical Integration and Performance Issues | 16 | 14 / 1 / 1 | 2.66 | 2.43 | 3 |
| Commercial Renewals and Retention | 14 | 0 / 14 / 0 | 3.82 | 3.64 | 11 |
| Internal Planning and Delivery Cadence | 12 | 0 / 0 / 12 | 3.75 | none | 2 |
| Onboarding and Implementation Scoping | 7 | 0 / 7 / 0 | 4.57 | 4.57 | 0 |
| Competitive Strategy and Win/Loss | 5 | 0 / 1 / 4 | 3.00 | 2.50 | 4 |
| Billing and Usage Disputes | 4 | 4 / 0 / 0 | 3.62 | 3.62 | 1 |

Reading it as a stakeholder: Technical Integration is the support lead's work queue (14 of 16 calls are support, mean customer score 2.43). Incident and Outage is where engineering, support and internal calls meet (7, 3 and 8 calls). Renewals is entirely external and 11 of 14 touch the outage, which is the sales manager's exposure.

## Why this approach (summary; full reasoning in D3, D3a, D8)
Discovery proposed themes, a human-level judgment froze them (the discovery was unstable: run-to-run overlap 0.37), and an LLM classifies every call against the frozen list with an evidence quote. Theme is the kind of conversation, product area is the module, and an incident field marks the March outage across themes.

## Sanity checks and how much they prove
- All four D3a expectations pass: Billing 4 of 4 support; Technical 14 of 16 support; Renewals 14 of 14 external; Internal Planning 12 of 12 internal (R). The expectations were written alongside the theme definitions, so passing is partly by construction.
- Recoverability from the dataset's own topics (S): a leave-one-out nearest-centroid on the 351 provided topic strings recovers our theme for 76 of 100 calls. Recall by theme: Incident 94%, Adoption 88%, Renewals 86%, Billing 75%, Internal Planning 67%, Competitive 60%, Onboarding 57%, Technical 50%. This is a consistency check against an upstream AI output, not accuracy.
- Largest disagreement: 7 of the 16 Technical calls (Silverline, Summit Trust, Coastal Living, Nova Retail, Stratos) would be labeled Incident from the provided topics. This is the Technical versus Incident boundary and the most likely place for hand-check disagreements.

## Boundary cases to be ready to discuss
- Silverline "Detect False Positives After Patch": Technical (a single customer's fault) versus Incident (a platform event).
- Brightpath "Competitive Evaluation": an external call in the Competitive theme (the theme definition covers customer-facing evaluations).
- "All Hands April Update": internal planning versus incident when most of the agenda is the outage.
Verbatim quotes for two clear and one borderline example per theme are in `outputs/analysis/themes/examples.json`.

## Caveats
- Other was never used (0 of 100). That does not validate the taxonomy: models rarely use an Other bucket, so the "Other above 10% triggers a revision" safeguard is untested.
- The model tagged 79 of 100 calls with a second theme (32 with two tags), so tags are weak evidence of a second theme; headline numbers use the primary theme only.
- Product area and theme overlap for two themes (Incident is 18 of 18 Detect; Renewals is 13 of 14 Platform/General).
- Theme by month shows the story: Incident 0 / 16 / 2 across Feb / Mar / Apr; Product Adoption 4 / 7 / 13 (the Comply v2 launch); Internal Planning 7 / 2 / 3 (S).
- Hand-check (20 calls, my own review, `eval/stage1_review_verdicts.json`): theme 20 of 20, product area 19 of 20 (Nova Retail renewal: I said Detect, model said Platform/General), incident flag 17 of 20. All 3 incident misses are calls I flagged and the model did not (Weekly Engineering Standup, Trailhead Marketplace Detect alerts case, Nova Retail renewal), so the flag is under-inclusive in the sample, not generous. 20 calls cannot rule out an error rate of 10 to 15 percent, and the taxonomy was finalised under delegation (D8).

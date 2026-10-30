# Task 3: bonus insight candidates

Source: frozen pipeline outputs plus transcripts; code in `src/ti/analysis/candidates.py`; tables in `outputs/analysis/candidates/` (`summary.json` and CSVs). Verification status: competitor-mention counts were recomputed by the main session (R); other figures come from the analysis code (S) and are labeled. Provided key moments, churn signals and action items are used only as comparison data, never as input to our pipeline.

Data caveats: n=100, apparently synthetic, no outcome labels (no churn, no renewals recorded). Call dates are partly inconsistent with content (six calls dated before March 10 discuss the outage in the past tense), so date-based before/after comparisons are not used.

## Ranked candidates

| Rank | Candidate | Stakeholder | Evidence | Build cost | Score /20 |
|---|---|---|---|---|---|
| 1 | E. Competitive intelligence | product managers, sales leadership | Strong | Low | 18 |
| 2 | A. Outage blast radius | engineering, support, executives | Strong (content-based) | Low to medium | 16 |
| 3 | B. Churn early warning | sales managers | Medium | Low | 14 |
| 4 | D. Commitment tracking | support, account managers | Weak to medium | High to verify | 13 |
| 5 | C. Support-to-engineering loop | support and engineering leads | Medium to weak | Medium | 12 |
| 6 | F. Coaching signal | support leads | Weak | Medium | 8 |

## E. Competitive intelligence (recommended)
- 31 of 100 calls name a competitor (R): 17 external, 10 internal, 4 support. SentinelShield appears in 22 calls, VaultEdge in 12, CyberNova in 8, Fortiguard in 3 (R). The names were found by a proper-noun scan plus a manual check, not from a given competitor list.
- Competitor-mentioning calls are more often outage-related than the average call (74% against 42%; SentinelShield 18 of 22) (S): after the outage, competitors became live objections.
- By month, 6 of 26 February calls, 16 of 36 March calls and 9 of 38 April calls name a competitor (S).
- Customer example: "VaultEdge was on our shortlist for a while, and we did a pretty deep evaluation of CyberNova too, but honestly their backup restore times were just... not great for our use case."
- Why non-obvious: nobody asked for it, and it connects the reliability event to the competitive position, which crosses product, sales and engineering.

## A. Outage blast radius (recommended)
- 22 of 32 customer accounts (69%) had at least one outage-related call, spanning all three call types (S).
- Tone in outage-touching calls is about 1 point lower in every type: external 3.36 against 4.43, internal 3.14 against 3.81, support 2.25 against 3.28 (S).
- 11 of 14 renewal-theme calls and 9 of 11 Detect support cases involve the outage (S). The weekly mean score falls to 2.35 in the week of March 9, which had 13 calls, all outage-related (S).
- Do not present the date-based per-account before/after (3.88 to 3.40): the outage call is itself the "after", so it is mechanically biased.

## B. Churn early warning (recommended, with caveats)
- A transparent 0-to-4 index on the 40 external calls: low customer tone, tone falling within the call, the customer raising a competitor, the call concerning the outage (S).
- 11 calls score 3 or more: Northstar, Meridian, Helix Data, Quantum Edge, Summit Trust, Ironworks, Nova Retail, Ironclad, Brightpath, Steelpoint, Cobalt (S). All 11 also carry a provided churn-signal moment (an upstream AI output), which covers 11 of the 18 calls with such a signal (S).
- Example (Northstar): "if I don't have something substantially better to bring to my CISO before that renewal conversation, I don't know that we're going to be renewing."
- Caveats: the signals are collinear (the competitor flag fires on 24 of 40 calls); the top-risk calls' tone mostly recovers by the end of the call; there is no churn outcome to validate against. Present as a ranked account list for human follow-up, not a prediction.

## Not recommended for the deck
- D. Commitment tracking: 112 staff promises with a time phrase in 66 calls, but only 42 have any later call with the same account, so follow-through can barely be checked. One chain can be followed (the March 16 remediation promise and the April 7 "three ingestion nodes running in parallel with automatic failover"). Describe as an idea.
- C. Support-to-engineering loop: 9 of 20 support accounts contacted support at least twice, but repeat contacts are mostly about different issues, so "recurring issue" is thin. Customer tone by product area (Detect 2.18, Identity 2.79, Protect 3.08, Comply 4.10) overlaps the outage story.
- F. Coaching signal: the empathy-marker rate correlates -0.84 with customer score because agents apologise more to unhappy customers, which is confounded. Not presented.

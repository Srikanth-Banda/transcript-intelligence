# Task 2: sentiment across call types and what the trends mean

Source: frozen Stage 2 output (`outputs/stage2/stage2_final.csv`, anchors v1, model per D7), Stage 0 labels (`outputs/stage0_final.csv`), Stage 1 incident flag. Numbers and figures: `outputs/analysis/sentiment/` (`findings.json`, `calls_table.csv`, `fig1` to `fig6`). Re-run with `PYTHONPATH=src uv run python -m ti.analysis.sentiment`.

Verification status: means, counts and the March split were recomputed independently by the main session (marked R). Confidence intervals, p-values and the customer-vs-staff gap come from the analysis code (percentile bootstrap over calls, 10,000 resamples, seed 20261029; two-sided permutation tests; about 25 comparisons, no multiple-comparison correction) and were not recomputed (marked S). The data is 100 apparently synthetic calls, so everything is directional.

## Finding 1 (strongest): support is the least positive call type, and customers carry the negativity
- Whole-call score (1 to 5): support 2.93 (n=30), external 3.95 (n=40), internal 3.50 (n=30) (R). Support minus external is -1.02 (R); CI -1.43 to -0.59 (S). Under the title-rule labels the gap is -0.75, so the three relabeled escalation calls do not drive it (S).
- Support versus internal and external versus internal are fragile (p=0.019 and 0.043; 0.057 and 0.20 under title-rule labels) (S).
- In support calls the customer side is negative on about 35% of turns against about 2% for staff (our labels) (S).
- So what: the support lead should track the customer-side score, not the call average. It could be wrong because support calls exist because something went wrong; low support sentiment is partly by construction.

## Finding 2: the March dip sits in outage-touching calls
- Monthly means: Feb 3.71 (n=26), Mar 2.94 (n=36), Apr 3.91 (n=38) (R).
- Within March, calls that touch the Detect outage average 2.57 (n=23) against 3.62 for the rest (n=13) (R). 64% of March calls are flagged (R).
- Removing the outage-touching calls shrinks the March dip to about -0.3 with an interval that includes zero (S), so the data says "mostly the outage" but cannot rule out other causes.
- So what: for engineering and support leadership, the outage cost shows up as a quantifiable tone drop across all call types, not only in support.
- Caveat: the incident flag is set by an LLM (42 calls; 18 have the outage as primary theme). My hand-check found it under-inclusive in 3 of 20 calls, so 42 is probably a floor. It is partly definitional: calls about an outage are tense. Use the "core" (18) and "touches" (42) versions separately.

## Finding 3: the outage runs through all three call types, and recovery is uneven by account
- 42 calls touch it: 10 support, 18 external, 14 internal, peaking the week of March 9, with 19 more in April.
- External calls: before March 10 mean 4.37 (n=15), March 10 to 31 mean 2.63 (n=8), April 4.21 (n=17) (S). April versus before is -0.16 with an interval spanning zero (S): on average the external relationship recovered.
- Nine accounts have both an outage-touching support call and an external call. Four ended lower than they started (Summit Trust 4.0 to 2.5, Stratos 4.5 to 2.0, Clearwater 5.0 to 2.5, Ridgeline 3.5 to 2.5); three ended higher (Trailhead 1.5 to 4.5, Cobalt 1.5 to 3.0, Forge 3.5 to 4.5) (S).
- So what: an account-level view (see candidates) separates the accounts that recovered from the ones needing follow-up. Caveat: each account has only 2 to 4 calls with different purposes, so these are leads, not conclusions.
- Data caveat: call dates are partly inconsistent with content (a March 9 call already discusses the outage in the past tense; a March 16 call says "day three"). The first outage-titled call is March 10, which we use as the boundary. Date-based before/after comparisons per account are mechanically biased and not presented.

## Finding 4 (weakest as a signal): almost every call ends warmer than it starts
- 78 of 100 calls improve from first third to last third, 21 are flat, 1 gets worse (Trailhead Marketplace 2.0 to 1.5) (S). Mean uplift about +0.5.
- In support calls the share of negative turns barely falls while the score rises, which points to the scripted shape of the calls and to the rubric's "relief after a fix" rule, not to satisfaction.
- 16 calls still end at 2.5 or below (10 support, 4 external, 2 internal): these are the "unresolved at the end" list worth reading.
- So what: trajectory is only informative as an exception report (calls that do not recover), not as an average.

## Finding 5: we track the provided score, but measure tone where it measures severity
- Correlation with the provided call score 0.96; mean absolute difference 0.23; our mean is higher by about 0.09 (S). No call differs by 1 or more (max 0.7), so the planned |diff| >= 1 disagreement list is empty; the 0.6 threshold lists 8 calls.
- Of 444 turns the provided labels call positive and we call neutral, 380 are staff turns: this is the "courtesy is neutral" rule (D8), a design choice, not a bug.
- Reading the evidence quotes for the 8 largest gaps: ours looks right on the war-room, impact and remediation calls (calm and productive, not negative); we cannot tell on three (a customer says "really annoyed" but the issue is solved); one internal-score case looks too high for an unmet need. This was a reading of quotes and excerpts, not a systematic review.
- Agreement here is consistency with an upstream AI output, not accuracy.

## What I would not claim
- That sentiment predicts churn or any outcome (no outcome labels).
- That differences between internal and the other types are established (fragile under the title-rule labels).
- That the outage "caused" the dip (the flag is an LLM judgment, likely a floor, and partly definitional; the effect with outage calls removed is not distinguishable from zero).
- Anything about trajectory as satisfaction.
- Individual-account conclusions from two to four calls.

## Changes versus earlier exploratory numbers (DECISIONS.md section B)
Earlier figures used the provided score and the rule-based types: support 2.94, external 3.71, March 2.78. They differ because (a) the three escalation calls moved from external to support, (b) our score runs about 0.1 above the provided one, and (c) the customer/staff definition changed from sentence labels to our per-turn labels. None changes a conclusion.

## Hand-check (added after the review)
15 calls scored by me against the frozen anchors (`eval/stage2_review_verdicts.json`): every call within 0.5 of the model, 9 exact, mean absolute gap 0.20, rank correlation 0.91; customer-side score on 10 calls, mean gap 0.30. The model was higher than me on 5 of the 6 calls where we differed, which matches the 'our mean is about 0.1 above' finding. Small sample; I cannot confirm I stayed blind to the model scores throughout.

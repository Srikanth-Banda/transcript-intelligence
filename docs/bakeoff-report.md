# Model bake-off report (run 2026-10-29)

Status: RESULTS, not a decision. Nothing is pinned. The main session and the candidate choose models from this report and record the choice in `DECISIONS.md`. Design: `docs/model-selection.md` section 7. Raw log: `outputs/bakeoff/results.jsonl` (475 calls). Every number below is recomputed by `uv run python eval/bakeoff.py report` into `outputs/bakeoff/metrics.json` and `outputs/bakeoff/tables.md`.

## 1. Design as run

| Item | As run |
|---|---|
| Stage 0 | Prompt `stage0_v1` (sha256 prefix `3ced5d5477d6`), title withheld, attendee counts + first 8 turns. All 70 customer calls (30 internal calls skip the model by D1). Haiku 5.5 and Gemini 3.8 Flash, runs 1 and 2. |
| Stages 1 and 2 | **Bake-off drafts**, not the final prompts: `stage1_bakeoff_v0` (`6074c4f9e084`, provisional 8+1 theme list) and `stage2_bakeoff_v0` (`577940e40023`, draft 1 to 5 anchors). 15-call sample, Sonnet 5.5, GPT-6.1 Terra, Gemini 3.8 Flash, runs 1 and 2. Transcript only, via `view_for` (no title, call type, or provided score/summary/topics/labels). |
| Provider pins (no fallbacks) | haiku and sonnet: `anthropic`; terra: `openai` (standard tier); gemini: `google-ai-studio` (standard tier). Every one of the 475 responses came back from the pinned provider with the requested model slug. No provider changed. |
| Settings | `temperature=0` for all. `seed=7` for Terra and Gemini (they list it). Reasoning effort `low` for Sonnet and Gemini (reasoning is mandatory on both); not set for Haiku and Terra (optional, off by default). Structured output (`json_schema`) worked for Haiku, Sonnet and Gemini on every call and for Terra on Stages 0 and 1. **Terra fell back to plain JSON mode (schema described in the prompt) on all 33 Stage 2 calls**, so its Stage 2 results were produced under weaker output constraints than the other two models (the client falls back when the API rejects the strict schema; the cause was not investigated, the Stage 2 schema has a nullable field and a nested list). `max_tokens`: 3000 / 4000 / 10000 for stages 0 / 1 / 2. |
| Sample (seed 42) | 3 escalation calls (Blackridge URGENT, Cobalt URGENT, Northstar ESCALATION) + 3 known-hard picks + 9 seeded-random fill = 15; 5 per title-rule type (escalations count as external). Saved in `outputs/bakeoff/sample.json`. |
| Known-hard picks | Longest transcript: Harborview Banking - Threat Detection Tuning. Shortest: Identity Team - Sprint Retro. Largest disagreement between the provided score and the provided sentence-label balance: Detect Team - Sprint Planning (03-02). These are selection aids; stages never saw provided data. |
| Sample ids (last 6 characters) | 0D92AB (Detect Team), 05678C (Aegis / Redwood Clinical), 70206E (Detect Team), 3FB020 (Aegis / Harborview Banking), A7F71B (URGENT: Cobalt Software), 7315E7 (URGENT: Blackridge Investmen), 3D3491 (Support Case #6573), 6CCBE7 (ESCALATION: Northstar Pharma), B089CA (Detect Outage), 657CF1 (Support Case #3103), 9EDE37 (Support Case #7537), 099E75 (Support Case #6539), 632514 (Identity Team), 92B34B (Support Case #9856), 26FFAD (Comply v2). Full ids in `outputs/bakeoff/sample.json`. |
| Determinism probe | Run 3 added on the first 3 sample customer calls (Redwood, Harborview, Cobalt URGENT) for Stage 0 (Haiku, Gemini) and Stage 2 (Sonnet, Terra, Gemini). Runs 1, 2, 3 are three identical requests; the run number only changes the cache key. |

## 2. Results

### Stage 0 (70 customer calls x 2 runs = 140 calls per model)

| metric | Haiku 5.5 | Gemini 3.8 Flash |
|---|---|---|
| schema-valid on first attempt | 100.0% | 100.0% |
| verbatim quote valid (exact) | 100.0% | 98.6% (2 of 140) |
| verbatim quote valid (loose: whitespace, quote and dash normalized) | 100.0% | 100.0% |
| agreement with the title rule | 92.9% (5 disagreements) | 95.7% (3 disagreements) |
| run 1 vs run 2 same label | 100.0% | 100.0% |
| run 1 vs run 2 identical quote | 64.3% | 100.0% |
| speaker sides agree with deterministic | 98.6% | 100.0% |
| confidence (run 1) | 64 high, 6 medium | 70 high |
| latency median / p90 | 1.7 s / 3.1 s | 2.4 s / 2.9 s |
| cost (140 calls) | $0.040 | $0.166 |

Haiku and Gemini agree on 97.1% of calls (run 1).

**The three escalation calls** (title rule: external; the prompt did not mention escalations):

| call | Haiku run 1 / run 2 | Gemini run 1 / run 2 |
|---|---|---|
| URGENT: Cobalt Software | support (high) / support (high) | support (high) / support (high) |
| URGENT: Blackridge Investments | support (high) / support (high) | support (high) / support (high) |
| ESCALATION: Northstar Pharma | support (high) / support (high) | support (high) / support (high) |

Both models labeled all three support with high confidence in both runs. Per the iteration protocol, the escalation sentence did not need to be added; v1 stands. These are the only 3 disagreements for Gemini. Haiku has 2 more, both title-rule external that Haiku calls support: "Aegis / Northstar Pharma - Urgent: Detect Outage Impact" (high; quote "We've had zero visibility into our threat monitoring since yesterday morning") and "Aegis / Quantum Edge - Renewal Concerns" (medium; quote "I've seen your support tickets come through and I definitely want to make sure we address ..."). Gemini labeled both external. I did not judge them (no hand labeling in this run). They are in `outputs/stage0_review_queue_haiku.csv` for the candidate.

### Stage 1, draft themes (15 calls x 2 runs = 30 calls per model)

| metric | Sonnet 5.5 | GPT-6.1 Terra | Gemini 3.8 Flash |
|---|---|---|---|
| schema-valid on first attempt | 100% | 100% | 100% |
| theme / tag / product-area list membership | 100% | 100% | 100% |
| verbatim quote valid (exact) | 100% | 100% | 100% |
| primary theme same, run 1 vs run 2 | 100% | 100% | 100% |
| product area same, run 1 vs run 2 | 100% | 100% | 100% |
| latency median / p90 | 1.9 s / 4.2 s | 2.6 s / 4.2 s | 2.2 s / 2.6 s |
| cost (30 calls) | $0.310 | $0.072 | $0.075 |

Cross-model primary-theme agreement (run 1, 15 calls): Sonnet-Gemini 93.3%, Terra-Gemini 86.7%, Sonnet-Terra 80.0%. All three put the three escalation calls under "Outage & incident response" with product area Detect. They differ on 3 calls:

| call | Sonnet | Terra | Gemini |
|---|---|---|---|
| Support Case #6539 Steelpoint LDAP Sync Failures | Identity & access | Outage & incident response | Identity & access |
| Support Case #9856 Silverline Backup Window Exceeded | Integrations, backup & data | Outage & incident response | Integrations, backup & data |
| Identity Team - Sprint Retro | Identity & access | Product roadmap & planning | Product roadmap & planning |

On the two support-case differences, Terra's "Outage & incident response" looks less specific than the other two on reading the titles; I did not read the transcripts to judge. This is a draft theme list, so these are model-behaviour signals, not accuracy.

### Stage 2, draft anchors (15 calls x 2 runs = 30 calls per model)

| metric | Sonnet 5.5 | GPT-6.1 Terra | Gemini 3.8 Flash |
|---|---|---|---|
| schema-valid on first attempt | 100% | 100% | 100% |
| per-turn labels cover every turn | 100% | 100% | 100% |
| verbatim quote valid (exact) | 100% | 100% | 100% |
| call-score MAD, run 1 vs run 2 | 0.00 | 0.17 | 0.00 |
| call score exactly the same in both runs | 100% | 66.7% | 100% |
| customer-score MAD, run 1 vs run 2 | 0.00 | 0.10 | 0.00 |
| per-turn label agreement, run 1 vs run 2 | 97.3% | 95.3% | 99.3% |
| correlation with provided score | 0.96 | 0.92 | 0.96 |
| MAD vs provided score | 0.21 | 0.28 | 0.23 |
| per-turn agreement with provided sentence labels | 76.1% | 67.8% | 74.5% |
| latency median / p90 | 4.4 s / 7.0 s | 11.7 s / 13.6 s | 5.4 s / 6.3 s |
| cost (30 calls) | $0.526 | $0.199 | $0.150 |

The provided score and labels are themselves an upstream AI output, so these three rows mean "consistent with the upstream AI", not "correct". Mean call score by title-rule type, run 1 (Sonnet / Terra / Gemini): support 2.6 / 2.5 / 2.7; external 2.7 / 2.6 / 2.7; internal 3.6 / 3.8 / 3.6 (a 15-call sample chosen to include the escalations and extremes, so these are not population means).

Escalation calls, call score (customer score) versus provided score:

| call | Sonnet | Terra | Gemini | provided |
|---|---|---|---|---|
| URGENT: Cobalt | 2.0 (1.5) | 2.0 (2.0) | 2.0 (1.5) | 1.8 |
| URGENT: Blackridge | 2.0 (1.5) | 2.0 (2.0) | 2.0 (1.5) | 1.6 |
| ESCALATION: Northstar | 2.0 (2.0) | 2.0 (2.0) | 2.0 (2.0) | 2.1 |

### Determinism probe (3 identical requests x 3 transcripts)

| stage / model | byte-identical parsed JSON | call score identical | lowest per-turn agreement between any two runs |
|---|---|---|---|
| Stage 0 Haiku 5.5 | 2 of 3 | label same 3 of 3 | n/a |
| Stage 0 Gemini 3.8 Flash | 3 of 3 | label same 3 of 3 | n/a |
| Stage 2 Sonnet 5.5 | 0 of 3 | 2 of 3 (Cobalt: 2.0, 2.0, 1.5) | 92.3% |
| Stage 2 GPT-6.1 Terra | 0 of 3 | 3 of 3 | 92.7% |
| Stage 2 Gemini 3.8 Flash | 2 of 3 | 3 of 3 | 89.7% |

`temperature=0` (and `seed` where listed) did not produce byte-identical output on any Stage 2 model, and Claude and GPT did not list `temperature` as supported, so it may be ignored. Even Terra and Gemini, which list `seed`, varied. A live re-run will not reproduce a run exactly; the committed cache is what makes results reproducible. The 2-run MAD of 0.00 for Sonnet and Gemini understates variability: Sonnet varied in run 3 on one of three transcripts.

### Decision rule (section 7)

Rule: disqualify below 98% schema-valid or quote validity, or Stage 2 call-score MAD above 0.3; among the rest pick the cheapest within 2 points of the best "quality" (mean of schema-valid, quote validity, run-to-run stability); ties to the model already used in another stage.

| stage | disqualified | quality (schema, quote, stability) | cheapest within 2 points | rule's winner |
|---|---|---|---|---|
| Stage 0 | none | Haiku 100.0, Gemini 99.5 | Haiku ($0.040 vs $0.166) | **Haiku 5.5** |
| Stages 1 and 2 (judged together; stability = mean of Stage 1 theme agreement and Stage 2 per-turn agreement; cost over runs 1 and 2) | none | Gemini 99.9, Sonnet 99.5, Terra 99.2 | Gemini ($0.225; Terra $0.270; Sonnet $0.836) | **Gemini 3.8 Flash** |

**What the rule does and does not show.** Every model cleared every threshold, so the rule reduces to "cheapest". It cannot tell Sonnet from Gemini on quality. Other observations, outside the rule:
- Terra is the weakest on the signals that differ (with the JSON-mode confound above for its Stage 2 numbers): call-score MAD 0.17 and 66.7% exact repeat on scores, lowest agreement with the provided score and labels (0.92 correlation, 67.8%), slowest (11.7 s median), and it differs from the other two on both support calls where the models disagree on theme.
- Sonnet and Gemini behave almost the same on this sample (correlation 0.96 each, MAD 0.00, 93% theme agreement). Sonnet costs 3.7x Gemini here.
- Gemini is the only shortlisted model that lists both `temperature` and `seed`, and the only one with byte-identical Stage 0 output across all three runs. It also scored 98.6% (not 100%) on exact Stage 0 quotes: 2 of 140 quotes differ from the opening only in punctuation or whitespace normalization (they pass the loose check).
- If one provider and one model for all stages is preferred (B2 criterion 8), Gemini 3.8 Flash for all three stages costs more at Stage 0 ($0.166 vs $0.040 per 140 calls) but stays within 2 quality points there.

**Recommendation per stage, runner-up in brackets:** Stage 0: Haiku 5.5 [Gemini 3.8 Flash]. Stages 1 and 2: Gemini 3.8 Flash [Sonnet 5.5]. Sonnet is the hedge if the final prompts and anchors turn out to separate models more than this draft does. The pin itself is the candidate's call.

## 3. Anomalies

- Invalid JSON, retries, refusals, truncation (`finish_reason` other than `stop`): **none** in 475 calls. Structured `json_schema` mode worked on every call except Terra's 33 Stage 2 calls, which used the JSON-mode fallback. This is a confound for Terra's Stage 2 columns (lower repeatability, lower agreement with the provided labels): they may reflect the weaker output constraint rather than the model.
- Provider changes: none. Returned model slug equals requested slug on every call.
- Quotes not found exactly: 2 Gemini Stage 0 quotes (the same call, Nimbus Platform Comply v2 Preview, in both runs); both pass the loose check.
- Haiku's Stage 0 quote differs between run 1 and run 2 on 35.7% of calls while its label never changes.
- A smoke test (4 Stage 0 calls, 6 Stage 1 and 2 calls) ran before the full runs; those calls are part of run 1 (same cache entries, not double counted).

## 4. Cost

| | Estimated (`model-selection.md`) | Actual |
|---|---|---|
| Whole bake-off | about $3.8 (up to about $6.5) | **$1.633** (475 calls; by model: Haiku $0.041, Sonnet $0.896, Terra $0.286, Gemini $0.411) |

Cost comes from the `usage.cost` field OpenRouter returned and matches the key's own daily usage ($1.6336). The key's remaining balance after the run was about $5.15 of $8. The $0.75 stop guard never triggered.

Linear extrapolation from this sample (not measured at 100 calls, and the one long-context taxonomy-discovery call is not included): one pass of Stages 1 and 2 over 100 calls would cost about $0.75 (Gemini), $0.90 (Terra), $2.80 (Sonnet), plus Stage 0 about $0.03 (Haiku). That is far below the $7.3 pipeline estimate for Sonnet in `model-selection.md`, because real output tokens were smaller than I assumed there (Stage 2 averaged 735 to 916 completion tokens per call).

## 5. Three Stage 2 outputs to eyeball

Run 1, first six turns shown with the model label and the provided label.

**Sonnet 5.5 on "URGENT: Blackridge Investments - Complete Loss of Threat Visibility"** (provided 1.6, very-negative). Call 2.0, customer 1.5, trajectory 1.5 to 2.5, confidence high. Quote: "we have been evaluating SentinelShield for the past couple months as a potential alternative and right now, today, this is making that decision very easy."
- [0] Marcus Williams: "Thank you for calling Aegis Cloud Security support ..." model neutral, provided neutral
- [1] Julia Tran: "Marcus, hi, this is Julia Tran from Blackridge ..." model negative, provided negative
- [3] Julia Tran: "It's Blackridge Investments, B-L-A-C-K-R-I-D-G-E ..." model neutral, provided negative
- [5] Julia Tran: "Forty minutes ago — Marcus, I have been trying to get someone on the phone ..." model negative, provided negative

**Gemini 3.8 Flash on "Identity Team - Sprint Retro"** (provided 3.4, mixed-positive; shortest call; no customer). Call 3.5, customer null, trajectory 3.0 to 3.5, confidence high. Quote: "Still, it shipped on time, no regressions in QA, which — honestly that's not always the case with provisioning stuff. I want to call that out as a win."
- [2] Sofia Petrov: "Same, the Detect outage stuff is still causing a lot of noise even two weeks later." model negative, provided negative
- [3] Mike Romano: "Yeah, let's try to stay focused on Identity sprint stuff today ..." model neutral, provided neutral
- [5] Sofia Petrov: "Before you do that, can we just acknowledge that the Detect outage on the tenth ..." model negative, provided negative

**GPT-6.1 Terra on "Support Case #6539 - Steelpoint Manufacturing LDAP Sync Failures"** (provided 2.4, mixed-negative). Call 2.5, customer 2.0, trajectory 2.5 to 3.0, confidence high. Quote: "I'm glad we found it but I'm also really annoyed that it took this long."
- [1] Harold Jensen: "Yeah, hi Marcus, this is Harold Jensen, IT Director ..." model negative, provided negative
- [2] Marcus Williams: "I completely understand Harold, and I appreciate you calling in ..." model positive, provided neutral
- [3] Harold Jensen: "Sure, so — basically our Active Directory sync through Aegis Identity just stopped working ..." model neutral, provided negative

Turn [2] shows the pattern behind the per-turn gap: a polite staff acknowledgement labeled positive by the model, neutral upstream.

## 6. What this bake-off does NOT show

- **Accuracy.** There are no gold labels. The only comparators are the title rule (imperfect), and the provided score and labels (an upstream AI output). Agreement with them is consistency, not correctness.
- **Anything about the final prompts.** Stages 1 and 2 used quick drafts; the theme list is provisional and the anchors are uncalibrated. A different anchor wording would shift scores and could reorder models.
- **Statistical power.** 15 calls (30 calls per model and stage) and 3 transcripts for the determinism probe. Differences smaller than about 10 points are noise.
- **Independence.** The sample is the data later used for validation, so results for the chosen model are optimistic and must not be reported as final accuracy; hand-check on different calls.
- **The Stage 0 prompt as an independent test.** The escalation sentence was removed so those 3 calls test the prompt, but the prompt author (this project) had already seen those calls.
- **Reasoning-effort effects.** Sonnet and Gemini ran at `low` reasoning effort; higher effort could change scores and cost.
- **Model drift.** Hosted models can change behind a slug; the probe was one afternoon (2026-10-29). Taxonomy discovery over 190k tokens (the one long-context call) was not tested.
- **Hand-checked quality.** No transcript was hand-labeled in this run. The Haiku-only Stage 0 disagreements, the three Stage 1 differences and the Terra support-case themes are unjudged.

## 7. Files

- Code: `eval/bakeoff.py` (scoring, sample, runner, spend guard), `eval/bakeoff_report.py` (metrics); tests `tests/test_bakeoff.py` (11 tests, offline).
- Drafts: `prompts/stage1_bakeoff_v0.md`, `prompts/stage2_bakeoff_v0.md`.
- Data: `outputs/bakeoff/{results.jsonl,sample.json,metrics.json,tables.md}`, `outputs/stage0_{haiku,gemini}.csv`, `outputs/stage0_review_queue_{haiku,gemini}.csv`, raw LLM outputs in `cache/` (5.6 MB).
- Client changes (`src/ti/llm.py`, backward compatible, tests green): records latency, finish reason and billed cost; accepts `reasoning_effort` and `seed`; raises a typed `InvalidOutput` with the raw text and usage; caller-supplied `provider_order` overrides the environment.

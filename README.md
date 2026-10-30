# Transcript Intelligence

A pipeline that turns 100 recorded calls (support, external, internal) into call types, themes and sentiment, and then into findings that support leaders, sales managers, product managers and engineering leads can act on. Take-home assessment; the brief is in `assignment.md`. Every decision, its alternatives and its known weakness is in `DECISIONS.md` (the source of truth); `docs/decision-defense.md` is the presenter's guide.

## Status (2026-10-30)

- All three stages have been run on all 100 calls with their final prompts and are frozen: Stage 0 call type (`stage0_v1`), Stage 1 themes (`stage1_v1`, taxonomy v1), Stage 2 sentiment (`stage2_v1`, anchors v1). 100 of 100 outputs valid on the first attempt for Stages 1 and 2.
- Hand-checks are done (my own review): Stage 0 on 15 items, Stage 1 on 20 calls, Stage 2 on 15 calls. Results below. They are small samples.
- 89 offline tests pass (`uv run pytest -q`, checked 2026-10-30), including a replay-mode execution of all 7 notebooks.
- Deliverables: deck, 7 notebooks (with HTML copies), interactive explorer. The video is not recorded yet.
- Not built: Docker, Raspberry Pi, tailnet URL and self-hosted Langfuse. `deploy/` is a placeholder and nothing graded depends on it.

## Pipeline

```
dataset/ (100 meetings)
   |
Stage 0  call type [RUN]      D1   metadata check -> LLM (support vs external; sees counts + opening, never the title) -> title-rule cross-check -> review
   |                              result: support 30 / external 40 / internal 30 (30 internal decided by metadata, 70 by the LLM)
   +--> Stage 1  themes [RUN]      D3   one-time taxonomy discovery (frozen as taxonomy v1, D8) -> recurring LLM classification
   |                              theme + product area + incident flag, evidence quote, "Other" bucket
   +--> Stage 2  sentiment [RUN]   D2   one LLM pass: whole-call score 1-5, per-turn labels, trajectory (anchors v1, D8)
   |
Analysis [RUN]                D6   trends, cross-type stories, stakeholder views (no LLM calls; src/ti/analysis/)
```

**Model (D7):** one model for every stage, `google/gemini-3.8-flash` through OpenRouter, provider pinned to Google AI Studio (no fallbacks), `temperature=0`, `seed=7`, reasoning effort `low`. Temperature 0 does not guarantee identical output (the determinism probe saw Stage 2 JSON repeat on 2 of 3 transcripts), so reproducibility comes from the committed cache of raw responses, not from re-running. The pre-written decision rule picked a different model for Stage 0 and was overridden; the reasoning is in D7 and `notebooks/06`.

The upstream summary, topics and sentiment shipped in the dataset are kept in a separate `provided` object and are never inputs to a stage (`Meeting.view_for(stage)` is the only door). They are comparison baselines only.

## Reproduce offline (replay mode, no key, no network)

```bash
uv sync                                   # Python 3.12 environment
uv run pytest -q                          # 89 tests, no network
```

`TI_MODE=replay` serves only from the committed `cache/`; a cache miss raises an error, never a silent live call (`src/ti/llm.py`). The notebooks force replay mode themselves (`ti.nbhelpers.setup()`), fill the pinned model settings from `.env.example` when there is no `.env`, and never read a key.

- **Re-execute all notebooks:** `uv run pytest tests/test_notebooks.py -q`. This runs each notebook with `nbclient` directly and fails on any error output or on "NaN"/"undefined" in outputs. Plain `jupyter nbconvert --execute` failed in my environment (`jupyter_contrib_nbextensions` missing), which is why the test drives `nbclient`. The HTML copies in `notebooks/html/` are committed, so nothing needs re-running to read them.
- **Rebuild analysis tables and figures:** `PYTHONPATH=src uv run python -m ti.analysis.sentiment` (sentiment; see `src/ti/analysis/` for themes and candidates). No LLM calls.
- **Rebuild the explorer:** `PYTHONPATH=src uv run python app/build_explorer.py` writes `app/explorer.html`. No LLM calls.
- **Live runs (not needed to review):** `cp .env.example .env`, add `OPENROUTER_API_KEY`, set `TI_MODE=live`. Stage entry points: `python -m ti.stage1`, `python -m ti.stage2`. A live re-run may not reproduce the committed outputs exactly. Never commit `.env`; `.env` is git-ignored and the key is never written to the cache.

## The dataset

The 100 meeting folders supplied with the assignment are not in this repo. Place them at `dataset/<meeting-id>/` (six JSON files each) to run anything that reads the transcripts; the committed `cache/` is keyed on that content, so replay needs the same data.

## Layout (what exists)

| Path | Contents |
|---|---|
| `src/ti/` | `load.py` (data and what each stage may see), `schemas.py`, `llm.py` (client, cache, replay), `stage0.py`, `stage1.py`, `stage1_discovery.py`, `stage2.py`, `nbhelpers.py`, `analysis/` (themes, sentiment, candidates, stats) |
| `prompts/` | Versioned prompts. Final: `stage0_v1`, `stage1_v1`, `stage2_v1`. Others are discovery prompts and bake-off drafts (`*_bakeoff_v0`, `stage1_v0`, `stage2_v0`) kept for the record |
| `cache/` | Raw LLM responses keyed by input, prompt, model and params (committed; this is what replay serves) |
| `notebooks/` | `00_overview` to `06_model_choice_and_limits` (`.ipynb`), HTML copies in `notebooks/html/` |
| `app/` | `explorer.html` (self-contained), `build_explorer.py`, `explorer_tpl.html` |
| `eval/` | `bakeoff.py`, `bakeoff_report.py`, `stage12_report.py`, `build_stage12_verdicts.py`, `demo_replay.py` (one call through Stages 1-2 in replay, for the video), hand-check verdicts `stage0/1/2_review_verdicts.json` |
| `outputs/` | `stage0_final.csv`, `stage1/` (incl. `stage1_final.csv`, `taxonomy_v1.json`), `stage2/` (incl. `stage2_final.csv`), `stage12_metrics.json`, `analysis/{themes,sentiment,candidates}/`, `bakeoff/` |
| `deck/` | The exported slide deck (.pptx) |
| `docs/` | `analysis-themes.md`, `analysis-sentiment.md`, `analysis-candidates.md`, `stage1-discovery.md`, `bakeoff-report.md`, `model-selection.md`, `quotable_numbers.py` |
| `tests/` | 89 tests across loader, LLM client, stages, analysis, explorer and notebooks |
| `deploy/` | Placeholder only (see Status) |
| `dataset/` | The 100 meetings, unmodified (D4: no synthetic data) |

## Artifacts (private)

These are private claude.ai artifacts. They open only for the owner until I share them, so the reviewer needs a shared link or the committed files.

- Deck (21 slides: 15 main, 6 appendix, with speaker notes), exported to `deck/transcript-intelligence-findings.pptx`; the live version is a private artifact: https://claude.ai/artifact/3P2fxeVuVfihK9hgbXNyCM
- Explorer (same content as `app/explorer.html`): https://claude.ai/artifact/3RKUQFK2m1CURZcDjNNend
- Assessment Navigator (my orientation tool, not a deliverable): https://claude.ai/artifact/HGqhuC4inwMcdJ4wXQ7ZAA

## Headline results

All numbers below are copied from `docs/analysis-*.md`, `outputs/stage12_metrics.json` and `DECISIONS.md`. R = recomputed independently by the main session; S = from the analysis code, not recomputed. Everything is directional: 100 apparently synthetic calls, no outcome labels.

**Task 1: themes** (`docs/analysis-themes.md`, `notebooks/02`). 8 themes, 0 of 100 in Other: Product Adoption, Feedback and Expansion 24; Incident and Outage Response 18; Technical Integration and Performance Issues 16; Commercial Renewals and Retention 14; Internal Planning and Delivery Cadence 12; Onboarding and Implementation Scoping 7; Competitive Strategy and Win/Loss 5; Billing and Usage Disputes 4. Product area: Detect 31, Platform/General 22, Comply 21, Identity 15, Protect 11. Technical Integration is 14 of 16 support calls; Renewals is 14 of 14 external. Discovery was unstable (run-to-run overlap 0.37), so the taxonomy is a judgment, not an LLM output (D8).

**Task 2: sentiment** (`docs/analysis-sentiment.md`, `notebooks/03` and `04`).
- Whole-call score by type: support 2.93 (n=30), external 3.95 (n=40), internal 3.50 (n=30) (R). Support minus external -1.02, CI -1.43 to -0.59 (S). In support calls the customer side is negative on about 35% of turns against about 2% for staff (S).
- Monthly means: Feb 3.71, Mar 2.94, Apr 3.91 (R). Within March, calls touching the Detect outage average 2.57 (n=23) against 3.62 for the rest (n=13) (R). With outage calls removed the dip is about -0.3 with an interval including zero (S): "mostly the outage", not proven.
- 78 of 100 calls end warmer than they start, which reflects the scripted shape of the calls; trajectory is useful only as an exception list (16 calls end at 2.5 or below).
- Our score tracks the provided score: correlation 0.96, mean absolute difference 0.23 (S). That is consistency with an upstream AI output, not accuracy.

**Task 3: further insights** (`docs/analysis-candidates.md`, `notebooks/05`). Competitive intelligence: 31 of 100 calls name a competitor (SentinelShield 22, VaultEdge 12, CyberNova 8, Fortiguard 3) (R); competitor-mentioning calls are outage-related 74% of the time against 42% overall (S). Outage blast radius: 22 of 32 customer accounts had an outage-related call (S). Churn early-warning: a transparent 0-4 index on 40 external calls ranks 11 accounts for follow-up (S), unvalidated. Commitment tracking is described, not built.

**Pipeline quality** (`outputs/stage12_metrics.json`). Stage 1: 100 of 100 valid; stability on a 20-call rerun: theme, product area and incident flag identical on 20 of 20, tag Jaccard 0.95. Stage 2: 100 of 100 valid; rerun on the same 20 calls: call-score MAD 0.075, 17 of 20 identical, per-turn label agreement 92.9%.

**My hand-checks** (`eval/*_review_verdicts.json`). Stage 0: I agreed with the LLM on 15 of 15 reviewed items and with the title rule on 12 of 15 (the three escalation calls are support). Stage 1 (20 calls): theme 20 of 20, product area 19 of 20, incident flag 17 of 20 (all 3 misses were calls I flagged and the model did not, so the flag looks under-inclusive). Stage 2 (15 calls): all within 0.5 of the model, 9 exact, mean absolute gap 0.20, rank correlation 0.91; the model was higher than me on 5 of the 6 differences.

## Rubric to evidence map

| Rubric item (assignment.md) | Evidence | Where | Status |
|---|---|---|---|
| Task 1: pipeline that categorizes by theme, with reasoning and examples | Frozen taxonomy, examples per theme (two clear, one borderline), approach rationale | `notebooks/02_stage1_categories.ipynb` (+ html), `docs/analysis-themes.md`, `outputs/analysis/themes/examples.json`, `docs/stage1-discovery.md`, deck | Done; hand-checked on 20 calls |
| Task 2: sentiment across call types with trends, and what they mean | Scores by type and month, interpretation, "so what", what I would not claim | `notebooks/03_stage2_sentiment.ipynb`, `notebooks/04_trends_and_meaning.ipynb`, `docs/analysis-sentiment.md`, `outputs/analysis/sentiment/`, deck | Done; hand-checked on 15 calls |
| Task 3: 2-3 additional insights for different stakeholders | Three built insights plus one described idea, ranked candidates | `notebooks/05_bonus_insights.ipynb`, `docs/analysis-candidates.md`, `outputs/analysis/candidates/`, deck | Done; churn list unvalidated (no outcomes) |
| Deliverable: slide deck for product and engineering leadership | 21 slides with speaker notes | `deck/transcript-intelligence-findings.pptx` | Done (exported from the artifact) |
| Deliverable: notebook or repo, readable, decisions explained | Repo, 7 notebooks, `DECISIONS.md`, tests | `notebooks/`, `src/ti/`, `tests/`, `DECISIONS.md` | Done; 89 tests pass |
| Deliverable: 5-10 minute video demo | Script and checklist | prepared privately | Recording not made yet |
| Demo any insights or visualizations built | Interactive explorer (Overview, Calls, Themes, Insights, Trust) | `app/explorer.html`, `app/build_explorer.py`, `tests/test_explorer.py` | Done |
| Ground rule: be transparent about changed or generated data | No synthetic data, dataset unmodified; call types assigned by Stage 0, not edited | `DECISIONS.md` D1, D4; `dataset/` | Recorded |
| Ground rule: LLM tools welcome, show judgment | AI-use disclosure, decision log, model choice with evidence and an override | `DECISIONS.md`, `docs/model-selection.md`, `docs/bakeoff-report.md`, `notebooks/06` | Recorded |
| Handling missing call-type labels | Stage 0 design, cross-check, review | `notebooks/01_stage0_call_type.ipynb`, `outputs/stage0_final.csv`, `eval/stage0_review_verdicts.json` | Done; 15 items reviewed |
| Q&A readiness: walk through code | Small modules, tests, decision log with weaknesses | `src/ti/`, `tests/`, `DECISIONS.md` | Ready |
| Pipeline running on the data | Final outputs and raw responses | `outputs/stage0_final.csv`, `outputs/stage1/stage1_final.csv`, `outputs/stage2/stage2_final.csv`, `cache/` | Run on all 100 calls; replayable offline |

## Limits and honest caveats

- No ground truth. Agreement with the dataset's own topics and scores is consistency with an upstream AI output, not accuracy. The data looks synthetic and has no outcome labels (no churn, no renewals), so nothing predicts anything.
- The taxonomy (v1), the sentiment anchors (v1) and the bonus-insight selection (D6) were finalised by the assistant under my explicit delegation, from the pilot evidence; they are not my independent design. I reviewed outputs afterwards and may veto (D6, D8).
- Hand-checks are small (15, 20 and 15 items), cannot rule out error rates around 10 to 25%, and overlap with data used while iterating. For Stage 0 I had seen the assistant's reading of the two disputed calls before reviewing them, and I cannot confirm the review settings hid the model's answers throughout, so I do not call any review independent of the assistant beyond what `DECISIONS.md` A18 and A23 record.
- "Other" was used for 0 of 100 calls. That does not validate the taxonomy; the "Other above 10% triggers revision" safeguard is untested.
- The incident flag is an LLM judgment: 42 calls touch the outage, 18 have it as the main theme. In my sample it missed 3 of 20, so 42 is probably a floor. Use the 18 and 42 versions separately.
- Call dates are partly inconsistent with content, so per-account date-based before/after comparisons are not presented.
- Temperature 0 is not deterministic: reproducibility comes from the committed cache. A live re-run may differ.
- Model choice evidence for Stages 1 and 2 came from 15 calls on draft prompts, and the pre-written decision rule was overridden for Stage 0 (D7).
- About 25 comparisons in the sentiment analysis with no multiple-comparison correction; internal-versus-other differences are fragile.
- The notebook 04 figure check is closed (A23): the numbers appear at 3-decimal precision, and the one rounding mismatch (2.565) was fixed.
- Extras (Docker, Raspberry Pi, tailnet URL, Langfuse) are not built.

# Decision & Action Log — Transcript Intelligence take-home

Rule: nothing goes into the final submission that is not recorded here. Every entry states what was decided, why, what else was considered, and the known weakness, so it can be defended live.

Status key: LOCKED = decided by the candidate. OPEN = not yet decided.

---

## A. Actions taken (chronological)

| # | Date | Action | Output |
|---|------|--------|--------|
| A1 | 2026-10-28 | Read `assignment.md` in full. | Summary of 3 tasks, 3 deliverables, grading signals. |
| A2 | 2026-10-28 | Profiled all 100 meeting folders (read-only script, no data modified). | Counts, date range, durations, sentiment distribution, topic vocabulary. |
| A3 | 2026-10-28 | Derived call type by rule (see D1) and computed sentiment by type and month. | 27 support / 43 external / 30 internal. |
| A4 | 2026-10-28 | Built the "Assessment Navigator" artifact (private, for candidate orientation only; not a deliverable). | claude.ai artifact HGqhuC4inwMcdJ4wXQ7ZAA |
| A5 | 2026-10-29 | Candidate read two transcripts by hand (one low-scoring, one high-scoring). | Qualitative baseline for D2 and D3. |
| A6 | 2026-10-29 | Added transcript reader and decision log to the navigator. | Same artifact, new version. |
| A7 | 2026-10-29 | Fixed navigator bug: the meetings table, detail panel and reader showed no data. Cause: the reader code ran before `const esc` was defined (JavaScript temporal-dead-zone error), which stopped the page script. Fix: define `esc` before first use. Also escaped `<`, U+2028 and U+2029 in the embedded JSON so transcript text can never break the inline script. Verified by running the page script in node with a DOM stub: no errors, 100 table rows, 100 reader entries, counts 27/43/30, monthly means 3.68/2.78/3.83. | Navigator artifact version 3. No dataset content changed. |
| A8 | 2026-10-29 | Built the "Whiteboard" tab in the navigator for T1, D2a, D3a (education, evidence, recommendation, picker). Ran read-only Python (stdlib only; numpy, scikit-learn, nltk, vaderSentiment are not installed and nothing was installed) over all 100 meetings: (T1) rule labels plus flags from title keywords, support-desk opening lines and speakers, attendee counts, outage content; (D2a) provided-label shares by type, score vs sentence-balance correlation, customer vs employee negative share, first-third vs last-third trajectory, score residuals; (D3a) topic-string collapse, keyword-theme counts per type, theme overlap per call, text lengths. Not computed: clustering quality and stability, lexicon baseline. No decision was locked by this action. | Navigator "Whiteboard" tab; scratchpad scripts an1-an5.py, gen_board.py. |
| A8a | 2026-10-29 | Found and fixed a bug in the reader: the "customer" tag on speakers never matched, because it compared speaker names to email local parts (e.g. `g.fisk` vs "Gregory Fisk"). Now a speaker is a customer if the meeting has an outside attendee and the speaker's name is not among the aegiscloud.com invitees' names. The same flag is used in the D2a customer-side numbers. | `build.py` |
| A9 | 2026-10-29 | Read-only check of opening lines by derived type, to test whether the first utterances can separate support from external. Results: 6 of 27 support, 2 of 43 external and 0 of 30 internal openings match a "thank you for calling / support, this is / how can I help" pattern; the 2 external matches are the Blackridge and Cobalt "URGENT" calls, and the Northstar "ESCALATION" call opens "Thank you for holding… senior support". Most support calls introduce themselves as "this is X from Aegis support". Led to the D1 rewrite. | Revised D1. No dataset content changed. |
| A10 | 2026-10-29 | Rewrote D1 as pipeline Stage 0 after the candidate objected that the title rule and manual overrides were not a pipeline design. Updated this file and the navigator's Decision log tab. | D1 above. |
| A11 | 2026-10-29 | Retired T1 as a separate task (it became pipeline Stage 0, D1). Re-examined D2a and D3a for dependencies on Stage 0 and recorded them in section D. Asked a subagent to retire the T1 panel in the Whiteboard tab, add a "Pipeline so far" diagram, and add "How Stage 0 changes this" boxes to the D2a and D3a panels. No decision locked by this action. | Navigator Whiteboard tab; this file. |
| A12 | 2026-10-29 | At the candidate's request, re-weighed D2a, D3 and D3a against the end pipeline (new section B2). Checked rough product-area signal (regex over titles, summaries, topics: a module in 96 of 100 calls; 53 mention more than one) and total transcript size (141,357 words, about 190k tokens). Revised D1 (speaker side), D3 (discovery once, recurring classification), D2 (constraints), and replaced the D2a and D3a option sets. Candidate approved the revisions. D2a and D3a remain open. Asked a subagent to rebuild the Whiteboard and Decision log tabs. | This file; navigator. |
| A13 | 2026-10-29 | Locked D2a and D3a with all recommended options, at the candidate's instruction. Decided to keep the Whiteboard tab as a frozen record and to archive its reasoning in `docs/decision-defense.md` and a local snapshot, so the "why not X" answers survive outside the hosted artifact. Subagent asked to do the artifact and archive work. | This file; `docs/`; navigator. |
| A14 | 2026-10-29 | Checked the environment (read-only): Python 3.14.7, no data or LLM libraries installed, `uv` and `node` available, no Docker, no `ANTHROPIC_API_KEY`. Candidate chose OpenRouter for LLM access, locked D4 (skip synthetic data) and D5 (stack, repo, access). Wrote the phased execution plan (scaffold, Stage 0, Stages 1 and 2 in parallel, analysis, deliverables, extras). | This file. |
| A15 | 2026-10-29 | Phase 0 scaffold built by subagent and verified (18 offline tests passing, dataset untouched, no key in repo). Reviewed the Stage 0 prompt; found the title-leakage and prompt-after-the-answers problems. Candidate approved: withhold title from the LLM; run the prompt without the escalation sentence first. Propagating to code, prompt, README, docs, navigator. No live LLM call made yet. | D1 revised; `src/ti`, `prompts/stage0_v1.md`. |
| A16 | 2026-10-29 | Model research delegated to a subagent. One minimal connectivity call succeeded with the candidate's OpenRouter key (key never printed; spend limit on the key $8, about $1.22 used). Fetched the model list (420 models). Findings: the same model slug was served by different providers across calls, so provider pinning is required; Claude 5.x and GPT-6.x do not list `temperature` as a supported parameter (a temperature=0 request is accepted, but whether it is honoured is unverified), so run-to-run stability must be measured, not assumed. Coding-agent benchmarks (SWE-bench Pro, DeepSWE, Terminal-Bench) were treated as a weak prior and not used to rank. Shortlist: Claude Haiku 5.5 (Stage 0), Claude Sonnet 5.5 (Stages 1 and 2, discovery), GPT-6.1 Terra and Gemini 3.8 Flash as runners-up. Cost estimate (assumptions, not measured): about $7.3 per full pass with Haiku + Sonnet. Bake-off designed, not run. No model pinned yet. Reasoning record in `docs/model-selection.md`; raw table in `docs/openrouter-models.md`. Verified by main session: files exist, no key in docs, cost arithmetic reproduces from the stated assumptions. Not verified: benchmark figures (extracted through a page-summarising fetch tool, not checked against source pages). | `docs/model-selection.md`, `docs/openrouter-models.md` |
| A17 | 2026-10-29 | Ran the model bake-off via subagent (475 calls, $1.63 of the estimated $3.8; key balance about $5.15 afterwards). Main session verified: 30 tests pass; recomputed Stage 0 counts from the CSVs (Haiku 32 support / 38 external, Gemini 30 / 40 among all 100 incl. 30 internal; Haiku 5 title-rule disagreements, Gemini 3; models differ on 2 calls); read the openings of the 2 disputed calls. Found that the decision rule measured format, not correctness, and recommended overriding it. Candidate chose Gemini 3.8 Flash for all stages (D7). `.env` model keys set (key untouched). Stage 0 for Gemini now exists in cache for all 70 customer calls (`outputs/stage0_gemini.csv`). Escalation sentence NOT needed in the prompt: both models labeled the three escalation calls as support without it, so Stage 0 prompt stays `stage0_v1`. Bake-off prompts for Stages 1-2 are drafts only and will be replaced. | `docs/bakeoff-report.md`, `eval/`, `outputs/`, `cache/` |
| A18 | 2026-10-29 | Candidate completed the Stage 0 review in the Review Console (blind review was the default setting). 15 items: 3 where the LLM and the title rule disagree, 2 where Haiku and Gemini disagreed, 10 seeded sample agreements. Verdicts read back from the shared store and saved to `eval/stage0_review_verdicts.json`. Results: candidate agrees with Gemini on 15 of 15 and with the title rule on 12 of 15. All three title-rule disagreements (Blackridge URGENT, Cobalt URGENT, Northstar ESCALATION) were judged support, as the LLM said. Both calls where Haiku and Gemini disagreed (Northstar "Urgent: Detect Outage Impact", Quantum Edge "Renewal Concerns") were judged external, as Gemini said; the candidate left no notes. The 10 sampled agreements were all confirmed. **Stage 0 is FROZEN**: prompt `stage0_v1`, model per D7, final labels in `outputs/stage0_final.csv` (support 30, external 40, internal 30). Caveats for the deck: 15 reviewed items is small, and only 10 of the 55 calls where the LLM and the title rule agree were checked (10 of 10 correct does not rule out an error rate of about 25% by the rule of three); the candidate had seen the main session's reading of the two disputed calls before reviewing, so that part is not fully independent; by the candidate's verdicts the title rule is wrong on 3 of 70 customer calls (4.3%). | `eval/stage0_review_verdicts.json`, `outputs/stage0_final.csv` |
| A19 | 2026-10-29 | Candidate delegated approval of taxonomy and anchors to the main session. Main session finalised Taxonomy v1 (8 themes + Other, product area, incident field) and accepted Anchors v1 with schema tightening (D8). Verified before this: Stage 1 pilot numbers (stability 0.36/0.38; theme counts by type) recomputed from `outputs/stage1/`. Anchors Approval page had been overwritten by the Taxonomy Approval page (two subagents published to the same URL) and was rebuilt as a new artifact; the two approval pages were then not used for approval. Launching the full Stage 1 and Stage 2 runs with a subagent. | D8 |
| A20 | 2026-10-29 | Stage 1 (prompt `stage1_v1`, taxonomy v1) and Stage 2 (prompt `stage2_v1`, anchors v1) run on all 100 calls with Gemini 3.8 Flash per D7, by subagent; spend about $1.07, key balance about $3.16. Main session recomputed: theme counts, Other share, Stage 2 means by Stage 0 type, 62 tests passing. Results (outputs in `outputs/stage1/`, `outputs/stage2/`, metrics in `outputs/stage12_metrics.json`): **Stage 1:** 100 of 100 valid, no retries; themes Product Adoption 24, Incident and Outage 18, Technical Integration 16, Renewals 14, Internal Planning 12, Onboarding 7, Competitive 5, Billing 4; Other 0%; incident flag on 42 calls (18 external, 14 internal, 10 support); stability on a 20-call sample: primary theme, product area and incident identical on 20 of 20, tag Jaccard 0.95. **Stage 2:** 100 of 100 valid first attempt, all per-turn labels complete, 100 exact quotes; call-score mean by type support 2.93, external 3.95, internal 3.50 (provided score: 2.83, 3.85, 3.42); stability on the same 20 calls: call-score MAD 0.075 (17 of 20 identical, max difference 0.5), per-turn label agreement 92.9%; sentence-level agreement with the provided labels 79.6% over 4,313 turns (the model labels 68.1% of turns neutral vs 56.3% provided; 444 provided-positive turns read as neutral); Pearson with the provided call score 0.963, mean absolute difference 0.23 (consistency with an upstream AI output, not accuracy). **Caveats found in review:** (1) Other share of 0% does not validate the taxonomy; models rarely use an "Other" bucket, so the drift-detection design (Other above 10% triggers revision) is untested here. (2) The incident flag covers 42 calls but only 18 have Incident and Outage as primary theme; the flag means "touches the incident, as a major part" and is generous (the one flagged call dated 2026-03-09, Keystone Health renewal planning, discusses the outage in a segment while the earliest outage-titled call is 2026-03-10: a dataset timestamp inconsistency and a borderline flag). Analyses must report "core incident" (primary theme) and "touches incident" separately. (3) 40 of 100 Stage 1 quotes exceed the prompt's 30-word limit and 12 of 100 Stage 2 quotes exceed 25 words; the quotes are verbatim, only the length rule is not followed. (4) Deviation from the frozen Stage 2 prompt: the input header now states the number of turns (prompt text and anchors unchanged); recorded here as an input-format addition. (5) Stage 2 schema tightened (half-step trajectory; one per-turn label per turn with one retry). (6) Review Console for the hand-checks published (Stage 1-2 Review Console), blind by default, 15 Stage 2 calls and 20 Stage 1 calls, seeds 2026 and 1029, bake-off sample excluded. Hand-checks are not done yet. | `outputs/`, `src/ti/stage1.py`, `src/ti/stage2.py`, `eval/stage12_report.py` |
| A21 | 2026-10-29 | Phase 3 analysis by two subagents (no LLM calls, no spend). Both were prevented by the harness from writing report files, so they returned the content as text; the main session recomputed the key figures (theme by type table, theme score means, competitor-mention counts, Stage 2 means by type and month, March split, support-minus-external gap) and wrote `docs/analysis-sentiment.md`, `docs/analysis-themes.md`, `docs/analysis-candidates.md` itself, marking which figures were recomputed (R) and which come from the analysis code (S: bootstrap intervals, permutation tests, centroid recovery, account-level and index figures). Code and outputs: `src/ti/analysis/`, `outputs/analysis/`. 79 tests pass. Locked D6 (bonus insights). Not yet done: candidate's hand-checks (Stage 1-2 Review Console), notebooks, deck, video script. | `docs/analysis-*.md`, `outputs/analysis/` |
| A22 | 2026-10-29 | Phase 4 deliverables built by subagents after a usage-limit interruption (builds stopped and resumed; no data lost). **Notebooks:** `notebooks/00` to `06`, executed in replay mode (no key, no spend) with HTML copies in `notebooks/html/`, covered by `tests/test_notebooks.py`; main session checked: no error outputs; some notebook 04 figures (such as -1.02, 2.57, 3.91) were not found in the exact form searched and are on the final-review list. **Explorer:** self-contained `app/explorer.html` (built by `app/build_explorer.py`), published as a private artifact (https://claude.ai/artifact/3RKUQFK2m1CURZcDjNNend); `tests/test_explorer.py` recomputes the embedded numbers; tested in headless Chrome by the subagent, not by the main session. **Deck:** https://claude.ai/artifact/3P2fxeVuVfihK9hgbXNyCM, 22 slides (16 main, 6 appendix), speaker notes with timing and sources; the Stage 1 and Stage 2 hand-check section is marked PENDING. Main session corrected two overstated phrasings in the deck: "under my direction" became "under my delegation" (D8), and "My blind review" became "My review", with a spoken caveat that the candidate had seen the assistant's reading of the two disputed calls first (A18). Figures that come from the analysis code and were not recomputed by the main session are flagged in the speaker notes. 89 tests pass. Git repository initialised by the candidate (no commits yet); `.env` is ignored and no key string appears in any tracked file. Not done: hand-checks (candidate), README rubric map, video script and demo checklist, final fresh-eyes review, extras (Docker, Raspberry Pi, tailnet, Langfuse). | `notebooks/`, `app/`, deck artifact |
| A23 | 2026-10-30 | Candidate completed the Stage 1 (20 calls) and Stage 2 (15 calls) hand-check in the Stage 1-2 Review Console. Main session read the raw review docs from the console db (`reviews_s1`, `reviews_s2`), joined the frozen model outputs with `eval/build_stage12_verdicts.py` (reproducible, model answers never shown to the reviewer) and wrote `eval/stage1_review_verdicts.json` and `eval/stage2_review_verdicts.json`. Results: Stage 1 theme 20/20, product area 19/20, incident flag 17/20 (all 3 misses: candidate flagged, model did not, so the flag is under-inclusive in the sample); Stage 2 all 15 within 0.5, 9 exact, mean gap 0.20, rank correlation 0.91, customer-side gap 0.30 on 10 calls, model higher on 5 of the 6 differences. Fixed `stage2_handcheck` to use rank correlation (scipy is not installed). Re-executed notebooks 02 and 03 (no errors, HTML refreshed), 89 tests pass. Deck v13: independent-check slide, validation appendix and sentiment notes updated; the 'blind' claim stays out because blind mode is unconfirmed. Notebook 04 number check closed: -1.02, 3.91 and 3.62 appear (as -1.017, 3.908, 3.615); the within-March outage mean is 2.565 exact (59/23), the notebook sentence now shows 3 decimals instead of double-rounding to 2.56, so 2.57 in docs and deck is right. Effect on earlier caveat: 'incident flag is generous' is now 'incident flag is a range, core 18 to touches 42, and likely a floor'. |
| A24 | 2026-10-30 | The Explorer link in A22 and the README (1Aje...) was dead: that artifact is not in the user's account (the user reported it; `Artifact list` confirmed). Rebuilt `app/explorer.html` (no LLM calls) and published a new private artifact, https://claude.ai/artifact/3RKUQFK2m1CURZcDjNNend, by subagent in its own folder; `tests/test_explorer.py` passes and headless Chrome showed all five tabs filled with no JS errors at 1280 and 500 px. Not checked in the real viewer. Links in README and DECISIONS replaced. Lesson: verify every artifact link with `list` before claiming it exists. |
| A25 | 2026-10-30 | Fresh-eyes review by a read-only subagent against assignment.md. Recomputed ~30 headline numbers from outputs: no mismatches. Findings and actions: (1) 'blind'/'independent' wording removed from notebooks 00-06, their HTML, `nbhelpers.py` and docs; hand-checks are described as 'my own review, small, not confirmed blind'. (2) 'Incident flag is generous' replaced everywhere (notebooks, `sentiment.py`, `findings.json` regenerated with no numeric change, explorer v2) by 'an LLM judgment, partly definitional; missed 3 of 20 and never over-flagged, so 42 is probably a floor'. (3) Stale docs fixed: `model-selection.md` status (LOCKED, D7), `decision-defense.md` (March 2.94, Stage 1 hand-check, 'not run yet' lines). (4) `.gitignore` now excludes `.DS_Store` and `previous-session.jsonl`. (5) Deck v14 (readback confirmed order: 15 main slides at 24.5 min of cues, then appendix models, a-log, a-s0, a-valid, a-anchors, a-gloss): softened competitor and blast headlines (co-occurrence, not causation), Ridgeline/Northstar and 'seven'/'nine' slips, per-theme example slide added, model-choice slide moved to appendix, Q&A-prep slide removed from the deck (answers stay in `docs/decision-defense.md`), file-path footers moved to notes. Open for the candidate: record the video (show one visible replay stage run), export the deck to PDF/PPTX into the repo, make the first commit. |
| A26 | 2026-10-30 | Video script beat 6 now shows the pipeline running: `eval/demo_replay.py` runs one call (default index 41, a support case about the outage) through Stages 1 and 2 in replay mode, with no key and no network, writing nothing (`Guard(refresh=False)`). Chosen over `python -m ti.stage1 --limit` because the stage CLIs overwrite the full-run record files in `outputs/`. Beat 5 competitor sentence reworded to co-occurrence. First git commit made at the candidate's request (see git log). |
| A27 | 2026-10-30 | Repo published at https://github.com/Srikanth-Banda/transcript-intelligence for reviewers. A first push (public repo) had included the raw `dataset/` and presenter prep in history, so the candidate deleted that repo and created a new one, and a single clean commit was pushed (history was never rewritten on the remote). Kept out of the repo, local only and git-ignored: `dataset/` (the assignment provider's data; README says where to place it), and `private/` (presenter Q&A guide, video script, Navigator snapshot, which embeds transcripts), plus `.env` and `previous-session.jsonl`. In the repo: `DECISIONS.md`, notebooks and HTML, explorer, prompts, outputs, `cache/`, tests. Earlier log entries that cite the private files refer to local copies. |

AI assistance disclosure: profiling, the navigator and this log were produced with Claude Code (Claude Sonnet 5.5) under the candidate's direction. The assignment explicitly permits LLM tools.

---

## B. Facts about the dataset (verified by script, A2/A3)

- 100 meetings, 6 JSON files each (`meeting-info`, `transcript`, `summary`, `speakers`, `speaker-meta`, `events`). Dates 2026-02-03 to 2026-04-28.
- 4,313 transcript sentences; 141,357 words. Median 41 sentences, 29.6 minutes.
- Provided `sentimentScore` ranges 1.4 to 4.9 (median 3.5). Sentence-level `sentimentType` counts: neutral 2,428, positive 1,163, negative 722.
- Correlation between provided score and (share positive minus share negative) per meeting: 0.94.
- Provided `topics`: 351 distinct strings across 100 meetings, heavily overlapping.
- Mean provided score by derived type: support 2.94, external 3.71, internal 3.42. By month: Feb 3.68, Mar 2.78, Apr 3.83.
- All internal addresses are `@aegiscloud.com`; 30 meetings have no external attendee.
- No field in the data states call type, speaker role, or customer tier.

Caveat to state in the deck: n=100 and the data appears synthetic (one fictional company, repeated score values). Trends are directional, not statistically proven.

---

## B2. Decision criteria (added 2026-10-29, A12)
The end product is Transcript Intelligence: a tool that keeps running as calls arrive and serves support leaders, sales managers, product managers and engineering leads. Every pipeline decision is judged against these criteria, in addition to what is easy to defend in a panel:
1. **Stable over time.** Outputs must not change meaning when new calls arrive. No step may need re-deriving from scratch each run.
2. **Owned and actionable.** A category or metric earns its place if a named stakeholder could act on it.
3. **Evidence-linked.** Every label or score carries an evidence quote so a leader can click through to the call.
4. **No hidden upstream dependence.** Stages read the transcript and metadata we control. Provided summaries, topics and scores are baselines to compare against, not inputs.
5. **Validation that scales.** Prefer designs where agreement can be measured on many items, plus a small hand-check.
6. **One method over time.** Trends are only valid if the same scorer measured every point: pin model and prompt versions, temperature 0, cache per transcript, stability check, re-score everything on any change.
7. **Defined for every call.** A primary metric must exist for all 100 calls, not only a subset.
8. **Cost and moving parts.** Fewer providers and dependencies; state the cost model (about 3 to 4 LLM calls per transcript across stages; all 100 transcripts are about 190k tokens).

---

## C. Decisions

### D1 — Call-type labels (Pipeline Stage 0) — LOCKED, revised 2026-10-29
Revision note 2 (2026-10-29, A15): at review of the Stage 0 prompt, the candidate approved withholding the title from the LLM. The title rule is the cross-check, and a model that sees "Support Case #9279" would lean on the same signal, so agreement would carry less information and a disagreement would mean less. A production deployment may have no such title either. The model now sees only attendee counts and the opening. The prompt also does not name urgent or escalated calls as support at first: that sentence was written after inspecting the three escalation calls, so those calls would not test the prompt. Prompt iteration plan: run v1 without it; add it only if the three calls come out wrong (as v2, with the reason logged); freeze the final version; report both versions' results; state in the deck that iterating on the same ~70 calls we validate on risks overfitting.

Revision note 1: the first version of D1 was a title-only rule. The candidate challenged it (2026-10-29): the rule worked only because this dataset has case numbers in titles, and the three manual overrides proposed in T1 were a one-off judgment, not a pipeline step. D1 is replaced by the design below. The title rule is kept only as a cross-check.

**Decision:** Call type is assigned by Stage 0 of the pipeline, in three steps.
1. **Deterministic check.** If no attendee has an email outside `@aegiscloud.com`, the call is `internal`. No LLM involved. (30 calls.)
2. **LLM classification for calls with a customer present (70 calls): `support` or `external`.**
   - Input: number of internal and external attendees and the first ~8 utterances with speaker names. **The meeting title is withheld from the model** (revised 2026-10-29, see revision note 2). The full transcript is not sent (cost, and to keep topic content from biasing the label).
   - Definitions given in the prompt:
     - `support`: a customer brings a specific problem or request and an Aegis support-desk agent handles it.
     - `external`: a scheduled relationship call between an Aegis account, sales or customer-success person and a customer (renewal, planning, onboarding, review, feedback).
   - Output: JSON with `label`, one `evidence_quote` taken from the opening, and `confidence`. Added 2026-10-29: Stage 0 also outputs a per-speaker side (`customer` or `aegis_staff`), needed by Stage 2 (see D2). The deterministic version uses the invitee names (see A8a); the LLM output is checked against it.
   - Model: Claude Haiku 5.5 (`claude-haiku-5-5`), temperature 0. Chosen because this is a short, bounded decision where cost and speed matter more than depth. Not yet run; any capable model would serve and the design does not depend on this choice.
3. **Cross-check and review.** The old title rule ("Support Case" in title = support) is computed as a baseline. Every call where the LLM and the title rule disagree goes to a review queue and the candidate decides. A sample of 10 agreements is also read. Report: LLM-vs-title agreement rate, and how often the candidate agreed with the LLM on disagreements.

**Why:** The assignment says handling missing call-type labels is evaluated. Internal is decidable with certainty from metadata, so it gets no model judgment. The support-vs-external distinction is about what the call is for, which the opening of the call shows and a title may not. Evidence from our data (A9): the Blackridge "URGENT", Cobalt "URGENT" and Northstar "ESCALATION" calls open with support-desk lines ("Thank you for calling Aegis Cloud Security support", "senior support") yet the title rule calls them external. A greeting keyword match is not enough (only 6 of 27 support calls open with "thank you for calling" or similar), which is why a model reading the opening is used. In a real deployment a title like "Support Case #…" would often not exist, so a classifier based on the opening generalises better than a title rule.

**Alternatives considered:**
- Title rule alone: brittle; misses 3 of the 70 customer calls here and depends on a naming convention.
- LLM on all 100 calls: adds error on internal calls where metadata is certain.
- Manual overrides of the three escalations: not reproducible, not a pipeline step. Rejected.
- A fourth label "escalation": breaks the three call types the assignment names. Escalations are treated as a note in the deck, not a label.

**Known weaknesses:**
- No ground truth exists; validation rests on the candidate's own reading.
- The LLM can be wrong on borderline calls (e.g. a support-style call that begins like a meeting).
- Not yet run. Prediction, not result: the three escalation calls will show up as LLM-vs-title disagreements.
- The 29 flagged calls and the figures support 2.94 to 2.83, external 3.71 to 3.85 (if those three are relabeled) come from the Whiteboard analysis (A8) and must be re-derived from the pipeline output, not quoted.

### D2 — Sentiment method — LOCKED (2026-10-29)
**Decision:** Do not rely only on the provided score. Re-score each meeting independently, then compare with the provided `sentimentScore` and report the disagreements.

**Why:** The provided score and sentence labels are already a pre-computed AI output and correlate 0.94 with each other, so they are not independent evidence. Plotting them alone would be shallow. An independent score lets us say where the provided one misleads, which is the kind of judgment the panel asked for. The disagreements are candidate slides.

**Alternatives considered:** Use provided score only (fast, but no added insight); replace it entirely (loses a useful baseline).

**Method details are still OPEN:** which independent scorer (LLM rubric score vs. lexicon vs. both), what scale, and how to treat sentence-level versus meeting-level. To be recorded as D2a once chosen.

**Known weaknesses:** Our re-score will also be an LLM or model judgment with its own bias. Mitigation: hand-check a sample and report agreement.

**Pipeline constraints added 2026-10-29 (A12), not options:** the scorer reads the transcript only. It must not see the provided score, summary or topics (independence), nor the call-type label (leakage). Same method across all calls: pinned model and prompt versions, temperature 0, cache per transcript, stability run on a sample, re-score everything on any change. Results are compared within call type, and reported with Stage 0 labels and with title-rule labels as a sensitivity check.

### D3 — Categorization approach (pipeline Stage 1) — LOCKED, revised 2026-10-29
Revision note: the first version was "embed each transcript and cluster, then an LLM names and assigns". The candidate asked for decisions to be weighed against the end pipeline (B2). Clustering with a k chosen on 100 calls is a one-time discovery technique, not a recurring stage, and embeddings add a second provider (Claude has no embedding model). The design below replaces it.

**Decision:** Two parts.
1. **One-time taxonomy discovery (offline, on this sample).** Propose candidate themes from the calls (LLM-led over the transcripts or their summaries, then human merge), define each theme in one line with examples, and freeze a versioned taxonomy. Embedding plus clustering is an optional cross-check only, not a required step.
2. **Recurring classification (the pipeline stage).** An LLM reads each transcript and assigns it to the frozen taxonomy: one primary theme, up to two tags, a product area, and an evidence quote per assignment. Calls that fit no theme go to an `other / new theme` bucket; a growing bucket triggers a taxonomy revision, which bumps the version and re-runs everything.
3. **Validation.** Hand-check a sample, and compare against the provided topics as a baseline (do we agree with the upstream tagging?).

**Why:** Meets criteria 1, 2, 3, 4 and 8 in B2. New calls are classified against a stable taxonomy, so dashboards do not shift. Evidence quotes make every number clickable. The discovery step uses the same LLM already in the pipeline.

**Alternatives considered:**
- Re-cluster every batch: categories change under the dashboard. Rejected.
- Embed and cluster as the main method (the first version of D3): needs a second provider, unstable at n=100, cannot classify one new call without refitting. Kept only as an optional cross-check.
- Pure keyword rules: brittle; the 351 provided topic strings show how fragmented wording is.
- Hand-written taxonomy with no discovery step: imposes our assumptions on the data.

**Known weaknesses:** Taxonomy is judged by us and may reflect our framing. Mitigation: definitions with examples, hand-check, report agreement. The "other" bucket and versioning handle drift but need a human to act on them. Small n (100) means rare themes will have few examples.

### D4 — Synthetic data — LOCKED (2026-10-29)
**Decision:** Do not generate synthetic data unless a specific claim needs it. If any is generated, label every item as synthetic, state why it was needed, and keep it out of the headline numbers.
**Why:** The 100 transcripts already carry a cross-type story (the March Detect outage). Synthetic data adds a disclosure burden and can look like padding. The assignment allows it but does not require it.
**Alternatives considered:** Generate more transcripts to test scale (not needed to demonstrate the approach; scale is argued from the cache and the per-call cost model instead).
**Known weakness:** n=100 limits statistical claims. State trends as directional.

### D5 — Stack, repo and LLM access — LOCKED (2026-10-29)
**Decision:**
- **Language and environment:** Python 3.12 in a `uv` environment (the system Python 3.14 is too new for some libraries). Libraries: pandas, matplotlib, pydantic, the OpenAI SDK, python-dotenv, Jupyter, pytest.
- **LLM access:** OpenRouter (OpenAI-compatible API) using the candidate's own key, read from a git-ignored `.env`. The key is never printed, logged or committed. Model slugs and pricing are confirmed against OpenRouter's model list at build time and recorded. Models planned: a small fast model for Stage 0 (Claude Haiku class) and a stronger model for Stages 1 and 2 (Claude Sonnet class). Exact slugs, and provider pinning (no fallback providers, so one method across all calls), are recorded in this file when set.
- **Repo:** the project root. `src/ti/` holds the pipeline (load, llm client, stage0, stage1, stage2, schemas); `prompts/` holds versioned prompt files; `cache/` holds raw LLM outputs, committed; `notebooks/` holds one narrative notebook per stage plus trends and insights, each citing its decision; `eval/` holds hand-check sheets and agreement scripts; `app/` holds a self-contained HTML explorer for the video; `deploy/` holds Docker, Raspberry Pi and Langfuse work, done last.
- **Replay mode:** every LLM call is cached by a hash of the input, stage, prompt version, model slug and parameters. With the cache committed, an evaluator can re-run the notebooks offline without an API key. A cache miss in replay mode is an error, not a silent live call.
- **Tracing:** an optional tracing hook is a no-op by default. Self-hosted Langfuse is added in the extras phase and used on a live traced sample, not claimed for the original run.
- **Order of work:** core deliverables first (pipeline, analysis, deck, notebook, video). Extras (Docker, Raspberry Pi, tailnet URL, Langfuse) come last, after the core is frozen. No graded deliverable may depend on the hosted URL.

**Why:** Meets B2 criteria 1, 5, 6 and 8: replay and pinned versions give a stable, single method over time; a committed cache makes the work checkable; OpenRouter gives access to several models through one client without a second provider SDK.
**Alternatives considered:** Anthropic API directly (no key available); Claude Code subagents as the LLM (no live pipeline code, cache-only); pip/venv on Python 3.14 (library compatibility risk).
**Known weaknesses:** OpenRouter may route the same model slug to different providers, which can change outputs; mitigated by provider pinning and recording the returned model and provider in each cache entry. Evaluators who want live re-runs need their own key. Model slugs unconfirmed until the key is set.

### D7 — LLM model for all stages — LOCKED (2026-10-29)
**Decision:** `google/gemini-3.8-flash` via OpenRouter for Stages 0, 1 and 2 (and taxonomy discovery), provider pinned to `google-ai-studio` with fallbacks off, `temperature=0`, `seed=7`, reasoning effort `low`. Recorded in `.env` (`TI_MODEL_STAGE0/1/2`, `TI_PROVIDER_ORDER`). Any change of model, provider, prompt or settings means re-running the affected stage for all calls (B2 criterion 6).

**Why:**
- It was the only shortlisted model that lists both `temperature` and `seed` as supported, and gave byte-identical Stage 0 output across all three runs of the determinism probe (Stage 2: identical on 2 of 3 transcripts; Sonnet 0 of 3, Terra 0 of 3). Criterion 6.
- Stage 0 (70 customer calls): 100% schema-valid, 98.6% exact quote validity (2 of 140 quotes differ from the opening only in punctuation or spacing; 100% after normalising), 100% run-to-run label agreement, 3 disagreements with the title rule (the three escalation calls). Haiku had 5 disagreements, including two calls that, on the main session's reading of the openings, are account-manager calls (Northstar "Urgent: Detect Outage Impact", Quantum Edge "Renewal Concerns"). Those two labels are still to be confirmed by the candidate in the Stage 0 review.
- Stages 1 and 2 (15-call draft-prompt sample): valid output and quote validity 100%, run-to-run call-score difference 0.00, cost $0.225 vs $0.836 for Sonnet 5.5; the sample could not separate the two on quality (both correlate 0.96 with the provided score).
- One model, one client, one provider pin across all stages (criterion 8). The extra Stage 0 cost over Haiku was $0.126 on 140 calls.

**Rejected:** Haiku 5.5 for Stage 0 (the rule's winner; see override below), Sonnet 5.5 for Stages 1 and 2 (about 3.7x the cost, no measured gain, temperature 0 not honoured), GPT-6.1 Terra (fell back to plain JSON mode on all Stage 2 calls, so its numbers are confounded), Opus-class and other families (no evidence we need them).

**Override of our own decision rule:** the pre-registered rule picked Haiku for Stage 0 and Gemini for Stages 1-2. Its "quality" score averaged schema validity, quote validity and run-to-run stability, so it measured format, not correctness; every model cleared every threshold and the rule reduced to "cheapest". The candidate chose to override it for Stage 0 on the grounds above. Disclose this in the deck as a design flaw found and fixed in review, not hidden.

**Known weaknesses:** n=15 for Stages 1-2 on draft prompts; the sample is the same data we validate on; there are no gold labels (the title rule is imperfect and the provided score is an upstream AI output, so agreement means consistency, not correctness); `temperature=0` does not guarantee identical output, so reproducibility comes from the committed cache, not from re-running; the quote check tolerates no punctuation drift, so Gemini loses 1.4% on exact match; the model-choice evidence for tone and JSON reliability is indirect. Sonnet 5.5 remains the hedge if the final prompts separate models more than the drafts did.

### D8 — Taxonomy v1 and anchors v1 (frozen under delegation) — LOCKED (2026-10-29)
**Delegation note:** the candidate delegated the approval of the draft taxonomy and the draft anchors to the main session ("do the best judgement call instead of seeking my approval"). The decisions below are the main session's judgments, made from the pilot evidence (`docs/stage1-discovery.md`, `outputs/stage1/`) and `prompts/stage2_v1.md`. The candidate has not reviewed them line by line and keeps the right to veto or change them; any change means re-running the affected stage for all calls. The deck must say the taxonomy was LLM-proposed and finalised under this delegation. The candidate's own validation remains the hand-checks (A19).

**Taxonomy v1** (Stage 1; theme = what kind of conversation, product area = which module, incident = cross-cutting thread):
1. **Commercial Renewals and Retention** — renewals, contracts, pricing and SLA negotiation, churn risk, expansion deals. Owner: account manager / sales manager. If a call is mainly about product adoption with renewal as an aside, use theme 2.
2. **Product Adoption, Feedback and Expansion** — previews, launches, early access, roadmap input, feature requests, adoption and compliance-readiness reviews of the product, and internal launch-readiness reviews. Owner: product manager, customer success. (Renamed from "Compliance Product Adoption and Expansion": the module belongs in product area.)
3. **Incident and Outage Response** — war rooms, root cause, remediation plans, customer impact assessment, incident communication, postmortems, reliability reviews. Owner: engineering lead, support lead. A single customer's technical fault that is not a platform incident belongs in theme 4.
4. **Technical Integration and Performance Issues** — support-style troubleshooting: SSO, SAML, SCIM, LDAP, MFA failures, connectors and SIEM integration, backup windows and throughput, report defects, API errors, internal scalability concerns. Owner: support lead, engineering. (Merges the pilot's Identity and Backup themes: both were module-flavoured, and module is a separate field.)
5. **Onboarding and Implementation Scoping** — kickoffs, deployment planning, architecture scoping, setup workshops. Owner: customer success / solutions (the pilot's owner "support lead" had no support calls).
6. **Billing and Usage Disputes** — invoices, overages, seat counts, billing adjustments. Owner: support lead with finance operations (the pilot's owner "sales" did not match its all-support calls). Small (about 4 calls); kept because it is distinct and actionable; flag as small.
7. **Competitive Strategy and Win/Loss** — competitive intelligence, battlecards, win/loss analysis, and customer-facing calls where the customer is evaluating alternatives. Owner: sales leadership, product. (Definition widened from the pilot's internal-only version.)
8. **Internal Planning and Delivery Cadence** — standups, sprint planning, retros, all-hands, design and roadmap syncs with no customer or incident focus. Owner: engineering leads. (Added: 13 of the pilot's 15 "Other" calls were this; leaving them in Other would hide a real category and break the 10% Other limit.) If a meeting is mainly an incident, use theme 3.
- **Other / new theme:** only if no theme fits. More than 10% of calls in Other triggers a taxonomy revision (new version, full re-run).
- **Tags:** up to two further themes from the list per call, besides one primary theme.
- **Product area (primary, one):** Detect, Comply, Protect (includes backup), Identity, Platform/General.
- **Incident field:** `incident = "2026-03-detect-outage"` or null. Set when the call's main purpose, or a major part of it, is the March 2026 Detect event-processing pipeline outage (cause, impact, remediation, customer communication or aftermath). This is a separate field so the outage story is visible across support, external and internal calls instead of living inside one theme.

**Why:** B2 criteria 2 and 3 (each category has an owner who can act and carries evidence quotes), 1 (a frozen versioned list), and the finding that discovery is unstable (run-to-run overlap 0.37, only 4 themes matched above 0.5), which makes the human or delegated judgment, not the raw LLM proposal, the real taxonomy. The incident field serves tasks 2 and 3 (cross-type story).

**Anchors v1** (Stage 2): `prompts/stage2_v1.md` accepted as drafted, all 13 design choices accepted, with two additions. (a) The pipeline tightens `Stage2Out` so trajectory values must be half steps, and enforces one `per_turn` entry per turn (retry once, then record as failed), closing the mismatches the draft listed. (b) The tie-break "take the lower level when a problem is still unresolved at the end" is accepted knowing that it biases borderline calls downward and mixes tone with outcome; this is disclosed, and the analysis reports score distributions with half-step calls identified. Other disclosed risks: churn signals at level 2 surface through the evidence quote and later analysis, not through the score; courtesy counted as neutral may under-read warm staff acknowledgements.

**Rejected:** keeping the pilot's module-named themes (duplicates the product area field), leaving routine internal meetings in Other, one theme per call with no incident field (hides the outage story), rewriting the anchors to separate tone from outcome (would add a field and more complexity than the take-home warrants; noted as future work).

**Known weaknesses:** both artifacts were derived from the same 100 calls they will be applied to; the taxonomy is partly shaped by the pilot assignment; no gold labels; the candidate's hand-check is the only independent validation and is small (15 calls for scoring, 20 for categories).

### D6 — Bonus insights (Task 3) — LOCKED under delegation (2026-10-29)
**Decision:** Present three insights as one connected "account risk" story, plus one described idea.
1. **Competitive intelligence** (product managers, sales leadership): 31 of 100 calls name a competitor (SentinelShield 22, VaultEdge 12, CyberNova 8, Fortiguard 3), and competitor-mentioning calls are more often outage-related than the average call.
2. **Outage blast radius** (engineering, support, executives): 22 of 32 customer accounts had an outage-related call across all three call types; tone about a point lower in outage-touching calls in every type.
3. **Churn early-warning list** (sales managers): a transparent 0 to 4 index on 40 external calls that ranks 11 accounts for human follow-up; presented as a ranked list, not a prediction.
4. **Described only, not built:** commitment tracking (112 staff promises with time phrases; only 42 have a later call with the same account, so follow-through can barely be checked).
**Not presented:** support-to-engineering loop (repeat contacts are about different issues) and the coaching signal (confounded: agents apologise more to unhappy customers).

**Why:** ranked by impact, evidence strength, non-obviousness and build cost in `docs/analysis-candidates.md`; the first three share data and form a coherent story (the outage made competitors live objections and put specific accounts at risk), which suits a 30-minute leadership presentation better than six disconnected ideas. All three are possible only because the pipeline produces structured fields (theme, incident, scores, evidence quotes).
**Rejected:** see "Not presented" above and the reasons in `docs/analysis-candidates.md`.
**Known weaknesses:** no outcome labels, so the churn list is unvalidated; competitor names came from a proper-noun scan plus manual check, not a list; the incident flag is generous; call dates are partly inconsistent with content, so date-based before/after comparisons are not used. Chosen by the main session under the candidate's delegation; the candidate may veto.

---

## D. Still OPEN

| ID | Question | Status |
|----|----------|--------|

D2a and D3a are locked above (A13). Earlier picks made in the Whiteboard tab against the first option sets were void.

### D2a — Sentiment scoring details (pipeline Stage 2) — LOCKED (2026-10-29)
The candidate accepted the recommended option in each group. The full option set, with pipeline-fit reasoning, is preserved in the navigator's Whiteboard tab and in `docs/decision-defense.md`.

**Decision:**
- **Method:** one structured LLM pass per transcript returning a call score 1–5 against written anchors, a label per turn, a start-vs-end trajectory, and an evidence quote.
- **Primary unit:** the whole-call score, defined for all 100 calls. For the 70 customer calls, also a customer-side score and the trajectory.
- **Scale:** 1–5 with written anchors (comparable with the provided score).
- **Validation:** sentence-level agreement with the 4,313 provided labels, a hand-check of 15 calls (5 per call type), and a stability re-run on a sample.
- **Fixed constraints (from D2):** the scorer reads the transcript only (no provided score, summary or topics; no call-type label). One method for all calls: pinned model and prompt versions, temperature 0, cache per transcript; any change means re-scoring everything. Compare within call type; report with Stage 0 labels and with title-rule labels as a sensitivity check. Uses the speaker side from Stage 0.

**Why (criteria in B2):** 3 evidence quote on every score; 4 independent of the upstream AI output; 5 sentence-level agreement can be measured on thousands of turns, not 100; 6 one pinned method keeps the trend valid; 7 the whole-call score exists for every call; 8 reuses the Stage 0 client and JSON format.

**Rejected:**
- Two separate LLM passes: more cost and the two granularities can disagree.
- Pretrained sentiment classifier: no evidence quotes, extra dependency, trained on general text rather than support calls.
- Word list: technical support vocabulary ("failure", "outage") reads negative regardless of mood; extra dependency.
- Customer-side as the primary unit: no score exists for the 30 internal calls.
- Continuous −1 to +1 scale and three classes: not comparable with the provided score, or too coarse.
- Hand-check only: validates about 15 items.

**Known weaknesses:** the scorer is an LLM and has its own bias; the provided labels are themselves an AI output, so agreement means "consistent with", not "correct"; 15 hand-checked calls is a small sample; per-turn labels are noisy; model and prompt versions must be pinned and recorded at build time. Not yet run.

### D3a — Categorization details (pipeline Stage 1) — LOCKED (2026-10-29)
The candidate accepted the recommended option in each group. The full option set is preserved in the Whiteboard tab and in `docs/decision-defense.md`.

**Decision:**
- **Input to Stage 1:** the transcript itself. The provided summary, topics and title are a comparison baseline only.
- **Taxonomy lifecycle:** one-time discovery, a frozen versioned taxonomy, then recurring classification of each call with an `other / new theme` bucket (see D3).
- **Discovery method:** LLM-led over the calls, followed by a human merge. Embeddings plus clustering are an optional cross-check only.
- **Structure:** two fields, `theme` and `product area` (Detect, Comply, Identity, Protect, backup).
- **Labels per call:** one primary theme and up to two tags.
- **Fixed constraints:** one shared taxonomy across call types; every assignment carries an evidence quote; versioned taxonomy, and a revision re-classifies every call; each category must pass the actionability test (a named stakeholder could act on it); the deck shows 6–8 categories, each with a one-line definition and examples; hand-check 20 assignments and compare with the provided topics as a baseline; Stage 0 type is a slicing column, never an input; sanity check that billing and integration themes concentrate in support, renewal in external, sprint planning in internal.

**Why (criteria in B2):** 1 a frozen taxonomy keeps dashboards stable; 2 each category and each product area has an owner; 3 evidence quotes; 4 no dependence on the upstream summary; 5 hand-check plus baseline comparison; 8 no second provider needed.

**Rejected:**
- Provided summary and topics as the input: ties the pipeline to an upstream AI output we do not control and inherits its framing.
- Customer turns only: no customer in the 30 internal calls.
- Re-cluster every batch: categories change when new calls arrive.
- Hand-written taxonomy with no discovery: imposes our assumptions.
- Embeddings plus clustering as the main method: needs a second provider and libraries not installed; unstable at n=100.
- Theme only or product area only: loses what product managers (module owners) or support leaders need.
- Single label or free multi-label: loses information or double counts.

**Known weaknesses:** the taxonomy reflects our judgment; a person must act on the "other" bucket; a taxonomy revision means a full re-run; n=100 gives rare themes few examples; calls touching several modules need a primary module; the product-area signal quoted (a module mentioned in 96 of 100 calls, 53 in more than one) is a rough keyword scan, not a classification. Not yet run.

### How Stage 0 (D1) constrains D2a and D3a (recorded 2026-10-29, A11)
**D2a, sentiment:** Stage 0 outputs the speaker side per call; compare within call type; do not pass the call-type label to the scorer; reuse the LLM client, JSON output and review step from Stage 0.

**D3a, categories:** Stage 0's type is a slicing dimension for theme-by-type tables, not an input; supports one shared taxonomy; sanity check that billing or integration themes concentrate in support, renewal in external, sprint planning in internal; Stage 0 reads only the opening, Stage 1 reads the transcript, so stages stay independent.

**Pipeline order so far:** Stage 0 call type (D1) → Stage 1 categorize (D3 discovery once, then recurring classification) and Stage 2 sentiment (D2) in parallel → Stage 3 insights and stakeholder views (D6 open).

---

## E. To-do before submission
- T1: Done (A18). Stage 0 built, run, reviewed and frozen.
- T2: Done (A13). Record the pinned model id, prompt versions and the frozen taxonomy version here when the pipeline is built.
- T3: Every figure in the deck must cite a cell in the notebook.
- T4: Add a short "Assumptions and limits" slide drawn from section B and the weaknesses above.

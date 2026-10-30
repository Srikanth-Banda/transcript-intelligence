# Model selection record (prepared 2026-10-29)

Status: LOCKED (D7). The bake-off ran (475 calls, $1.63) and Gemini 3.8 Flash was chosen for all stages, with a disclosed override of the pre-written decision rule (see DECISIONS.md D7, A17). The sections below are the pre-run record: DECISIONS.md D5 planned "Haiku class for Stage 0, Sonnet class for Stages 1-2"; this record checks that plan against what exists on OpenRouter today. Raw candidate table: `docs/openrouter-models.md`.

## 1. Connectivity (verified)
- `OPENROUTER_API_KEY` loaded through python-dotenv; the key was never printed.
- `/api/v1/auth/key` answered OK. The key has a spend **limit of $8 and about $1.22 already used** (usage field as returned at the time). This matters for cost, see section 6.
- One minimal chat call to `anthropic/claude-haiku-4.5` returned "OK". Further tiny probes (about $0.0003 total) went to claude-haiku-5.5, claude-sonnet-5.5, gpt-6-luna and gemini-3.8-flash; all answered.
- Observed routing: the same slug was served by different providers across calls (Amazon Bedrock, Claude Platform on AWS). So provider pinning (`TI_PROVIDER_ORDER`, no fallbacks, D5) is required for criterion 6 and the provider must be recorded in every cache entry.

## 2. Criteria (from DECISIONS.md B2, applied to models)
1. Strict JSON/schema adherence (`structured_outputs` / `response_format` supported).
2. Verbatim quoting without invention (criterion 3, evidence-linked).
3. Instruction following with long written anchors/taxonomies.
4. Long-context reading: a median transcript is about 1,900 tokens, so context is not a constraint; the one taxonomy-discovery call (about 190k-230k tokens) needs a 1M window.
5. Nuance on tone (Stage 2).
6. Determinism and one method over time (criterion 6): pinned provider, temperature 0 where supported, `seed` where supported, reproducible via cache.
7. Few providers and moving parts, low cost (criterion 8).

## 3. What exists on OpenRouter now (verified from the models endpoint, 2026-10-29)
Newest generation per family (price in USD per million tokens, input/output; context):
| Family | Newest relevant slugs | Notes |
|---|---|---|
| Anthropic | claude-haiku-5.5 ($0.10/$0.50, 1M), claude-sonnet-5.5 ($2/$10, 1M), claude-opus-5.5 ($4/$20, 1M), claude-fable-5.1 ($10/$50, 1M) | structured_outputs + response_format listed; **no `temperature`, no `seed` in supported_parameters**; Sonnet 5.5 reasoning is mandatory (efforts low to max), Haiku 5.5 optional |
| OpenAI | gpt-6-luna ($0.10/$0.50), gpt-6.1-terra ($1/$5), gpt-6.1-sol ($2/$10), gpt-6-astra ($10/$50); ~1.05M | structured outputs + `seed`; **no `temperature`** listed; reasoning optional |
| Google | gemini-3.8-flash ($0.75/$3.75), gemini-3.5-flash-lite ($0.30/$2.50), gemini-4-argon ($2/$10) | structured outputs + `temperature` + `seed`; reasoning mandatory on 3.8-flash |
| Open weight / other | deepseek-v4.1-flash ($0.045/$0.50), qwen3.8-flash ($0.15/$0.47), qwen3.8-max-0902 ($2/$6), mistral-large-4-0 ($0.70/$2.10), glm-5.3, kimi-k3.1-pro, grok-4.7 | DeepSeek has 40+ hosting providers with different behaviour (hard to pin one method); Qwen served by Alibaba only; no new Meta Llama found |
All shortlisted slugs list `structured_outputs` and `response_format`. Providers (endpoints API): Claude Haiku/Sonnet 5.5 via Anthropic, Amazon Bedrock, Azure, Google Vertex, "Claude Platform on AWS"; GPT-6 family via OpenAI, Azure (Bedrock for some); Gemini via Google and Google AI Studio.

**Determinism finding (important):** for Claude 5.x and GPT-6/6.1 a `temperature=0` request was accepted without error but `temperature` is not in supported_parameters, so it may be ignored. Whether outputs are stable on these models is therefore an empirical question for the bake-off, not something we can assume. Gemini 3.8 Flash lists both `temperature` and `seed`. This is a real argument for measuring run-to-run stability before locking.

## 4. Benchmark evidence (with caveats)
All fetched 2026-10-29. BenchLM and Arena figures were read via a fetch tool that summarises pages, so numbers are as extracted, not checked against raw HTML. Cross-check: Sonnet 5.5 AA-LCR 83% also appeared in a third-party search snippet (tosea.ai).

**Coding-agent benchmarks (suggested by the user): weak prior only.** DeepSWE (113 tasks, agentic coding, mini-swe-agent harness; https://deepswe.datacurve.ai/blog/deepswe), SWE-bench Pro and Terminal-Bench measure whether an agent fixes repositories. They do not measure JSON adherence, verbatim quoting or tone judgement. Datacurve's own audit (reported via https://yage.ai/share/deepswe-benchmark-audit-en-20260528.html, a second-hand source I did not verify) says SWE-bench Pro's verifier has high error rates. BenchLM DeepSWE: Sonnet 5.5 71.0, Gemini 3.8 Flash 73.8, DeepSeek V4.1 Flash 77.0, GPT-6 Luna 66.6 (https://benchlm.ai/md/models/*.md). These numbers barely separate the candidates and I did not use them to rank. Sonnet 5.5 SWE-bench Pro 81.3 (same BenchLM page); not listed for the others.

**Closer-to-task evidence found:**
| Evidence | Numbers | Source | Caveat |
|---|---|---|---|
| Long-context reasoning, AA-LCR | Haiku 5.5 82.7; Sonnet 5.5 82.7; GPT-6.1 Terra 82.7; GPT-6 Luna 83.3; Gemini 3.8 Flash 81.3; DeepSeek V4.1 Flash 84.0 | benchlm.ai/md/models/{claude-haiku-5-5, claude-sonnet-5-5, gpt-6-1-terra, gpt-6-luna, gemini-3-8-flash, deepseek-v4-1-flash}.md | Three identical 82.7 values look like a saturated or coarse metric; does not separate models. Reasoning over documents, not our task. |
| Document extraction, ExtractBench (LlamaIndex) | Sonnet 5.5 94.68; GPT-6.1 Terra 94.28; GPT-6 Luna 91.01; DeepSeek V4.1 Flash 87.11; Gemini 3.8 Flash 80.71. Haiku 5.5 not listed | same pages | Closest proxy for schema-filled extraction; ExtractBench Pro is very low for all (27-32%, Luna 0%), so hard extraction is unsolved. Test is PDFs/forms, not transcripts. |
| AA-Omniscience hallucination rate (lower better) | Haiku 5.5 34.2; GPT-6.1 Terra 34.5; Sonnet 5.5 43.3; Gemini 3.8 Flash 55.1; GPT-6 Luna 79.3; DeepSeek V4.1 Flash 96.5 | same pages | Measures made-up facts on knowledge questions, a loose proxy for invented quotes. Use only as a flag. |
| Artificial Analysis Intelligence Index | Sonnet 5.5 54.2; GPT-6.1 Terra 51.0; DeepSeek V4.1 Flash 39.5; Haiku 5.5 36.2; Gemini 3.8 Flash 30.6; GPT-6 Luna 27.8 | same pages | Composite incl. math, coding, agentic; general capability only. |
| Instruction following, IFBench | Leaderboard https://benchlm.ai/md/benchmarks/ifbench.md lists Qwen3.8 Max 82.8, Qwen3.8-Omni-Flash 81.5, Grok 4.3 81.3, Gemini 3.5 Flash 76.3, Claude Opus 4.5 58.0. **No Claude 5.x, GPT-6 or Gemini 3.8 entry** | as stated | Cannot compare the shortlist on instruction following. Opus 4.5 at 58 is an old model, not evidence about Sonnet 5.5. |
| Long-context composite (LongBench v2, MRCRv2, etc.) | https://www.benchlm.ai/best/long-context lists only 7 older models (GPT-5.5 85.3, Qwen3.8 Max 79.6, Opus 4.5 68.2) | as stated | None of the shortlist present; not usable. |
| LMArena (Text Arena, human preference), as of 2026-10-27 | Sonnet 5.5 (xHigh) 1477 rank 31; DeepSeek-V4.1-Flash 1476 rank 35; Gemini 3.8 Flash (High) 1496 rank 10 (Preliminary); GPT-6 Luna 1441 rank 97; Haiku 5.5 (High) 1425 rank 126 | https://arena.ai/leaderboard/text | Chat preference, not structured tasks; rating differences of 20 points are small; style effects. |
| BenchLM overall | Sonnet 5.5 81.84 (#6); GPT-6.1 Terra 80.46 (#9); Haiku 5.5 66.42 (#24); Gemini 3.8 Flash 66.22 (#27); DeepSeek V4.1 Flash 65.22 (#30); GPT-6 Luna 62.14 (#46) | benchlm.ai model pages | Weighted mostly by agentic/coding/knowledge categories; coverage partial per model (51-77 of 724 benchmarks). |

**Not found / not verified:** any JSON-schema-reliability benchmark for these models; any sentiment or call-tone classification result; IFEval/IFBench for Claude 5.x, GPT-6, Gemini 3.8; MRCR/RULER for the shortlist. I did not use any number I could not trace to a fetched page.

## 5. Shortlist (max 4) and recommendation
1. `anthropic/claude-sonnet-5.5` - provisional primary for Stages 1 and 2 (and taxonomy discovery).
2. `anthropic/claude-haiku-5.5` - provisional primary for Stage 0.
3. `openai/gpt-6.1-terra` - runner-up for Stages 1-2 (half Sonnet's price).
4. `google/gemini-3.8-flash` - runner-up for Stage 0, and the only shortlisted model that lists both `temperature` and `seed`.

Reasoning:
- One family for all stages (Claude) keeps one provider contract and one prompt style (criterion 8); it also matches the plan already recorded in D5.
- Evidence favouring Sonnet 5.5 for the hard stages: highest BenchLM overall and Intelligence Index among the shortlist, best ExtractBench score (94.68, within 0.4 of Terra), 1M context for discovery, no other model beats it on any trustworthy metric we found. This is a modest, indirect case, not proof.
- Evidence for the runner-up: Terra is within noise of Sonnet on ExtractBench and AA-LCR, has the lowest hallucination rate alongside Haiku, supports `seed`, and costs half. If the bake-off shows Terra equal or better on stability and quote validity, Terra becomes the primary and saves money.
- Haiku 5.5 for Stage 0: the cheapest model with a low hallucination rate (34.2). Its Arena rank is low (126) but Stage 0 is a rule-like classification of 8 turns; the bake-off tests it against the title rule directly. GPT-6 Luna and DeepSeek V4.1 Flash were excluded despite a similar price because of their high hallucination rates (79.3, 96.5) on a task that requires verbatim evidence, and DeepSeek has 40+ differing hosts (hard to pin one method).
- Excluded: Opus 5.5 / Fable 5.1 (2-5x cost, no evidence we need it); Gemini 4 Argon (not examined, $2/$10 and preliminary); Qwen/Mistral/GLM/Kimi/Grok (single-host or non-US hosting questions and no task evidence; not examined further, so this is a scoping choice, not a finding that they are worse).

Important unknown that could flip the recommendation: determinism of Claude 5.x and GPT-6 given no `temperature` support. If run-to-run stability is poor for them, Gemini 3.8 Flash (supports temperature+seed) becomes more attractive despite lower benchmark scores.

## 6. Cost estimate (USD, from the listed prices)
Assumptions (mine, not measured): 100 transcripts, about 190k transcript tokens per stage. Stage 0 about 1.5k input and 0.5k output per call; Stage 1 about 4.4k input (transcript + prompt + taxonomy) and 1.5k output; Stage 2 about 3.4k input and 3k output (per-turn labels about 1k). Output tokens include reasoning tokens (Sonnet 5.5 reasoning is mandatory, so these are the most uncertain). Discovery: about 230k in and 15k out, run twice. "3x" = main pass plus two stability re-runs.
| Configuration | 1 pass | 3x passes |
|---|---|---|
| Haiku 5.5 (S0) + Sonnet 5.5 (S1, S2, discovery) | about $7.3 | about $22 (up to about $36 if outputs are twice my assumption) |
| Haiku 5.5 + GPT-6.1 Terra | about $3.7 | about $11 |
| Gemini 3.8 Flash for all | about $3.0 | about $9 |
Stage 0 alone is about $0.04 (Haiku). Stage 2 is the largest line item because of the output.
**Budget warning:** the key's limit is $8 with about $1.22 used. Even the bake-off (section 7, about $4-6.5) nearly exhausts it, and the full Sonnet pipeline does not fit. The user must raise the key limit (or cap stability re-runs to a sample, which D2a already allows) before the real run. Cache hits make re-runs free, but only for unchanged prompts.

## 7. Bake-off design (NOT run; needs user approval)
**Sample:** 15 calls for Stages 1-2: the three escalation calls (Blackridge URGENT, Cobalt URGENT, Northstar ESCALATION), 5 per call type spanning the three types, a few known-hard ones (very short, very long, internal calls with ambiguous sides, calls where the provided score and the title-rule disagree), chosen with a fixed seed and listed in the eval folder before running. Stage 0 uses all 100 calls (cheap, 8 turns each).
**Runs:** Stage 0 - Haiku 5.5 and Gemini 3.8 Flash (Terra optional), run twice. Stages 1-2 - Sonnet 5.5, GPT-6.1 Terra, Gemini 3.8 Flash, each run twice at identical settings, provider pinned, temperature 0 (and seed where listed).
**Measure per model:** (a) schema-valid rate on first attempt; (b) verbatim-quote validity: every quoted string found exactly in the transcript, scripted check; (c) Stage 0 agreement with the title rule and, on disagreements, a manual look; (d) run-to-run stability: identical-label rate and, for Stage 2, mean absolute score difference between run 1 and 2; (e) Stage 2 score spread against the written anchors (is the 1-5 range used, are the three escalation calls scored low) and against the provided score, reported not as truth; (f) p50/p95 latency; (g) actual cost per call from the returned usage field, including reasoning tokens.
**Decision rule:** disqualify any model with schema-valid rate below 98%, quote validity below 98% or Stage 2 run-to-run mean absolute difference above 0.3. Among the rest pick the lowest-cost model whose stability and quote validity are within 2 points of the best and whose theme/score outputs a hand-check judges not worse on the three escalation calls; ties go to the model already used in another stage (fewer moving parts). If none pass, test Gemini with temperature+seed or lower reasoning effort.
**Caveats:** n=15 is small, so differences smaller than about 10 points are noise; the sample is the same data later used for validation, so scores for the chosen model are optimistic and must not be reported as final accuracy (hand-check on 15 different calls); the title rule is itself imperfect; hosted models can change behind a slug, so record dates and returned provider.
**Estimated cost:** about $3.8 on my assumptions (Stage 0: two models on 100 calls about $0.4; Stages 1-2: Sonnet about $1.8, Terra about $0.9, Gemini about $0.7), about $6.5 if outputs are twice my assumption. Fits only barely in the remaining key budget (about $6.8).

## 8. Still unknown
- Whether `temperature=0` is honoured on Claude 5.x and GPT-6/6.1, and their real run-to-run stability.
- Real output and reasoning token counts (all costs are estimates).
- Instruction-following, JSON-reliability and sentiment evidence for the shortlist (none found).
- Whether the three identical AA-LCR scores (82.7) reflect real equality or a data artifact.
- Whether Gemini 4 Argon or Qwen3.8 Max (strong on IFBench, 1M context) would beat the shortlist; not examined beyond listings.
- Key spend limit and who raises it.

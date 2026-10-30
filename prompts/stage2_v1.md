# Stage 2 prompt: tone score (whole call and customer side)

- Version: stage2_v1
- Decision: D2, D2a (locked), D7 (model) in DECISIONS.md
- **Status: DRAFT awaiting the candidate's approval of the anchors (Anchors Approval artifact). No live run has used this prompt.** After approval the final anchor text replaces the draft here and the version is bumped if any wording changed.
- Input: the full transcript as numbered turns (index, speaker, side, sentence) from `Meeting.view_for("stage2")`. No title, no call type, no provided summary, topics, score or sentence labels.
- Model: set in `.env` as `TI_MODEL_STAGE2` (pinned in D7).
- Replaces `prompts/stage2_bakeoff_v0.md`, which was a model-comparison draft only. Nothing from that draft's results may be reported as pipeline output.

## Design notes (not part of the prompt)

The anchors are written from what the 1 to 5 scale should mean, with observable cues. They were not tuned on the provided `sentimentScore` or sentence labels (an upstream AI output). The provided values are used afterwards only as a consistency comparison (D2a).

### Whole-call anchors, rationale and borderline cases

| Level | Observable criteria | Borderline case and resolution | Whole-call vs customer-side difference |
|---|---|---|---|
| 5 Warm | At least one speaker shows clear enthusiasm, delight, praise or gratitude beyond courtesy (for example "really excited", "this is exactly what we needed"), and this recurs across the call. No complaint and no unresolved problem. The call ends with mutual positivity or a firm positive next step. | A friendly planning call with a single enthusiastic remark is a 4, not a 5. A 5 needs enthusiasm to be a recurring feature of the call. | Cheerful staff can lift the whole-call score above the customer score. On internal calls this level means a team that is visibly pleased (shipped on time, praise for each other). |
| 4 Constructive | Cooperative and friendly. May include a small concern, a minor delay, or a question that is answered smoothly. Light appreciation ("thanks, that helps"). The call ends agreed and settled. | A problem is raised, fixed during the call, and the speaker says they are glad: 4, because relief counts as positive. If the frustration before the fix was strong and repeated, score 3.5. | A customer who is quietly satisfied but not expressive stays a 4 on both scales. |
| 3 Neutral or balanced | Businesslike, factual or procedural (status rounds, walkthroughs, routine tracking), OR positives and negatives are roughly equal. Concerns are raised and handled calmly without visible frustration. | A calm, factual discussion of a serious outage in which nobody expresses frustration is a 3. The seriousness of the topic does not lower the score; only the tone of the speakers does. | Staff apologies and empathy phrases ("I'm so sorry about that") affect the whole-call score only when they show real alarm; formulaic apologies do not move it. |
| 2 Strained | At least one speaker states dissatisfaction, impatience, worry about impact, or doubt about the other party, and this lasts across more than one turn or the problem is unresolved or only partly resolved at the end. Everyone stays professional. At most a mild mention of reconsidering ("we may look at other options"). | One sharp remark in an otherwise calm call that ends resolved is a 3, not a 2. A customer who says they might be "shopping platforms" but stays constructive and agrees next steps is a 2: a stated risk, not an ultimatum. | Tension between internal teams ("can we just acknowledge the outage") counts here; there is no customer score for such a call. |
| 1 Breakdown | Anger, accusations or sustained hostility; a firm threat to cancel or leave, or an ultimatum with a deadline; visible distress; or the conversation stops being productive. The call ends with the relationship at serious risk and no agreed path. | A firm "we will terminate unless this is fixed by Friday" is a 1 or 1.5. The same sentence delivered calmly with an agreed escalation path is a 2. | A call can be a 1 for the customer while the whole-call score is 1.5 if staff stay calm and constructive. |

Half steps: Use a half step (for example 2.5) when the call clearly sits between two adjacent levels. If you are torn between two levels and a problem is still unresolved at the end of the call, take the lower; otherwise take the higher.

### Customer-side anchors

| Level | Observable criteria | Borderline case and resolution |
|---|---|---|
| 5 Delighted | The customer expresses delight, strong satisfaction or praise beyond courtesy, more than once, and raises no open problem. | "Thanks, great" at the end of a routine call is a 4 at most. Delight must be specific ("this is exactly what we needed"). |
| 4 Satisfied | The customer is cooperative, satisfied or reassured. Thanks come with substance ("that fixed it, thanks"). Any concern raised was resolved. | A customer who was frustrated early and clearly relieved at the end scores 3 to 3.5, not 4, because the frustration was real. |
| 3 Neutral or mixed | The customer is factual, with no clear satisfaction or dissatisfaction, or satisfaction and dissatisfaction are about equal across the call. | A customer who states one concern calmly and accepts the answer is a 3. |
| 2 Dissatisfied | The customer states frustration, impatience, dissatisfaction or worry about impact, or says the problem is still not solved. Still civil. | Stating that a problem hurts the business without anger ("this is costing us") is a 2 if repeated or unresolved, otherwise 3. |
| 1 Angry or leaving | The customer is angry, repeatedly says the situation is unacceptable, or gives a firm ultimatum or threat to leave or escalate formally. | "I'm not happy" is a 2. "If this isn't fixed today we are leaving" is a 1. |

Internal calls have no customer: `customer_score` is null and `call_score` covers the team's mood. Staff apologies, cheerfulness and staff-to-staff tension count only in `call_score`.

### Rules

- **Technical words are topic, not mood.** Words such as outage, failure, breach, error, down or critical describe the subject. They do not make a turn negative. A turn is negative only when the speaker expresses frustration, worry, tension, blame or dissatisfaction.
- **Courtesy is neutral.** Greetings, thanks, "I understand", "let me look into that" and protocol apologies ("I'm sorry for the inconvenience") are neutral. A turn is positive only if it shows appreciation beyond courtesy, enthusiasm, praise, agreement with evident satisfaction, or relief. A staff apology that itself shows alarm or distress is negative.
- **Sarcasm and understatement.** Judge the intended meaning, not the literal words. "Great, another outage" is negative. Understatement ("it's a bit of a problem" about a total loss of service) is read at its real weight.
- **Resolved versus unresolved.** The end of the call matters. A problem that is fixed during the call and met with relief lifts the tone; a problem still open at the end holds the score down. Do not give credit for promises alone ("we will look into it") unless the speaker accepts them with evident reassurance.
- **Per-turn labels.** Label every turn on its own by tone: negative (frustration, worry, tension, blame, dissatisfaction, impatience, threat, or alarmed bad news), neutral (factual, procedural, questions, courtesy, calm bad news), positive (appreciation beyond courtesy, enthusiasm, praise, relief, evident satisfaction). A turn with both positive and negative tone takes the stronger one; if equal, neutral. Very short turns ("yeah", "okay") are neutral unless the words or the context make the tone clear.
- **Trajectory.** Let n be the number of turns. The first third is the first ceil(n/3) turns and the last third is the last ceil(n/3) turns. Score each on the same 1 to 5 whole-call scale (half steps allowed). Count turns, not minutes.
- **Evidence quote.** Copy one short passage (up to 25 words) character for character from a single turn, including punctuation and dashes, choosing the one that most influenced call_score. Do not paraphrase, join separate turns, or add ellipses.

### Design choices to look at hardest

- **A whole-call score exists for every one of the 100 calls.** Task 2 compares support, external and internal calls, and internal calls have no customer. The whole-call score is the number compared across types; the customer-side score is an extra for the 70 customer calls.
- **Every level is defined by checkable cues, not adjectives.** A reviewer can point at the turn that justifies the level. This is what makes hand-checking and disagreement analysis possible.
- **Tone, not topic.** Support calls are full of words like failure and outage. Scoring them as negative would make the support score a measure of vocabulary.
- **Courtesy and protocol apologies are neutral.** In the bake-off, a polite staff acknowledgement was labeled positive by a model while the provided label was neutral. Treating courtesy as neutral keeps positive for real appreciation. Risk: a genuinely warm acknowledgement may be under-read.
- **Half steps with a stated tie-break (lower if a problem is still unresolved at the end).** Gives a score to calls that sit between levels, and makes the choice reproducible. Risk: it biases borderline calls downward. Look at this one.
- **A stated risk of leaving is a 2; a firm ultimatum is a 1.** Keeps 1 for real breakdowns. Risk: churn signals at level 2 will need the evidence quote to surface.
- **The end of the call matters.** Relief after a fix lifts the tone; an open problem at the end holds it down. Risk: a long calm call with a bad last minute is penalised.
- **Trajectory counts turns, not minutes.** Simple, reproducible from the transcript alone. Risk: uneven turn lengths make thirds unequal in time.
- **Per-turn labels on every turn.** Enables sentence-level agreement against the provided labels (4,313 sentences) and the trajectory. Risk: long output on long calls; truncation is detected by the schema and eval checks.
- **Reasoning allowed, quote verbatim.** The model may reason before answering, but the output is JSON only and the quote must match the transcript exactly (checked by script).
- **The scorer sees the transcript, speaker names and sides only.** No title, call type, summary, topics or provided score. Sides reveal whether a customer is present; that is inherent to scoring the customer side.
- **The anchors were not tuned on the provided scores.** They were written from what the scale should mean. The provided score is used afterwards only as a consistency comparison (D2a), and it is itself an AI output.
- **Changing the anchors means re-scoring every call.** One method across all calls keeps trends valid (decision criterion 6).

### Schema alignment (`src/ti/schemas.py` `Stage2Out`)

- Matches: `call_score`, `customer_score` (null allowed), `per_turn` (`index`, `label`), `trajectory` (`start`, `end`), `evidence_quote`, `confidence` (low, medium, high).
- Mismatch 1: the prompt asks for half steps in `trajectory.start` and `trajectory.end`, but the schema only checks 1 to 5 (`ge=1, le=5`), so 3.33 would pass. `call_score` and `customer_score` do enforce half steps.
- Mismatch 2: "one `per_turn` entry for every turn, in order" is not enforced by the schema; it is checked by `eval/bakeoff.py` `check_stage2` (coverage).
- Mismatch 3: "evidence quote is verbatim from a single turn" is not enforced by the schema; it is checked by script.
- No schema was edited. Decide with the candidate whether to tighten 1 in the build phase.

### Transcripts read while drafting (text only, no provided scores or labels)

Weekly Engineering Standup (turns 0-5 and last 2); Support Case #3266 Trailhead Marketplace Detect Alerts Not Firing (turns 0-8 and last 2); Aegis / Coastal Living Co Onboarding Kickoff (turns 0-6 and last 2). They informed the wording of the criteria (for example the "shopping platforms" borderline in level 2 and the staff-apology rule). The two worked examples are invented, not copied from the dataset.

## Change log
- v1 (2026-10-29): first full draft of the anchors for approval. Not run.

<!-- PROMPT START -->
You rate the emotional tone of one recorded call at Aegis Cloud Security, a B2B SaaS company. You will receive the full transcript as numbered turns, each with index, speaker, side ("customer" = works at an outside company, "aegis_staff" = works at Aegis) and sentence. You are given nothing else about the call: no title, no call type, no summary and no earlier scores. Judge only from the words in the transcript.

Score the TONE of the speakers, not how serious the topic is.

Whole-call score (call_score, all speakers, 1 to 5). Anchors:
- 5 (Warm): At least one speaker shows clear enthusiasm, delight, praise or gratitude beyond courtesy (for example "really excited", "this is exactly what we needed"), and this recurs across the call. No complaint and no unresolved problem. The call ends with mutual positivity or a firm positive next step. Borderline: A friendly planning call with a single enthusiastic remark is a 4, not a 5. A 5 needs enthusiasm to be a recurring feature of the call.
- 4 (Constructive): Cooperative and friendly. May include a small concern, a minor delay, or a question that is answered smoothly. Light appreciation ("thanks, that helps"). The call ends agreed and settled. Borderline: A problem is raised, fixed during the call, and the speaker says they are glad: 4, because relief counts as positive. If the frustration before the fix was strong and repeated, score 3.5.
- 3 (Neutral or balanced): Businesslike, factual or procedural (status rounds, walkthroughs, routine tracking), OR positives and negatives are roughly equal. Concerns are raised and handled calmly without visible frustration. Borderline: A calm, factual discussion of a serious outage in which nobody expresses frustration is a 3. The seriousness of the topic does not lower the score; only the tone of the speakers does.
- 2 (Strained): At least one speaker states dissatisfaction, impatience, worry about impact, or doubt about the other party, and this lasts across more than one turn or the problem is unresolved or only partly resolved at the end. Everyone stays professional. At most a mild mention of reconsidering ("we may look at other options"). Borderline: One sharp remark in an otherwise calm call that ends resolved is a 3, not a 2. A customer who says they might be "shopping platforms" but stays constructive and agrees next steps is a 2: a stated risk, not an ultimatum.
- 1 (Breakdown): Anger, accusations or sustained hostility; a firm threat to cancel or leave, or an ultimatum with a deadline; visible distress; or the conversation stops being productive. The call ends with the relationship at serious risk and no agreed path. Borderline: A firm "we will terminate unless this is fixed by Friday" is a 1 or 1.5. The same sentence delivered calmly with an agreed escalation path is a 2.
Use a half step (for example 2.5) when the call clearly sits between two adjacent levels. If you are torn between two levels and a problem is still unresolved at the end of the call, take the lower; otherwise take the higher.

Customer-side score (customer_score, 1 to 5). Score only the turns whose side is "customer"; staff turns give context but are not scored. If no turn has side "customer", return null. Anchors:
- 5 (Delighted): The customer expresses delight, strong satisfaction or praise beyond courtesy, more than once, and raises no open problem. Borderline: "Thanks, great" at the end of a routine call is a 4 at most. Delight must be specific ("this is exactly what we needed").
- 4 (Satisfied): The customer is cooperative, satisfied or reassured. Thanks come with substance ("that fixed it, thanks"). Any concern raised was resolved. Borderline: A customer who was frustrated early and clearly relieved at the end scores 3 to 3.5, not 4, because the frustration was real.
- 3 (Neutral or mixed): The customer is factual, with no clear satisfaction or dissatisfaction, or satisfaction and dissatisfaction are about equal across the call. Borderline: A customer who states one concern calmly and accepts the answer is a 3.
- 2 (Dissatisfied): The customer states frustration, impatience, dissatisfaction or worry about impact, or says the problem is still not solved. Still civil. Borderline: Stating that a problem hurts the business without anger ("this is costing us") is a 2 if repeated or unresolved, otherwise 3.
- 1 (Angry or leaving): The customer is angry, repeatedly says the situation is unacceptable, or gives a firm ultimatum or threat to leave or escalate formally. Borderline: "I'm not happy" is a 2. "If this isn't fixed today we are leaving" is a 1.
The customer-side score ignores staff tone: staff apologies, cheerfulness and staff-to-staff tension affect call_score only. The two scores can differ (cheerful staff and a frustrated customer; calm customer and alarmed staff).

Rules:
1. Technical words are topic, not mood. Words such as outage, failure, breach, error, down or critical describe the subject. They do not make a turn negative. A turn is negative only when the speaker expresses frustration, worry, tension, blame or dissatisfaction.
2. Courtesy is neutral. Greetings, thanks, "I understand", "let me look into that" and protocol apologies ("I'm sorry for the inconvenience") are neutral. A turn is positive only if it shows appreciation beyond courtesy, enthusiasm, praise, agreement with evident satisfaction, or relief. A staff apology that itself shows alarm or distress is negative.
3. Sarcasm and understatement. Judge the intended meaning, not the literal words. "Great, another outage" is negative. Understatement ("it's a bit of a problem" about a total loss of service) is read at its real weight.
4. Resolved versus unresolved. The end of the call matters. A problem that is fixed during the call and met with relief lifts the tone; a problem still open at the end holds the score down. Do not give credit for promises alone ("we will look into it") unless the speaker accepts them with evident reassurance.
5. Per-turn labels. Label every turn on its own by tone: negative (frustration, worry, tension, blame, dissatisfaction, impatience, threat, or alarmed bad news), neutral (factual, procedural, questions, courtesy, calm bad news), positive (appreciation beyond courtesy, enthusiasm, praise, relief, evident satisfaction). A turn with both positive and negative tone takes the stronger one; if equal, neutral. Very short turns ("yeah", "okay") are neutral unless the words or the context make the tone clear. Return one entry for EVERY turn, in order, using the turn's index.
6. Trajectory. Let n be the number of turns. The first third is the first ceil(n/3) turns and the last third is the last ceil(n/3) turns. Score each on the same 1 to 5 whole-call scale (half steps allowed). Count turns, not minutes.
7. Evidence quote. Copy one short passage (up to 25 words) character for character from a single turn, including punctuation and dashes, choosing the one that most influenced call_score. Do not paraphrase, join separate turns, or add ellipses.
8. confidence: "high" when the tone is clear and consistent, "medium" when it shifts or is mixed, "low" when the transcript is too short or ambiguous to judge.

Illustrative example A (invented for this prompt; not dataset content). A customer call.
Turns:
0 | Dana | aegis_staff | Thanks for calling Aegis support, how can I help?
1 | Lee | customer | Our sync has been down since this morning and my team can't log in. This is the second time this month.
2 | Dana | aegis_staff | I'm sorry about that. I can see the failed job and I'm restarting it now.
3 | Lee | customer | Okay. Honestly I'm frustrated, we've lost half a day.
4 | Dana | aegis_staff | Understood. It's running again, can you try a login?
5 | Lee | customer | That works. Thanks, that's a relief.
Output:
{"call_score": 3.5, "customer_score": 3, "per_turn": [{"index": 0, "label": "neutral"}, {"index": 1, "label": "negative"}, {"index": 2, "label": "neutral"}, {"index": 3, "label": "negative"}, {"index": 4, "label": "neutral"}, {"index": 5, "label": "positive"}], "trajectory": {"start": 2.5, "end": 4}, "evidence_quote": "Honestly I'm frustrated, we've lost half a day.", "confidence": "medium"}

Illustrative example B (invented for this prompt; not dataset content). An internal call with no customer.
Turns:
0 | Sam | aegis_staff | Quick status round. Priya, you first?
1 | Priya | aegis_staff | Ingestion refactor is sixty percent done, retry logic is in review.
2 | Priya | aegis_staff | Before we move on, can we talk about the outage? The noise from it is still eating our week.
3 | Sam | aegis_staff | Fair. Let's stay on the sprint today and take the outage in the retro.
4 | Priya | aegis_staff | Fine, but it keeps getting pushed.
5 | Sam | aegis_staff | Noted. I'll put it first on the retro agenda.
Output:
{"call_score": 2.5, "customer_score": null, "per_turn": [{"index": 0, "label": "neutral"}, {"index": 1, "label": "neutral"}, {"index": 2, "label": "negative"}, {"index": 3, "label": "neutral"}, {"index": 4, "label": "negative"}, {"index": 5, "label": "neutral"}], "trajectory": {"start": 3, "end": 2.5}, "evidence_quote": "Fine, but it keeps getting pushed.", "confidence": "medium"}

The examples show the format and how the rules apply. They are not the answer for any real call.

Return only JSON, nothing else:
{
  "call_score": <number, 1 to 5 in half steps>,
  "customer_score": <number in half steps, or null when no turn has side "customer">,
  "per_turn": [{"index": 0, "label": "negative" | "neutral" | "positive"}, ...],
  "trajectory": {"start": <number 1 to 5>, "end": <number 1 to 5>},
  "evidence_quote": "<verbatim text from one turn>",
  "confidence": "low" | "medium" | "high"
}
<!-- PROMPT END -->

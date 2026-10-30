# Stage 1 prompt: taxonomy DISCOVERY, batch pass

- Version: stage1_discovery_v1
- Decision: D3, D3a in DECISIONS.md (one-time discovery, then a frozen versioned taxonomy)
- Input: 25 full transcripts per call to the model (speaker and side only). No title, no call type, no provided summary/topics/score (`view_for("stage1")`).
- Why batches of 25 and not one pass over all 100: see `docs/stage1-discovery.md` (reliability of verbatim quotes on a long context, and the second run uses a different split so stability also tests sensitivity to batch composition).
- Product names are NOT given in the prompt, so the product-area list is discovered from the transcripts and not led.

## Change log
- v1 (2026-10-29): first version. Awaiting candidate review of the resulting proposal; nothing here is frozen.

<!-- PROMPT START -->
You are helping design a theme taxonomy for recorded calls at Aegis Cloud Security, a B2B SaaS company. The calls are customer support calls, calls between Aegis account managers and customers, and internal Aegis meetings. The taxonomy will be used by product and engineering leaders, support leaders and sales managers to see what the calls are about.

You will receive a batch of full call transcripts. Each starts with "=== call XXXXXX ===" where XXXXXX is the call id, followed by lines "Speaker (side): sentence". "side" is "customer" or "aegis_staff".

Task: read all the calls in the batch and propose CANDIDATE THEMES, plus a separate list of product areas.

A theme is what the call is about in terms of the issue or purpose (for example a kind of problem, a business event, or a kind of decision). A theme is NOT the product name and NOT the type of call.

Actionability test, which every theme must pass: you can name which one of these four stakeholders would act on a pattern of calls with this theme, and say in one sentence what they would do: "support lead", "sales / account manager", "product manager", "engineering lead". If you cannot, it is a topic label, not a theme; leave it out. Reject vague labels such as "discussion", "update" or "meeting".

For each theme return:
- name: short, plain, 2 to 5 words.
- definition: one sentence saying what makes a call belong to this theme.
- distinguishing: one sentence saying how it differs from the most similar theme in your list.
- owner: one of "support lead", "sales / account manager", "product manager", "engineering lead".
- actionable_because: one sentence on what the owner would do with a pattern of these calls.
- meeting_ids: the ids of EVERY call in this batch that substantially involve this theme, not only the best examples. A call may appear under more than one theme.
- evidence: up to 3 items, each {meeting_id, quote}. A quote must be copied EXACTLY, character for character, from a single line of that call. Do not paraphrase, shorten with "...", or join text from different lines. Use quotes from different calls where possible.

Rules:
1. Propose between 5 and 12 themes. Propose fewer if the calls support fewer. A theme needs at least 2 calls in this batch; a single call goes in other_note instead.
2. Base everything on the transcripts. Do not guess from names or invent details. Do not use any outside knowledge about Aegis.
3. product_areas: list the products, modules or product families that the speakers actually name in this batch, using the names as the speakers say them. For each give evidence (up to 2 items {meeting_id, quote}, same exact-copy rule) and meeting_ids of every call in the batch where that product is a main subject. Merge obvious spelling variants. Do not invent products that nobody names.
4. other_note: one or two sentences on calls that fit none of your themes and why. Write "none" if every call fits.
5. Every meeting_id you use must be an id that appears in this batch.

Return only JSON matching the schema.
<!-- PROMPT END -->

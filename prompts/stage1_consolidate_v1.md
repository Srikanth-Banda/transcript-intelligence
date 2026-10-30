# Stage 1 prompt: taxonomy DISCOVERY, consolidation pass

- Version: stage1_consolidate_v1
- Decision: D3, D3a
- Input: the four batch outputs of one discovery run as JSON (theme names, definitions, owners, call counts). No transcripts.
- Evidence quotes and call id lists are NOT asked of the model here: code takes the union of the source themes' call ids and evidence, so nothing can be invented at this step.

## Change log
- v1 (2026-10-29): first version.

<!-- PROMPT START -->
You merge candidate themes that were proposed independently from four batches of call transcripts at Aegis Cloud Security.

Input: a JSON object with "themes" (each has a source id like "b2.t3", a name, definition, distinguishing, owner, actionable_because, and the number of calls) and "product_areas" (each has a source id like "b1.p2" and a name).

Task:
1. Merge themes that are the same idea under different wording into one consolidated theme. Keep themes that are genuinely different separate. Return at most 12 consolidated themes.
2. For each consolidated theme give: name (2 to 5 words), definition (one sentence), distinguishing (one sentence versus its nearest neighbor), owner (one of "support lead", "sales / account manager", "product manager", "engineering lead"), actionable_because (one sentence), and merged_from (the list of source ids it combines).
3. Every theme source id must appear in exactly one merged_from list, or in "dropped" with a one-sentence reason (use dropping only for a theme that fails the actionability test: no stakeholder would act on a pattern of such calls). Do not invent source ids.
4. Merge the product areas the same way: canonical name as the speakers use it, and merged_from source ids. Every product-area source id appears in exactly one list.
5. other_note: one or two sentences on what the batches say about calls that fit no theme.

Return only JSON matching the schema.
<!-- PROMPT END -->

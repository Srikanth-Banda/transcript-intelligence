# Stage 1 prompt: BAKE-OFF DRAFT (model comparison only)

- Version: stage1_bakeoff_v0
- Decision: D3, D3a in DECISIONS.md
- Status: **BAKE-OFF DRAFT. Not the final prompt.** Written only to compare models on a 15-call sample (docs/model-selection.md section 7). The real Stage 1 prompt goes through the candidate's approval gate (taxonomy discovery, then frozen taxonomy) and will be re-run from scratch. Results from this draft must not be reported as pipeline output.
- Input: the full transcript (turn index, speaker, side, sentence). No title, no call type, no provided summary/topics/score (view_for("stage1")).

## Limitations of this draft
- The theme list below is PROVISIONAL, derived from the keyword families in the Whiteboard exploration (presenter notes appendix). It is not the frozen taxonomy and has not been through discovery or the actionability test.
- `taxonomy_version` is set to `provisional-bakeoff`.
- The schema does not enforce the theme and product-area lists (strings); membership is checked by eval/bakeoff.py.

## Change log
- v0 (2026-10-29): first draft for the bake-off.

<!-- PROMPT START -->
You label one recorded call at Aegis Cloud Security, a B2B SaaS company that sells these products: Detect (threat detection and monitoring), Comply (compliance reporting, including Comply v2), Identity (SSO, SAML, SCIM, LDAP, MFA, identity management), Protect (data protection), and backup / CloudPrime (backup and restore). You will receive the full transcript as numbered turns, each with speaker, side (customer or aegis_staff) and sentence.

Pick exactly one primary theme from this PROVISIONAL list (the theme the call is mostly about):
1. Outage & incident response
2. Compliance & audit
3. Renewal, pricing & billing
4. Churn & competitive risk
5. Onboarding & rollout
6. Identity & access
7. Product roadmap & planning
8. Integrations, backup & data
9. Other / new theme (use only if none of the eight fits; then say what the call is about in `tags`)

Rules:
1. `primary_theme`: copy one theme name exactly as written above.
2. `tags`: zero, one or two further themes from the same list that also clearly come up (never repeat the primary theme). For "Other / new theme" put a short description in tags[0].
3. `product_area`: the one Aegis product the call is mostly about: "Detect", "Comply", "Identity", "Protect", "Backup", or "Platform/General" when no single product dominates.
4. `evidence_quote`: one short passage copied EXACTLY (character for character) from a single turn of the transcript that best supports the primary theme. Do not paraphrase and do not join text from different turns.
5. `confidence`: "high" if the call is clearly about the primary theme, "medium" if two themes compete, "low" if it fits poorly.
6. `taxonomy_version`: always the string "provisional-bakeoff".
7. Judge only from the transcript. Do not guess from names or invent details.

Return only JSON:
{
  "primary_theme": "<theme>",
  "tags": ["<theme>", "<theme>"],
  "product_area": "<product area>",
  "evidence_quote": "<verbatim text>",
  "confidence": "low" | "medium" | "high",
  "taxonomy_version": "provisional-bakeoff"
}
<!-- PROMPT END -->

## Stage 0 (70 customer calls x 2 runs, title withheld)

| model | calls | schema-valid first attempt % | quote exact % | quote loose % | agree w/ title rule % | run1 vs run2 label % | sides agree % | latency med/p90 s | cost USD |
|---|---|---|---|---|---|---|---|---|---|
| haiku | 140 | 100.0 | 100.0 | 100.0 | 92.9 | 100.0 | 98.6 | 1.7/3.1 | 0.0401 |
| gemini | 140 | 100.0 | 98.6 | 100.0 | 95.7 | 100.0 | 100.0 | 2.4/2.9 | 0.1656 |

## Stage 1 (15 calls x 2 runs, provisional themes)

| model | calls | schema-valid % | list membership % | quote exact % | quote loose % | theme agree run1/run2 % | product-area agree % | latency med/p90 s | cost USD |
|---|---|---|---|---|---|---|---|---|---|
| sonnet | 30 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 1.9/4.2 | 0.3100 |
| terra | 30 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 2.6/4.2 | 0.0715 |
| gemini | 30 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 2.2/2.6 | 0.0753 |

## Stage 2 (15 calls x 2 runs, draft anchors)

| model | calls | schema-valid % | per-turn complete % | quote exact % | call-score MAD run1/run2 | exact same score % | customer MAD | per-turn agree run1/run2 % | corr w/ provided | MAD vs provided | per-turn agree w/ provided % | latency med/p90 s | cost USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sonnet | 30 | 100.0 | 100.0 | 100.0 | 0.00 | 100.0 | 0.00 | 97.3 | 0.96 | 0.21 | 76.1 | 4.4/7.0 | 0.5255 |
| terra | 30 | 100.0 | 100.0 | 100.0 | 0.17 | 66.7 | 0.10 | 95.3 | 0.92 | 0.28 | 67.8 | 11.7/13.6 | 0.1987 |
| gemini | 30 | 100.0 | 100.0 | 100.0 | 0.00 | 100.0 | 0.00 | 99.3 | 0.96 | 0.23 | 74.5 | 5.4/6.3 | 0.1501 |

## Determinism probe (3 identical requests per transcript, 3 transcripts)

| stage/model | identical JSON | detail |
|---|---|---|
| stage0/haiku | 2/3 | Aegis / Redwood Clinical - Product Feedb: same label True; Aegis / Harborview Banking - Threat Dete: same label True; URGENT: Cobalt Software - Aegis Detect D: same label True |
| stage0/gemini | 3/3 | Aegis / Redwood Clinical - Product Feedb: same label True; Aegis / Harborview Banking - Threat Dete: same label True; URGENT: Cobalt Software - Aegis Detect D: same label True |
| stage2/sonnet | 0/3 | Aegis / Redwood Clinical - Product Feedb: scores [3.5, 3.5, 3.5], min per-turn agree 100.0%; Aegis / Harborview Banking - Threat Dete: scores [4.0, 4.0, 4.0], min per-turn agree 92.3%; URGENT: Cobalt Software - Aegis Detect D: scores [2.0, 2.0, 1.5], min per-turn agree 97.3% |
| stage2/terra | 0/3 | Aegis / Redwood Clinical - Product Feedb: scores [3.0, 3.0, 3.0], min per-turn agree 92.7%; Aegis / Harborview Banking - Threat Dete: scores [4.0, 4.0, 4.0], min per-turn agree 93.6%; URGENT: Cobalt Software - Aegis Detect D: scores [2.0, 2.0, 2.0], min per-turn agree 97.3% |
| stage2/gemini | 2/3 | Aegis / Redwood Clinical - Product Feedb: scores [3.5, 3.5, 3.5], min per-turn agree 100.0%; Aegis / Harborview Banking - Threat Dete: scores [4.0, 4.0, 4.0], min per-turn agree 89.7%; URGENT: Cobalt Software - Aegis Detect D: scores [2.0, 2.0, 2.0], min per-turn agree 100.0% |

## Decision rule

- stage0: winner **haiku**; disqualified: {}; quality (mean of schema, quote, stability): {"haiku": 100.0, "gemini": 99.5}; eligible within 2 points: ['haiku', 'gemini']
- stage12: winner **gemini**; disqualified: {}; quality (mean of schema, quote, stability): {"sonnet": 99.5, "terra": 99.2, "gemini": 99.9}; eligible within 2 points: ['sonnet', 'terra', 'gemini']
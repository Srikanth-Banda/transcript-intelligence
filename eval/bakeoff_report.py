"""Compute every bake-off metric from outputs/bakeoff/results.jsonl and write tables + Stage 0 CSVs.

`uv run python eval/bakeoff.py report` -> outputs/bakeoff/metrics.json, outputs/bakeoff/tables.md,
outputs/stage0_<model>.csv and outputs/stage0_review_queue_<model>.csv.
"""

from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict

import pandas as pd

import bakeoff as B
from ti import OUTPUT_DIR
from ti.stage0 import build_user_message, classify, review_queue

HEADLINE_RUNS = (1, 2)


def _by(results, stage, model, runs=HEADLINE_RUNS):
    return [r for r in results if r["stage"] == stage and r["model"] == model and r["run"] in runs]


def _pctl(xs, p):
    xs = sorted(x for x in xs if x is not None)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")


def _common(rs):
    return {
        "calls": len(rs),
        "schema_valid_first_attempt": B.rate([bool(r["ok"] and r["first_attempt_ok"]) for r in rs]),
        "failed": sum(1 for r in rs if not r["ok"]),
        "retried": sum(1 for r in rs if r.get("retried")),
        "truncated": sum(1 for r in rs if r.get("finish_reason") not in (None, "stop")),
        "latency_median_s": st.median([r["latency_s"] for r in rs if r.get("latency_s")]) if rs else float("nan"),
        "latency_p90_s": _pctl([r.get("latency_s") for r in rs], 0.9),
        "cost_usd": sum(r.get("cost") or 0 for r in rs),
        "mean_completion_tokens": st.mean([r["completion_tokens"] for r in rs if r.get("completion_tokens")]) if rs else float("nan"),
    }


def _pair(rs, key=lambda r: r["meeting_id"]):
    """run 1 and run 2 records matched by meeting, only where both are ok."""
    a = {key(r): r for r in rs if r["run"] == 1 and r["ok"]}
    b = {key(r): r for r in rs if r["run"] == 2 and r["ok"]}
    ids = sorted(set(a) & set(b))
    return [(a[i], b[i]) for i in ids]


def stage0_metrics(results, meetings, model):
    by_id = {m.meeting_id: m for m in meetings}
    rs = _by(results, "stage0", model)
    out = _common(rs)
    q_exact, q_loose, agree_title, sides = [], [], [], []
    for r in rs:
        if not r["ok"]:
            continue
        m = by_id[r["meeting_id"]]
        opening = build_user_message(m).split("opening:\n", 1)[1]
        p = r["parsed"]
        q_exact.append(B.quote_valid(p["evidence_quote"], [opening]))
        q_loose.append(B.quote_valid(p["evidence_quote"], [opening], loose=True))
        agree_title.append(p["label"] == m.title_rule_label)
        det = m.speaker_sides()
        sides.append(all(det.get(s["speaker"]) == s["side"] for s in p["speaker_sides"] if s["speaker"] in det))
    out.update(quote_valid_exact=B.rate(q_exact), quote_valid_loose=B.rate(q_loose),
               agree_title_rule=B.rate(agree_title), sides_agree_deterministic=B.rate(sides))
    pairs = _pair(rs)
    out["run_to_run_label_agreement"] = B.rate([a["parsed"]["label"] == b["parsed"]["label"] for a, b in pairs])
    out["run_to_run_quote_identical"] = B.rate([a["parsed"]["evidence_quote"] == b["parsed"]["evidence_quote"] for a, b in pairs])
    out["confidence_run1"] = dict(Counter(r["parsed"]["confidence"] for r in rs if r["ok"] and r["run"] == 1))
    dis = []
    for r in rs:
        if r["ok"] and r["run"] == 1 and r["parsed"]["label"] != by_id[r["meeting_id"]].title_rule_label:
            m = by_id[r["meeting_id"]]
            dis.append({"title": m.title, "title_rule": m.title_rule_label, "model": r["parsed"]["label"],
                        "confidence": r["parsed"]["confidence"], "quote": r["parsed"]["evidence_quote"][:140]})
    out["disagreements_run1"] = dis
    esc = {}
    for r in rs:
        m = by_id[r["meeting_id"]]
        if m.title.startswith(B.ESCALATION_PREFIXES) and r["ok"]:
            esc.setdefault(m.title.split(" - ")[0], {})[f"run{r['run']}"] = f"{r['parsed']['label']} ({r['parsed']['confidence']})"
    out["escalation_calls"] = esc
    return out


def stage12_metrics(results, meetings, sample, model):
    by_id = {m.meeting_id: m for m in meetings}
    out = {}
    for stage in ("stage1", "stage2"):
        rs = _by(results, stage, model)
        s = _common(rs)
        q_exact, q_loose = [], []
        for r in rs:
            if not r["ok"]:
                continue
            m = by_id[r["meeting_id"]]
            turns = [t.sentence for t in m.turns]
            q_exact.append(B.quote_valid(r["parsed"]["evidence_quote"], turns))
            q_loose.append(B.quote_valid(r["parsed"]["evidence_quote"], turns, loose=True))
        s.update(quote_valid_exact=B.rate(q_exact), quote_valid_loose=B.rate(q_loose))
        pairs = _pair(rs)
        if stage == "stage1":
            checks = [B.check_stage1(r["parsed"]) for r in rs if r["ok"]]
            s["list_membership_ok"] = B.rate([all(c.values()) for c in checks])
            s["theme_agreement_run1_run2"] = B.rate([a["parsed"]["primary_theme"] == b["parsed"]["primary_theme"] for a, b in pairs])
            s["product_area_agreement_run1_run2"] = B.rate([a["parsed"]["product_area"] == b["parsed"]["product_area"] for a, b in pairs])
            s["theme_distribution_run1"] = dict(Counter(r["parsed"]["primary_theme"] for r in rs if r["ok"] and r["run"] == 1))
            esc = {}
            for r in rs:
                m = by_id[r["meeting_id"]]
                if m.title.startswith(B.ESCALATION_PREFIXES) and r["ok"] and r["run"] == 1:
                    esc[m.title.split(" - ")[0]] = f"{r['parsed']['primary_theme']} | {r['parsed']['product_area']}"
            s["escalation_calls_run1"] = esc
        else:
            checks = [B.check_stage2(r["parsed"], len(by_id[r["meeting_id"]].turns), by_id[r["meeting_id"]].has_external)
                      for r in rs if r["ok"]]
            s["per_turn_complete"] = B.rate([c["per_turn_complete"] for c in checks])
            s["customer_null_ok"] = B.rate([c["customer_null_ok"] for c in checks])
            s["call_score_mad_run1_run2"] = B.mad([a["parsed"]["call_score"] for a, b in pairs], [b["parsed"]["call_score"] for a, b in pairs])
            s["call_score_exact_same_run1_run2"] = B.rate([a["parsed"]["call_score"] == b["parsed"]["call_score"] for a, b in pairs])
            cp = [(a, b) for a, b in pairs if a["parsed"]["customer_score"] is not None and b["parsed"]["customer_score"] is not None]
            s["customer_score_mad_run1_run2"] = B.mad([a["parsed"]["customer_score"] for a, b in cp], [b["parsed"]["customer_score"] for a, b in cp])
            s["per_turn_label_agreement_run1_run2"] = st.mean(
                [B.per_turn_agreement(B.per_turn_map(a["parsed"]["per_turn"]), B.per_turn_map(b["parsed"]["per_turn"])) for a, b in pairs])
            s["trajectory_mad_run1_run2"] = st.mean(
                [(abs(a["parsed"]["trajectory"]["start"] - b["parsed"]["trajectory"]["start"]) + abs(a["parsed"]["trajectory"]["end"] - b["parsed"]["trajectory"]["end"])) / 2 for a, b in pairs])
            # spread against the provided (upstream AI) score and labels; run 1 and run 2 averaged
            xs, ys = [], []
            turn_acc = []
            lab = {"negative": "negative", "neutral": "neutral", "positive": "positive"}
            for r in rs:
                if not r["ok"]:
                    continue
                m = by_id[r["meeting_id"]]
                xs.append(r["parsed"]["call_score"])
                ys.append(m.provided.sentiment_score)
                mine = B.per_turn_map(r["parsed"]["per_turn"])
                prov = {t.index: lab[m.provided.turn_sentiments[i]] for i, t in enumerate(m.turns)}
                turn_acc.append(B.per_turn_agreement(mine, prov))
            s["corr_with_provided_score"] = B.pearson(xs, ys)
            s["mad_vs_provided_score"] = B.mad(xs, ys)
            s["mean_score_model"] = st.mean(xs)
            s["mean_score_provided"] = st.mean(ys)
            s["per_turn_agreement_with_provided_labels"] = st.mean(turn_acc)
            s["call_score_by_type_run1"] = {}
            for t in ("support", "external", "internal"):
                v = [r["parsed"]["call_score"] for r in rs if r["ok"] and r["run"] == 1 and by_id[r["meeting_id"]].title_rule_label == t]
                s["call_score_by_type_run1"][t] = round(st.mean(v), 2) if v else None
            esc = {}
            for r in rs:
                m = by_id[r["meeting_id"]]
                if m.title.startswith(B.ESCALATION_PREFIXES) and r["ok"] and r["run"] == 1:
                    esc[m.title.split(" - ")[0]] = {"call": r["parsed"]["call_score"], "customer": r["parsed"]["customer_score"], "provided": m.provided.sentiment_score}
            s["escalation_scores_run1"] = esc
        out[stage] = s
    return out


def determinism(results, meetings, sample):
    """Runs 1,2,3 are three identical requests (the run number only changes the cache key)."""
    by_id = {m.meeting_id: m for m in meetings}
    first3 = [i for i in sample["ids"] if sample["has_customer"][i]][:3]
    out = {}
    for stage, models in (("stage0", ["haiku", "gemini"]), ("stage2", ["sonnet", "terra", "gemini"])):
        for model in models:
            rows = []
            for mid in first3:
                rs = sorted([r for r in results if r["stage"] == stage and r["model"] == model and r["meeting_id"] == mid and r["ok"]
                             and r["run"] in (1, 2, 3)], key=lambda r: r["run"])
                if len(rs) < 3:
                    rows.append({"meeting": by_id[mid].title[:40], "n_runs": len(rs)})
                    continue
                parsed = [json.dumps(r["parsed"], sort_keys=True) for r in rs]
                row = {"meeting": by_id[mid].title[:40], "n_runs": 3, "identical_json": len(set(parsed)) == 1}
                if stage == "stage0":
                    row["same_label"] = len({r["parsed"]["label"] for r in rs}) == 1
                else:
                    scores = [r["parsed"]["call_score"] for r in rs]
                    row["call_scores"] = scores
                    row["same_call_score"] = len(set(scores)) == 1
                    maps = [B.per_turn_map(r["parsed"]["per_turn"]) for r in rs]
                    row["per_turn_agreement_min"] = min(B.per_turn_agreement(maps[i], maps[j]) for i in range(3) for j in range(i + 1, 3))
                rows.append(row)
            out[f"{stage}/{model}"] = {
                "transcripts": rows,
                "identical_json_count": sum(1 for r in rows if r.get("identical_json")),
                "of": len(rows),
            }
    return out


def write_stage0_csvs(results, meetings):
    by_id = {m.meeting_id: m for m in meetings}
    for model in ("haiku", "gemini"):
        recs = {r["meeting_id"]: r for r in results if r["stage"] == "stage0" and r["model"] == model and r["run"] == 1 and r["ok"]}
        rows = []
        for m in meetings:
            if m.is_internal_by_metadata:
                rows.append(classify(m, None))
                continue
            r = recs[m.meeting_id]
            p = r["parsed"]
            det = m.speaker_sides()
            sides_agree = all(det.get(s["speaker"]) == s["side"] for s in p["speaker_sides"] if s["speaker"] in det)
            rows.append({"meeting_id": m.meeting_id, "title": m.title, "title_rule_label": m.title_rule_label,
                         "prompt_version": r["prompt_version"], "label": p["label"], "source": "llm", "confidence": p["confidence"],
                         "evidence_quote": p["evidence_quote"], "sides_agree": sides_agree,
                         "model": r.get("model_returned"), "cache_hit": r.get("cache_hit")})
        df = pd.DataFrame(rows)
        df["disagree"] = df["label"] != df["title_rule_label"]
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUTPUT_DIR / f"stage0_{model}.csv", index=False)
        review_queue(df).to_csv(OUTPUT_DIR / f"stage0_review_queue_{model}.csv", index=False)


def apply_rules(m0, m12):
    s12 = {}
    for m, v in m12.items():
        calls = v["stage1"]["calls"] + v["stage2"]["calls"]
        schema = (v["stage1"]["schema_valid_first_attempt"] * v["stage1"]["calls"] + v["stage2"]["schema_valid_first_attempt"] * v["stage2"]["calls"]) / calls
        quote = (v["stage1"]["quote_valid_exact"] + v["stage2"]["quote_valid_exact"]) / 2
        stability = (v["stage1"]["theme_agreement_run1_run2"] + v["stage2"]["per_turn_label_agreement_run1_run2"]) / 2
        s12[m] = {"schema": schema, "quote": quote, "stability": stability, "cost": v["stage1"]["cost_usd"] + v["stage2"]["cost_usd"],
                  "mad": v["stage2"]["call_score_mad_run1_run2"]}
    r12 = B.decide(s12, max_mad=0.3, tie_prefer=["sonnet", "terra", "gemini"])
    winner12 = r12["winner"]
    fam = {"sonnet": "haiku", "gemini": "gemini"}
    prefer0 = [fam[winner12]] if winner12 in fam else []
    s0 = {m: {"schema": v["schema_valid_first_attempt"], "quote": v["quote_valid_exact"], "stability": v["run_to_run_label_agreement"], "cost": v["cost_usd"]}
          for m, v in m0.items()}
    r0 = B.decide(s0, tie_prefer=prefer0 + ["haiku", "gemini"])
    return {"stage0": {"stats": s0, **r0}, "stage12": {"stats": s12, **r12}}


def _fmt(x, nd=1):
    return "n/a" if x is None or (isinstance(x, float) and x != x) else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def tables(m0, m12, det, rules):
    L = []
    L.append("## Stage 0 (70 customer calls x 2 runs, title withheld)\n")
    L.append("| model | calls | schema-valid first attempt % | quote exact % | quote loose % | agree w/ title rule % | run1 vs run2 label % | sides agree % | latency med/p90 s | cost USD |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for m, v in m0.items():
        L.append(f"| {m} | {v['calls']} | {_fmt(v['schema_valid_first_attempt'])} | {_fmt(v['quote_valid_exact'])} | {_fmt(v['quote_valid_loose'])} | {_fmt(v['agree_title_rule'])} | {_fmt(v['run_to_run_label_agreement'])} | {_fmt(v['sides_agree_deterministic'])} | {_fmt(v['latency_median_s'])}/{_fmt(v['latency_p90_s'])} | {_fmt(v['cost_usd'],4)} |")
    L.append("\n## Stage 1 (15 calls x 2 runs, provisional themes)\n")
    L.append("| model | calls | schema-valid % | list membership % | quote exact % | quote loose % | theme agree run1/run2 % | product-area agree % | latency med/p90 s | cost USD |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for m, v in m12.items():
        s = v["stage1"]
        L.append(f"| {m} | {s['calls']} | {_fmt(s['schema_valid_first_attempt'])} | {_fmt(s['list_membership_ok'])} | {_fmt(s['quote_valid_exact'])} | {_fmt(s['quote_valid_loose'])} | {_fmt(s['theme_agreement_run1_run2'])} | {_fmt(s['product_area_agreement_run1_run2'])} | {_fmt(s['latency_median_s'])}/{_fmt(s['latency_p90_s'])} | {_fmt(s['cost_usd'],4)} |")
    L.append("\n## Stage 2 (15 calls x 2 runs, draft anchors)\n")
    L.append("| model | calls | schema-valid % | per-turn complete % | quote exact % | call-score MAD run1/run2 | exact same score % | customer MAD | per-turn agree run1/run2 % | corr w/ provided | MAD vs provided | per-turn agree w/ provided % | latency med/p90 s | cost USD |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m, v in m12.items():
        s = v["stage2"]
        L.append(f"| {m} | {s['calls']} | {_fmt(s['schema_valid_first_attempt'])} | {_fmt(s['per_turn_complete'])} | {_fmt(s['quote_valid_exact'])} | {_fmt(s['call_score_mad_run1_run2'],2)} | {_fmt(s['call_score_exact_same_run1_run2'])} | {_fmt(s['customer_score_mad_run1_run2'],2)} | {_fmt(s['per_turn_label_agreement_run1_run2'])} | {_fmt(s['corr_with_provided_score'],2)} | {_fmt(s['mad_vs_provided_score'],2)} | {_fmt(s['per_turn_agreement_with_provided_labels'])} | {_fmt(s['latency_median_s'])}/{_fmt(s['latency_p90_s'])} | {_fmt(s['cost_usd'],4)} |")
    L.append("\n## Determinism probe (3 identical requests per transcript, 3 transcripts)\n")
    L.append("| stage/model | identical JSON | detail |")
    L.append("|---|---|---|")
    for k, v in det.items():
        detail = "; ".join(f"{r['meeting']}: " + (f"scores {r.get('call_scores')}, min per-turn agree {_fmt(r.get('per_turn_agreement_min'))}%" if 'call_scores' in r else f"same label {r.get('same_label')}") for r in v["transcripts"])
        L.append(f"| {k} | {v['identical_json_count']}/{v['of']} | {detail} |")
    L.append("\n## Decision rule\n")
    for k, r in rules.items():
        L.append(f"- {k}: winner **{r['winner']}**; disqualified: {json.dumps({a: b for a, b in (r.get('disqualified') or {}).items() if b})}; quality (mean of schema, quote, stability): {json.dumps({a: round(b,1) for a,b in (r.get('quality') or {}).items()})}; eligible within 2 points: {r.get('eligible')}")
    return "\n".join(L)


def build_report(meetings):
    results = B.load_results()
    sample = json.loads((B.OUT / "sample.json").read_text())
    m0 = {m: stage0_metrics(results, meetings, m) for m in ("haiku", "gemini")}
    m12 = {m: stage12_metrics(results, meetings, sample, m) for m in ("sonnet", "terra", "gemini")}
    det = determinism(results, meetings, sample)
    rules = apply_rules(m0, m12)
    write_stage0_csvs(results, meetings)
    # cross-model agreement (run 1)
    cross = {}
    by_key = defaultdict(dict)
    for r in results:
        if r["ok"] and r["run"] == 1 and r["stage"] in ("stage0", "stage1"):
            by_key[(r["stage"], r["meeting_id"])][r["model"]] = r["parsed"]["label" if r["stage"] == "stage0" else "primary_theme"]
    for stage, pairs in (("stage0", [("haiku", "gemini")]), ("stage1", [("sonnet", "terra"), ("sonnet", "gemini"), ("terra", "gemini")])):
        for a, b in pairs:
            xs = [v for (s, _), v in by_key.items() if s == stage and a in v and b in v]
            cross[f"{stage}:{a}-{b}"] = B.rate([v[a] == v[b] for v in xs])
    all_recs = [r for r in results]
    total = {"total_cost_usd": sum(r.get("cost") or 0 for r in all_recs), "calls": len(all_recs),
             "failed": sum(1 for r in all_recs if not r["ok"]),
             "by_model": {m: round(sum(r.get("cost") or 0 for r in all_recs if r["model"] == m), 4) for m in B.MODELS}}
    metrics = {"stage0": m0, "stage12": m12, "determinism": det, "rules": rules, "cross_model_agreement_run1": cross, "totals": total}
    (B.OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    (B.OUT / "tables.md").write_text(tables(m0, m12, det, rules))
    print((B.OUT / "tables.md").read_text())
    print("\ncross-model agreement:", json.dumps(cross, indent=1))
    print("\ntotals:", json.dumps(total))

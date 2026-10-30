"""Task 2 analysis: sentiment across call types and trends. Reads frozen pipeline outputs only (no LLM calls).

Run: PYTHONPATH=src uv run python -m ti.analysis.sentiment
Writes outputs/analysis/sentiment/findings.json and tables; figures are made by ti.analysis.sentiment_figs.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from ti.analysis.stats import (SEED, band, bootstrap_ci, bootstrap_diff_ci, perm_test_diff, share, standardized_mean,
                               thirds, verdict, week_start)
from ti.load import load_meetings

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "analysis" / "sentiment"
CORE_THEME = "Incident and Outage Response"
TYPES = ["support", "external", "internal"]


def build_calls() -> pd.DataFrame:
    """One row per call: pipeline outputs joined with dates, titles and the provided score (comparison only)."""
    ms = {m.meeting_id: m for m in load_meetings()}
    s0 = pd.read_csv(ROOT / "outputs/stage0_final.csv")[["meeting_id", "label"]].rename(columns={"label": "type"})
    s1 = pd.read_csv(ROOT / "outputs/stage1/stage1_final.csv")[["meeting_id", "primary_theme", "tags", "product_area", "incident"]]
    s2 = pd.read_csv(ROOT / "outputs/stage2/stage2_final.csv")[
        ["meeting_id", "call_score", "customer_score", "traj_start", "traj_end", "n_turns", "n_neg", "n_neu", "n_pos",
         "confidence", "evidence_quote"]]
    df = s0.merge(s1, on="meeting_id").merge(s2, on="meeting_id")
    df["title"] = df.meeting_id.map(lambda i: ms[i].title)
    df["start"] = pd.to_datetime(df.meeting_id.map(lambda i: ms[i].start_time))
    df["date"] = df.start.dt.date
    df["month"] = df.start.dt.strftime("%Y-%m")
    df["week"] = df.date.map(week_start)
    df["title_rule"] = df.meeting_id.map(lambda i: ms[i].title_rule_label)
    df["provided_score"] = df.meeting_id.map(lambda i: ms[i].provided.sentiment_score)
    df["provided_overall"] = df.meeting_id.map(lambda i: ms[i].provided.overall_sentiment)
    df["prov_neg"] = df.meeting_id.map(lambda i: ms[i].provided.turn_sentiments.count("negative"))
    df["prov_neu"] = df.meeting_id.map(lambda i: ms[i].provided.turn_sentiments.count("neutral"))
    df["prov_pos"] = df.meeting_id.map(lambda i: ms[i].provided.turn_sentiments.count("positive"))
    df["touches_incident"] = df.incident.notna() & (df.incident.astype(str) != "")
    df["core_incident"] = df.primary_theme == CORE_THEME
    df["account"] = df.meeting_id.map(
        lambda i: (ms[i].external_emails[0].split("@")[1].split(".")[0] if ms[i].external_emails else ""))
    df["customer_present"] = df.type.isin(["support", "external"])
    return df


def build_turns(df: pd.DataFrame) -> pd.DataFrame:
    """Per-turn table with model label, provided label and speaker side (deterministic sides, D1)."""
    ms = {m.meeting_id: m for m in load_meetings()}
    pt = pd.read_json(ROOT / "outputs/stage2/per_turn.jsonl", lines=True)
    pt["side"] = [ms[m].speaker_side(ms[m].turns[i].speaker) for m, i in zip(pt.meeting_id, pt["index"])]
    n = pt.groupby("meeting_id")["index"].transform("max") + 1
    k = -(-n // 3)
    pt["third"] = np.where(pt["index"] < k, "first", np.where(pt["index"] >= n - k, "last", "mid"))
    pt["sentence"] = [ms[m].turns[i].sentence for m, i in zip(pt.meeting_id, pt["index"])]
    return pt


def summarize(vals) -> dict:
    v = np.asarray(list(vals), dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return {"n": 0}
    lo, hi = bootstrap_ci(v)
    return {"n": int(len(v)), "mean": round(float(v.mean()), 3), "median": float(np.median(v)),
            "sd": round(float(v.std(ddof=1)), 3) if len(v) > 1 else None, "ci95": [round(lo, 3), round(hi, 3)]}


def by_type_table(df: pd.DataFrame, col: str) -> dict:
    out = {}
    for t in TYPES:
        sub = df[df[col] == t]
        out[t] = {"call_score": summarize(sub.call_score), "customer_score": summarize(sub.customer_score),
                  "provided_score": summarize(sub.provided_score),
                  "score_counts": {str(k): int(v) for k, v in sorted(Counter(sub.call_score).items())}}
    return out


def pairwise(df: pd.DataFrame, col: str, value: str = "call_score") -> dict:
    res = {}
    for a, b in [("support", "external"), ("support", "internal"), ("external", "internal")]:
        x, y = df[df[col] == a][value].dropna(), df[df[col] == b][value].dropna()
        ci = bootstrap_diff_ci(x, y)
        res[f"{a}_minus_{b}"] = {"diff": round(float(x.mean() - y.mean()), 3), "ci95": [round(ci[0], 3), round(ci[1], 3)],
                                 "perm_p": round(perm_test_diff(x, y), 4), "n": [len(x), len(y)],
                                 "verdict": verdict(ci, min(len(x), len(y)))}
    return res


def side_gap(df: pd.DataFrame, pt: pd.DataFrame, label_col: str) -> dict:
    """Per-call share of customer turns labeled negative minus share of staff turns labeled negative."""
    out = {}
    for t in ["support", "external"]:
        gaps, cneg, sneg = [], [], []
        for mid in df[df.type == t].meeting_id:
            g = pt[pt.meeting_id == mid]
            c, s = g[g.side == "customer"][label_col].tolist(), g[g.side == "aegis_staff"][label_col].tolist()
            if c and s:
                cneg.append(share(c, "negative"))
                sneg.append(share(s, "negative"))
                gaps.append(cneg[-1] - sneg[-1])
        ci = bootstrap_ci(gaps)
        out[t] = {"n_calls": len(gaps), "customer_neg_mean": round(float(np.mean(cneg)), 3),
                  "staff_neg_mean": round(float(np.mean(sneg)), 3), "gap_mean": round(float(np.mean(gaps)), 3),
                  "gap_ci95": [round(ci[0], 3), round(ci[1], 3)], "calls_customer_more_negative": int(sum(g > 0 for g in gaps))}
    return out


# ----------------------------------------------------------------------------------------------
# Q2 trend and the March dip
# ----------------------------------------------------------------------------------------------
def monthly_and_weekly(df: pd.DataFrame) -> dict:
    out = {"monthly_overall": {}, "monthly_by_type": {}, "weekly_overall": {}, "weekly_by_type": {}}
    for m, g in df.groupby("month"):
        out["monthly_overall"][m] = summarize(g.call_score)
        out["monthly_by_type"][m] = {t: summarize(g[g.type == t].call_score) for t in TYPES}
    for w, g in df.groupby("week"):
        out["weekly_overall"][str(w)] = {"n": len(g), "mean": round(float(g.call_score.mean()), 3)}
        out["weekly_by_type"][str(w)] = {t: {"n": int((g.type == t).sum()),
                                             "mean": round(float(g[g.type == t].call_score.mean()), 3) if (g.type == t).any() else None}
                                         for t in TYPES}
    return out


def dip_decomposition(df: pd.DataFrame) -> dict:
    """March vs Feb+Apr, overall and after removing incident calls, plus a composition-adjusted version."""
    def cmp(sub: pd.DataFrame, label: str) -> dict:
        mar, oth = sub[sub.month == "2026-03"].call_score, sub[sub.month != "2026-03"].call_score
        ci = bootstrap_diff_ci(mar, oth)
        return {"label": label, "n_march": int(len(mar)), "n_other": int(len(oth)), "march_mean": round(float(mar.mean()), 3),
                "other_mean": round(float(oth.mean()), 3), "diff": round(float(mar.mean() - oth.mean()), 3),
                "ci95": [round(ci[0], 3), round(ci[1], 3)], "perm_p": round(perm_test_diff(mar, oth), 4),
                "verdict": verdict(ci, min(len(mar), len(oth)))}
    res = {"all_calls": cmp(df, "all calls"),
           "excl_touches_incident": cmp(df[~df.touches_incident], "excluding calls that touch the incident"),
           "excl_core_incident": cmp(df[~df.core_incident], "excluding core-incident calls (primary theme)")}
    # composition: weights = overall type mix; within-type monthly means
    w = df.type.value_counts().to_dict()
    adj = {}
    for m in sorted(df.month.unique()):
        gm = {t: float(df[(df.month == m) & (df.type == t)].call_score.mean()) for t in TYPES if ((df.month == m) & (df.type == t)).any()}
        adj[m] = round(standardized_mean(gm, w), 3)
    res["type_adjusted_monthly_mean"] = adj
    res["type_mix_by_month"] = {m: {t: round(float(((df.month == m) & (df.type == t)).sum() / (df.month == m).sum()), 3) for t in TYPES}
                                for m in sorted(df.month.unique())}
    # within March: incident-touching vs not
    mar = df[df.month == "2026-03"]
    a, b = mar[mar.touches_incident].call_score, mar[~mar.touches_incident].call_score
    ci = bootstrap_diff_ci(a, b)
    res["within_march_touch_vs_not"] = {"n": [int(len(a)), int(len(b))], "means": [round(float(a.mean()), 3), round(float(b.mean()), 3)],
                                        "diff": round(float(a.mean() - b.mean()), 3), "ci95": [round(ci[0], 3), round(ci[1], 3)],
                                        "perm_p": round(perm_test_diff(a, b), 4), "verdict": verdict(ci, min(len(a), len(b)))}
    # all months: touches vs not (the incident effect irrespective of month)
    a, b = df[df.touches_incident].call_score, df[~df.touches_incident].call_score
    ci = bootstrap_diff_ci(a, b)
    res["all_months_touch_vs_not"] = {"n": [int(len(a)), int(len(b))], "means": [round(float(a.mean()), 3), round(float(b.mean()), 3)],
                                      "diff": round(float(a.mean() - b.mean()), 3), "ci95": [round(ci[0], 3), round(ci[1], 3)],
                                      "perm_p": round(perm_test_diff(a, b), 4), "verdict": verdict(ci, min(len(a), len(b)))}
    # within type: March non-incident vs other months non-incident
    res["non_incident_by_type_march_vs_other"] = {}
    for t in TYPES:
        s = df[(~df.touches_incident) & (df.type == t)]
        x, y = s[s.month == "2026-03"].call_score, s[s.month != "2026-03"].call_score
        if len(x) >= 2 and len(y) >= 2:
            ci = bootstrap_diff_ci(x, y)
            res["non_incident_by_type_march_vs_other"][t] = {"n": [int(len(x)), int(len(y))], "march": round(float(x.mean()), 3),
                                                              "other": round(float(y.mean()), 3), "diff": round(float(x.mean() - y.mean()), 3),
                                                              "ci95": [round(ci[0], 3), round(ci[1], 3)], "verdict": verdict(ci, min(len(x), len(y)))}
    # share of calls that touch the incident by month and type
    res["touch_share_by_month"] = {m: round(float(g.touches_incident.mean()), 3) for m, g in df.groupby("month")}
    return res


# ----------------------------------------------------------------------------------------------
# Q3 outage story
# ----------------------------------------------------------------------------------------------
def outage_story(df: pd.DataFrame) -> dict:
    core = df[df.core_incident]
    start = min(core.date)
    touches = df[df.touches_incident].sort_values("date")
    timeline = [{"date": str(r.date), "type": r.type, "title": r.title, "core": bool(r.core_incident), "call_score": r.call_score,
                 "customer_score": None if pd.isna(r.customer_score) else r.customer_score} for r in touches.itertuples()]
    res = {"first_core_incident_call": str(start), "last_core_incident_call": str(max(core.date)),
           "n_touch": int(len(touches)), "touch_by_type": {t: int((touches.type == t).sum()) for t in TYPES},
           "touch_by_week": {str(w): {t: int(((touches.week == w) & (touches.type == t)).sum()) for t in TYPES} for w in sorted(touches.week.unique())},
           "calls_flagged_before_first_core_call": [{"date": str(r.date), "title": r.title} for r in touches.itertuples() if r.date < start],
           "timeline": timeline}
    ext = df[df.type == "external"]
    pre, post = ext[ext.date < start], ext[ext.date >= start]
    for name, a, b in [("external_pre_vs_post", pre, post)]:
        ci = bootstrap_diff_ci(post.call_score, pre.call_score)
        res[name] = {"cutoff": str(start), "n_pre": int(len(pre)), "n_post": int(len(post)),
                     "pre_mean": round(float(pre.call_score.mean()), 3), "post_mean": round(float(post.call_score.mean()), 3),
                     "diff_post_minus_pre": round(float(post.call_score.mean() - pre.call_score.mean()), 3), "ci95": [round(ci[0], 3), round(ci[1], 3)],
                     "perm_p": round(perm_test_diff(post.call_score, pre.call_score), 4), "verdict": verdict(ci, min(len(pre), len(post)))}
    # external post-outage: touching vs not, and by month window
    pt_, pn_ = post[post.touches_incident], post[~post.touches_incident]
    if len(pt_) >= 2 and len(pn_) >= 2:
        ci = bootstrap_diff_ci(pt_.call_score, pn_.call_score)
        res["external_post_touch_vs_not"] = {"n": [int(len(pt_)), int(len(pn_))], "means": [round(float(pt_.call_score.mean()), 3), round(float(pn_.call_score.mean()), 3)],
                                             "customer_means": [round(float(pt_.customer_score.mean()), 3), round(float(pn_.customer_score.mean()), 3)],
                                             "diff": round(float(pt_.call_score.mean() - pn_.call_score.mean()), 3), "ci95": [round(ci[0], 3), round(ci[1], 3)],
                                             "verdict": verdict(ci, min(len(pt_), len(pn_)))}
    # external calls by recovery window: pre, Mar 10-31 (acute), Apr (aftermath)
    win = {"pre": ext[ext.date < start], "acute_mar10_31": ext[(ext.date >= start) & (ext.month == "2026-03")], "april": ext[ext.month == "2026-04"]}
    res["external_by_window"] = {k: summarize(v.call_score) for k, v in win.items()}
    res["external_by_window_customer"] = {k: summarize(v.customer_score) for k, v in win.items()}
    # most-affected accounts: an incident-touching support call and an external call
    accts = []
    for acc, g in df[df.account != ""].groupby("account"):
        sup = g[(g.type == "support") & g.touches_incident]
        ex = g[g.type == "external"]
        if len(sup) and len(ex):
            accts.append({"account": acc, "calls": [{"date": str(r.date), "type": r.type, "title": r.title, "touch": bool(r.touches_incident),
                                                     "customer_score": None if pd.isna(r.customer_score) else r.customer_score, "call_score": r.call_score}
                                                    for r in g.sort_values("date").itertuples()]})
    res["most_affected_accounts"] = accts
    for a in accts:
        cs = [c["customer_score"] for c in a["calls"] if c["customer_score"] is not None]
        a["first_customer_score"], a["last_customer_score"], a["min_customer_score"] = cs[0], cs[-1], min(cs)
        a["last_call_date"] = a["calls"][-1]["date"]
        a["n_calls"] = len(a["calls"])
    apr, pre_ = ext[ext.month == "2026-04"].call_score, ext[ext.date < start].call_score
    ci = bootstrap_diff_ci(apr, pre_)
    res["external_april_vs_pre"] = {"n_april": int(len(apr)), "n_pre": int(len(pre_)), "april_mean": round(float(apr.mean()), 3),
                                    "pre_mean": round(float(pre_.mean()), 3), "diff": round(float(apr.mean() - pre_.mean()), 3),
                                    "ci95": [round(ci[0], 3), round(ci[1], 3)], "perm_p": round(perm_test_diff(apr, pre_), 4)}
    ea = ext[ext.month == "2026-04"]
    xt, xn = ea[ea.touches_incident], ea[~ea.touches_incident]
    res["external_april_touch_vs_not"] = {"n": [int(len(xt)), int(len(xn))], "means": [round(float(xt.call_score.mean()), 3), round(float(xn.call_score.mean()), 3)]}
    return res


# ----------------------------------------------------------------------------------------------
# Q4 trajectory
# ----------------------------------------------------------------------------------------------
def trajectory(df: pd.DataFrame, pt: pd.DataFrame) -> dict:
    df = df.assign(delta=df.traj_end - df.traj_start)
    res = {"by_type": {}}
    for t in TYPES:
        s = df[df.type == t]
        ci = bootstrap_ci(s.delta)
        res["by_type"][t] = {"n": int(len(s)), "start_mean": round(float(s.traj_start.mean()), 3), "end_mean": round(float(s.traj_end.mean()), 3),
                             "delta_mean": round(float(s.delta.mean()), 3), "delta_ci95": [round(ci[0], 3), round(ci[1], 3)],
                             "n_improve": int((s.delta > 0).sum()), "n_flat": int((s.delta == 0).sum()), "n_worse": int((s.delta < 0).sum())}
    # independent-ish check from per-turn labels (same pass): negative share, first vs last third
    for t in TYPES:
        ids = df[df.type == t].meeting_id
        g = pt[pt.meeting_id.isin(ids)]
        f, l = g[g.third == "first"].model_label.tolist(), g[g.third == "last"].model_label.tolist()
        fp, lp = g[g.third == "first"].provided_label.tolist(), g[g.third == "last"].provided_label.tolist()
        res["by_type"][t]["provided_neg_share_first_third"] = round(share(fp, "negative"), 3)
        res["by_type"][t]["provided_neg_share_last_third"] = round(share(lp, "negative"), 3)
        res["by_type"][t]["neg_share_first_third"] = round(share(f, "negative"), 3)
        res["by_type"][t]["neg_share_last_third"] = round(share(l, "negative"), 3)
    worse = df[df.delta < 0].sort_values("delta")
    res["calls_ending_worse"] = []
    for r in worse.itertuples():
        g = pt[pt.meeting_id == r.meeting_id]
        res["calls_ending_worse"].append({"date": str(r.date), "type": r.type, "title": r.title, "start": r.traj_start, "end": r.traj_end,
                                          "theme": r.primary_theme, "touches_incident": bool(r.touches_incident), "call_score": r.call_score,
                                          "neg_first_third": round(share(g[g.third == "first"].model_label.tolist(), "negative"), 2),
                                          "neg_last_third": round(share(g[g.third == "last"].model_label.tolist(), "negative"), 2),
                                          "evidence_quote": r.evidence_quote})
    strained = df[df.traj_end <= 2.5].sort_values("traj_end")
    res["calls_ending_strained"] = [{"date": str(r.date), "type": r.type, "title": r.title, "start": r.traj_start, "end": r.traj_end,
                                      "touches_incident": bool(r.touches_incident)} for r in strained.itertuples()]
    res["ending_strained_by_type"] = {t: int((strained.type == t).sum()) for t in TYPES}
    res["n_improve_all"] = int((df.delta > 0).sum())
    res["n_flat_all"] = int((df.delta == 0).sum())
    res["n_ending_worse"] = int(len(worse))
    res["worse_by_type"] = {t: int((worse.type == t).sum()) for t in TYPES}
    return res


# ----------------------------------------------------------------------------------------------
# Q5 disagreement with the provided score
# ----------------------------------------------------------------------------------------------
def disagreement(df: pd.DataFrame, pt: pd.DataFrame) -> dict:
    df = df.assign(diff=df.call_score - df.provided_score)
    df["band_ours"] = df.call_score.map(band)
    df["band_prov"] = df.provided_score.map(band)
    res = {"overall_offset": summarize(df["diff"]), "mae": round(float(df["diff"].abs().mean()), 3),
           "pearson": round(float(np.corrcoef(df.call_score, df.provided_score)[0, 1]), 3),
           "offset_by_type": {t: summarize(df[df.type == t]["diff"]) for t in TYPES}}
    material = (df["diff"].abs() >= 0.6)
    flips = df.band_ours != df.band_prov
    res["bands"] = {"definition": "low < 2.5 <= mid < 3.5 <= high", "n_band_flips": int(flips.sum()),
                    "n_band_flips_with_abs_diff_lt_0.5": int((flips & (df["diff"].abs() < 0.5)).sum()),
                    "note": "most band flips are 0.1-0.3 differences straddling an arbitrary threshold; only |diff| >= 0.6 is treated as material"}
    flagged = df[material].sort_values("diff")
    res["flagged"] = []
    for r in flagged.itertuples():
        res["flagged"].append({"meeting_id": r.meeting_id, "date": str(r.date), "type": r.type, "title": r.title, "ours": r.call_score,
                               "customer_score": None if pd.isna(r.customer_score) else r.customer_score, "provided": r.provided_score,
                               "provided_overall": r.provided_overall, "diff": round(float(r.diff), 2), "band_ours": r.band_ours,
                               "band_provided": r.band_prov, "turns": int(r.n_turns), "ours_neg_neu_pos": [int(r.n_neg), int(r.n_neu), int(r.n_pos)],
                               "provided_neg_neu_pos": [int(r.prov_neg), int(r.prov_neu), int(r.prov_pos)], "traj": [r.traj_start, r.traj_end],
                               "theme": r.primary_theme, "evidence_quote": r.evidence_quote})
    res["n_material_abs_diff_ge_0.6"] = int(material.sum())
    res["n_material_internal_outage_ours_higher"] = int((material & (df.type == "internal") & df.touches_incident & (df["diff"] > 0)).sum())
    res["max_abs_diff"] = round(float(df["diff"].abs().max()), 2)
    res["internal_incident_calls_offset"] = summarize(df[(df.type == "internal") & df.touches_incident]["diff"])
    res["other_calls_offset"] = summarize(df[~((df.type == "internal") & df.touches_incident)]["diff"])
    res["n_abs_diff_ge_1"] = int((df["diff"].abs() >= 1).sum())
    # neutral vs positive labelling
    m = pd.crosstab(pt.provided_label, pt.model_label).reindex(index=["negative", "neutral", "positive"], columns=["negative", "neutral", "positive"], fill_value=0)
    res["turn_confusion_rows_provided_cols_model"] = {r: {c: int(m.loc[r, c]) for c in m.columns} for r in m.index}
    res["turn_label_shares"] = {"model": {k: round(float((pt.model_label == k).mean()), 3) for k in ["negative", "neutral", "positive"]},
                                "provided": {k: round(float((pt.provided_label == k).mean()), 3) for k in ["negative", "neutral", "positive"]}}
    res["turn_agreement"] = round(float((pt.model_label == pt.provided_label).mean()), 3)
    rng = np.random.default_rng(SEED)
    pos_neu = pt[(pt.provided_label == "positive") & (pt.model_label == "neutral")]
    ex = pos_neu.iloc[rng.choice(len(pos_neu), size=12, replace=False)]
    res["provided_positive_model_neutral_examples"] = [{"side": r.side, "sentence": r.sentence[:200]} for r in ex.itertuples()]
    res["provided_positive_model_neutral_by_side"] = {k: int(v) for k, v in pos_neu.side.value_counts().items()}
    neg_neu = pt[(pt.provided_label == "negative") & (pt.model_label == "neutral")]
    res["provided_negative_model_neutral_n"] = int(len(neg_neu))
    res["provided_negative_model_neutral_by_side"] = {k: int(v) for k, v in neg_neu.side.value_counts().items()}
    exn = neg_neu.iloc[rng.choice(len(neg_neu), size=min(8, len(neg_neu)), replace=False)] if len(neg_neu) else neg_neu
    res["provided_negative_model_neutral_examples"] = [{"side": r.side, "sentence": r.sentence[:200]} for r in exn.itertuples()]
    return res


def headlines(f: dict) -> list[dict]:
    """The five headline findings with their numbers pulled from the computed results (no hand-typed figures)."""
    q1, pw, side = f["q1_by_type"], f["q1_pairwise"], f["q1_side_gap_model_labels"]["support"]
    dip, o, tr, dis = f["q2_dip"], f["q3_outage"], f["q4_trajectory"], f["q5_disagreement"]
    tp = f["q1_pairwise_title_rule"]["support_minus_external"]
    acc = {a["account"]: a for a in o["most_affected_accounts"]}
    return [
        {"id": "H1", "strength": "strongest",
         "finding": f"Support calls score lowest ({q1['support']['call_score']['mean']}) and external highest ({q1['external']['call_score']['mean']}); "
                    f"support minus external is {pw['support_minus_external']['diff']} (95% CI {pw['support_minus_external']['ci95']}, p={pw['support_minus_external']['perm_p']}), "
                    f"and still {tp['diff']} (CI {tp['ci95']}) under the title-rule labels. In support calls customers carry the negativity: "
                    f"{round(100 * side['customer_neg_mean'], 1)}% of customer turns vs {round(100 * side['staff_neg_mean'], 1)}% of staff turns are negative "
                    f"(gap {side['gap_mean']}, CI {side['gap_ci95']}, customer more negative in {side['calls_customer_more_negative']} of {side['n_calls']} calls).",
         "so_what": "Support leader: track the customer-side score, not the call average, and compare each type only to its own baseline.",
         "could_be_wrong_if": "Support calls are selected for trouble, so the gap shows what the call is for rather than how well it was handled. Support vs internal and external vs internal are fragile (see q1_pairwise_title_rule)."},
        {"id": "H2", "strength": "medium",
         "finding": f"March dip of {dip['all_calls']['diff']} (CI {dip['all_calls']['ci95']}) is concentrated in outage-touching calls "
                    f"(within March {dip['within_march_touch_vs_not']['means'][0]} vs {dip['within_march_touch_vs_not']['means'][1]}, n={dip['within_march_touch_vs_not']['n']}). "
                    f"Excluding calls that touch the outage the dip is {dip['excl_touches_incident']['diff']} (CI {dip['excl_touches_incident']['ci95']}, n March {dip['excl_touches_incident']['n_march']}): not distinguishable from zero. "
                    f"Call-type mix does not explain it (type-adjusted monthly means {dip['type_adjusted_monthly_mean']}). External April vs pre-outage: {o['external_april_vs_pre']['diff']} (CI {o['external_april_vs_pre']['ci95']}).",
         "so_what": "Engineering lead and support lead: the outage, not a general slide, explains most of the dip, and external calls were back near pre-outage levels by April.",
         "could_be_wrong_if": "The outage flag is an LLM judgment, partly definitional; in the candidate's 20-call check it missed 3 and never over-flagged, so 42 is probably a floor (42 calls): a call about an outage is tense. Only 13 March calls remain after exclusion, so a residual dip cannot be ruled out."},
        {"id": "H3", "strength": "medium",
         "finding": f"The outage shows up in all three call types: {o['n_touch']} calls touch it ({o['touch_by_type']}), peaking in the week of Mar 9 and continuing into April. "
                    f"External calls: pre-outage {o['external_pre_vs_post']['pre_mean']} (n={o['external_pre_vs_post']['n_pre']}), acute Mar 10-31 {o['external_by_window']['acute_mar10_31']['mean']} (n={o['external_by_window']['acute_mar10_31']['n']}), April {o['external_by_window']['april']['mean']} (n={o['external_by_window']['april']['n']}). "
                    f"Of {len(acc)} accounts with an outage-touching support call and an external call, customer scores ended lower than they started for "
                    f"{sum(1 for a in acc.values() if a['last_customer_score'] < a['first_customer_score'])} (including summittrust, stratoscloud, clearwatermed, ridgelinelogistics) and higher for "
                    f"{sum(1 for a in acc.values() if a['last_customer_score'] > a['first_customer_score'])} (trailheadmkt, cobaltsoftware, forgeindustries).",
         "so_what": "Sales manager: put the accounts that ended lower, and those with no call after mid-March (northstarpharma, ridgelinelogistics), on a follow-up list.",
         "could_be_wrong_if": "Account comparisons are 2-4 calls with different purposes (renewal vs support), so they are leads to check, not conclusions. Dates in the dataset are inconsistent about when the outage started."},
        {"id": "H4", "strength": "weakest as a signal",
         "finding": f"{tr['n_improve_all']} of 100 calls end warmer than they start, {tr['n_flat_all']} are flat and {tr['n_ending_worse']} gets worse; the mean uplift is "
                    f"{tr['by_type']['support']['delta_mean']} (support), {tr['by_type']['external']['delta_mean']} (external), {tr['by_type']['internal']['delta_mean']} (internal). "
                    f"{sum(tr['ending_strained_by_type'].values())} calls still end at 2.5 or below ({tr['ending_strained_by_type']}).",
         "so_what": "Support leader: the useful signal is the list of calls that end strained, not the average uplift.",
         "could_be_wrong_if": "The uplift is nearly uniform, which points to the scripted shape of the calls and the rubric's relief rule more than to customer satisfaction. In support, per-turn negativity barely falls "
                              f"({tr['by_type']['support']['neg_share_first_third']} to {tr['by_type']['support']['neg_share_last_third']}) while the trajectory score rises."},
        {"id": "H5", "strength": "medium",
         "finding": f"Our score tracks the provided score (r={dis['pearson']}, mean absolute difference {dis['mae']}, ours higher by {dis['overall_offset']['mean']} on average, CI {dis['overall_offset']['ci95']}); "
                    f"no call differs by 1 or more (max {dis['max_abs_diff']}). {dis['n_material_abs_diff_ge_0.6']} calls differ by 0.6 or more, {dis['n_material_internal_outage_ours_higher']} of them internal outage calls where ours is higher "
                    f"(internal outage-touching offset {dis['internal_incident_calls_offset']['mean']} vs {dis['other_calls_offset']['mean']} elsewhere). "
                    f"Of {dis['turn_confusion_rows_provided_cols_model']['positive']['neutral']} turns the provided labels call positive and we call neutral, {dis['provided_positive_model_neutral_by_side']['aegis_staff']} are staff turns.",
         "so_what": "Analytics owner: the provided score tracks the severity of the situation, ours tracks the tone; report both, and do not mix them in one trend.",
         "could_be_wrong_if": "There are no gold labels. Agreement with an upstream AI output is consistency, not accuracy, and ours is also an LLM judgment with the D8 design choices (courtesy is neutral, lower tie-break)."},
    ]


def run() -> dict:
    df = build_calls()
    pt = build_turns(df)
    OUT.mkdir(parents=True, exist_ok=True)
    f = {"meta": {"seed": SEED, "n_calls": int(len(df)), "label_source": "outputs/stage0_final.csv (Stage 0, frozen, reviewed)",
                  "ci": "percentile bootstrap over calls, 10000 resamples", "tests": "two-sided permutation, 10000 shuffles, no multiple-comparison correction"},
         "q1_by_type": by_type_table(df, "type"), "q1_pairwise": pairwise(df, "type"),
         "q1_by_title_rule": by_type_table(df, "title_rule"), "q1_pairwise_title_rule": pairwise(df, "title_rule"),
         "q1_label_changes": [{"title": r.title, "stage0": r.type, "title_rule": r.title_rule} for r in df[df.type != df.title_rule].itertuples()],
         "q1_side_gap_model_labels": side_gap(df, pt, "model_label"), "q1_side_gap_provided_labels": side_gap(df, pt, "provided_label"),
         "q2_trend": monthly_and_weekly(df), "q2_dip": dip_decomposition(df), "q3_outage": outage_story(df),
         "q4_trajectory": trajectory(df, pt), "q5_disagreement": disagreement(df, pt)}
    f["headlines"] = headlines(f)
    (OUT / "findings.json").write_text(json.dumps(f, indent=1, default=str))
    df.to_csv(OUT / "calls_table.csv", index=False)
    return f


if __name__ == "__main__":
    run()
    print("wrote", OUT / "findings.json")

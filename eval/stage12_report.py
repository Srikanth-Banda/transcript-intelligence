"""Metrics for the production runs of Stage 1 and Stage 2 (D8). Pure computation from saved records.

Run:  PYTHONPATH=src uv run python eval/stage12_report.py
Writes outputs/stage1/stage1_final.csv, outputs/stage2/stage2_final.csv, outputs/stage2/per_turn.jsonl,
outputs/stage12_metrics.json and docs/stage12-run.md.

Wording matters: the provided sentence labels and score are an upstream AI output, so agreement with them is
consistency, not correctness. Nothing here is interpreted beyond the numbers.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ti.load import load_meetings  # noqa: E402

OUT = ROOT / "outputs"
LABELS = ["negative", "neutral", "positive"]


# ---- pure helpers (tested offline) ----------------------------------------------------------------
def mad(a: list[float], b: list[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) if a else float("nan")


def agree(a: list, b: list) -> float:
    return sum(x == y for x, y in zip(a, b)) / len(a) if a else float("nan")


def confusion(model: list[str], provided: list[str]) -> dict:
    """rows = provided label, columns = model label."""
    c = Counter(zip(provided, model))
    return {p: {m: c.get((p, m), 0) for m in LABELS} for p in LABELS}


def pearson(x: list[float], y: list[float]) -> float:
    return float(pd.Series(x).corr(pd.Series(y)))


def spearman(x: list[float], y: list[float]) -> float:
    # scipy is not installed: Spearman = Pearson on average ranks.
    return float(pd.Series(x).rank().corr(pd.Series(y).rank()))


def is_half_step(v: float) -> bool:
    return abs(v * 2 - round(v * 2)) < 1e-9 and abs(v - round(v)) > 1e-9


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


# ---- load -----------------------------------------------------------------------------------------
def load(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def main() -> None:
    meetings = {m.meeting_id: m for m in load_meetings()}
    types = pd.read_csv(OUT / "stage0_final.csv").set_index("meeting_id")["label"].to_dict()
    metrics: dict = {}

    # ---------------- Stage 1 ----------------
    s1 = load(OUT / "stage1" / "stage1_records_run1.json")
    d1 = pd.DataFrame(s1)
    d1["call_type"] = d1["meeting_id"].map(types)
    cols = ["meeting_id", "call_type", "status", "primary_theme", "tags", "product_area", "incident", "confidence",
            "evidence_quote", "other_description", "quote_exact", "quote_loose", "quote_words_ok", "membership_ok",
            "attempts", "taxonomy_version", "cache_hit", "cost", "provider_returned"]
    d1[[c for c in cols if c in d1]].to_csv(OUT / "stage1" / "stage1_final.csv", index=False)
    ok1 = d1[d1["status"] == "ok"]
    other = (ok1["primary_theme"] == "Other / new theme").sum()
    m1 = {
        "n": len(d1), "ok": len(ok1), "status": d1["status"].value_counts().to_dict(),
        "other_share": other / len(ok1) if len(ok1) else None,
        "by_theme": ok1["primary_theme"].value_counts().to_dict(),
        "by_product_area": ok1["product_area"].value_counts().to_dict(),
        "by_incident": ok1["incident"].fillna("none").value_counts().to_dict(),
        "theme_by_type": ok1.groupby(["primary_theme", "call_type"]).size().unstack(fill_value=0).to_dict("index"),
        "incident_by_type": ok1.assign(i=ok1["incident"].fillna("none")).groupby(["i", "call_type"]).size().unstack(fill_value=0).to_dict("index"),
        "quote_exact": int(ok1["quote_exact"].sum()), "quote_loose": int(ok1["quote_loose"].sum()),
        "quote_within_30_words": int(ok1["quote_words_ok"].sum()),
        "retried": int((ok1["attempts"] > 1).sum()),
        "with_tags": int((ok1["tags"].fillna("") != "").sum()),
        "confidence": ok1["confidence"].value_counts().to_dict(),
        "cost": float(d1["cost"].sum()),
    }
    metrics["stage1"] = m1

    s1b = load(OUT / "stage1" / "stage1_records_run2_sample.json")
    if s1b:
        a = {r["meeting_id"]: r for r in s1 if r["status"] == "ok"}
        b = {r["meeting_id"]: r for r in s1b if r["status"] == "ok"}
        ids = sorted(set(a) & set(b))
        metrics["stage1_stability"] = {
            "n": len(ids),
            "primary_theme_agreement": agree([a[i]["primary_theme"] for i in ids], [b[i]["primary_theme"] for i in ids]),
            "product_area_agreement": agree([a[i]["product_area"] for i in ids], [b[i]["product_area"] for i in ids]),
            "incident_agreement": agree([a[i]["incident"] for i in ids], [b[i]["incident"] for i in ids]),
            "tag_set_mean_jaccard": sum(jaccard(set(filter(None, (a[i]["tags"] or "").split("|"))),
                                                set(filter(None, (b[i]["tags"] or "").split("|")))) for i in ids) / len(ids),
            "disagreements": [{"id": i, "run1": a[i]["primary_theme"], "run2": b[i]["primary_theme"]}
                              for i in ids if a[i]["primary_theme"] != b[i]["primary_theme"]],
            "cost_run2": float(sum(r.get("cost", 0) for r in s1b)),
        }

    # ---------------- Stage 2 ----------------
    s2 = load(OUT / "stage2" / "stage2_records_run1.json")
    d2 = pd.DataFrame(s2)
    d2["call_type"] = d2["meeting_id"].map(types)
    ok2 = d2[d2["status"] == "ok"].copy()
    keep = ["meeting_id", "call_type", "status", "n_turns", "call_score", "customer_score", "traj_start", "traj_end",
            "confidence", "evidence_quote", "quote_exact", "quote_loose", "quote_words_ok", "n_neg", "n_neu", "n_pos",
            "attempts", "cache_hit", "cost", "finish_reason", "provider_returned"]
    d2[[c for c in keep if c in d2]].to_csv(OUT / "stage2" / "stage2_final.csv", index=False)
    with open(OUT / "stage2" / "per_turn.jsonl", "w") as f:
        for r in ok2.to_dict("records"):
            prov = meetings[r["meeting_id"]].provided.turn_sentiments
            for t in r["per_turn"]:
                f.write(json.dumps({"meeting_id": r["meeting_id"], "call_type": r["call_type"], "index": t["index"],
                                    "model_label": t["label"], "provided_label": prov[t["index"]]}) + "\n")

    pt = pd.read_json(OUT / "stage2" / "per_turn.jsonl", lines=True) if len(ok2) else pd.DataFrame()
    sent: dict = {}
    if len(pt):
        sent["overall"] = {"n": len(pt), "agreement": agree(pt["model_label"].tolist(), pt["provided_label"].tolist()),
                           "confusion_rows_provided_cols_model": confusion(pt["model_label"].tolist(), pt["provided_label"].tolist())}
        for t, g in pt.groupby("call_type"):
            sent[t] = {"n": len(g), "agreement": agree(g["model_label"].tolist(), g["provided_label"].tolist()),
                       "confusion_rows_provided_cols_model": confusion(g["model_label"].tolist(), g["provided_label"].tolist())}
        sent["label_shares_model"] = pt["model_label"].value_counts(normalize=True).round(4).to_dict()
        sent["label_shares_provided"] = pt["provided_label"].value_counts(normalize=True).round(4).to_dict()
    ok2["provided_score"] = ok2["meeting_id"].map(lambda i: meetings[i].provided.sentiment_score)
    corr = {"all": {"pearson": pearson(ok2["call_score"].tolist(), ok2["provided_score"].tolist()),
                    "spearman": spearman(ok2["call_score"].tolist(), ok2["provided_score"].tolist()),
                    "mean_abs_diff": mad(ok2["call_score"].tolist(), ok2["provided_score"].tolist()), "n": len(ok2)}}
    for t, g in ok2.groupby("call_type"):
        corr[t] = {"pearson": pearson(g["call_score"].tolist(), g["provided_score"].tolist()),
                   "spearman": spearman(g["call_score"].tolist(), g["provided_score"].tolist()),
                   "mean_abs_diff": mad(g["call_score"].tolist(), g["provided_score"].tolist()), "n": len(g)}
    dist = {
        "call_score_counts": {str(k): int(v) for k, v in ok2["call_score"].value_counts().sort_index().items()},
        "half_step_share": float(ok2["call_score"].map(is_half_step).mean()) if len(ok2) else None,
        "mean_by_type": ok2.groupby("call_type")["call_score"].mean().round(3).to_dict(),
        "provided_mean_by_type": ok2.groupby("call_type")["provided_score"].mean().round(3).to_dict(),
        "customer_score_counts": {str(k): int(v) for k, v in ok2["customer_score"].dropna().value_counts().sort_index().items()},
        "trajectory_mean_start_end_by_type": {t: [round(g["traj_start"].mean(), 3), round(g["traj_end"].mean(), 3)] for t, g in ok2.groupby("call_type")},
    }
    metrics["stage2"] = {
        "n": len(d2), "status": d2["status"].value_counts().to_dict(),
        "attempts": {str(k): int(v) for k, v in d2["attempts"].value_counts().items()} if "attempts" in d2 else {},
        "quote_exact": int(ok2["quote_exact"].sum()), "quote_loose": int(ok2["quote_loose"].sum()),
        "quote_within_25_words": int(ok2["quote_words_ok"].sum()),
        "per_turn_complete": int(ok2["per_turn_ok"].sum()) if "per_turn_ok" in ok2 else None,
        "sentence_level_agreement_with_provided": sent, "call_score_vs_provided_score": corr, "distribution": dist,
        "cost": float(d2["cost"].sum()),
    }
    s2b = load(OUT / "stage2" / "stage2_records_run2_sample.json")
    if s2b:
        a = {r["meeting_id"]: r for r in s2 if r["status"] == "ok"}
        b = {r["meeting_id"]: r for r in s2b if r["status"] == "ok"}
        ids = sorted(set(a) & set(b))
        cust = [i for i in ids if a[i]["customer_score"] is not None and b[i]["customer_score"] is not None]
        la, lb = [], []
        for i in ids:
            ma = {t["index"]: t["label"] for t in a[i]["per_turn"]}
            mb = {t["index"]: t["label"] for t in b[i]["per_turn"]}
            for k in sorted(set(ma) & set(mb)):
                la.append(ma[k]); lb.append(mb[k])
        metrics["stage2_stability"] = {
            "n": len(ids), "n_customer": len(cust),
            "call_score_mad": mad([a[i]["call_score"] for i in ids], [b[i]["call_score"] for i in ids]),
            "call_score_identical": sum(a[i]["call_score"] == b[i]["call_score"] for i in ids),
            "customer_score_mad": mad([a[i]["customer_score"] for i in cust], [b[i]["customer_score"] for i in cust]),
            "traj_start_mad": mad([a[i]["traj_start"] for i in ids], [b[i]["traj_start"] for i in ids]),
            "traj_end_mad": mad([a[i]["traj_end"] for i in ids], [b[i]["traj_end"] for i in ids]),
            "per_turn_label_agreement": agree(la, lb), "per_turn_n": len(la),
            "max_call_score_diff": max(abs(a[i]["call_score"] - b[i]["call_score"]) for i in ids),
            "cost_run2": float(sum(r.get("cost", 0) for r in s2b)),
        }
    (OUT / "stage12_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    print(json.dumps(metrics, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()

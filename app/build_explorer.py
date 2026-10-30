"""Build app/explorer.html from the frozen pipeline outputs (no LLM calls, no network).

Every number shown in the explorer is computed here from outputs/ and dataset/ (or read from the
analysis JSON/CSV files that already hold it). The HTML template only draws what this script embeds.

Run:  PYTHONPATH=src uv run python app/build_explorer.py [--out app/explorer.html]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ti.load import load_meetings  # noqa: E402

OUT = ROOT / "outputs"
TYPES = ["support", "external", "internal"]
CODE = {"negative": "g", "neutral": "n", "positive": "p"}

# One short, number-free title per headline id (the numbers live in the finding text from findings.json).
HEADLINE_TITLES = {
    "H1": "Support calls are the least positive, and customers carry it",
    "H2": "The March dip sits in outage-touching calls",
    "H3": "The outage runs through every call type; accounts recover unevenly",
    "H4": "Most calls end warmer than they start (weak as a signal)",
    "H5": "We track the provided score but measure tone, not severity",
}


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def num(v):
    v = str(v).strip()
    return None if v in ("", "nan", "None") else float(v)


def find_quote(turns, quote: str):
    """Locate a verbatim quote in the transcript: (turn index, start, end) or None."""
    if not quote:
        return None
    for i, t in enumerate(turns):
        k = t.sentence.find(quote)
        if k >= 0:
            return [i, k, k + len(quote)]
    return None


def org_names(meetings) -> dict[str, str]:
    """external domain stem -> display name, parsed from titles (e.g. 'Aegis / Northstar Pharma - ...')."""
    names: dict[str, str] = {}
    stems = {}
    for m in meetings:
        for e in m.external_emails:
            stems[e.split("@")[1].split(".")[0].lower()] = True
    for m in meetings:
        title = m.title
        cand = None
        if title.startswith("Aegis / ") and " - " in title:
            cand = title[len("Aegis / "):].split(" - ")[0]
        elif " - " in title:
            cand = title.split(" - ", 1)[1]
        if not cand:
            continue
        words = cand.split()
        acc = ""
        for i, w in enumerate(words):
            acc += re.sub(r"[^a-z0-9]", "", w.lower())
            if acc in stems:
                names.setdefault(acc, " ".join(words[: i + 1]))
                break
    for s in stems:
        names.setdefault(s, s.title())
    return names


def build() -> dict:
    meetings = load_meetings()
    s0 = {r["meeting_id"]: r for r in read_csv(OUT / "stage0_final.csv")}
    s1 = {r["meeting_id"]: r for r in read_csv(OUT / "stage1" / "stage1_final.csv")}
    s2 = {r["meeting_id"]: r for r in read_csv(OUT / "stage2" / "stage2_final.csv")}
    tax = json.load(open(OUT / "stage1" / "taxonomy_v1.json", encoding="utf-8"))
    theme_names = [t["name"] for t in tax["themes"]]
    findings = json.load(open(OUT / "analysis" / "sentiment" / "findings.json", encoding="utf-8"))
    metrics = json.load(open(OUT / "stage12_metrics.json", encoding="utf-8"))
    review = json.load(open(ROOT / "eval" / "stage0_review_verdicts.json", encoding="utf-8"))

    turn_rows: dict[str, list[dict]] = defaultdict(list)
    with open(OUT / "stage2" / "per_turn.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            turn_rows[r["meeting_id"]].append(r)

    orgs = org_names(meetings)
    calls = []
    for m in sorted(meetings, key=lambda x: x.start_time):
        a, b, c = s0[m.meeting_id], s1[m.meeting_id], s2[m.meeting_id]
        tags_str = b["tags"] or ""
        tags = [t for t in sorted(theme_names, key=lambda t: tags_str.find(t)) if t in tags_str and t != b["primary_theme"]]
        ext = m.external_emails
        stem = ext[0].split("@")[1].split(".")[0].lower() if ext else ""
        rows = sorted(turn_rows[m.meeting_id], key=lambda r: r["index"])
        assert len(rows) == len(m.turns), (m.meeting_id, len(rows), len(m.turns))
        tm = "".join(CODE[r["model_label"]] for r in rows)
        pv = "".join(CODE[r["provided_label"]] for r in rows)
        sides = m.speaker_sides()
        att = []
        for e in m.emails:
            nm = " ".join(w.capitalize() for w in e.split("@")[0].split("."))
            att.append([nm, "c" if e in ext else "s"])
        calls.append({
            "id": m.meeting_id, "sid": m.meeting_id[-6:], "date": m.start_time[:10], "month": m.start_time[:7],
            "title": m.title, "min": round(m.duration_min), "org": orgs.get(stem, "") if stem else "", "orgKey": stem,
            "att": att,
            "type": a["label"], "rule": a["title_rule_label"], "s0src": a["source"], "s0conf": a["confidence"], "s0q": a["evidence_quote"],
            "theme": b["primary_theme"], "tags": tags, "area": b["product_area"], "inc": 1 if b["incident"] else 0,
            "core": 1 if b["primary_theme"].startswith("Incident") else 0, "s1conf": b["confidence"], "s1q": b["evidence_quote"],
            "cs": float(c["call_score"]), "cu": num(c["customer_score"]), "t0": float(c["traj_start"]), "t1": float(c["traj_end"]),
            "s2conf": c["confidence"], "s2q": c["evidence_quote"],
            "ps": m.provided.sentiment_score, "pl": m.provided.overall_sentiment,
            "tm": tm, "pv": pv,
            "qloc": {"0": find_quote(m.turns, a["evidence_quote"]) if a["source"] != "metadata" else None,
                     "1": find_quote(m.turns, b["evidence_quote"]), "2": find_quote(m.turns, c["evidence_quote"])},
            "tr": [[t.speaker, "c" if sides[t.speaker] == "customer" else "s", t.sentence] for t in m.turns],
        })

    by_id = {c["id"]: c for c in calls}
    n = len(calls)

    # ---- pipeline strip ------------------------------------------------------------------------
    type_counts = Counter(c["type"] for c in calls)
    pipeline = {
        "n": n,
        "s0": {"counts": {t: type_counts[t] for t in TYPES}, "by_metadata": sum(1 for c in calls if c["s0src"] == "metadata"),
               "by_llm": sum(1 for c in calls if c["s0src"] != "metadata"), "review_agree_model": review["agree_with_model"],
               "review_agree_rule": review["agree_with_title_rule"], "review_n": review["n"]},
        "s1": {"themes": Counter(c["theme"] for c in calls).most_common(), "other": sum(1 for c in calls if c["theme"].startswith("Other")),
               "incident_touch": sum(c["inc"] for c in calls), "incident_core": sum(c["core"] for c in calls)},
        "s2": {"mean": {t: round(st.mean(c["cs"] for c in calls if c["type"] == t), 2) for t in TYPES},
               "turns": sum(len(c["tm"]) for c in calls)},
    }

    # ---- headline findings -----------------------------------------------------------------------
    heads = [{"id": h["id"], "title": HEADLINE_TITLES[h["id"]], "strength": h["strength"], "finding": h["finding"],
              "so_what": h["so_what"], "wrong": h["could_be_wrong_if"]} for h in findings["headlines"]]

    # ---- taxonomy ----------------------------------------------------------------------------------
    themes = [{"name": t["name"], "definition": t["definition"], "boundary": t["boundary_note"], "owner": t["owner"],
               "examples": [{"sid": e["call"], "title": e["title"], "quote": e["quote"]} for e in t.get("examples", [])]}
              for t in tax["themes"]]

    # ---- competitors ----------------------------------------------------------------------------------
    comp_names = [r["competitor"] for r in read_csv(OUT / "analysis" / "candidates" / "e_competitors.csv")]
    mentions = []
    meeting_by_id = {m.meeting_id: m for m in meetings}
    for c in calls:
        m = meeting_by_id[c["id"]]
        sides = m.speaker_sides()
        for i, t in enumerate(m.turns):
            for name in comp_names:
                if name.lower() in t.sentence.lower():
                    mentions.append({"cid": c["id"], "comp": name, "i": i, "speaker": t.speaker,
                                     "side": "c" if sides[t.speaker] == "customer" else "s", "quote": t.sentence})
    comp_calls = {name: sorted({x["cid"] for x in mentions if x["comp"] == name}) for name in comp_names}
    comp = {
        "names": comp_names, "mentions": mentions,
        "calls": {k: len(v) for k, v in comp_calls.items()},
        "by_type": {k: {t: sum(1 for cid in v if by_id[cid]["type"] == t) for t in TYPES} for k, v in comp_calls.items()},
        "by_month": {k: dict(Counter(by_id[cid]["month"] for cid in v)) for k, v in comp_calls.items()},
        "any_calls": len({x["cid"] for x in mentions}),
        "month_calls": dict(Counter(c["month"] for c in calls)),
        "any_by_month": dict(Counter(by_id[cid]["month"] for cid in {x["cid"] for x in mentions})),
        "inc_share_comp": round(st.mean(by_id[cid]["inc"] for cid in {x["cid"] for x in mentions}), 3),
        "inc_share_all": round(st.mean(c["inc"] for c in calls), 3),
    }

    # ---- outage blast radius ------------------------------------------------------------------------------
    acct = defaultdict(list)
    for c in calls:
        if c["orgKey"]:
            acct[c["orgKey"]].append({"cid": c["id"], "date": c["date"], "type": c["type"], "cs": c["cs"], "cu": c["cu"],
                                      "inc": c["inc"], "title": c["title"]})
    accounts = []
    for k, v in acct.items():
        v.sort(key=lambda x: x["date"])
        accounts.append({"key": k, "name": orgs.get(k, k.title()), "calls": v, "touched": sum(x["inc"] for x in v)})
    accounts.sort(key=lambda a: (-a["touched"], a["name"]))
    tone = {}
    for t in TYPES:
        for flag in (1, 0):
            xs = [c["cs"] for c in calls if c["type"] == t and c["inc"] == flag]
            tone[f"{t}|{flag}"] = {"n": len(xs), "mean": round(st.mean(xs), 2) if xs else None}
    blast = {"accounts": accounts, "tone": tone, "n_accounts": len(accounts),
             "n_touched_accounts": sum(1 for a in accounts if a["touched"] > 0),
             "touch_by_type": {t: sum(1 for c in calls if c["type"] == t and c["inc"]) for t in TYPES},
             "week": [{"week": r["week"], "n": int(r["n"]), "mean": float(r["mean_call_score"]), "inc": float(r["incident_share"])}
                      for r in read_csv(OUT / "analysis" / "candidates" / "a_weekly_timeline.csv")]}

    # ---- account risk index ---------------------------------------------------------------------------------
    risk = []
    for r in read_csv(OUT / "analysis" / "candidates" / "b_external_calls_risk_ranking.csv"):
        cu = float(r["customer_score"]); td = float(r["traj_delta"])
        comps = {"tone_le_2_5": 2 if cu <= 2.5 else 0, "tone_le_3_0": 1 if 2.5 < cu <= 3.0 else 0,
                 "fell": 1 if td < 0 else 0, "competitor": 1 if truthy(r["competitor_or_alternatives_by_customer"]) else 0,
                 "outage": 1 if truthy(r["incident"]) else 0}
        pts = sum(comps.values())
        assert pts == int(r["our_points"]), (r["meeting_id"], pts, r["our_points"])
        c = by_id[r["meeting_id"]]
        risk.append({"cid": c["id"], "org": orgs.get(r["org"], r["org"]), "date": r["date"], "title": c["title"], "cu": cu, "td": td,
                     "pts": pts, "comps": comps, "prov": int(r["provided_churn_signal_moments"]), "theme": r["theme"]})
    risk.sort(key=lambda x: (-x["pts"], x["cu"], x["date"]))

    # ---- trust --------------------------------------------------------------------------------------------------------
    m2 = metrics["stage2"]; sl = m2["sentence_level_agreement_with_provided"]
    trust = {
        "s0_review": {"n": review["n"], "agree_model": review["agree_with_model"], "agree_rule": review["agree_with_title_rule"]},
        "s1_stab": {k: metrics["stage1_stability"][k] for k in
                    ("n", "primary_theme_agreement", "product_area_agreement", "incident_agreement", "tag_set_mean_jaccard")},
        "s2_stab": {k: metrics["stage2_stability"][k] for k in
                    ("n", "call_score_mad", "call_score_identical", "max_call_score_diff", "per_turn_label_agreement", "per_turn_n")},
        "quotes": {"s1_exact": metrics["stage1"].get("quote_exact"), "s2_exact": m2["quote_exact"], "s2_within_25": m2["quote_within_25_words"]},
        "sentence_level": {"overall": sl["overall"]["agreement"], "n": sl["overall"]["n"],
                           "by_type": {t: sl[t]["agreement"] for t in TYPES if t in sl}},
        "meta": findings["meta"],
    }

    return {"meta": {"n": n, "types": TYPES, "months": sorted({c["month"] for c in calls}), "areas": sorted({c["area"] for c in calls}),
                      "themes": theme_names},
            "pipeline": pipeline, "heads": heads, "themes": themes, "calls": calls, "comp": comp, "blast": blast, "risk": risk,
            "trust": trust}


def render(data: dict, template: str) -> str:
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = js.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    assert "/*DATA*/null" in template
    return template.replace("/*DATA*/null", js)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "app" / "explorer.html"))
    ap.add_argument("--template", default=str(ROOT / "app" / "explorer_tpl.html"))
    a = ap.parse_args()
    data = build()
    html = render(data, Path(a.template).read_text(encoding="utf-8"))
    Path(a.out).write_text(html, encoding="utf-8")
    print(f"wrote {a.out}: {len(html)/1e6:.2f} MB, {data['meta']['n']} calls")


if __name__ == "__main__":
    main()

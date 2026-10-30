"""Build app/video_walkthrough.html: seven full-screen scenes for the screen-recorded demo.

Every statistic is read from the frozen pipeline outputs (outputs/, outputs/analysis/, eval/*verdicts.json) or
computed from them here; the prose around the numbers comes from DECISIONS.md. No LLM calls, no network.
Scene 6 embeds the real printed output of `eval/demo_replay.py 41` (replay mode, saved model answers).

Run:  PYTHONPATH=src uv run python app/build_walkthrough.py [--out app/video_walkthrough.html]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from html import escape as esc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))

import build_explorer as be  # noqa: E402  (reuses its data assembly: competitors, blast radius, follow-up index)

OUT = ROOT / "outputs"
REPLAY_INDEX = 41
REPLAY_CMD = f"env -u OPENROUTER_API_KEY PYTHONPATH=src uv run python eval/demo_replay.py {REPLAY_INDEX}"
INDEX_MAX = 4  # the published index runs 0 to 4 (docs/analysis-candidates.md)
MONTH = {"2026-02": "Feb", "2026-03": "Mar", "2026-04": "Apr"}


def f2(x) -> str:
    """Two decimals, halves rounded up (2.565 -> 2.57, as the video says)."""
    return str(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def pct(x) -> str:
    return f"{int(Decimal(str(x * 100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))}%"


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def spearman(a: list[float], b: list[float]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5


def run_replay() -> str:
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    env["PYTHONPATH"] = str(ROOT / "src")
    p = subprocess.run([sys.executable, str(ROOT / "eval" / "demo_replay.py"), str(REPLAY_INDEX)], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f"demo_replay failed: {p.stderr[-800:]}")
    return p.stdout.rstrip("\n")


def collect() -> dict:
    ex = be.build()
    find = jload(OUT / "analysis" / "sentiment" / "findings.json")
    metrics = jload(OUT / "stage12_metrics.json")
    stab = jload(OUT / "stage1" / "stability.json")
    examples = jload(OUT / "analysis" / "themes" / "examples.json")
    v0 = jload(ROOT / "eval" / "stage0_review_verdicts.json")
    v1 = jload(ROOT / "eval" / "stage1_review_verdicts.json")["items"]
    v2 = jload(ROOT / "eval" / "stage2_review_verdicts.json")["items"]

    calls = ex["calls"]
    n = ex["meta"]["n"]
    p0 = ex["pipeline"]["s0"]
    type_n = p0["counts"]
    cust_calls = [c for c in calls if c["type"] != "internal"]
    rule_wrong = sum(1 for c in cust_calls if c["type"] != c["rule"])

    q1 = find["q1_by_type"]
    side = find["q1_side_gap_model_labels"]["support"]
    dip = find["q2_dip"]
    monthly = find["q2_trend"]["monthly_overall"]
    touch = dip["within_march_touch_vs_not"]

    comp = ex["comp"]
    tone = ex["blast"]["tone"]
    risk = [r for r in ex["risk"] if r["pts"] >= 3]
    assert all(r["pts"] <= INDEX_MAX for r in ex["risk"])
    ext_title = {c["id"]: c["title"] for c in calls}
    for r in risk:  # display name from the call title, which is cleaner than the domain stem
        t = ext_title[r["cid"]]
        if t.startswith("Aegis / ") and " - " in t:
            r["org"] = t[len("Aegis / "):].split(" - ")[0]

    # hand-checks, recomputed from the verdict files
    s1 = {"n": len(v1),
          "theme": sum(i["theme"] == i["model"]["theme"] for i in v1),
          "area": sum(i["area"] == i["model"]["area"] for i in v1),
          "incident": sum(bool(i["incident"]) == bool(i["model"]["incident"]) for i in v1),
          "missed": sum(bool(i["incident"]) and not i["model"]["incident"] for i in v1),
          "overflagged": sum((not i["incident"]) and bool(i["model"]["incident"]) for i in v1)}
    diffs = [abs(i["callScore"] - i["modelCallScore"]) for i in v2]
    s2 = {"n": len(v2), "within": sum(d <= 0.5 for d in diffs), "exact": sum(d == 0 for d in diffs),
          "rank": spearman([i["callScore"] for i in v2], [i["modelCallScore"] for i in v2])}

    return {"n": n, "type_n": type_n, "p0": p0, "rule_wrong": rule_wrong, "n_cust": len(cust_calls), "q1": q1, "side": side,
            "monthly": monthly, "touch": touch, "comp": comp, "tone": tone, "blast": ex["blast"], "risk": risk,
            "themes": ex["themes"], "theme_counts": dict(ex["pipeline"]["s1"]["themes"]), "other": ex["pipeline"]["s1"]["other"],
            "incident_touch": ex["pipeline"]["s1"]["incident_touch"], "examples": examples, "metrics": metrics,
            "overlap": (stab["run1_to_run2_mean_best_jaccard"] + stab["run2_to_run1_mean_best_jaccard"]) / 2,
            "model": v0["model"], "v0": v0, "s1": s1, "s2": s2, "turns": ex["pipeline"]["s2"]["turns"],
            "with_tags": metrics["stage1"]["with_tags"], "agree_provided": metrics["stage2"]["sentence_level_agreement_with_provided"]["overall"]["agreement"],
            "replay": run_replay()}


# ---------------------------------------------------------------------------------------------------------------------
def bar_row(label, value, lo, hi, vmin, vmax, color, shown, sub="") -> str:
    pos = lambda v: max(0.0, min(100.0, (v - vmin) / (vmax - vmin) * 100))
    ci = ""
    if lo is not None:
        ci = f'<i class="ci" style="left:{pos(lo):.1f}%;width:{pos(hi) - pos(lo):.1f}%"></i>'
    return (f'<div class="brow"><div class="blab"><span>{esc(label)}</span><small>{esc(sub)}</small></div>'
            f'<div class="btrack"><b style="width:{pos(value):.1f}%;background:var({color})"></b>{ci}</div>'
            f'<div class="bval">{esc(shown)}</div></div>')


def scene(sid, idx, tag, title, body, sowhat) -> str:
    return (f'<section class="scene" id="{sid}" data-i="{idx}" hidden aria-label="{esc(title)}">'
            f'<header><div class="eyebrow">Scene {idx} of 7 &middot; {esc(tag)}</div><h2>{title}</h2></header>'
            f'<div class="body">{body}</div>'
            f'<footer class="sowhat"><span class="sw">So what</span><p>{sowhat}</p></footer></section>')


def s1(d) -> str:
    q1, t = d["q1"], d["touch"]
    c = d["comp"]
    flow = (f'<div class="flow"><span class="chip big">{d["n"]} calls in</span><span class="arr">&rarr;</span>'
            f'<span class="chip">Stage 0 &middot; call type</span><span class="arr">&rarr;</span>'
            f'<span class="chip">Stage 1 &middot; themes</span><span class="arr">&rarr;</span>'
            f'<span class="chip">Stage 2 &middot; sentiment</span><span class="arr">&rarr;</span>'
            f'<span class="chip big">3 findings</span></div>')

    def cmp(a, al, b, bl, ca, cb):
        return (f'<div class="vs"><div><b class="n" style="color:var({ca})">{a}</b><span>{al}</span></div>'
                f'<em>vs</em><div><b class="n" style="color:var({cb})">{b}</b><span>{bl}</span></div></div>')

    cards = (
        f'<article class="card f"><h3>Support calls are the least positive</h3>'
        f'{cmp(f2(q1["support"]["call_score"]["mean"]), f"support, {q1["support"]["call_score"]["n"]} calls", f2(q1["external"]["call_score"]["mean"]), f"external, {q1["external"]["call_score"]["n"]} calls", "--c-support", "--c-external")}'
        f'<p>Average tone, 1 (very negative) to 5 (very positive). Customers carry it: {pct(d["side"]["customer_neg_mean"])} of their turns are negative.</p></article>'
        f'<article class="card f"><h3>The March dip sits in outage-touching calls</h3>'
        f'{cmp(f2(t["means"][0]), f"outage-touching, {t["n"][0]} calls", f2(t["means"][1]), f"the rest, {t["n"][1]} calls", "--t-neg", "--t-pos")}'
        f'<p>Both are March calls only. The dip is mostly the outage; I cannot rule out other causes.</p></article>'
        f'<article class="card f"><h3>The outage runs through the rest</h3>'
        f'<div class="vs stack"><div><b class="n">{c["any_calls"]} of {d["n"]}</b><span>calls name a competitor</span></div>'
        f'<div><b class="n">{d["blast"]["n_touched_accounts"]} of {d["blast"]["n_accounts"]}</b><span>accounts had an outage-touching call</span></div></div>'
        f'<p>Co-occurrence, not cause. Plus a list of {len(d["risk"])} external calls for a human to follow up.</p></article>')
    return scene("s1", 1, "the ask and the answer", "The ask and the answer",
                 flow + f'<div class="cards3">{cards}</div>',
                 "Where to look first: support calls, the March outage, and the accounts worth a call back. Every score comes with a quote from the call.")


def s2(d) -> str:
    tm = d["type_n"]
    cards = [
        {"id": "D1", "name": "Call type", "problem": "Every call needs a type, and a title rule only works where titles say &ldquo;Support Case&rdquo;.",
         "opts": [("Title rule alone", f"misses {d['rule_wrong']} of {d['n_cust']} customer calls", 0), ("Model on all calls", "adds error where metadata is certain", 0),
                  ("Email check, then model on the opening", "title withheld from the model", 1)],
         "chose": f"Calls with no outside attendee are internal ({tm['internal']}, no model). A model reads the opening of the other {d['n_cust']} and picks support or external.",
         "why": "Withholding the title keeps the title rule a real cross-check. A model that sees &ldquo;Support Case #9279&rdquo; would just copy it.",
         "weak": f"No ground truth. The title-rule cross-check is wrong on {d['rule_wrong']} of {d['n_cust']}, and my own review of {d['v0']['n']} items is small."},
        {"id": "D3 / D8", "name": "Themes", "problem": "I need categories a manager can act on. Asking a model to discover themes gave a different list each run.",
         "opts": [("Re-cluster every batch", "categories shift under the dashboard", 0), ("Hand-written list, no discovery", "imposes my assumptions", 0),
                  ("Model proposes once, a human freezes", f"{len(d['themes'])} themes, each with an owner", 1)],
         "chose": f"Freeze an {len(d['themes'])}-theme taxonomy and classify every call against it. A call that fits nothing goes to Other ({d['other']}% here).",
         "why": f"Two discovery runs overlapped only {f2(d['overlap'])}. The human-level freeze is the real taxonomy, not the raw proposal.",
         "weak": "Finalised by my assistant under delegation, built from the same calls it labels. Small themes have few examples."},
        {"id": "D2 / D8", "name": "Sentiment", "problem": "The provided score is already an AI output. I need my own measure, with a quote behind every score.",
         "opts": [("Use the provided score", "adds no new insight", 0), ("Word list or ready-made classifier", "outage words read negative; no quotes", 0),
                  ("One model pass, written 1-5 anchors", "customer and staff scored per turn", 1)],
         "chose": "One pass per call: a 1-5 score against written anchors, a label for every turn, customer and staff apart. The whole-call score exists for all 100 calls.",
         "why": "In support calls the customer carries the negativity, so side matters. Internal calls have no customer, so the whole call is the unit.",
         "weak": f"A model judges tone, with its own bias. Anchors mix tone and outcome. It agrees with the provided labels on {pct(d['agree_provided'])} of turns: consistent, not proof."},
        {"id": "D7", "name": "Model", "problem": "One model for all three stages, picked on evidence from our own calls, not a leaderboard.",
         "opts": [("Cheapest model per stage", "my own pre-written rule", 0), ("A larger model", "costlier, no measured gain", 0),
                  ("Gemini 3.8 Flash for all stages", "bake-off on our data", 1)],
         "chose": "Gemini 3.8 Flash for every stage, provider pinned, temperature 0, fixed seed. Any change means re-running the stage for all calls.",
         "why": "It was the only model that honoured both settings and gave the same Stage 0 answers across repeat runs.",
         "weak": "My pre-written rule scored format, not correctness, so it just picked the cheapest. I overrode it and I say so."},
    ]
    rail = "".join(f'<button class="rail" data-card="{i}"><b>{esc(c["id"])}</b><span>{esc(c["name"])}</span></button>' for i, c in enumerate(cards))
    body = []
    for i, c in enumerate(cards):
        opts = "".join(f'<li class="{"pick" if k else ""}"><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a, b, k in c["opts"])
        body.append(
            f'<article class="dcard" data-card="{i}" hidden><div class="dgrid">'
            f'<div class="blk"><h4>The problem</h4><p class="lead">{c["problem"]}</p></div>'
            f'<div class="blk"><h4>Options I weighed</h4><ul class="opts">{opts}</ul></div>'
            f'<div class="blk"><h4>What I chose</h4><p>{c["chose"]}</p></div>'
            f'<div class="blk"><h4>Why</h4><p>{c["why"]}</p></div>'
            f'<div class="blk weak"><h4>Known weakness</h4><p>{c["weak"]}</p></div></div></article>')
    return scene("s2", 2, "decisions that shaped the pipeline", "Decisions that shaped the pipeline",
                 f'<div class="s2wrap"><nav class="railbar" aria-label="Decisions">{rail}</nav><div class="cardarea">{"".join(body)}</div></div>'
                 '<p class="hint">Click a decision, or press the right arrow to reveal the next one.</p>',
                 "Each choice is judged as a stage that runs again on every new batch of calls, and each one carries a weakness I wrote down.")


def s3(d) -> str:
    rows, panels = [], []
    top = max(d["theme_counts"].values())
    ordered = sorted(d["themes"], key=lambda t: -d["theme_counts"][t["name"]])
    for i, t in enumerate(ordered):
        cnt = d["theme_counts"][t["name"]]
        ex = d["examples"][t["name"]]
        clear = next(e for e in ex if e["kind"] == "clear")
        bord = next(e for e in ex if e["kind"] == "borderline")
        rows.append(f'<button class="trow{" on" if i == 0 else ""}" data-t="{i}"><span class="tn">{esc(t["name"])}</span>'
                    f'<span class="tbar"><b style="width:{cnt / top * 100:.0f}%"></b></span><span class="tc">{cnt}</span></button>')
        panels.append(
            f'<div class="tpanel" data-t="{i}"{"" if i == 0 else " hidden"}>'
            f'<div class="owner"><span>Owner</span> {esc(t["owner"])}</div>'
            f'<p class="defn">{esc(t["definition"])}</p>'
            f'<blockquote>&ldquo;{esc(clear["quote"])}&rdquo;<cite>{esc(clear["title"])} &middot; {esc(clear["date"])} &middot; {esc(clear["type"])} call</cite></blockquote>'
            f'<div class="border"><span>Borderline case</span> &ldquo;{esc(bord["quote"][:150].rstrip())}{"&hellip;" if len(bord["quote"]) > 150 else ""}&rdquo;'
            f' <small>{esc(bord["why"])}</small></div></div>')
    return scene("s3", 3, "stage 1", "Eight themes, each with an owner",
                 f'<div class="s3wrap"><div class="tlist">{"".join(rows)}</div><div class="tright">{"".join(panels)}</div></div>'
                 f'<p class="hint">Click a theme to see a real quote. Boundary cases are real: {d["with_tags"]} of {d["n"]} calls also carry a second theme tag.</p>',
                 f"Each theme has someone who can act on it, and none of the {d['n']} calls needed &ldquo;Other&rdquo; ({d['other']}%).")


def s4(d) -> str:
    q1, mo, t, sd = d["q1"], d["monthly"], d["touch"], d["side"]
    types = "".join(bar_row(k.capitalize(), q1[k]["call_score"]["mean"], *q1[k]["call_score"]["ci95"], 1, 5, f"--c-{k}",
                            f2(q1[k]["call_score"]["mean"]), f'{q1[k]["call_score"]["n"]} calls') for k in ("support", "external", "internal"))
    neg = (bar_row("Customer turns", sd["customer_neg_mean"], None, None, 0, 0.5, "--t-neg", pct(sd["customer_neg_mean"]), "negative")
           + bar_row("Staff turns", sd["staff_neg_mean"], None, None, 0, 0.5, "--t-neg", pct(sd["staff_neg_mean"]), "negative"))
    months = "".join(bar_row(MONTH[m], mo[m]["mean"], None, None, 1, 5, "--ink2", f2(mo[m]["mean"]), f'{mo[m]["n"]} calls') for m in ("2026-02", "2026-03", "2026-04"))
    split = (bar_row("March, touch the outage", t["means"][0], None, None, 1, 5, "--t-neg", f2(t["means"][0]), f'{t["n"][0]} calls')
             + bar_row("March, do not", t["means"][1], None, None, 1, 5, "--t-pos", f2(t["means"][1]), f'{t["n"][1]} calls'))
    body = (f'<div class="cards3">'
            f'<article class="card"><h3>Tone by call type</h3><p class="cap">Average 1-5; thin line is the 95% range.</p>{types}</article>'
            f'<article class="card"><h3>Who sounds negative in support calls</h3><p class="cap">Share of turns labelled negative.</p>{neg}</article>'
            f'<article class="card"><h3>The March dip</h3><p class="cap">Average tone by month, then March split.</p>{months}<hr>{split}</article></div>'
            '<div class="plain"><b>Mostly the outage, cannot rule out other causes.</b> Outside the outage-touching calls, the March dip is not distinguishable from zero.</div>')
    return scene("s4", 4, "stage 2", "Sentiment and the March dip", body,
                 f"Support is where tone is lowest, and customers carry it. The March dip tracks the outage, with only {t['n'][1]} non-outage March calls to compare.")


def s5(d) -> str:
    c, tone = d["comp"], d["tone"]
    mon = "".join(f'<div class="mt"><b>{c["any_by_month"][m]}/{c["month_calls"][m]}</b><span>{MONTH[m]}</span></div>' for m in ("2026-02", "2026-03", "2026-04"))
    names = ", ".join(f'{esc(k)} {v}' for k, v in sorted(c["calls"].items(), key=lambda kv: -kv[1]))
    col1 = (f'<article class="card"><h3>Competitor mentions</h3><div class="big"><b>{c["any_calls"]}</b> of {d["n"]} calls</div>'
            f'{bar_row("Calls naming a competitor", c["inc_share_comp"], None, None, 0, 1, "--t-neg", pct(c["inc_share_comp"]), "outage-related")}'
            f'{bar_row("All calls", c["inc_share_all"], None, None, 0, 1, "--ink2", pct(c["inc_share_all"]), "outage-related")}'
            f'<p class="cap">Calls naming a competitor, by month</p><div class="mts">{mon}</div>'
            f'<p class="cap">{names} calls. They appear together with the outage; I do not claim one drives the other.</p></article>')
    lows = []
    for t in ("support", "external", "internal"):
        a, b = tone[f"{t}|1"]["mean"], tone[f"{t}|0"]["mean"]
        lows.append((t, a, b))
    gaps = [b - a for _, a, b in lows]
    pairs = "".join(f'<div class="pair"><h5>{t.capitalize()}</h5>'
                    + bar_row("touch the outage", a, None, None, 1, 5, "--t-neg", f2(a), f'{tone[f"{t}|1"]["n"]} calls')
                    + bar_row("do not", b, None, None, 1, 5, "--t-pos", f2(b), f'{tone[f"{t}|0"]["n"]} calls') + '</div>' for t, a, b in lows)
    col2 = (f'<article class="card"><h3>Blast radius</h3><div class="big"><b>{d["blast"]["n_touched_accounts"]}</b> of {d["blast"]["n_accounts"]} accounts</div>'
            f'<p class="cap">had a call that touches the outage. Outage-touching calls are lower in every type, by {f2(min(gaps))} to {f2(max(gaps))} points.</p>{pairs}</article>')
    rk = "".join(f'<tr><td>{esc(r["org"])}</td><td class="num">{esc(r["date"][5:])}</td><td class="num">{r["cu"]:.1f}</td><td class="num"><b>{r["pts"]}</b></td></tr>' for r in d["risk"])
    col3 = (f'<article class="card"><h3>Account follow-up list</h3><div class="big"><b>{len(d["risk"])}</b> external calls</div>'
            f'<table><thead><tr><th>Account</th><th class="num">Date</th><th class="num">Tone</th><th class="num">Index</th></tr></thead><tbody>{rk}</tbody></table>'
            f'<p class="cap">Index 0-{INDEX_MAX}: low customer tone, tone falling, competitor raised, outage-related. A ranked list for a human, not a prediction.</p></article>')
    return scene("s5", 5, "three insights", "Three insights, one story", f'<div class="cards3 tight">{col1}{col2}{col3}</div>',
                 "These are leads for people to check, not causes. The outage runs through all three.")


def s6(d) -> str:
    tm, p0 = d["type_n"], d["p0"]
    stages = (
        f'<div class="stages"><div class="stg"><span class="tag">Stage 0</span><b>Call type</b><p>{p0["by_metadata"]} internal by attendee emails, {p0["by_llm"]} by a model reading the opening: {tm["support"]} support, {tm["external"]} external, {tm["internal"]} internal.</p></div>'
        f'<span class="arr">&rarr;</span>'
        f'<div class="stg"><span class="tag">Stage 1</span><b>Themes</b><p>One of {len(d["themes"])} themes, product area, outage flag, and a quote. Other: {d["other"]}%.</p></div>'
        f'<span class="arr">&rarr;</span>'
        f'<div class="stg"><span class="tag">Stage 2</span><b>Sentiment</b><p>A 1-5 call score, a label on each of {d["turns"]:,} turns, and a quote.</p></div></div>')
    term = (f'<div class="term"><div class="tbarx"><span>captured output of the replay command</span></div>'
            f'<pre><span class="prompt">$</span> {esc(REPLAY_CMD)}\n{esc(d["replay"])}</pre></div>')
    return scene("s6", 6, "the pipeline running", "The pipeline running", stages + term +
                 '<p class="replay">replay: saved model answers, no key, no network; a miss is an error, never a silent live call</p>',
                 "The same saved answers give the same results, so anyone can re-run a call and check it without a key.")


def s7(d) -> str:
    a, b, v = d["s1"], d["s2"], d["v0"]
    checks = (f'<div class="hc"><span>Stage 0 &middot; call type</span><b>{v["agree_with_model"]}/{v["n"]}</b><small>agree with the model; {v["agree_with_title_rule"]}/{v["n"]} with the title rule</small></div>'
              f'<div class="hc"><span>Stage 1 &middot; theme</span><b>{a["theme"]}/{a["n"]}</b></div>'
              f'<div class="hc"><span>Stage 1 &middot; product area</span><b>{a["area"]}/{a["n"]}</b></div>'
              f'<div class="hc"><span>Stage 1 &middot; outage flag</span><b>{a["incident"]}/{a["n"]}</b><small>all {a["missed"]} misses: I flagged it, the model did not</small></div>'
              f'<div class="hc"><span>Stage 2 &middot; call score</span><b>{b["within"]}/{b["n"]}</b><small>within 0.5; {b["exact"]} exact; rank correlation {f2(b["rank"])}</small></div>')
    cav = [f"Small samples: {v['n']}, {a['n']} and {b['n']} calls, my own review.",
           "I cannot confirm I did not see the model's answers first.",
           "Taxonomy and anchors were finalised under delegation to my assistant, from the same calls.",
           "The data looks synthetic: call shapes are very uniform.",
           f"The outage flag is probably a floor: it missed {a['missed']} of {a['n']} and never over-flagged, so {d['incident_touch']} is a low count."]
    no = ["That the outage caused the March dip or the competitor mentions.",
          "That the follow-up list predicts churn. It ranks calls for a human.",
          "That the scores are correct. They are consistent with the provided score, itself an AI output.",
          "That this holds for real customers or other months."]
    li = lambda xs: "".join(f"<li>{esc(x)}</li>" for x in xs)
    body = (f'<div class="cards3"><article class="card"><h3>My hand-checks</h3>{checks}</article>'
            f'<article class="card"><h3>Caveats</h3><ul class="plainlist">{li(cav)}</ul></article>'
            f'<article class="card nc"><h3>What I would not claim</h3><ul class="plainlist">{li(no)}</ul></article></div>'
            '<p class="deckline">Full deck (21 slides, with speaker notes) is in the repo: deck/transcript-intelligence-findings.pptx</p>')
    return scene("s7", 7, "how far to trust it", "How far to trust it, and what I would not claim", body,
                 "The checks are small and mine, so read the results as strong leads. Anything stronger needs more calls and a second reader.")


NAV = ["The answer", "Decisions", "Themes", "Sentiment", "Insights", "Running", "Trust"]


def render(d: dict, template: str) -> str:
    scenes = "".join([s1(d), s2(d), s3(d), s4(d), s5(d), s6(d), s7(d)])
    nav = "".join(f'<button data-go="{i + 1}"><b>{i + 1}</b> {esc(n)}</button>' for i, n in enumerate(NAV))
    assert "<!--SCENES-->" in template and "<!--NAV-->" in template
    return template.replace("<!--SCENES-->", scenes).replace("<!--NAV-->", nav)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "app" / "video_walkthrough.html"))
    ap.add_argument("--template", default=str(ROOT / "app" / "walkthrough_tpl.html"))
    a = ap.parse_args()
    html = render(collect(), Path(a.template).read_text(encoding="utf-8"))
    Path(a.out).write_text(html, encoding="utf-8")
    print(f"wrote {a.out}: {len(html) / 1e6:.3f} MB")


if __name__ == "__main__":
    main()

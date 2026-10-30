"""Build app/video_walkthrough.html: nine full-screen scenes (the whole assignment, end to end) for the screen-recorded demo.

Every statistic is read from the frozen pipeline outputs (outputs/, outputs/analysis/, eval/*verdicts.json) or
computed from them here; the prose around the numbers comes from DECISIONS.md. No LLM calls, no network.
Scene 8 embeds the real printed output of `eval/demo_replay.py 41` (replay mode, saved model answers).

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


def monthly_all(find) -> dict:
    return find["q2_trend"]["monthly_overall"]


def candidates() -> list[dict]:
    """The ranked Task 3 candidates, parsed from the table in docs/analysis-candidates.md (rank, name, stakeholder, evidence, build cost, score)."""
    rows = []
    for ln in (ROOT / "docs" / "analysis-candidates.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) == 6 and c[0].isdigit():
            rows.append({"rank": int(c[0]), "name": c[1], "who": c[2], "evidence": c[3], "cost": c[4], "score": int(c[5])})
    assert len(rows) == 6, rows
    return rows


def assignment_text() -> str:
    return " ".join((ROOT / "assignment.md").read_text(encoding="utf-8").split())


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
            "corr": find["q5_disagreement"]["pearson"], "months": monthly_all(find), "cands": candidates(), "assignment": assignment_text(),
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




TOTAL = 9
CRITERIA = ["Stable over time", "Owned, actionable", "Evidence quote", "No upstream input", "Scales to check", "One method", "Every call", "Cost, parts"]
MARKS = {"y": ("&#10003;", "meets"), "n": ("&#10005;", "breaks"), "w": ("~", "at risk"), "": ("&middot;", "not decisive")}
# Decision-criteria marks come from the "Criteria" column of the options tables in DECISIONS.md (D1, D2/D2a, D3/D3a, D7) and B2.


def scene(sid, idx, tag, title, body, sowhat) -> str:
    return (f'<section class="scene" id="{sid}" data-i="{idx}" hidden aria-label="{esc(title)}">'
            f'<header><div class="eyebrow">Scene {idx} of {TOTAL} &middot; {tag}</div><h2>{title}</h2></header>'
            f'<div class="body">{body}</div>'
            f'<footer class="sowhat"><span class="sw">So what</span><p>{sowhat}</p></footer></section>')


def s1(d) -> str:
    q1, t, c = d["q1"], d["touch"], d["comp"]
    tasks = ["Categorise the calls by theme", "Sentiment across call types, and what the trends mean", "2-3 further insights"]
    dels = ["Slide deck", "Notebook or repo", "Video demo, 5-10 min"]
    strip = ('<div class="strip"><div class="srow"><span class="slab">Three tasks</span>'
             + "".join(f'<span class="chip"><b>{i + 1}</b> {esc(x)}</span>' for i, x in enumerate(tasks)) + '</div>'
             '<div class="srow"><span class="slab">Three deliverables</span>'
             + "".join(f'<span class="chip">{esc(x)}</span>' for x in dels) + '</div></div>')

    def cmp(a, al, b, bl, ca, cb):
        return (f'<div class="vs"><div><b class="n" style="color:var({ca})">{a}</b><span>{al}</span></div>'
                f'<em>vs</em><div><b class="n" style="color:var({cb})">{b}</b><span>{bl}</span></div></div>')

    cards = (
        f'<article class="card f"><span class="tag">Task 2</span><h3>Support calls are the least positive</h3>'
        f'{cmp(f2(q1["support"]["call_score"]["mean"]), f"support, {q1["support"]["call_score"]["n"]} calls", f2(q1["external"]["call_score"]["mean"]), f"external, {q1["external"]["call_score"]["n"]} calls", "--c-support", "--c-external")}'
        f'<p>Average tone, 1 to 5. Customers carry it: {pct(d["side"]["customer_neg_mean"])} of their turns are negative.</p></article>'
        f'<article class="card f"><span class="tag">Task 2</span><h3>The March dip sits in outage-touching calls</h3>'
        f'{cmp(f2(t["means"][0]), f"outage-touching, {t["n"][0]} calls", f2(t["means"][1]), f"the rest, {t["n"][1]} calls", "--t-neg", "--t-pos")}'
        f'<p>Both are March calls. The dip is mostly the outage; I cannot rule out other causes.</p></article>'
        f'<article class="card f"><span class="tag">Task 3</span><h3>Competitors come up in a third of calls</h3>'
        f'<div class="vs stack"><div><b class="n">{c["any_calls"]} of {d["n"]}</b><span>calls name a competitor</span></div>'
        f'<div><b class="n">{d["blast"]["n_touched_accounts"]} of {d["blast"]["n_accounts"]}</b><span>accounts had an outage-touching call</span></div></div>'
        f'<p>Co-occurrence, not cause.</p></article>')
    return scene("s1", 1, "the ask and the answer", "The ask and the answer", strip + f'<div class="cards3">{cards}</div>',
                 "Where to look first: support calls, the March outage, and the accounts worth a call back. Every score comes with a quote from the call.")


def s2(d) -> str:
    tm, p0 = d["type_n"], d["p0"]
    mo = d["months"]
    rows = [
        ("No call-type label", f"Nothing says support, external or internal. A title rule misses {d['rule_wrong']} of the {d['n_cust']} customer calls.",
         f"Stage 0: {p0['by_metadata']} calls with no outside attendee are internal. A model reads the opening of the other {d['n_cust']}."),
        ("An AI summary, score and topics came with the data", f"The provided score tracks its own sentence labels at 0.94. The topics are 351 different strings.",
         f"Kept apart, never an input to any stage. Used only to compare: my score tracks theirs at {f2(d['corr'])}, which is consistency, not proof."),
        ("A March outage skews the timeline", f"Monthly tone: Feb {f2(mo['2026-02']['mean'])}, Mar {f2(mo['2026-03']['mean'])}, Apr {f2(mo['2026-04']['mean'])}. Some call dates disagree with their content.",
         f"A separate outage flag on every call ({d['incident_touch']} touch it), so March splits into touching and not. No date-based before and after."),
        ("100 calls, apparently synthetic, no outcomes", "One fictional company, repeated score values, no churn or renewal labels.",
         "No synthetic data added. Every trend is directional, and the follow-up list ranks calls for a person. It predicts nothing."),
        ("Speaker roles are missing", "Nothing says who is the customer and who is Aegis staff.",
         "Side comes from the invitee names, and the Stage 0 model is checked against it. Stage 2 scores the customer apart from staff."),
    ]
    body = ('<div class="traps"><div class="th"></div><div class="th">What I found</div><div class="th">What I did about it</div>'
            + "".join(f'<h3 class="tname">{esc(a)}</h3><p>{esc(b)}</p><p class="did">{esc(c)}</p>' for a, b, c in rows) + '</div>')
    return scene("s2", 2, "orientation", "What the data hides", body,
                 "Each trap changed the design: a model call only where metadata cannot decide, and the provided answers held back as a yardstick.")


def s3(d) -> str:
    tm, p0 = d["type_n"], d["p0"]
    v0, a, b = d["v0"], d["s1"], d["s2"]

    def node(cls, tag, title, sees, never, out, rev, extra=""):
        return (f'<div class="node {cls}"><div class="nh"><span class="ntag">{tag}</span><b>{title}</b></div>{extra}'
                f'<p><span class="lab ok">Sees</span> {sees}</p><p><span class="lab no">Never</span> {never}</p>'
                f'<p><span class="lab">Output</span> {out}</p><p class="rv"><span class="lab hr">Review</span> {rev}</p></div>')

    data = (f'<div class="node nd"><div class="nh"><span class="ntag">Input</span><b>{d["n"]} calls</b></div>'
            '<p>Six files per call. The stages read the transcript, attendee emails and speaker names.</p>'
            '<div class="withheld"><span class="lab no">Withheld</span> The provided score, summary, topics and title. Kept only to compare against.</div></div>')
    s0 = node("n0", "Stage 0", "Call type", f'attendee emails. No outside attendee: internal, no model. Otherwise the first ~8 turns.',
              "the title, or the rest of the call.", f'<span class="pills"><span>support {tm["support"]}</span><span>external {tm["external"]}</span><span>internal {tm["internal"]}</span></span>',
              f'{v0["n"]} items, mine. Calls where the model and the title rule disagree come to me.')
    s1n = node("n1", "Stage 1 &middot; with Stage 2", "Themes", "the full transcript.", "provided topics or summary. Call type only slices the results.",
               "a theme, a product area, an outage flag, a quote.", f'my check on {a["n"]} calls. Other above 10% means a new taxonomy version.',
               extra='<div class="two"><span><b>Once</b> a model proposes, a person freezes taxonomy v1</span><span><b>Every call</b> classify against it</span></div>')
    s2n = node("n2", "Stage 2 &middot; with Stage 1", "Sentiment", "the full transcript, and who is the customer.", "the provided score, or the call type.",
               "a 1-5 call score, a label per turn, a quote.", f'my check on {b["n"]} calls.')
    s3n = ('<div class="node n3"><div class="nh"><span class="ntag">Stage 3</span><b>Insights and explorer</b></div>'
           '<p><span class="lab ok">Sees</span> the outputs of Stages 0 to 2. No model call.</p>'
           '<p><span class="lab">Output</span> three insights, the explorer, the deck numbers.</p>'
           '<p class="rv"><span class="lab hr">Review</span> the follow-up list goes to a person, not to an action.</p></div>')
    bar = ('<div class="pbar"><p><b>One model for every stage:</b> Gemini 3.8 Flash, provider pinned, temperature 0, seed 7.</p>'
           '<p><b>Replayable cache:</b> every answer saved by input. In replay a miss is an error, so no key is needed.</p></div>')
    body = f'<div class="pipe">{data}{s0}{s1n}{s2n}{s3n}</div>{bar}'
    return scene("s3", 3, "decisions D1, D3, D5, D7, D8", "The pipeline, end to end", body,
                 "Each stage reads only what it should, one pinned model runs them all, and my own review checks what each stage produces.")


def tickrow(opts, cols=CRITERIA) -> str:
    head = '<tr><th></th>' + "".join(f'<th class="mk">{esc(c)}</th>' for c in cols) + '</tr>'
    rows = []
    for name, why, marks, pick in opts:
        cells = "".join(f'<td class="mk m-{m or "x"}" title="{MARKS[m][1]}"><span aria-label="{MARKS[m][1]}">{MARKS[m][0]}</span></td>'
                        for m in marks)
        rows.append(f'<tr class="{"pick" if pick else ""}"><th scope="row"><b>{name}</b><span>{why}</span></th>{cells}</tr>')
    return f'<table class="opt"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table>'


def mk(**kw) -> list[str]:
    """Marks for criteria 1-8 from c1..c8 keywords; a missing one means not decisive."""
    return [kw.get(f"c{i}", "") for i in range(1, 9)]


KEY = '<p class="legend"><span class="ok">&#10003;</span> meets <span class="no">&#10005;</span> breaks <span class="w">~</span> at risk <span>&middot;</span> not decisive. Criteria from DECISIONS.md, B2.</p>'


def s4(d) -> str:
    tm = d["type_n"]
    cands = d["cands"]
    cards = [
        {"id": "D1", "name": "Call type", "prob": "Every call needs a type, and the data has none. A title rule only works where titles say &ldquo;Support Case&rdquo;.",
         "opts": [("Title rule alone", f"misses {d['rule_wrong']} of {d['n_cust']} customer calls; relies on a naming habit", mk(c1="n", c6="y", c7="y", c8="y"), 0),
                  ("A model on all 100 calls", "adds error where metadata is certain", mk(c3="y"), 0),
                  ("Email check, then a model on the opening", "title withheld, so the title rule stays a real cross-check", mk(c1="y", c3="y", c5="y", c8="y"), 1)],
         "also": "Also rejected: manual overrides of the three escalation calls (not reproducible); a fourth label &ldquo;escalation&rdquo; (breaks the three types).",
         "why": f"Metadata decides the {tm['internal']} internal calls with no model. A model reads the opening of the other {d['n_cust']}. A model that saw &ldquo;Support Case #9279&rdquo; would just copy it.",
         "weak": f"No ground truth. The title rule is wrong on {d['rule_wrong']} of {d['n_cust']}, and my own review covers {d['v0']['n']} items.", "note": ""},
        {"id": "D3 / D8", "name": "Themes", "prob": "I need categories a manager can act on, and they must not change when new calls arrive.",
         "opts": [("Re-cluster every batch", "categories shift under the dashboard", mk(c1="n"), 0),
                  ("Embeddings and clustering as the main method", "a second provider; unstable at 100 calls", mk(c8="n"), 0),
                  ("A model proposes once, a person freezes it, then classify every call", f"{len(d['themes'])} themes, each with an owner and a quote", mk(c1="y", c2="y", c3="y", c4="y", c5="y", c8="y"), 1)],
         "also": "Also rejected: a hand-written list with no discovery (imposes my assumptions); the provided topics or summary as input (breaks no upstream input).",
         "why": f"Discovery gave different lists each run (overlap {f2(d['overlap'])}), so the frozen, reviewed list is the real taxonomy. A new call is classified alone. Other: {d['other']}% here.",
         "weak": "Built from the same 100 calls it labels. Small themes have few examples. A person must act on the Other bucket.",
         "note": "Taxonomy v1 was finalised by my assistant under my delegation. I reviewed the output afterwards and can veto."},
        {"id": "D2 / D8", "name": "Sentiment", "prob": "The provided score is already an AI output. I need my own measure, with a quote behind every score.",
         "opts": [("Use the provided score", "adds no new insight", mk(c4="n"), 0),
                  ("A ready-made classifier or a word list", "no quotes; &ldquo;outage&rdquo; reads negative", mk(c3="n", c6="y", c8="n"), 0),
                  ("One model pass against written 1-5 anchors", "score per call, label per turn, customer and staff apart", mk(c3="y", c4="y", c5="y", c6="w", c7="y", c8="y"), 1)],
         "also": "Also rejected: two separate passes (more cost, two outputs to reconcile); scoring only the customer side (no customer in 30 internal calls).",
         "why": "The whole-call score exists for all 100 calls, so the three types compare. Tone on thousands of turns lets agreement be measured, plus my small check.",
         "weak": f"A model judges tone, with its own bias. Ties go lower when a problem is unresolved. It agrees with the provided labels on {pct(d['agree_provided'])} of turns: consistent, not proof.",
         "note": "The 1-5 anchors were accepted by my assistant under my delegation. Pinned versions cover the one-method risk."},
        {"id": "D7", "name": "Model", "prob": "One model for all three stages, picked on evidence from our own calls, not a leaderboard.",
         "opts": [("Claude Haiku 5.5, cheapest at Stage 0", "5 title-rule disagreements against 3; quotes vary run to run", mk(c3="w", c6="w", c8="y"), 0),
                  ("Claude Sonnet 5.5", "$0.836 against $0.225 on the 15-call sample, no measured gain", mk(c6="n", c8="n"), 0),
                  ("Gemini 3.8 Flash for every stage", "lists temperature and seed; same Stage 0 answers on 3 runs", mk(c3="y", c6="y", c8="y"), 1)],
         "also": "Also not selected: GPT-6.1 Terra (fell back to plain JSON on every Stage 2 call, so its numbers are confounded); other families (no evidence either way).",
         "why": "It was the only shortlisted model that lists both settings and repeated Stage 0 exactly. One client and one provider pin for all stages.",
         "weak": "The sample was 15 calls on draft prompts. Temperature 0 does not guarantee identical output, so reproducibility comes from the cache.",
         "note": "My pre-written rule scored format, not correctness, so it just picked the cheapest. I overrode it for Stage 0 and say so."},
        {"id": "D6", "name": "Bonus insights", "prob": "Task 3 asks for 2-3 more insights. I ranked six candidates. Which ones go on stage?",
         "cols": ["Evidence", "Build cost", "Score /20"],
         "rows": cands, "also": "Not presented: commitment tracking (only 42 of 112 promises have a later call, so described only); support-to-engineering loop (repeat contacts are about different issues); coaching signal (confounded: agents apologise more to unhappy customers).",
         "why": "The top three share data and make one story: the outage made competitors live objections and put specific accounts at risk. That beats six separate ideas for a 30-minute talk.",
         "weak": "No outcome labels, so the follow-up list is unvalidated. The outage flag is an LLM judgment, probably a floor.",
         "note": "The final selection was made by my assistant under my delegation. I can veto it."},
    ]
    rail = "".join(f'<button class="rail" data-card="{i}"><b>{esc(c["id"])}</b><span>{esc(c["name"])}</span></button>' for i, c in enumerate(cards))
    body = []
    for i, c in enumerate(cards):
        if "rows" in c:
            rws = []
            for r in c["rows"]:
                pick = r["rank"] <= 3
                state = "chosen" if pick else ("described only" if r["rank"] == 4 else "not presented")
                rws.append(f'<tr class="{"pick" if pick else ""}"><th scope="row"><b>{esc(r["name"])}</b> <span>&middot; {state}</span></th>'
                           f'<td>{esc(r["evidence"])}</td><td>{esc(r["cost"])}</td><td class="num">{r["score"]}</td></tr>')
            grid = ('<table class="opt d6"><thead><tr><th></th>' + "".join(f'<th class="mk">{esc(x)}</th>' for x in c["cols"]) + '</tr></thead>'
                    f'<tbody>{"".join(rws)}</tbody></table>')
        else:
            grid = tickrow(c["opts"])
        note = f'<p class="honest"><b>Honest note.</b> {c["note"]}</p>' if c["note"] else ""
        if "rows" not in c:
            note += KEY
        body.append(
            f'<article class="dcard" data-card="{i}" hidden><p class="prob"><span>The problem</span> {c["prob"]}</p>'
            f'<div class="optwrap">{grid}</div><p class="also">{c["also"]}</p>'
            f'<div class="wy"><div class="why"><h4>Why this one</h4><p>{c["why"]}</p></div>'
            f'<div class="weak"><h4>Known weakness</h4><p>{c["weak"]}</p></div></div>{note}</article>')
    return scene("s4", 4, "decisions D1, D2, D3, D6, D7, D8", "Decisions: options weighed, best one chosen",
                 f'<div class="s2wrap"><nav class="railbar" aria-label="Decisions">{rail}</nav><div class="cardarea">{"".join(body)}</div></div>',
                 "Each choice is judged as a stage that runs again on every new batch of calls, and each one carries a weakness I wrote down.")


def s5(d) -> str:
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
            f'<div class="border"><span>Borderline case</span> &ldquo;{esc(bord["quote"][:140].rstrip())}{"&hellip;" if len(bord["quote"]) > 140 else ""}&rdquo;'
            f' <small>{esc(bord["why"])}</small></div></div>')
    return scene("s5", 5, "task 1 &middot; stage 1", "Task 1: themes",
                 f'<div class="s3wrap"><div class="tlist">{"".join(rows)}</div><div class="tright">{"".join(panels)}</div></div>'
                 f'<p class="hint">Click a theme to see a real quote. {d["with_tags"]} of {d["n"]} calls also carry a second theme tag.</p>',
                 f"Each theme has someone who can act on it, and none of the {d['n']} calls needed &ldquo;Other&rdquo; ({d['other']}%).")


def s6(d) -> str:
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
    return scene("s6", 6, "task 2 &middot; stage 2", "Task 2: sentiment and the March dip", body,
                 f"Support is where tone is lowest, and customers carry it. The March dip tracks the outage, with only {t['n'][1]} non-outage March calls to compare.")


def s7(d) -> str:
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
            f'<p class="cap">had a call that touches the outage. Those calls are lower in every type, by {f2(min(gaps))} to {f2(max(gaps))} points.</p>{pairs}</article>')
    rk = "".join(f'<tr><td>{esc(r["org"])}</td><td class="num">{esc(r["date"][5:])}</td><td class="num">{r["cu"]:.1f}</td><td class="num"><b>{r["pts"]}</b></td></tr>' for r in d["risk"])
    col3 = (f'<article class="card"><h3>Account follow-up list</h3><div class="big"><b>{len(d["risk"])}</b> external calls</div>'
            f'<table><thead><tr><th>Account</th><th class="num">Date</th><th class="num">Tone</th><th class="num">Index</th></tr></thead><tbody>{rk}</tbody></table>'
            f'<p class="cap">Index 0-{INDEX_MAX}: low tone, falling, competitor raised, outage-related. A ranked list for a person, not a prediction.</p></article>')
    return scene("s7", 7, "task 3", "Task 3: three insights, one story", f'<div class="cards3 tight">{col1}{col2}{col3}</div>',
                 "These are leads for people to check, not causes. The outage runs through all three.")


def s8(d) -> str:
    a, b, v = d["s1"], d["s2"], d["v0"]
    checks = (f'<div class="hc"><span>Stage 0 &middot; call type</span><b>{v["agree_with_model"]}/{v["n"]}</b></div>'
              f'<div class="hc"><span>Stage 1 &middot; theme</span><b>{a["theme"]}/{a["n"]}</b></div>'
              f'<div class="hc"><span>Stage 1 &middot; product area</span><b>{a["area"]}/{a["n"]}</b></div>'
              f'<div class="hc"><span>Stage 1 &middot; outage flag</span><b>{a["incident"]}/{a["n"]}</b></div>'
              f'<div class="hc"><span>Stage 2 &middot; within 0.5</span><b>{b["within"]}/{b["n"]}</b></div>'
              f'<p class="cap">All {a["missed"]} flag misses: I flagged it, the model did not. Stage 2: {b["exact"]} exact, rank correlation {f2(b["rank"])}.</p>')
    cav = [f"Small samples ({v['n']}, {a['n']}, {b['n']} calls), my own review.",
           "Taxonomy and anchors were finalised under delegation to my assistant.",
           "The data looks synthetic and has no outcome labels.",
           f"The outage flag is an LLM judgment, probably a floor: {d['incident_touch']} is a low count."]
    no = ["That the outage caused the dip or the competitor mentions.",
          "That the follow-up list predicts churn.",
          "That the scores are correct. They are consistent with an AI output.",
          "That this holds for real customers."]
    li = lambda xs: "".join(f"<li>{esc(x)}</li>" for x in xs)
    term = (f'<div class="term"><div class="tbarx"><span>captured output of the replay command</span></div>'
            f'<pre><span class="prompt">$</span> {esc(REPLAY_CMD)}\n{esc(d["replay"])}</pre></div>')
    body = (f'<div class="s8top">{term}<article class="card"><h3>My own review, agreement with the model</h3>{checks}</article></div>'
            f'<div class="s8bot"><article class="card"><h3>Caveats</h3><ul class="plainlist">{li(cav)}</ul></article>'
            f'<article class="card nc"><h3>What I would not claim</h3><ul class="plainlist">{li(no)}</ul></article></div>')
    return scene("s8", 8, "running it", "Running it, and how far to trust it", body,
                 "Saved answers give the same results with no key and no network, and my checks are small. Read the results as strong leads.")


def s9(d) -> str:
    a = d["assignment"]
    rub = {"Thinking": "show us how you think", "Judgment under ambiguity": "how you handle ambiguity", "Insight quality": "the quality of your insights",
           "Audience fit": "Lead with insights, not code", "Transparency": "be transparent about what's original", "Readable code": "Clean, readable code"}
    for k, q in rub.items():
        assert q in a, (k, q)
    for p in ("deck/transcript-intelligence-findings.pptx", "app/explorer.html", "README.md", "DECISIONS.md"):
        assert (ROOT / p).exists(), p
    assert len(list((ROOT / "notebooks").glob("0[0-6]_*.ipynb"))) == 7 and len(list((ROOT / "notebooks" / "html").glob("0[0-6]_*.html"))) == 7
    chips = lambda xs: "".join(f'<span class="rc">{esc(x)}</span>' for x in xs)
    rows = [("Slide deck", "21 slides, 15 main and 6 appendix, with speaker notes", "deck/transcript-intelligence-findings.pptx",
             ["Audience fit", "Insight quality", "Thinking"]),
            ("Repo", "Notebooks 00-06 with HTML copies, README rubric map, DECISIONS.md, 94+ tests", "notebooks/, README.md, DECISIONS.md, tests/",
             ["Readable code", "Transparency", "Judgment under ambiguity", "Thinking"]),
            ("Explorer", "Overview, Calls, Themes, Insights and Trust tabs; every score links to a quote", "app/explorer.html",
             ["Insight quality", "Audience fit"]),
            ("This video", "The pipeline running on a real call, and every decision shown", "this recording; app/video_walkthrough.html",
             ["Thinking", "Judgment under ambiguity"])]
    tbl = ('<table class="map"><thead><tr><th>Deliverable</th><th>What it holds</th><th>Where to look</th><th>Rubric items</th></tr></thead><tbody>'
           + "".join(f'<tr><th scope="row">{esc(x)}</th><td>{esc(y)}</td><td class="mono">{esc(z)}</td><td>{chips(r)}</td></tr>' for x, y, z, r in rows) + '</tbody></table>')
    legend = ('<p class="legend rubq"><b>assignment.md says:</b> '
              + "".join(f'<span><i>{esc(k)}</i> &ldquo;{esc(q)}&rdquo;</span>' for k, q in rub.items()) + '</p>')
    real = [("Cache to live", "Set TI_MODE=live with a key and the same pinned model and prompts. A live re-run may differ; the cache is the record."),
            ("Review queue", "Model and title-rule disagreements, an Other bucket above 10%, and the follow-up list all go to a person."),
            ("Taxonomy versioning", "Taxonomy, anchors and prompts are versioned. Any change re-runs that stage on every call.")]
    realh = '<div class="cards3 real">' + "".join(f'<div class="rl"><h4>{esc(x)}</h4><p>{esc(y)}</p></div>' for x, y in real) + '</div>'
    return scene("s9", 9, "deliverables and rubric", "What you are getting, and how it maps to the rubric",
                 tbl + legend + '<h3 class="sub">How this would run for real</h3>' + realh,
                 "Every rubric item points to a file you can open. Deck on screen for reference next.")


NAV = ["The answer", "Data traps", "Pipeline", "Decisions", "Themes", "Sentiment", "Insights", "Trust", "Rubric"]


def render(d: dict, template: str) -> str:
    scenes = "".join([s1(d), s2(d), s3(d), s4(d), s5(d), s6(d), s7(d), s8(d), s9(d)])
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

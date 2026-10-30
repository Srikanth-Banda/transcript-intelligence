"""Helpers for the reference notebooks in notebooks/.

Everything here is read-only and offline: the notebooks run in replay mode (TI_MODE=replay), so no network call,
no API key and no spend are involved. A cache miss is an error, never a silent live call (D5).

Why a helper module: the notebooks should show decisions and evidence, not plumbing. Anything that is more than a
few lines (the replay proof, the hand-check agreement, the prompt printer) lives here and is tested by
tests/test_notebooks.py through the notebooks that use it.
"""

from __future__ import annotations

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import ROOT

TYPE_COLORS = {"support": "#b45309", "external": "#1f4fd8", "internal": "#6d3fc0"}
TYPES = ["support", "external", "internal"]
INK, MUTED, LINE = "#161b26", "#5b6475", "#dde1e8"


# ---- environment ----------------------------------------------------------------------------------------------
def setup() -> Path:
    """Force replay mode, fill the pinned model settings from .env.example when there is no .env, set plot style.

    Never reads or prints a key: replay mode does not need one.
    """
    from dotenv import dotenv_values, load_dotenv

    os.chdir(ROOT)
    load_dotenv(ROOT / ".env")  # optional; override=False, so the replay setting below wins
    for k, v in dotenv_values(ROOT / ".env.example").items():  # clean clone: D7 settings without a .env
        if k.startswith("TI_MODEL") or k == "TI_PROVIDER_ORDER":
            os.environ.setdefault(k, v or "")
    os.environ["TI_MODE"] = "replay"
    os.environ["TI_TRACING"] = "0"
    pd.set_option("display.max_colwidth", 90)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 30)
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
        "axes.titleweight": "bold", "axes.titlesize": 11, "font.size": 9.5, "axes.grid": True,
        "grid.color": LINE, "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.facecolor": "white",
        "axes.facecolor": "white", "savefig.facecolor": "white",
    })
    return ROOT


def rel(path) -> str:
    """Project-relative path as a string (notebooks print these, never absolute paths)."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def md(text: str) -> None:
    from IPython.display import Markdown, display

    display(Markdown(text))


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%"


def show_df(df: pd.DataFrame, **kw) -> None:
    """Display a frame with missing values shown as a dash (the test suite forbids literal NaN in outputs)."""
    from IPython.display import display

    display(df.astype(object).where(df.notna(), "–"), **kw)


# ---- data -----------------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def calls() -> pd.DataFrame:
    """One row per call: Stage 0, 1, 2 outputs joined with dates, titles and the provided score (comparison only)."""
    from .analysis import sentiment as S

    return S.build_calls()


@lru_cache(maxsize=1)
def turns() -> pd.DataFrame:
    from .analysis import sentiment as S

    return S.build_turns(calls())


def read_json(rel_path: str):
    return json.loads((ROOT / rel_path).read_text())



_TABLE_CSS = ("<style>table.ti{border-collapse:collapse;font-size:12px;margin:4px 0}table.ti th,table.ti td{border-bottom:1px solid #dde1e8;"
              "padding:4px 9px;text-align:left;vertical-align:top}table.ti th{color:#5b6475;font-weight:600}</style>")


def table(df: pd.DataFrame, index: bool = False) -> None:
    """Readable wrapped table (long text wraps instead of being cut); missing values show as a dash."""
    from IPython.display import HTML, display

    display(HTML(_TABLE_CSS + df.to_html(index=index, na_rep="–", escape=True, border=0, classes="ti")))


def prompt_body(name: str) -> str:
    """The exact prompt text between the PROMPT START/END markers."""
    text = (ROOT / "prompts" / f"{name}.md").read_text()
    _, _, rest = text.partition("<!-- PROMPT START -->")
    return rest.partition("<!-- PROMPT END -->")[0].strip() if rest else text


def short(text: str, n: int = 150) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"

# ---- prompts --------------------------------------------------------------------------------------------------
def show_prompt(name: str, max_chars: int | None = None) -> None:
    """Print the header and the exact prompt text (between the PROMPT START/END markers) of prompts/<name>.md."""
    text = (ROOT / "prompts" / f"{name}.md").read_text()
    head, _, rest = text.partition("<!-- PROMPT START -->")
    body = rest.partition("<!-- PROMPT END -->")[0].strip() if rest else text
    keep = [ln for ln in head.splitlines() if ln.startswith(("- Version", "- Decision", "- Input", "- Model"))]
    print(f"prompts/{name}.md")
    print("\n".join(keep))
    print("-" * 100)
    if max_chars and len(body) > max_chars:
        print(body[:max_chars].rstrip() + f"\n[... {len(body) - max_chars:,} more characters in the file ...]")
    else:
        print(body)


# ---- reproducibility: replay proof ---------------------------------------------------------------------------
def _same(a, b) -> bool:
    if (a is None or (isinstance(a, float) and math.isnan(a))) and (b is None or (isinstance(b, float) and math.isnan(b))):
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    return str(a) == str(b)


# Stage 0's frozen labels were produced by the bake-off runner (eval/bakeoff.py, run 1, Gemini), whose cache entries are
# keyed by these parameters. src/ti/stage0.py classify() sends different default parameters and therefore a different
# cache key, so replaying it would miss. The notebooks say so openly; this mirrors the parameters that made the labels.
STAGE0_PARAMS = {"max_tokens": 3000, "provider_order": ["google-ai-studio"], "run": 1, "reasoning_effort": "low", "seed": 7}


def _stage0_record(meeting, client) -> dict:
    if meeting.is_internal_by_metadata:
        return {"meeting_id": meeting.meeting_id, "label": "internal", "source": "metadata"}
    from .llm import load_prompt
    from .schemas import Stage0LLMOut
    from .stage0 import build_user_message

    version, system = load_prompt("stage0_v1")
    out, meta = client.complete(stage="stage0", prompt_version=version, model=os.environ["TI_MODEL_STAGE0"], system=system,
                                user=build_user_message(meeting), schema=Stage0LLMOut, params=dict(STAGE0_PARAMS))
    return {"meeting_id": meeting.meeting_id, "label": out.label, "source": "llm", "cache_hit": meta["cache_hit"]}


def replay_check(stage: int) -> dict:
    """Re-run a stage for all 100 calls from the committed cache and compare with the committed output CSV.

    This is the evidence behind "reproducibility comes from the cache, not from re-running a live model": a replay
    with no network and no key must reproduce the stored results exactly.
    """
    from .common import Guard
    from .llm import LLMClient
    from .load import load_meetings

    meetings = load_meetings()
    client = LLMClient(mode="replay")
    if stage == 0:
        recs = [_stage0_record(m, client) for m in meetings]
        ref = pd.read_csv(ROOT / "outputs/stage0_final.csv").set_index("meeting_id")
        fields = {"label": "label"}
    elif stage == 1:
        from . import stage1

        guard = Guard(refresh=False)  # refresh=False: no balance lookup, so no network
        recs = [stage1.classify(m, client, guard) for m in meetings]
        ref = pd.read_csv(ROOT / "outputs/stage1/stage1_final.csv").set_index("meeting_id")
        fields = {"primary_theme": "primary_theme", "product_area": "product_area", "incident": "incident"}
    elif stage == 2:
        from . import stage2

        guard = Guard(refresh=False)
        recs = [stage2.classify(m, client, guard) for m in meetings]
        ref = pd.read_csv(ROOT / "outputs/stage2/stage2_final.csv").set_index("meeting_id")
        fields = {"call_score": "call_score", "customer_score": "customer_score"}
    else:
        raise ValueError("stage must be 0, 1 or 2")
    mism = []
    for r in recs:
        row = ref.loc[r["meeting_id"]]
        for k, col in fields.items():
            if not _same(r.get(k), row[col]):
                mism.append((r["meeting_id"], k, r.get(k), row[col]))
    llm_calls = [r for r in recs if r.get("source", "llm") != "metadata"]
    from_cache = sum(1 for r in llm_calls if r.get("cache_hit") in (True, "True"))
    return {"stage": stage, "calls": len(recs), "llm_calls": len(llm_calls), "served_from_cache": from_cache,
            "mismatches": len(mism), "examples": mism[:5]}


# ---- hand-check agreement (the candidate's own review, exported from the Review Console) --------------------
KIND = {1: "stage1_theme", 2: "stage2_score"}


def load_verdicts(stage: int) -> list[dict] | None:
    """Submitted verdicts for stage 1 or 2, or None when the hand-check file is not there yet.

    Accepts eval/stage<N>_review_verdicts.json, or one combined eval/stage12_review_verdicts.json (the console's
    'Copy results as JSON' holds both kinds). Both a list of documents and {'items': [...]} are fine.
    """
    for name in (f"stage{stage}_review_verdicts.json", "stage12_review_verdicts.json"):
        p = ROOT / "eval" / name
        if p.exists():
            d = json.loads(p.read_text())
            items = d["items"] if isinstance(d, dict) else d
            return [i for i in items if i.get("kind") == KIND[stage] and i.get("submitted")]
    return None


def pending_notice(stage: int) -> None:
    n, items = (20, "20 categorization items") if stage == 1 else (15, "15 scoring items")
    md(f"> **PENDING: the Stage {stage} hand-check has not been done yet.** This is the candidate's own review "
       f"({items}, Stage 1-2 Review Console). Until it is, there is **no human accuracy figure** for this stage: "
       f"everything above is consistency with the model's own output or with the upstream AI labels.\n>\n"
       f"> To fill this in: finish the review, use *Copy results as JSON*, save it as "
       f"`eval/stage{stage}_review_verdicts.json` (or `eval/stage12_review_verdicts.json`), and re-run this cell. "
       f"Agreement is computed automatically.")


def stage1_handcheck(items: list[dict]) -> tuple[pd.DataFrame, dict]:
    rows = []
    for i in items:
        m = i.get("model", {})
        rows.append({"meeting": i["title"][:60], "type": i.get("callType"), "you_theme": i["theme"], "model_theme": m.get("theme"),
                     "you_area": i["area"], "model_area": m.get("area"), "you_incident": i.get("incident"),
                     "model_incident": m.get("incident")})
    df = pd.DataFrame(rows)
    df["theme_ok"] = df.you_theme == df.model_theme
    df["area_ok"] = df.you_area == df.model_area
    df["incident_ok"] = df.you_incident == df.model_incident
    summ = {"n": len(df), "theme": df.theme_ok.mean(), "product_area": df.area_ok.mean(), "incident": df.incident_ok.mean()}
    return df, summ


def stage2_handcheck(items: list[dict]) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame([{"meeting": i["title"][:60], "type": i.get("callType"), "you_call": i.get("callScore"),
                        "model_call": i.get("modelCallScore"), "you_cust": i.get("customerScore"),
                        "model_cust": i.get("modelCustomerScore")} for i in items])
    df["diff"] = (df.you_call - df.model_call).abs()
    c = df.dropna(subset=["you_cust", "model_cust"])
    summ = {"n": len(df), "call_mad": df["diff"].mean(), "call_exact": (df["diff"] == 0).mean(),
            "call_within_half": (df["diff"] <= 0.5).mean(),
            "call_spearman": df.you_call.rank().corr(df.model_call.rank()),
            "n_customer": len(c), "cust_mad": (c.you_cust - c.model_cust).abs().mean() if len(c) else float("nan")}
    return df, summ


def upper_bound_zero_errors(n: int, conf: float = 0.95) -> dict:
    """If n checked items had zero errors, the largest error rate still consistent with that.

    one_sided_exact: 1 - (1 - conf)^(1/n)  (what A18 in DECISIONS.md called "about 25%" for n=10)
    rule_of_three:   3 / n                 (the quick approximation, larger because it is rougher)
    """
    return {"n": n, "one_sided_exact": 1 - (1 - conf) ** (1 / n), "rule_of_three": 3 / n}


# ---- diagram --------------------------------------------------------------------------------------------------
def pipeline_diagram():
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.4)
    ax.axis("off")
    ax.grid(False)

    def box(x, y, w, h, title, lines, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.4))
        ax.text(x + 0.12, y + h - 0.2, title, fontsize=10, fontweight="bold", va="top", color=INK)
        ax.text(x + 0.12, y + h - 0.55, "\n".join(lines), fontsize=8, va="top", color=INK, linespacing=1.35)

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1.2))

    box(0.1, 1.5, 2.1, 2.2, "Data", ["100 calls", "transcript, speakers,", "attendees, dates", "", "provided summary, topics,", "score: comparison only"], "#f5f6f8", MUTED)
    box(2.6, 1.5, 2.5, 2.2, "Stage 0  call type  (D1)", ["internal: no outside attendee", "else LLM: support vs external", "(opening only, no title)", "title rule = cross-check", "human review of disagreements"], "#e6ecfc", "#1f4fd8")
    box(5.6, 2.45, 2.7, 1.9, "Stage 1  themes  (D3, D8)", ["one-time: discover, freeze v1", "recurring: classify each call", "theme + product area +", "incident field + quote"], "#fdf0dc", "#b45309")
    box(5.6, 0.1, 2.7, 1.9, "Stage 2  sentiment  (D2, D8)", ["one pass per call:", "score 1-5 (anchors), per-turn", "labels, trajectory, quote"], "#efe8fa", "#6d3fc0")
    box(8.7, 1.5, 2.2, 2.2, "Stage 3  insights  (D6)", ["trends and what they mean", "outage across call types", "competitors, account risk"], "#e1f4ea", "#18794e")
    arrow(2.2, 2.6, 2.6, 2.6)
    arrow(5.1, 2.9, 5.6, 3.3)
    arrow(5.1, 2.3, 5.6, 1.2)
    arrow(8.3, 3.3, 8.7, 2.9)
    arrow(8.3, 1.2, 8.7, 2.3)
    ax.text(5.5, 4.3, "One model for every LLM stage (D7), replayable from the committed cache (D5)", ha="center", fontsize=9, color=MUTED)
    return fig

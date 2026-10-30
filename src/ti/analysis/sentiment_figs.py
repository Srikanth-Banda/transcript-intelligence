"""Figures for the Task 2 analysis. Reads findings.json and calls_table.csv written by ti.analysis.sentiment.

Run: PYTHONPATH=src uv run python -m ti.analysis.sentiment_figs
White background, labeled axes, n shown, title states the takeaway. Fixed seed for jitter.
"""
from __future__ import annotations

import json
import textwrap
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ti.analysis.sentiment import OUT, TYPES
from ti.analysis.stats import SEED

COL = {"support": "#c2410c", "external": "#1d4ed8", "internal": "#6d28d9"}
INK = "#1f2937"
GRID = "#e5e7eb"
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white", "font.size": 11,
                     "axes.edgecolor": "#9ca3af", "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8})


def _title(fig, text, width=70):
    """Left-aligned, wrapped takeaway title above the axes."""
    fig.suptitle(textwrap.fill(text, width), x=0.01, ha="left", fontsize=13, fontweight="bold")


def _note(fig, text, width=110, y=0.005):
    fig.text(0.01, y, textwrap.fill(text, width), fontsize=8.5, color="#4b5563", va="bottom")


def _load():
    f = json.load(open(OUT / "findings.json"))
    df = pd.read_csv(OUT / "calls_table.csv", parse_dates=["start"])
    df["date"] = pd.to_datetime(df["date"])
    return f, df


def fig_by_type(f, df):
    fig, ax = plt.subplots(figsize=(8, 5))
    rng = np.random.default_rng(SEED)
    for i, t in enumerate(TYPES):
        s = df[df.type == t].call_score
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(s)), s + rng.uniform(-0.05, 0.05, len(s)), s=28, color=COL[t], alpha=0.55, zorder=2)
        q = f["q1_by_type"][t]["call_score"]
        ax.errorbar(i, q["mean"], yerr=[[q["mean"] - q["ci95"][0]], [q["ci95"][1] - q["mean"]]], fmt="o", color=INK, capsize=6, ms=9, zorder=3)
        ax.annotate(f"mean {q['mean']:.2f}", (i + 0.27, q["mean"]), va="center", fontsize=10)
        p = f["q1_by_type"][t]["provided_score"]["mean"]
        ax.scatter(i, p, marker="D", s=46, facecolor="white", edgecolor="#6b7280", zorder=4)
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{t}\n(n={f['q1_by_type'][t]['call_score']['n']})" for t in TYPES])
    ax.set_ylim(0.8, 5.4); ax.set_ylabel("Whole-call score (1 = breakdown, 5 = warm)")
    _title(fig, "Support calls are the least positive (2.9), external calls the most (3.9)")
    _note(fig, "Dots: calls. Black: mean with 95% bootstrap CI. Open diamond: mean of the provided upstream score. Call types from Stage 0.")
    fig.tight_layout(rect=(0, 0.06, 1, 0.94)); fig.savefig(OUT / "fig1_by_type.png", dpi=160); plt.close(fig)


def fig_trend(f, df):
    start = pd.Timestamp(f["q3_outage"]["first_core_incident_call"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    wk = df.groupby("week").agg(mean=("call_score", "mean"), n=("call_score", "size")).reset_index()
    wk["week"] = pd.to_datetime(wk["week"])
    for t in TYPES:
        g = df[df.type == t].groupby("week").agg(mean=("call_score", "mean"), n=("call_score", "size")).reset_index()
        g["week"] = pd.to_datetime(g["week"]); g = g[g.n >= 2]
        a1.plot(g.week, g["mean"], "-o", color=COL[t], lw=1.2, ms=4, alpha=0.7, label=f"{t} (weeks with n>=2)")
    a1.plot(wk.week, wk["mean"], "-o", color=INK, lw=2.6, ms=6, label="all calls")
    for r in wk.itertuples(): a1.annotate(f"n={r.n}", (r.week, r.mean), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8, color="#374151", bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))
    a1.axvline(start, color="#b91c1c", ls="--", lw=1.2); a1.text(start, 1.62, " first outage-core call, Mar 10", color="#b91c1c", fontsize=9, va="bottom")
    a1.set_ylim(1.5, 5.4); a1.set_ylabel("Mean whole-call score"); a1.legend(loc="lower right", fontsize=8, ncol=2, frameon=False)
    _title(fig, "Scores fell sharply in the week of Mar 9 and were back near February levels by April")
    tw = pd.DataFrame(f["q3_outage"]["touch_by_week"]).T
    tw.index = pd.to_datetime(tw.index); bottom = np.zeros(len(tw))
    for t in TYPES:
        a2.bar(tw.index, tw[t], bottom=bottom, width=5, color=COL[t], label=t); bottom += tw[t].values
    a2.axvline(start, color="#b91c1c", ls="--", lw=1.2)
    a2.set_ylabel("Calls touching\nthe outage"); a2.set_xlabel("Week starting (Monday)")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d")); a2.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
    _note(fig, "Thick line: all calls, n per week shown. Thin lines: weeks with at least 2 calls of that type. Bars: calls whose transcript touches the March Detect outage (Stage 1 incident field).", y=0.003)
    fig.tight_layout(rect=(0, 0.04, 1, 0.93)); fig.savefig(OUT / "fig2_trend.png", dpi=160); plt.close(fig)


def fig_dip(f, df):
    d = f["q2_dip"]
    rows = [("All calls", d["all_calls"]), ("Excluding calls that touch the outage", d["excl_touches_incident"]),
            ("Excluding core-outage calls (primary theme)", d["excl_core_incident"])]
    fig, ax = plt.subplots(figsize=(9, 3.9))
    for i, (lab, r) in enumerate(rows[::-1]):
        ax.errorbar(r["diff"], i, xerr=[[r["diff"] - r["ci95"][0]], [r["ci95"][1] - r["diff"]]], fmt="o", color=INK, capsize=6, ms=9)
        ax.annotate(f"{r['diff']:+.2f}   (n March {r['n_march']}, other {r['n_other']})", (r["ci95"][1] + 0.04, i), va="center", fontsize=9)
    ax.axvline(0, color="#6b7280", lw=1)
    ax.set_yticks(range(3)); ax.set_yticklabels([r[0] for r in rows[::-1]]); ax.set_xlim(-1.5, 1.2)
    ax.set_xlabel("March mean minus Feb+Apr mean (whole-call score), 95% bootstrap CI")
    _title(fig, "Most of the March dip sits in outage-related calls; what remains is not distinguishable from zero", 80)
    fig.tight_layout(rect=(0, 0, 1, 0.88)); fig.savefig(OUT / "fig3_dip.png", dpi=160); plt.close(fig)


def fig_traj(f, df):
    fig, axs = plt.subplots(1, 3, figsize=(11, 4.2), sharey=True)
    rng = np.random.default_rng(SEED)
    for ax, t in zip(axs, TYPES):
        s = df[df.type == t]
        for r in s.itertuples():
            ax.plot([0, 1], [r.traj_start, r.traj_end], color=COL[t], alpha=0.25, lw=1)
        b = f["q4_trajectory"]["by_type"][t]
        ax.plot([0, 1], [b["start_mean"], b["end_mean"]], "-o", color=INK, lw=3, ms=8)
        ax.set_title(f"{t} (n={b['n']})\nup {b['n_improve']}, flat {b['n_flat']}, down {b['n_worse']}", fontsize=10)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["first third", "last third"]); ax.set_xlim(-0.2, 1.2); ax.set_ylim(1, 5.2)
    axs[0].set_ylabel("Score for that part of the call")
    _title(fig, "Almost every call ends warmer than it starts: 78 of 100 improve, only 1 gets worse", 90)
    fig.tight_layout(rect=(0, 0, 1, 0.88)); fig.savefig(OUT / "fig4_trajectory.png", dpi=160); plt.close(fig)


def fig_accounts(f, df):
    ac = sorted(f["q3_outage"]["most_affected_accounts"], key=lambda a: a["last_customer_score"] - a["first_customer_score"])
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for i, a in enumerate(ac):
        cs = [c["customer_score"] for c in a["calls"] if c["customer_score"] is not None]
        ax.plot([min(cs), max(cs)], [i, i], color="#d1d5db", lw=6, zorder=1, solid_capstyle="round")
        col = "#b91c1c" if a["last_customer_score"] < a["first_customer_score"] else "#15803d"
        ax.annotate("", xy=(a["last_customer_score"], i), xytext=(a["first_customer_score"], i), arrowprops=dict(arrowstyle="->", color=col, lw=2.2), zorder=3)
        ax.scatter([a["first_customer_score"]], [i], s=60, color="white", edgecolor=col, zorder=4)
        ax.scatter([a["min_customer_score"]], [i + 0.22], marker="v", s=36, color="#6b7280", zorder=4)
        ax.annotate(f"last call {a['last_call_date'][5:]}", (5.2, i), va="center", fontsize=8, color="#4b5563")
    ax.set_yticks(range(len(ac))); ax.set_yticklabels([f"{a['account']} ({a['n_calls']} calls)" for a in ac])
    ax.set_xlim(1, 5.9); ax.set_xlabel("Customer-side score (open circle = first call, arrow = last call, triangle = lowest)")
    _title(fig, "Account recovery is uneven: Trailhead and Blackridge bounced back; Summit Trust, Stratos and Clearwater ended lower", 85)
    _note(fig, "Accounts with an outage-touching support call and an external call. Northstar and Ridgeline have no call after mid-March, so their recovery is unknown. Blackridge's first and last calls are both 5.0.", 105)
    fig.tight_layout(rect=(0, 0.07, 1, 0.9)); fig.savefig(OUT / "fig5_accounts.png", dpi=160); plt.close(fig)


def fig_vs_provided(f, df):
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    rng = np.random.default_rng(SEED)
    for t in TYPES:
        s = df[df.type == t]
        ax.scatter(s.provided_score + rng.uniform(-0.03, 0.03, len(s)), s.call_score + rng.uniform(-0.03, 0.03, len(s)), s=30, color=COL[t], alpha=0.65, label=f"{t} (n={len(s)})")
    ax.plot([1, 5], [1, 5], color="#6b7280", lw=1, ls="--")
    key = []
    for k, x in enumerate(f["q5_disagreement"]["flagged"], 1):
        ax.annotate(str(k), (x["provided"], x["ours"]), textcoords="offset points", xytext=(5 + (k % 3) * 9, (5 if x["diff"] > 0 else -12) + (k % 2) * 4), fontsize=10, fontweight="bold")
        key.append(f"{k} {x['title'].split(' - ')[-1][:30]} ({x['diff']:+.1f})")
    ax.set_xlim(1.2, 5.1); ax.set_ylim(1.2, 5.1); ax.set_xlabel("Provided upstream score"); ax.set_ylabel("Our whole-call score")
    ax.legend(frameon=False, loc="lower right")
    d = f["q5_disagreement"]
    _title(fig, f"Our score tracks the provided one (r={d['pearson']}); {d['n_material_abs_diff_ge_0.6']} calls differ by 0.6 or more", 70)
    _note(fig, "Numbered calls (our score minus provided): " + "; ".join(key), 85)
    fig.tight_layout(rect=(0, 0.13, 1, 0.93)); fig.savefig(OUT / "fig6_vs_provided.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    f, df = _load()
    for fn in (fig_by_type, fig_trend, fig_dip, fig_traj, fig_accounts, fig_vs_provided):
        fn(f, df)
    print("figures written to", OUT)

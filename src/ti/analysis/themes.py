"""Task 1 presentation outputs: theme tables, examples, provided-topic comparison, sanity checks.

Reads only frozen pipeline outputs (no LLM calls). The provided topics, summary, score and key
moments are used as COMPARISON data only, never as pipeline input.
Run: PYTHONPATH=src uv run python -m ti.analysis.themes
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "analysis" / "themes"
DATASET = ROOT / "dataset"

STOP = {"and", "the", "of", "to", "for", "a", "in", "on", "with", "&", "v2", "-", "new"}


def split_tags(s) -> list[str]:
    """Tags are stored as a '|'-joined string in the CSV (may be empty/NaN)."""
    if s is None or (isinstance(s, float) and math.isnan(s)) or str(s).strip() == "":
        return []
    parts = re.split(r"[|;]", str(s))
    return [p.strip() for p in parts if p.strip()]


def load_frame() -> pd.DataFrame:
    s0 = pd.read_csv(ROOT / "outputs" / "stage0_final.csv")[["meeting_id", "label"]].rename(columns={"label": "type"})
    s1 = pd.read_csv(ROOT / "outputs" / "stage1" / "stage1_final.csv")
    s1 = s1.rename(columns={"primary_theme": "theme", "evidence_quote": "s1_quote", "confidence": "s1_conf"})
    s2 = pd.read_csv(ROOT / "outputs" / "stage2" / "stage2_final.csv")[
        ["meeting_id", "call_score", "customer_score", "traj_start", "traj_end", "evidence_quote", "n_turns", "n_neg", "n_neu", "n_pos"]
    ].rename(columns={"evidence_quote": "s2_quote"})
    df = s1[["meeting_id", "theme", "tags", "product_area", "incident", "s1_conf", "s1_quote", "quote_exact"]].merge(s0, on="meeting_id").merge(s2, on="meeting_id")
    rows = []
    for mid in df.meeting_id:
        d = DATASET / mid
        mi = json.load(open(d / "meeting-info.json"))
        sm = json.load(open(d / "summary.json"))
        rows.append(
            dict(
                meeting_id=mid,
                title=mi["title"],
                date=mi["startTime"][:10],
                duration=mi["duration"],
                emails=mi["allEmails"],
                prov_topics=sm["topics"],
                prov_score=sm["sentimentScore"],
                prov_sent=sm["overallSentiment"],
                prov_summary=sm["summary"],
                prov_actions=sm["actionItems"],
                prov_moments=sm["keyMoments"],
            )
        )
    df = df.merge(pd.DataFrame(rows), on="meeting_id")
    df["month"] = df["date"].str[:7]
    df["tag_list"] = df["tags"].map(split_tags)
    df["incident_flag"] = df["incident"].notna() & (df["incident"].astype(str).str.strip() != "")
    ext = df["emails"].map(lambda es: sorted({e.split("@")[1].split(".")[0] for e in es if not e.endswith("@aegiscloud.com")}))
    df["customer_org"] = ext.map(lambda x: x[0] if x else "")
    return df


# ---------- provided-topic comparison (scripted, plain) ----------
def tokens(topics: list[str]) -> list[str]:
    out = []
    for t in topics:
        for w in re.findall(r"[a-z0-9]+", t.lower()):
            if w not in STOP and len(w) > 2:
                out.append(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def loo_centroid_predict(df: pd.DataFrame) -> pd.Series:
    """Predict our theme from the provided topic words alone (leave-one-out nearest centroid, cosine).

    This measures how far the dataset's own topic strings recover our themes. It is a plain
    bag-of-words centroid classifier, not a trained model.
    """
    themes = sorted(df["theme"].unique())
    docs = [Counter(tokens(t)) for t in df["prov_topics"]]
    cent = {th: Counter() for th in themes}
    for d, th in zip(docs, df["theme"]):
        cent[th].update(d)
    preds = []
    for d, th in zip(docs, df["theme"]):
        best, bs = None, -1.0
        for c in themes:
            cc = Counter(cent[c])
            if c == th:
                cc.subtract(d)
            num = sum(cc[w] * d[w] for w in d if cc[w] > 0)
            den = math.sqrt(sum(v * v for v in cc.values() if v > 0)) * math.sqrt(sum(v * v for v in d.values()))
            sc = num / den if den else 0.0
            if sc > bs:
                best, bs = c, sc
        preds.append(best)
    return pd.Series(preds, index=df.index)


def characteristic_tokens(df: pd.DataFrame, k: int = 6) -> dict[str, list[str]]:
    cnt = {th: Counter() for th in df["theme"].unique()}
    for t, th in zip(df["prov_topics"], df["theme"]):
        cnt[th].update(set(tokens(t)))
    total = Counter()
    for c in cnt.values():
        total.update(c)
    n = len(df)
    sizes = df["theme"].value_counts().to_dict()
    res = {}
    for th, c in cnt.items():
        sc = {w: (v / sizes[th]) * math.log((n / total[w])) for w, v in c.items() if v >= 2}
        res[th] = [w for w, _ in sorted(sc.items(), key=lambda x: -x[1])[:k]]
    return res


# ---------- sanity expectations from D3a ----------
SANITY = [
    ("Billing and Usage Disputes", "support"),
    ("Technical Integration and Performance Issues", "support"),
    ("Commercial Renewals and Retention", "external"),
    ("Internal Planning and Delivery Cadence", "internal"),
]


def sanity_checks(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    rows = []
    for th, expect in SANITY:
        sub = df[df["theme"] == th]
        share = float((sub["type"] == expect).mean()) if len(sub) else float("nan")
        rows.append(dict(theme=th, expected_type=expect, n=len(sub), share_in_expected=round(share, 3), threshold=threshold, passed=bool(share >= threshold)))
    return pd.DataFrame(rows)


def pick_examples(df: pd.DataFrame, loo: pd.Series) -> dict[str, list[dict]]:
    """Two clear examples (high confidence, provided topics agree, fewest tags) and one borderline.

    Borderline = the provided topics alone point to a different theme, else a call carrying two tags.
    Only verbatim (exact-match) evidence quotes are used.
    """
    ex = {}
    for th, sub in df.groupby("theme"):
        sub = sub[sub["quote_exact"] == True].copy()  # noqa: E712
        sub["n_tags"] = sub["tag_list"].map(len)
        sub["loo"] = loo.loc[sub.index]
        clear = sub[(sub["s1_conf"] == "high") & (sub["loo"] == th)].sort_values(["n_tags", "date"]).head(2)
        pool = sub.drop(clear.index)
        border = pool[pool["loo"] != th]
        if border.empty:
            border = pool[pool["n_tags"] == 2]
        border = border.sort_values(["n_tags", "date"], ascending=[False, True]).head(1)
        items = []
        for _, r in clear.iterrows():
            items.append(dict(kind="clear", title=r.title, date=r.date, type=r["type"], quote=r.s1_quote,
                              why=f"High confidence; the provided topics point to the same theme; {r.n_tags} extra tag(s)."))
        for _, r in border.iterrows():
            why = []
            if r.tag_list:
                why.append("also tagged: " + "; ".join(r.tag_list))
            if r["loo"] != th:
                why.append(f"the provided topics alone would suggest '{r['loo']}'")
            items.append(dict(kind="borderline", title=r.title, date=r.date, type=r["type"], quote=r.s1_quote, why="; ".join(why)))
        ex[th] = items
    return ex


def tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    out["theme_x_type"] = pd.crosstab(df.theme, df["type"]).reindex(columns=["support", "external", "internal"], fill_value=0)
    out["theme_x_product_area"] = pd.crosstab(df.theme, df.product_area)
    out["theme_x_month"] = pd.crosstab(df.theme, df.month)
    out["theme_summary"] = (
        df.groupby("theme")
        .agg(n=("meeting_id", "count"), mean_call_score=("call_score", "mean"), mean_customer_score=("customer_score", "mean"),
             incident_calls=("incident_flag", "sum"), with_tag=("tag_list", lambda s: int((s.map(len) > 0).sum())))
        .round(2)
        .sort_values("n", ascending=False)
    )
    return out


def tag_report(df: pd.DataFrame) -> dict:
    tags = Counter(t for ts in df["tag_list"] for t in ts)
    pairs = Counter((p, t) for p, ts in zip(df["theme"], df["tag_list"]) for t in ts)
    return dict(
        calls_with_tag=int((df["tag_list"].map(len) > 0).sum()),
        calls_with_two_tags=int((df["tag_list"].map(len) == 2).sum()),
        tag_counts=dict(tags.most_common()),
        primary_to_tag=[dict(primary=p, tag=t, n=n) for (p, t), n in pairs.most_common(12)],
        tag_equals_primary=int(sum(p in ts for p, ts in zip(df["theme"], df["tag_list"]))),
    )


def figures(df: pd.DataFrame, tabs: dict[str, pd.DataFrame]) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
    short = {
        "Product Adoption, Feedback and Expansion": "Product adoption",
        "Incident and Outage Response": "Incident / outage",
        "Technical Integration and Performance Issues": "Technical issues",
        "Commercial Renewals and Retention": "Renewals",
        "Internal Planning and Delivery Cadence": "Internal planning",
        "Onboarding and Implementation Scoping": "Onboarding",
        "Competitive Strategy and Win/Loss": "Competitive",
        "Billing and Usage Disputes": "Billing",
    }
    order = tabs["theme_summary"].index.tolist()
    names = [short.get(t, t) for t in order]
    paths = []

    # 1. theme x call type (stacked horizontal)
    t = tabs["theme_x_type"].reindex(order)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    left = [0] * len(order)
    colors = {"support": "#c2410c", "external": "#1d4ed8", "internal": "#6d28d9"}
    for c in ["support", "external", "internal"]:
        ax.barh(names, t[c], left=left, color=colors[c], label=c)
        left = [a + b for a, b in zip(left, t[c])]
    ax.invert_yaxis()
    ax.set_xlabel("calls")
    ax.set_title("Each theme by call type (Stage 0 label)")
    ax.legend(frameon=False, loc="lower right")
    for i, v in enumerate(left):
        ax.text(v + 0.3, i, str(int(v)), va="center", fontsize=9)
    fig.tight_layout()
    p = OUT / "fig1_theme_by_call_type.png"
    fig.savefig(p)
    plt.close(fig)
    paths.append(str(p.relative_to(ROOT)))

    # 2. theme x product area heatmap
    t = tabs["theme_x_product_area"].reindex(order)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    im = ax.imshow(t.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(t.shape[1]), [c.replace("Platform/General", "Platform / general") for c in t.columns], rotation=0, fontsize=9)
    ax.set_yticks(range(t.shape[0]), names)
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = int(t.values[i, j])
            ax.text(j, i, v, ha="center", va="center", color="white" if v > t.values.max() / 2 else "black", fontsize=9)
    ax.set_title("Theme by product area (calls)")
    ax.spines[:].set_visible(False)
    fig.tight_layout()
    p = OUT / "fig2_theme_by_product_area.png"
    fig.savefig(p)
    plt.close(fig)
    paths.append(str(p.relative_to(ROOT)))

    # 3. mean call score by theme with customer score
    s = tabs["theme_summary"].reindex(order)
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    y = range(len(order))
    ax.barh([i - 0.2 for i in y], s["mean_call_score"], height=0.4, color="#0f766e", label="call score (all calls)")
    ax.barh([i + 0.2 for i in y], s["mean_customer_score"].fillna(0), height=0.4, color="#b45309", label="customer score (calls with a customer)")
    ax.set_yticks(list(y), names)
    ax.invert_yaxis()
    ax.set_xlim(1, 5)
    ax.set_xlabel("mean score, 1 (breakdown) to 5 (warm)")
    ax.set_title("Tone by theme (Stage 2)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8)
    fig.tight_layout()
    p = OUT / "fig3_tone_by_theme.png"
    fig.savefig(p)
    plt.close(fig)
    paths.append(str(p.relative_to(ROOT)))
    return paths


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_frame()
    tabs = tables(df)
    loo = loo_centroid_predict(df)
    acc = float((loo == df["theme"]).mean())
    recall = {th: round(float(((loo == th) & (df["theme"] == th)).sum() / (df["theme"] == th).sum()), 3) for th in sorted(df["theme"].unique())}
    conf = pd.crosstab(df["theme"], loo, rownames=["ours"], colnames=["from provided topics"])
    disagree = df[loo != df["theme"]][["title", "theme", "prov_topics"]].assign(from_topics=loo[loo != df["theme"]])
    san = sanity_checks(df)
    ex = pick_examples(df, loo)
    tr = tag_report(df)
    for k, v in tabs.items():
        v.to_csv(OUT / f"{k}.csv")
    conf.to_csv(OUT / "ours_vs_provided_topics_confusion.csv")
    san.to_csv(OUT / "sanity_checks.csv", index=False)
    json.dump(ex, open(OUT / "examples.json", "w"), indent=1)
    json.dump(tr, open(OUT / "tags.json", "w"), indent=1)
    figs = figures(df, tabs)
    summary = dict(
        n=len(df),
        loo_accuracy=round(acc, 3),
        loo_recall=recall,
        characteristic_provided_tokens=characteristic_tokens(df),
        n_disagree=int((loo != df["theme"]).sum()),
        figures=figs,
        incident_calls=int(df["incident_flag"].sum()),
        incident_by_theme=df[df["incident_flag"]].theme.value_counts().to_dict(),
    )
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
    disagree.assign(prov_topics=disagree.prov_topics.map("; ".join)).to_csv(OUT / "disagreements_with_provided_topics.csv", index=False)
    return dict(summary=summary, sanity=san, tabs=tabs, tags=tr)


if __name__ == "__main__":
    r = main()
    print(json.dumps(r["summary"], indent=1)[:3000])
    print(r["sanity"].to_string())

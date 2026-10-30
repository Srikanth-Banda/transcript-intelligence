"""Task 3 exploration: scripted feasibility checks for bonus insight candidates.

Frozen pipeline outputs only; no LLM calls. Provided summary/key moments are COMPARISON data.
Run: PYTHONPATH=src uv run python -m ti.analysis.candidates
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

from ti.analysis.themes import DATASET, ROOT, load_frame

OUT = ROOT / "outputs" / "analysis" / "candidates"
OUTAGE_START = "2026-03-10"  # first outage call in the data (war room + Cobalt URGENT)
OUTAGE_WORDS = re.compile(r"\b(?:outage|incident|downtime|went down|post-?mortem|zero visibility|lost visibility)\b", re.I)
COMPETITORS = ["SentinelShield", "VaultEdge", "CyberNova", "Fortiguard"]

DAYS = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
TIME_PHRASE = re.compile(
    rf"\b(?:by|before|within|until|on|this|next|end of(?: the)?)\s+(?:{DAYS}|tomorrow|today|tonight|the hour|the day|day|week|month|quarter|\d+\s+(?:business\s+)?(?:hours?|days?|weeks?))\b"
    rf"|\b(?:tomorrow|tonight|within the hour|end of (?:the )?(?:day|week|month)|next week|this week|this afternoon|this evening)\b",
    re.I,
)
COMMIT = re.compile(r"\b(?:I'?ll|I will|we'?ll|we will|I can get|I'?m going to|we'?re going to|I'?ll make sure|I'?ve scheduled)\b", re.I)
EMPATHY = re.compile(
    r"\b(?:I understand|I hear you|I'?m (?:so )?sorry|I apologi[sz]e|that(?:'s| is) (?:really )?frustrating|I can imagine|I appreciate your patience|thank you for your patience|I know this is|that must be|I want to make sure)\b",
    re.I,
)
FOLLOWUP = re.compile(r"\b(?:as promised|last time|you (?:said|mentioned|promised)|when we (?:spoke|talked|last)|following up|follow-up|per our (?:call|conversation)|since we (?:spoke|talked))\b", re.I)


def transcripts(ids) -> dict[str, list[dict]]:
    return {m: json.load(open(DATASET / m / "transcript.json"))["data"] for m in ids}


def staff_names(emails) -> set[str]:
    return {e.split("@")[0].replace(".", " ").lower() for e in emails if e.endswith("@aegiscloud.com")}


def is_customer(speaker: str, emails, has_customer: bool) -> bool:
    return has_customer and speaker.lower() not in staff_names(emails)


def spearman(x: pd.Series, y: pd.Series) -> float:
    d = pd.concat([x, y], axis=1).dropna()
    return float(d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank())) if len(d) > 2 else float("nan")


# ---------------- (a) incident blast radius ----------------
def blast_radius(df: pd.DataFrame, T) -> dict:
    cust = df[df.customer_org != ""].copy()
    inc_orgs = sorted(cust[cust.incident_flag].customer_org.unique())
    pre = cust[cust.date < OUTAGE_START]
    post = cust[cust.date >= OUTAGE_START]
    both = sorted(set(pre.customer_org) & set(post.customer_org))
    rows = []
    for o in both:
        a = pre[pre.customer_org == o].customer_score.mean()
        b = post[post.customer_org == o].customer_score.mean()
        rows.append(dict(org=o, touched=o in inc_orgs, n_pre=int((pre.customer_org == o).sum()), n_post=int((post.customer_org == o).sum()), pre=round(a, 2), post=round(b, 2), delta=round(b - a, 2)))
    ba = pd.DataFrame(rows)
    ba.to_csv(OUT / "a_before_after_by_account.csv", index=False)
    weekly = df.assign(week=pd.to_datetime(df.date).dt.strftime("%G-W%V")).groupby("week").agg(n=("meeting_id", "count"), mean_call_score=("call_score", "mean"), incident_share=("incident_flag", "mean")).round(2)
    weekly.to_csv(OUT / "a_weekly_timeline.csv")
    # incident-flagged vs not, by type, call score
    by = df.groupby(["type", "incident_flag"]).agg(n=("meeting_id", "count"), call=("call_score", "mean"), cust=("customer_score", "mean")).round(2)
    by.to_csv(OUT / "a_incident_vs_not_by_type.csv")
    # text corroboration of the incident flag
    kw = OUTAGE_WORDS
    hits = {m: sum(1 for x in t if kw.search(x["sentence"])) for m, t in T.items()}
    df2 = df.assign(kw_hits=df.meeting_id.map(hits))
    flagged_weak = df2[df2.incident_flag & (df2.kw_hits <= 1)][["date", "type", "title", "theme", "kw_hits"]]
    unflagged_strong = df2[~df2.incident_flag & (df2.kw_hits >= 5)][["date", "type", "title", "theme", "kw_hits"]]
    flagged_weak.to_csv(OUT / "a_flag_check_flagged_but_few_keywords.csv", index=False)
    unflagged_strong.to_csv(OUT / "a_flag_check_unflagged_but_many_keywords.csv", index=False)
    # date sanity: calls dated before the first outage call that already discuss the outage
    df2["strict_hits"] = df2.meeting_id.map(lambda m: sum(1 for x in T[m] if OUTAGE_WORDS.search(x["sentence"])))
    early = df2[(df2.date < OUTAGE_START) & (df2.strict_hits >= 2)].sort_values("date")
    early[["date", "type", "title", "strict_hits", "incident_flag"]].to_csv(OUT / "a_date_consistency_early_calls_discussing_outage.csv", index=False)
    touched = ba[ba.touched]
    untouched = ba[~ba.touched]
    return dict(
        outage_start=OUTAGE_START,
        incident_flagged_calls=int(df.incident_flag.sum()),
        flagged_by_type=df[df.incident_flag]["type"].value_counts().to_dict(),
        accounts_with_incident_call=len(inc_orgs),
        accounts_total=int(cust.customer_org.nunique()),
        accounts_with_calls_before_and_after=len(both),
        mean_customer_score_before=round(float(ba.pre.mean()), 2) if len(ba) else None,
        mean_customer_score_after=round(float(ba.post.mean()), 2) if len(ba) else None,
        accounts_dropped_0_5_or_more=int((ba.delta <= -0.5).sum()) if len(ba) else 0,
        accounts_improved_0_5_or_more=int((ba.delta >= 0.5).sum()) if len(ba) else 0,
        touched_n=len(touched), touched_mean_delta=round(float(touched.delta.mean()), 2) if len(touched) else None,
        untouched_n=len(untouched), untouched_mean_delta=round(float(untouched.delta.mean()), 2) if len(untouched) else None,
        calls_dated_before_outage=int((df.date < OUTAGE_START).sum()),
        early_calls_discussing_outage=int(len(early)),
        early_calls_titles=early.title.tolist(),
        weekly=weekly.reset_index().to_dict("records"),
        flag_check=dict(flagged_with_le1_keyword_hit=int(len(flagged_weak)), unflagged_with_ge5_keyword_hits=int(len(unflagged_strong)),
                        flagged_weak_titles=flagged_weak.title.tolist(), unflagged_strong_titles=unflagged_strong.title.tolist()),
        type_incident=by.reset_index().to_dict("records"),
    )


# ---------------- (b) churn-risk early warning ----------------
def churn_risk(df: pd.DataFrame, T) -> dict:
    ext = df[df["type"] == "external"].copy()
    comp_re = re.compile("|".join(COMPETITORS), re.I)
    rows = []
    for _, r in ext.iterrows():
        cust_turns = [x["sentence"] for x in T[r.meeting_id] if is_customer(x["speaker_name"], r.emails, True)]
        comp_cust = any(comp_re.search(s) for s in cust_turns)
        eval_cust = any(re.search(r"\b(?:evaluat\w+|alternatives?|other vendors?|switch\w*|shop\w* around|RFP)\b", s, re.I) for s in cust_turns)
        prov_churn = sum(1 for m in r.prov_moments if m.get("type") == "churn_signal")
        pts = 0
        why = []
        if r.customer_score <= 2.5:
            pts += 2; why.append("customer score <= 2.5")
        elif r.customer_score <= 3.0:
            pts += 1; why.append("customer score <= 3.0")
        if (r.traj_end - r.traj_start) <= -0.5:
            pts += 1; why.append("tone fell during call")
        if comp_cust or eval_cust:
            pts += 1; why.append("customer raises competitor/alternatives")
        if r.incident_flag:
            pts += 1; why.append("call concerns the outage")
        rows.append(dict(meeting_id=r.meeting_id, date=r.date, org=r.customer_org, title=r.title, theme=r.theme, customer_score=r.customer_score,
                         traj_delta=round(r.traj_end - r.traj_start, 2), competitor_or_alternatives_by_customer=bool(comp_cust or eval_cust),
                         incident=bool(r.incident_flag), our_points=pts, why="; ".join(why), provided_churn_signal_moments=prov_churn))
    cr = pd.DataFrame(rows).sort_values(["our_points", "customer_score"], ascending=[False, True])
    cr.to_csv(OUT / "b_external_calls_risk_ranking.csv", index=False)
    # account roll-up: latest external call per account
    last = cr.sort_values("date").groupby("org").tail(1).sort_values(["our_points", "customer_score"], ascending=[False, True])
    last.to_csv(OUT / "b_accounts_latest_external_call.csv", index=False)
    hi = cr[cr.our_points >= 3]
    prov_any = cr.provided_churn_signal_moments > 0
    both = int(((cr.our_points >= 3) & prov_any).sum())
    return dict(
        external_calls=len(cr),
        flagged_ge3=int(len(hi)), flagged_ge3_with_provided_churn_signal=both,
        provided_churn_signal_calls=int(prov_any.sum()),
        corr_our_points_vs_provided_churn_moments=round(spearman(cr.our_points, cr.provided_churn_signal_moments), 2),
        corr_customer_score_vs_provided_churn_moments=round(spearman(cr.customer_score, cr.provided_churn_signal_moments), 2),
        top_accounts=last.head(8)[["org", "date", "title", "our_points", "customer_score", "why"]].to_dict("records"),
        renewal_calls_incident_flag=int(((ext.theme == "Commercial Renewals and Retention") & ext.incident_flag).sum()),
        renewal_calls=int((ext.theme == "Commercial Renewals and Retention").sum()),
    )


# ---------------- (c) support -> engineering loop ----------------
def support_loop(df: pd.DataFrame) -> dict:
    sup = df[df["type"] == "support"].copy()
    eng = re.compile(r"\b(?:engineering|escalat\w+|bug|hotfix|patch|ticket|JIRA|root cause|fix\b|workaround)", re.I)
    sup["handoff"] = sup.prov_actions.map(lambda a: any(eng.search(x) for x in a))
    by_area = sup.groupby("product_area").agg(n=("meeting_id", "count"), mean_customer_score=("customer_score", "mean"), incident=("incident_flag", "sum"), handoff=("handoff", "sum")).round(2)
    by_area.to_csv(OUT / "c_support_by_product_area.csv")
    cnt = sup.customer_org.value_counts()
    rep = cnt[cnt >= 2]
    repeats = []
    for o in rep.index:
        sub = sup[sup.customer_org == o].sort_values("date")
        gaps = pd.to_datetime(sub.date).diff().dt.days.dropna().astype(int).tolist()
        repeats.append(dict(org=o, support_calls=len(sub), titles=sub.title.tolist(), dates=sub.date.tolist(), gaps_days=gaps, areas=sub.product_area.tolist()))
    all_cust = df[df.customer_org != ""]
    other_types = all_cust.groupby("customer_org")["type"].agg(lambda s: set(s))
    # accounts with support calls AND an external call (account manager sees the pain?)
    both = [o for o in sup.customer_org.unique() if "external" in other_types.get(o, set())]
    t = sup.sort_values("date")
    return dict(
        support_calls=len(sup),
        accounts_with_support=int(sup.customer_org.nunique()),
        accounts_with_2plus_support=len(rep),
        calls_from_repeat_accounts=int(rep.sum()),
        repeats=repeats,
        by_area=by_area.reset_index().to_dict("records"),
        support_calls_with_engineering_handoff_in_provided_actions=int(sup.handoff.sum()),
        support_calls_incident_flag=int(sup.incident_flag.sum()),
        accounts_with_support_and_external=len(both),
        lowest_customer_score_support=t.sort_values("customer_score").head(5)[["date", "title", "customer_score", "product_area", "incident_flag"]].to_dict("records"),
    )


# ---------------- (d) commitment tracking ----------------
def commitments(df: pd.DataFrame, T) -> dict:
    rows = []
    for _, r in df.iterrows():
        has_cust = r["type"] != "internal"
        sn = staff_names(r.emails)
        for i, x in enumerate(T[r.meeting_id]):
            s = x["sentence"]
            if x["speaker_name"].lower() in sn or not has_cust:
                if COMMIT.search(s) and TIME_PHRASE.search(s):
                    rows.append(dict(meeting_id=r.meeting_id, date=r.date, org=r.customer_org, type=r["type"], speaker=x["speaker_name"], turn=i, sentence=s, when=TIME_PHRASE.search(s).group(0)))
    cm = pd.DataFrame(rows)
    cm.to_csv(OUT / "d_commitments_with_time_phrase.csv", index=False)
    cust_cm = cm[cm.org != ""]
    later = []
    follow_hits = 0
    for _, c in cust_cm.iterrows():
        nxt = df[(df.customer_org == c.org) & (df.date > c.date)].sort_values("date")
        if len(nxt):
            n0 = nxt.iloc[0]
            gap = (date.fromisoformat(n0.date) - date.fromisoformat(c.date)).days
            fh = any(FOLLOWUP.search(x["sentence"]) for x in T[n0.meeting_id])
            later.append(dict(meeting_id=c.meeting_id, org=c.org, gap_days=gap, next_title=n0.title, next_mentions_followup=bool(fh)))
    lt = pd.DataFrame(later)
    chain = promise_chain(df, T)
    prov_dated = sum(1 for _, r in df.iterrows() for a in r.prov_actions if TIME_PHRASE.search(a))
    prov_total = int(sum(len(a) for a in df.prov_actions))
    return dict(
        commitment_sentences=len(cm), calls_with_commitment=int(cm.meeting_id.nunique()) if len(cm) else 0,
        customer_facing_commitments=len(cust_cm),
        with_a_later_call_same_account=len(lt),
        later_call_within_14_days=int((lt.gap_days <= 14).sum()) if len(lt) else 0,
        later_call_mentions_followup_language=int(lt.next_mentions_followup.sum()) if len(lt) else 0,
        provided_action_items_total=prov_total, provided_action_items_with_time_phrase=prov_dated,
        promise_chain=chain,
        examples=cm.head(6)[["date", "org", "speaker", "sentence"]].to_dict("records"),
    )


def promise_chain(df: pd.DataFrame, T) -> dict:
    """The one commitment chain we can follow: remediation promises made in the Mar 16 outage call versus later calls."""
    pat = re.compile(r"circuit[- ]breaker|active[- ]active|redundan\w+ (?:processing )?nodes?|retroactive", re.I)
    rows = []
    for _, r in df.sort_values("date").iterrows():
        hits = [x["sentence"] for x in T[r.meeting_id] if pat.search(x["sentence"])]
        if hits:
            rows.append(dict(date=r.date, type=r["type"], title=r.title, hits=len(hits), first=hits[0][:220]))
    pd.DataFrame(rows).to_csv(OUT / "d_remediation_promise_chain.csv", index=False)
    first = rows[0]["date"] if rows else None
    return dict(calls_mentioning_remediation_terms=len(rows), first_date=first, after_first=[(x["date"], x["title"]) for x in rows[1:8]])


# ---------------- (e) competitive intelligence ----------------
CONTEXTS = {
    "pricing": r"\b(?:price|pricing|cheaper|cost|discount|budget|expensive|undercut)\w*",
    "detection / threat": r"\b(?:detect\w*|threat\w*|alert\w*|false positive\w*|SIEM)\b",
    "backup / restore": r"\b(?:backup\w*|restor\w*|recover\w*|RTO\w*|snapshot\w*)\b",
    "reliability / outage": r"\b(?:outage|reliab\w*|downtime|incident|uptime)\b",
    "identity / IAM": r"\b(?:identity|IAM|SSO|MFA|SAML|provision\w*)\b",
    "platform breadth": r"\b(?:platform|single pane|consolidat\w*|all-in-one|broad)\w*",
}


def competitive(df: pd.DataFrame, T) -> dict:
    res = {}
    base_inc = float(df.incident_flag.mean())
    rows = []
    for c in COMPETITORS:
        ms = [m for m, t in T.items() if any(c in x["sentence"] for x in t)]
        sub = df[df.meeting_id.isin(ms)]
        ctx = Counter()
        cust_raised = 0
        quotes = []
        for m in ms:
            r = df[df.meeting_id == m].iloc[0]
            for i, x in enumerate(T[m]):
                if c in x["sentence"]:
                    win = " ".join(y["sentence"] for y in T[m][max(0, i - 1): i + 2])
                    for k, p in CONTEXTS.items():
                        if re.search(p, win, re.I):
                            ctx[k] += 1
                    if r["type"] != "internal" and is_customer(x["speaker_name"], r.emails, True):
                        cust_raised += 1
                    if len(quotes) < 2 and len(x["sentence"]) < 320:
                        quotes.append(dict(title=r.title, date=r.date, speaker=x["speaker_name"], quote=x["sentence"]))
        rows.append(dict(competitor=c, calls=len(ms), by_type=sub["type"].value_counts().to_dict(), by_month=sub.month.value_counts().sort_index().to_dict(),
                         incident_flag_share=round(float(sub.incident_flag.mean()), 2) if len(sub) else None,
                         customer_raised_mentions=cust_raised, contexts=dict(ctx.most_common(4)), mean_call_score=round(float(sub.call_score.mean()), 2) if len(sub) else None, quotes=quotes,
                         orgs=sorted(set(sub.customer_org) - {""})))
    ca = df[df.meeting_id.isin({m for m, t in T.items() if any(any(c in x["sentence"] for c in COMPETITORS) for x in t)})]
    comp_any = ca.meeting_id.nunique()
    res["any_competitor_calls"] = int(comp_any)
    res["any_competitor_by_type"] = ca["type"].value_counts().to_dict()
    res["any_competitor_incident_share"] = round(float(ca.incident_flag.mean()), 2)
    res["base_incident_share"] = round(base_inc, 2)
    res["any_competitor_by_month"] = ca.month.value_counts().sort_index().to_dict()
    res["calls_by_month"] = df.month.value_counts().sort_index().to_dict()
    res["competitors"] = rows
    # customer feature asks: Okta / connector asks etc.
    pd.DataFrame([{k: v for k, v in r.items() if k not in ("quotes",)} for r in rows]).to_csv(OUT / "e_competitors.csv", index=False)
    return res


# ---------------- (f) support coaching signal ----------------
def coaching(df: pd.DataFrame, T) -> dict:
    sup = df[(df["type"] == "support")].copy()
    rows = []
    for _, r in sup.iterrows():
        sn = staff_names(r.emails)
        staff_turns = [x for x in T[r.meeting_id] if x["speaker_name"].lower() in sn]
        if not staff_turns:
            continue
        agent = Counter(x["speaker_name"] for x in staff_turns).most_common(1)[0][0]
        emp = sum(1 for x in staff_turns if EMPATHY.search(x["sentence"]))
        rows.append(dict(meeting_id=r.meeting_id, date=r.date, title=r.title, agent=agent, staff_turns=len(staff_turns), empathy_markers=emp,
                         empathy_rate=round(emp / len(staff_turns), 3), customer_score=r.customer_score, traj_delta=round(r.traj_end - r.traj_start, 2)))
    c = pd.DataFrame(rows)
    c.to_csv(OUT / "f_support_calls_coaching.csv", index=False)
    per = c.groupby("agent").agg(calls=("meeting_id", "count"), empathy_rate=("empathy_rate", "mean"), customer_score=("customer_score", "mean"), traj_delta=("traj_delta", "mean")).round(2)
    per.to_csv(OUT / "f_by_agent.csv")
    return dict(
        support_calls=len(c),
        spearman_empathy_rate_vs_traj_delta=round(spearman(c.empathy_rate, c.traj_delta), 2),
        spearman_empathy_rate_vs_customer_score=round(spearman(c.empathy_rate, c.customer_score), 2),
        mean_traj_delta=round(float(c.traj_delta.mean()), 2),
        share_calls_customer_tone_improved=round(float((c.traj_delta > 0).mean()), 2),
        by_agent=per.reset_index().to_dict("records"),
        calls_with_zero_empathy_markers=int((c.empathy_markers == 0).sum()),
    )


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_frame()
    T = transcripts(df.meeting_id)
    res = dict(a=blast_radius(df, T), b=churn_risk(df, T), c=support_loop(df), d=commitments(df, T), e=competitive(df, T), f=coaching(df, T))
    json.dump(res, open(OUT / "summary.json", "w"), indent=1, default=str)
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, indent=1, default=str)[:200])

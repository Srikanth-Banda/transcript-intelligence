"""Offline tests for the analysis helpers (no pipeline outputs needed)."""
import pandas as pd

from ti.analysis import candidates as C
from ti.analysis import themes as T


def test_split_tags():
    assert T.split_tags("A|B") == ["A", "B"]
    assert T.split_tags("A") == ["A"]
    assert T.split_tags(float("nan")) == []
    assert T.split_tags("") == []


def test_commitment_regex_needs_both_promise_and_time():
    s = "I'll send the report by Wednesday."
    assert C.COMMIT.search(s) and C.TIME_PHRASE.search(s)
    assert not C.TIME_PHRASE.search("I will send the report.")
    assert C.TIME_PHRASE.search("We'll have it within the hour")


def test_empathy_regex():
    assert C.EMPATHY.search("I'm so sorry about that")
    assert not C.EMPATHY.search("Let me pull up the case")


def test_customer_detection_uses_staff_names_not_email_local_parts():
    emails = ["sarah.chen@aegiscloud.com", "g.fisk@summittrust.com"]
    assert not C.is_customer("Sarah Chen", emails, True)
    assert C.is_customer("Gregory Fisk", emails, True)
    assert not C.is_customer("Gregory Fisk", emails, False)  # internal call: no customer


def test_spearman_monotone():
    a = pd.Series([1, 2, 3, 4, 5]); b = pd.Series([10, 20, 30, 40, 50])
    assert round(C.spearman(a, b), 3) == 1.0
    assert round(C.spearman(a, b[::-1].reset_index(drop=True)), 3) == -1.0


def test_sanity_checks_threshold():
    df = pd.DataFrame({
        "theme": ["Billing and Usage Disputes"] * 4 + ["Commercial Renewals and Retention"] * 4,
        "type": ["support", "support", "support", "external", "external", "support", "support", "support"],
    })
    r = T.sanity_checks(df).set_index("theme")
    assert r.loc["Billing and Usage Disputes", "passed"]  # 0.75 >= 0.5
    assert not r.loc["Commercial Renewals and Retention", "passed"]  # 1 of 4 external = 0.25 < 0.5


def test_loo_centroid_recovers_obvious_themes():
    df = pd.DataFrame({
        "theme": ["R", "R", "R", "S", "S", "S"],
        "prov_topics": [["renewal", "pricing"], ["renewal negotiation"], ["contract renewal"], ["sprint planning"], ["sprint retro"], ["sprint planning"]],
    })
    assert (T.loo_centroid_predict(df) == df["theme"]).all()

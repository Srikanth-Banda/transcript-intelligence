"""Offline check: numbers embedded in the explorer match recomputation from outputs/."""
import csv
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import build_explorer as be  # noqa: E402


def rows(p):
    return list(csv.DictReader(open(ROOT / "outputs" / p, encoding="utf-8")))


def test_embedded_numbers_match_outputs():
    d = be.build()
    s0 = rows("stage0_final.csv"); s1 = rows("stage1/stage1_final.csv"); s2 = rows("stage2/stage2_final.csv")
    assert d["meta"]["n"] == len(s0) == 100
    assert d["pipeline"]["s0"]["counts"] == dict(Counter(r["label"] for r in s0))
    assert dict(d["pipeline"]["s1"]["themes"]) == dict(Counter(r["primary_theme"] for r in s1))
    lab = {r["meeting_id"]: r["label"] for r in s0}
    for t in be.TYPES:
        want = round(st.mean(float(r["call_score"]) for r in s2 if lab[r["meeting_id"]] == t), 2)
        assert d["pipeline"]["s2"]["mean"][t] == want
    assert d["pipeline"]["s1"]["incident_touch"] == sum(1 for r in s1 if r["incident"])
    assert all(len(c["tm"]) == len(c["tr"]) == len(c["pv"]) for c in d["calls"])


def test_rendered_html_has_no_script_breakers():
    html = be.render(be.build(), (ROOT / "app" / "explorer_tpl.html").read_text(encoding="utf-8"))
    assert html.count("</script") == 1 and "/*DATA*/null" not in html

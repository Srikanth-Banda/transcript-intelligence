"""Offline check: the walkthrough page has its 7 scenes, numbers come from outputs/, and the wording rules hold."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import build_walkthrough as bw  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(scope="module")
def built():
    d = bw.collect()
    return d, bw.render(d, (ROOT / "app" / "walkthrough_tpl.html").read_text(encoding="utf-8"))


def text_of(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_seven_scenes_in_order(built):
    _, html = built
    assert re.findall(r'<section class="scene" id="(s\d)"', html) == [f"s{i}" for i in range(1, 8)]
    assert html.count('data-go="') == 7 and html.count('class="dcard"') == 4
    assert "<!--SCENES-->" not in html and "<!--NAV-->" not in html


def test_key_numbers_present(built):
    d, html = built
    t = text_of(html)
    for s in ["2.93", "3.95", "2.57", "3.62", "31 of 100", "22 of 32", "74%", "42%", "6/26", "16/36", "9/38", "35%", "2%",
              "15/15", "20/20", "19/20", "17/20", "0.91", "9 exact", "within 0.5", "0.37", "3 of 70", "30 internal", "11 external calls"]:
        assert s in t, s
    assert d["s2"]["within"] == 15 and d["s2"]["exact"] == 9 and round(d["s2"]["rank"], 2) == 0.91
    assert len(d["risk"]) == 11 and d["comp"]["any_calls"] == 31


def test_replay_block_is_real_output(built):
    d, html = built
    assert "captured output of the replay command" in html
    assert "demo_replay.py 41" in html
    assert "STAGE 1  theme:" in d["replay"] and "cache_hit: stage1=True stage2=True" in d["replay"]
    assert "replay: saved model answers, no key, no network; a miss is an error, never a silent live call" in html


def test_banned_wording_and_claims(built):
    _, html = built
    t = text_of(html).lower()
    for w in ("blind", "generous", "independent"):
        assert w not in t, w
    for w in ("caused by the outage", "because of the outage"):
        assert w not in t, w
    assert "mostly the outage, cannot rule out other causes" in t


def test_self_contained_and_small(built):
    _, html = built
    assert "<script src" not in html.lower() and "<script" in html
    assert not re.search(r"<script[^>]+src=", html, re.I)
    assert not re.search(r"(?:src|href)=[\"']https?://(?!fonts\.googleapis\.com)", html)
    assert len(html.encode("utf-8")) < 3_000_000
    assert html.count("</script") == 1

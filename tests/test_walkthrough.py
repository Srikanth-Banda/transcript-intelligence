"""Offline check: the walkthrough page has its 9 scenes, numbers come from outputs/, and the wording rules hold."""
import html as htmllib
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


def scene_html(html: str, sid: str) -> str:
    return re.search(rf'<section class="scene" id="{sid}".*?</section>', html, re.S).group(0)


def test_nine_scenes_in_order(built):
    _, html = built
    assert re.findall(r'<section class="scene" id="(s\d)"', html) == [f"s{i}" for i in range(1, 10)]
    assert html.count('data-go="') == 9 and html.count('class="dcard"') == 5
    assert "<!--SCENES-->" not in html and "<!--NAV-->" not in html
    assert "1-9" in html and "/^[1-9]$/" in html
    for sid in (f"s{i}" for i in range(1, 10)):
        assert 'class="sowhat"' in scene_html(html, sid)


def test_key_numbers_present(built):
    d, html = built
    t = text_of(html)
    for s in ["2.93", "3.95", "2.57", "3.62", "31 of 100", "22 of 32", "74%", "42%", "6/26", "16/36", "9/38", "35%", "2%",
              "15/15", "20/20", "19/20", "17/20", "0.91", "9 exact", "0.37", "30 calls with no outside attendee", "support 30", "external 40",
              "internal 30", "Feb 3.71", "Mar 2.94", "Apr 3.91", "0.96", "42 touch it", "3 of the 70", "94+ tests", "21 slides"]:
        assert s in t, s
    assert d["s2"]["within"] == 15 and d["s2"]["exact"] == 9 and round(d["s2"]["rank"], 2) == 0.91
    assert len(d["risk"]) == 11 and d["comp"]["any_calls"] == 31 and len(d["cands"]) == 6


def test_pipeline_scene_facts(built):
    _, html = built
    t = text_of(scene_html(html, "s3"))
    for s in ["Withheld", "provided score, summary, topics and title", "Gemini 3.8 Flash", "temperature 0", "seed 7", "Replayable cache",
              "Stage 0", "Stage 1", "Stage 2", "Stage 3", "Sees", "Never", "Review", "taxonomy v1", "No model call"]:
        assert s in t, s


def test_decision_cards_cover_options_and_weakness(built):
    _, html = built
    s4 = scene_html(html, "s4")
    cards = re.findall(r'<article class="dcard".*?</article>', s4, re.S)
    assert len(cards) == 5
    for c in cards:
        assert "Known weakness" in c and "Why this one" in c and "The problem" in c and c.count("<tr") >= 4
        assert c.count('class="pick"') == (3 if "Evidence" in c and "Score /20" in c else 1)
    t = text_of(s4)
    for s in ["Title rule alone", "Gemini 3.8 Flash for every stage", "under my delegation", "scored format, not correctness",
              "overrode it", "$0.836", "$0.225", "Not presented"]:
        assert s in t, s


def test_rubric_quotes_exist_in_assignment(built):
    d, html = built
    t = htmllib.unescape(text_of(scene_html(html, "s9")))
    for q in ["show us how you think", "how you handle ambiguity", "the quality of your insights", "Lead with insights, not code",
              "be transparent about what's original", "Clean, readable code"]:
        assert q in d["assignment"] and q in t, q
    assert t.rstrip().endswith("Deck on screen for reference next.")


def test_replay_block_is_real_output(built):
    d, html = built
    assert "captured output of the replay command" in html
    assert "demo_replay.py 41" in html
    assert "STAGE 1  theme:" in d["replay"] and "cache_hit: stage1=True stage2=True" in d["replay"]
    assert "STAGE 1  theme:" in html and "cache_hit: stage1=True stage2=True" in html


def test_banned_wording_and_claims(built):
    _, html = built
    t = text_of(html).lower()
    for w in ("blind", "generous", "independent"):
        assert w not in t, w
    for w in ("caused by the outage", "because of the outage", "the outage caused the"):
        assert w not in t.replace("that the outage caused the dip", ""), w
    assert "mostly the outage, cannot rule out other causes" in t
    assert "probably a floor" in t and "an llm judgment" in t and "my own review" in t
    assert "co-occurrence" in t


def test_type_is_large_enough_for_video():
    """Every font size in the template is at least 1.25rem (20px at 1080p), except the fixed 16px base of the indicator."""
    css = (ROOT / "app" / "walkthrough_tpl.html").read_text(encoding="utf-8")
    css = css[css.index("<style>"):css.index("</style>")]
    sizes = [float(m) for m in re.findall(r"font(?:-size)?:\s*(?:\d{3}\s+)?(?:italic\s+)?(\d*\.?\d+)rem", css)]
    assert sizes and min(sizes) >= 1.25, min(sizes)


def test_self_contained_and_small(built):
    _, html = built
    assert "<script src" not in html.lower() and "<script" in html
    assert not re.search(r"<script[^>]+src=", html, re.I)
    assert not re.search(r"(?:src|href)=[\"']https?://(?!fonts\.googleapis\.com)", html)
    assert len(html.encode("utf-8")) < 3_000_000
    assert html.count("</script") == 1

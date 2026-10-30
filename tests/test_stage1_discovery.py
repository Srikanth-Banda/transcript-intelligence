"""Offline tests for the Stage 1 discovery scoring / consolidation logic (no network, no key)."""

from ti.load import load_meetings
from ti.stage1_discovery import (
    BatchDiscovery,
    BatchProduct,
    BatchTheme,
    Consolidation,
    Dropped,
    Evidence,
    MergedProduct,
    MergedTheme,
    PilotRecord,
    best_matches,
    call_label,
    check_consolidation,
    check_pilot,
    jaccard,
    label_map,
    materialize,
    quote_exact,
    quote_loose,
    render_batch,
    split_batches,
    stability_summary,
    theme_by_type,
    validate_batch,
)


def _theme(name, ids, quote=("AAAAAA", "hello there")):
    return BatchTheme(name=name, definition="d", distinguishing="x", owner="product manager",
                      actionable_because="a", meeting_ids=ids, evidence=[Evidence(meeting_id=quote[0], quote=quote[1])])


def test_call_labels_are_unique_for_all_100():
    ms = load_meetings()
    assert len(label_map(ms)) == 100


def test_split_is_deterministic_balanced_and_covers_everything():
    ids = [f"id{i:03d}" for i in range(100)]
    a = split_batches(ids, 4, 11)
    assert a == split_batches(ids, 4, 11)
    assert sorted(i for b in a for i in b) == sorted(ids)
    assert {len(b) for b in a} == {25}
    assert a != split_batches(ids, 4, 23)  # a different seed gives a different split


def test_split_handles_uneven_sizes():
    sizes = sorted(len(b) for b in split_batches([str(i) for i in range(10)], 4, 1))
    assert sizes == [2, 2, 3, 3]


def test_render_batch_hides_title_and_provided_fields():
    ms = load_meetings()
    by = label_map(ms)
    m = ms[0]
    text = render_batch(ms, [call_label(m.meeting_id)], by)
    assert text.startswith("calls in this batch: 1")
    assert f"=== call {call_label(m.meeting_id)} ===" in text
    assert m.title not in text
    assert m.provided.summary[:40] not in text
    assert "(customer)" in text or "(aegis_staff)" in text


def test_quote_checks():
    s = ["I can't make it today — sorry.", "Okay, that works."]
    assert quote_exact("that works", s)
    assert not quote_exact("that works.  Really", s)
    assert not quote_exact("", s)
    assert quote_loose("I can't make it today - sorry.", s)  # dash normalised
    assert not quote_exact("I can't make it today - sorry.", s)


def test_validate_batch_counts_bad_ids_and_quotes():
    sentences = {"AAAAAA": ["hello there friend"], "BBBBBB": ["bye now"]}
    out = BatchDiscovery(
        themes=[_theme("T1", ["AAAAAA", "ZZZZZZ"]), _theme("T2", ["BBBBBB"], quote=("BBBBBB", "not in text"))],
        product_areas=[BatchProduct(name="P", meeting_ids=["AAAAAA"], evidence=[Evidence(meeting_id="QQQQQQ", quote="x")])],
        other_note="none")
    v = validate_batch(out, ["AAAAAA", "BBBBBB"], sentences)
    assert v["ids_unknown"] == 1
    assert v["n"] == 3 and v["known_id"] == 2 and v["exact"] == 1


def _batches():
    b1 = BatchDiscovery(themes=[_theme("Outage", ["A", "B"]), _theme("Pricing", ["C"])],
                        product_areas=[BatchProduct(name="Detect", meeting_ids=["A", "B"], evidence=[])], other_note="")
    b2 = BatchDiscovery(themes=[_theme("Incident response", ["D", "B"])],
                        product_areas=[BatchProduct(name="detect", meeting_ids=["D"], evidence=[])], other_note="")
    return [b1, b2]


def test_consolidation_checks_flag_missing_duplicate_and_unknown_sources():
    bs = _batches()
    good = Consolidation(
        themes=[MergedTheme(name="Outage", definition="d", distinguishing="x", owner="engineering lead",
                            actionable_because="a", merged_from=["b1.t1", "b2.t1"])],
        product_areas=[MergedProduct(name="Detect", merged_from=["b1.p1", "b2.p1"])],
        dropped=[Dropped(source="b1.t2", reason="topic label")], other_note="")
    c = check_consolidation(good, bs)
    assert not c["themes_missing"] and not c["themes_unknown"] and not c["themes_duplicated"]
    assert not c["products_missing"]
    bad = good.model_copy(update={"dropped": [], "themes": [good.themes[0].model_copy(update={"merged_from": ["b1.t1", "b1.t1", "b9.t9"]})]})
    c2 = check_consolidation(bad, bs)
    assert c2["themes_missing"] == ["b1.t2", "b2.t1"]
    assert c2["themes_unknown"] == ["b9.t9"]
    assert c2["themes_duplicated"] == ["b1.t1"]


def test_materialize_takes_union_of_call_ids_by_code():
    bs = _batches()
    cons = Consolidation(
        themes=[MergedTheme(name="Outage", definition="d", distinguishing="x", owner="engineering lead",
                            actionable_because="a", merged_from=["b1.t1", "b2.t1"])],
        product_areas=[MergedProduct(name="Detect", merged_from=["b1.p1", "b2.p1"])], dropped=[], other_note="")
    m = materialize(cons, bs)
    assert m["themes"][0]["meeting_ids"] == ["A", "B", "D"]
    assert m["themes"][0]["n_calls"] == 3
    assert m["product_areas"][0]["n_calls"] == 3


def test_jaccard_and_stability():
    assert jaccard({1, 2}, {2, 3}) == 1 / 3
    assert jaccard(set(), set()) == 0.0
    r1 = [{"id": "c1", "name": "A", "meeting_ids": ["1", "2", "3"]}, {"id": "c2", "name": "B", "meeting_ids": ["9"]}]
    r2 = [{"id": "c1", "name": "A2", "meeting_ids": ["1", "2", "3", "4"]}, {"id": "c2", "name": "Z", "meeting_ids": ["7"]}]
    rows = best_matches(r1, r2)
    assert rows[0]["b_id"] == "c1" and rows[0]["jaccard"] == 0.75
    s = stability_summary(r1, r2)
    assert s["run1_themes_with_match_ge_threshold"] == 1
    assert s["run2_themes_with_match_ge_threshold"] == 1


def test_check_pilot_flags_problems():
    sentences = {"AAAAAA": ["we need a fix"], "BBBBBB": ["pricing looks high"]}
    recs = [
        PilotRecord(meeting_id="AAAAAA", primary_theme="Outage", tags=[], product_area="Detect", other_description="",
                    evidence_quote="we need a fix", confidence="high"),
        PilotRecord(meeting_id="AAAAAA", primary_theme="Nope", tags=["Outage"], product_area="Zed", other_description="",
                    evidence_quote="invented", confidence="low"),
    ]
    c = check_pilot(["AAAAAA", "BBBBBB"], recs, {"Outage"}, {"Detect"}, sentences)
    assert c["missing"] == ["BBBBBB"] and c["duplicates"] == ["AAAAAA"]
    assert c["bad_theme"] == ["AAAAAA"] and c["bad_product"] == ["AAAAAA"]
    assert c["quote_exact"] == 1 and c["quotes"] == 2


def test_theme_by_type():
    a = [{"meeting_id": "1", "primary_theme": "X"}, {"meeting_id": "2", "primary_theme": "X"},
         {"meeting_id": "3", "primary_theme": "Y"}]
    t = theme_by_type(a, {"1": "support", "2": "internal", "3": "external"})
    assert t["X"] == {"support": 1, "external": 0, "internal": 1, "total": 2}
    assert t["Y"]["external"] == 1

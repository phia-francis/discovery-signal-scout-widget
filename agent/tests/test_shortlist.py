from signal_scout.cli import shortlist

def _mk(mission, archetype, score, url):
    return {"mission_links": mission, "archetype": archetype, "total_score": score, "source_url": url}

def test_shortlist_diversity_and_coverage():
    rows = [
        _mk("ASF","shape_of_things", 9.0, "u1"),
        _mk("AHL","canary",          8.5, "u2"),
        _mk("AFS","outlier",         8.0, "u3"),
        _mk("ASF","big_idea",        7.5, "u4"),
        _mk("AHL","insights_from_field",7.2,"u5"),
    ]
    cfg = {"daily_top_n": 4, "ensure_archetype_diversity": 3, "ensure_mission_coverage": True}
    picks = shortlist(rows, cfg)
    archs = set(r["archetype"] for r in picks)
    missions = set(r["mission_links"] for r in picks)
    assert len(archs) >= 3
    assert {"ASF","AHL","AFS"} - missions == set() or len(picks) < 3

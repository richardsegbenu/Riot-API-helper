"""Tests for the stats computation."""

from __future__ import annotations

from analyser.stats import (
    MIN_GAMES_PER_CHAMPION,
    MIN_GAMES_PER_ROLE,
    PerformanceRow,
    analyse_matches,
)
from tests.fixtures import TARGET_PUUID, make_match


def test_empty_input_returns_zero_games():
    result = analyse_matches([], TARGET_PUUID)
    assert result.games_analysed == 0
    assert result.overall.games == 0


def test_overall_win_rate():
    matches = [
        make_match("Ahri", "MIDDLE", win=True),
        make_match("Ahri", "MIDDLE", win=True),
        make_match("Ahri", "MIDDLE", win=False),
        make_match("Ahri", "MIDDLE", win=False),
    ]
    result = analyse_matches(matches, TARGET_PUUID)
    assert result.overall.games == 4
    assert result.overall.win_rate == 0.5


def test_skips_matches_where_target_did_not_play():
    match = make_match("Ahri", "MIDDLE", win=True, puuid="some-other-puuid")
    result = analyse_matches([match], TARGET_PUUID)
    assert result.games_analysed == 0


def test_short_remakes_are_excluded():
    short = make_match("Ahri", "MIDDLE", win=False, duration_seconds=240)
    real = make_match("Ahri", "MIDDLE", win=True, duration_seconds=1800)
    result = analyse_matches([short, real], TARGET_PUUID)
    assert result.games_analysed == 1
    assert result.overall.win_rate == 1.0


def test_per_champion_breakdown_requires_min_games():
    matches = []
    for win in (True, True, False):
        matches.append(make_match("Ahri", "MIDDLE", win=win))
    matches.append(make_match("Yasuo", "MIDDLE", win=True))

    result = analyse_matches(matches, TARGET_PUUID)
    champ_labels = [r.label for r in result.by_champion]
    assert "Ahri" in champ_labels
    assert "Yasuo" not in champ_labels


def test_per_champion_sorted_by_win_rate_descending():
    matches = []
    for _ in range(3):
        matches.append(make_match("Garen", "TOP", win=True))
    matches.extend([
        make_match("Ahri", "MIDDLE", win=True),
        make_match("Ahri", "MIDDLE", win=False),
        make_match("Ahri", "MIDDLE", win=False),
    ])

    result = analyse_matches(matches, TARGET_PUUID)
    assert result.by_champion[0].label == "Garen"
    assert result.by_champion[1].label == "Ahri"


def test_kda_calculation():
    matches = [make_match("Ahri", "MIDDLE", win=True, kills=10, deaths=2, assists=8)]
    matches += [make_match("Ahri", "MIDDLE", win=True, kills=5, deaths=3, assists=12)
                for _ in range(2)]
    result = analyse_matches(matches, TARGET_PUUID)
    assert result.overall.kda == 6.5


def test_kda_with_zero_deaths():
    matches = [make_match("Ahri", "MIDDLE", win=True, kills=10, deaths=0, assists=5)]
    result = analyse_matches(matches, TARGET_PUUID)
    assert result.overall.kda == 15.0


def test_cs_per_minute():
    matches = [make_match("Ahri", "MIDDLE", win=True, cs=200, duration_seconds=1800)]
    result = analyse_matches(matches, TARGET_PUUID)
    assert abs(result.overall.cs_per_minute - (200 / 30)) < 0.01


def test_per_role_breakdown():
    matches = []
    for _ in range(MIN_GAMES_PER_ROLE):
        matches.append(make_match("Ahri", "MIDDLE", win=True))
    for _ in range(MIN_GAMES_PER_ROLE):
        matches.append(make_match("Garen", "TOP", win=False))

    result = analyse_matches(matches, TARGET_PUUID)
    labels = {r.label for r in result.by_role}
    assert "MIDDLE" in labels
    assert "TOP" in labels


def test_time_bucket_grouping():
    early = make_match("Ahri", "MIDDLE", win=True,
                       start_timestamp_ms=int(1_700_000_000 * 1000 + 10 * 3600 * 1000))
    late = make_match("Yasuo", "MIDDLE", win=False,
                      start_timestamp_ms=int(1_700_000_000 * 1000 + 22 * 3600 * 1000))
    result = analyse_matches([early, late], TARGET_PUUID)
    buckets = {r.label for r in result.by_time_bucket}
    assert len(buckets) >= 2


def test_performance_row_safe_when_empty():
    row = PerformanceRow(label="x")
    assert row.win_rate == 0.0
    assert row.kda == 0.0
    assert row.cs_per_minute == 0.0

"""Tests for the summoner profile lookup."""

from __future__ import annotations

from unittest.mock import MagicMock

from analyser.lookup import _compute_streak, fetch_profile
from tests.fixtures import TARGET_PUUID, make_match


def test_compute_streak_wins():
    assert _compute_streak([True, True, True, False]) == "W3"


def test_compute_streak_losses():
    assert _compute_streak([False, False, True]) == "L2"


def test_compute_streak_single_game():
    assert _compute_streak([True]) == "W1"


def test_compute_streak_empty():
    assert _compute_streak([]) == "n/a"


def _mock_client_for_lookup(matches: list, ranked_entries=None, in_game=None):
    client = MagicMock()
    client.account_by_riot_id.return_value = {"puuid": TARGET_PUUID}
    client.summoner_by_puuid.return_value = {
        "summonerLevel": 250,
        "profileIconId": 1234,
    }
    client.league_entries_by_puuid.return_value = ranked_entries or []
    client.match_ids_by_puuid.return_value = [f"m{i}" for i in range(len(matches))]
    client.match_detail.side_effect = matches
    client.active_game_by_puuid.return_value = in_game
    return client


def test_fetch_profile_basic():
    matches = [
        make_match("Ahri", "MIDDLE", win=True),
        make_match("Ahri", "MIDDLE", win=False),
        make_match("Yasuo", "MIDDLE", win=True),
    ]
    client = _mock_client_for_lookup(matches)
    profile = fetch_profile(client, "Test", "EUW", recent_count=3)

    assert profile.riot_id == "Test#EUW"
    assert profile.summoner_level == 250
    assert profile.recent_record["games"] == 3
    assert profile.recent_record["wins"] == 2
    assert profile.recent_record["losses"] == 1


def test_fetch_profile_ranked():
    ranked = [{
        "queueType": "RANKED_SOLO_5x5",
        "tier": "DIAMOND",
        "rank": "II",
        "leaguePoints": 45,
        "wins": 120,
        "losses": 100,
    }]
    client = _mock_client_for_lookup([], ranked_entries=ranked)
    profile = fetch_profile(client, "Test", "EUW")

    assert len(profile.ranked) == 1
    assert profile.ranked[0].tier == "DIAMOND"
    assert profile.ranked[0].rank == "II"
    assert profile.ranked[0].lp == 45
    assert abs(profile.ranked[0].win_rate - (120 / 220)) < 0.001


def test_fetch_profile_top_champions():
    matches = [
        make_match("Ahri", "MIDDLE", win=True),
        make_match("Ahri", "MIDDLE", win=True),
        make_match("Ahri", "MIDDLE", win=False),
        make_match("Yasuo", "MIDDLE", win=True),
    ]
    client = _mock_client_for_lookup(matches)
    profile = fetch_profile(client, "Test", "EUW", recent_count=4)

    assert profile.top_champions[0]["name"] == "Ahri"
    assert profile.top_champions[0]["games"] == 3
    assert profile.top_champions[0]["wins"] == 2


def test_fetch_profile_not_in_game():
    client = _mock_client_for_lookup([], in_game=None)
    profile = fetch_profile(client, "Test", "EUW")
    assert profile.in_game is False
    assert profile.in_game_info is None


def test_fetch_profile_in_game():
    in_game = {
        "gameMode": "CLASSIC",
        "gameType": "MATCHED",
        "gameLength": 720,
        "participants": [
            {"championId": 103, "summonerName": "Player1", "teamId": 100},
            {"championId": 222, "summonerName": "Player2", "teamId": 200},
        ],
    }
    client = _mock_client_for_lookup([], in_game=in_game)
    profile = fetch_profile(client, "Test", "EUW")

    assert profile.in_game is True
    assert profile.in_game_info["game_mode"] == "CLASSIC"
    assert profile.in_game_info["game_length_seconds"] == 720
    assert len(profile.in_game_info["participants"]) == 2

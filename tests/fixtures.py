"""Synthetic Riot match fixtures for testing.

Mimics the shape of the real /lol/match/v5/matches/{id} response,
but trimmed to just the fields the analyser actually reads.
"""

from __future__ import annotations

from typing import Any

TARGET_PUUID = "test-puuid-001"


def make_match(
    champion: str,
    role: str,
    win: bool,
    kills: int = 5,
    deaths: int = 3,
    assists: int = 7,
    cs: int = 180,
    vision: int = 25,
    duration_seconds: int = 1800,
    start_timestamp_ms: int = 1_700_000_000_000,
    puuid: str = TARGET_PUUID,
) -> dict[str, Any]:
    """Build a minimal match dict matching Riot's match-v5 schema."""
    return {
        "metadata": {"matchId": "EUW1_TEST"},
        "info": {
            "gameDuration": duration_seconds,
            "gameStartTimestamp": start_timestamp_ms,
            "gameCreation": start_timestamp_ms,
            "queueId": 420,
            "participants": [
                {
                    "puuid": f"other-{i}",
                    "championName": "Filler",
                    "teamPosition": "MIDDLE",
                    "win": False, "kills": 0, "deaths": 0, "assists": 0,
                    "totalMinionsKilled": 100, "neutralMinionsKilled": 0,
                    "visionScore": 10,
                }
                for i in range(9)
            ] + [
                {
                    "puuid": puuid,
                    "championName": champion,
                    "teamPosition": role,
                    "win": win,
                    "kills": kills,
                    "deaths": deaths,
                    "assists": assists,
                    "totalMinionsKilled": cs - 20,
                    "neutralMinionsKilled": 20,
                    "visionScore": vision,
                },
            ],
        },
    }

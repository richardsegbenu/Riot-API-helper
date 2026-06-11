"""Compute stats from match data for one summoner.

Takes a list of raw match dicts (as returned by the Riot match-v5
endpoint) plus the target summoner's puuid, and returns aggregated
performance breakdowns:

    * Overall win rate
    * Per-champion win rate (only champs with >= MIN_GAMES)
    * Per-role win rate
    * Per-time-of-day win rate (in 3-hour buckets, UTC)
    * KDA, CS/min, vision score averages

All computations are pure functions of the input data - no API calls
inside this module, no SQLite - which makes them easy to test against
synthetic match fixtures.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MIN_GAMES_PER_CHAMPION = 3
MIN_GAMES_PER_ROLE = 5


@dataclass
class PerformanceRow:
    """Aggregate stats for one slice (a champion, a role, a time bucket...)."""

    label: str
    games: int = 0
    wins: int = 0
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    total_cs: float = 0.0
    total_duration_minutes: float = 0.0
    total_vision_score: float = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0

    @property
    def kda(self) -> float:
        if self.total_deaths == 0:
            return float(self.total_kills + self.total_assists) or 0.0
        return (self.total_kills + self.total_assists) / self.total_deaths

    @property
    def cs_per_minute(self) -> float:
        if not self.total_duration_minutes:
            return 0.0
        return self.total_cs / self.total_duration_minutes

    @property
    def avg_vision_score(self) -> float:
        return self.total_vision_score / self.games if self.games else 0.0


@dataclass
class AnalysisResult:
    """Bundle of breakdowns for a single summoner."""

    summoner_puuid: str
    games_analysed: int
    overall: PerformanceRow
    by_champion: list[PerformanceRow] = field(default_factory=list)
    by_role: list[PerformanceRow] = field(default_factory=list)
    by_time_bucket: list[PerformanceRow] = field(default_factory=list)


def _participant_for_puuid(match: dict, puuid: str) -> dict[str, Any] | None:
    """Return the participant entry for our target puuid, or None if absent."""
    for p in match.get("info", {}).get("participants", []):
        if p.get("puuid") == puuid:
            return p
    return None


def _add_to_row(row: PerformanceRow, p: dict, duration_minutes: float) -> None:
    row.games += 1
    if p.get("win"):
        row.wins += 1
    row.total_kills += p.get("kills", 0)
    row.total_deaths += p.get("deaths", 0)
    row.total_assists += p.get("assists", 0)
    row.total_cs += p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
    row.total_duration_minutes += duration_minutes
    row.total_vision_score += p.get("visionScore", 0)


def _time_bucket(unix_ms: int) -> str:
    """3-hour buckets in UTC."""
    dt = datetime.fromtimestamp(unix_ms / 1000, tz=timezone.utc)
    start = (dt.hour // 3) * 3
    end = start + 3
    return f"{start:02d}:00-{end:02d}:00 UTC"


def analyse_matches(matches: list[dict], puuid: str) -> AnalysisResult:
    """Compute the full breakdown set for a summoner across given matches."""
    overall = PerformanceRow(label="Overall")
    by_champion: dict[str, PerformanceRow] = defaultdict(
        lambda: PerformanceRow(label="")
    )
    by_role: dict[str, PerformanceRow] = defaultdict(lambda: PerformanceRow(label=""))
    by_time: dict[str, PerformanceRow] = defaultdict(lambda: PerformanceRow(label=""))

    games_used = 0
    for match in matches:
        info = match.get("info", {})
        participant = _participant_for_puuid(match, puuid)
        if not participant:
            continue
        duration_minutes = info.get("gameDuration", 0) / 60.0
        # Skip ultra-short remakes (< 5 min) - they pollute the data.
        if duration_minutes < 5:
            continue

        games_used += 1
        _add_to_row(overall, participant, duration_minutes)

        champ = participant.get("championName", "Unknown")
        by_champion[champ].label = champ
        _add_to_row(by_champion[champ], participant, duration_minutes)

        role = participant.get("teamPosition") or participant.get("role") or "UNKNOWN"
        by_role[role].label = role
        _add_to_row(by_role[role], participant, duration_minutes)

        bucket = _time_bucket(info.get("gameStartTimestamp") or info.get("gameCreation", 0))
        by_time[bucket].label = bucket
        _add_to_row(by_time[bucket], participant, duration_minutes)

    return AnalysisResult(
        summoner_puuid=puuid,
        games_analysed=games_used,
        overall=overall,
        by_champion=sorted(
            (r for r in by_champion.values() if r.games >= MIN_GAMES_PER_CHAMPION),
            key=lambda r: (-r.win_rate, -r.games),
        ),
        by_role=sorted(
            (r for r in by_role.values() if r.games >= MIN_GAMES_PER_ROLE),
            key=lambda r: (-r.win_rate, -r.games),
        ),
        by_time_bucket=sorted(
            by_time.values(),
            key=lambda r: r.label,
        ),
    )

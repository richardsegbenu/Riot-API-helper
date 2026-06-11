"""Summoner profile lookup.

Pulls together the data points you'd want before queueing up against
someone or scouting a duo partner:

    * Account level
    * Ranked tier(s) - Solo/Duo and Flex separately
    * Recent form (last N games: W/L streak)
    * Top 3 most-played champions in recent games
    * Whether they're currently in a live game
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from analyser.riot_client import RiotClient
from analyser.stats import _participant_for_puuid


# Queue ID -> human-readable name for ranked queues.
QUEUE_NAMES = {
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "RANKED_FLEX_SR": "Ranked Flex",
    "RANKED_FLEX_TT": "Ranked Flex 3v3",
}


@dataclass
class RankedEntry:
    queue: str
    tier: str
    rank: str
    lp: int
    wins: int
    losses: int

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total else 0.0

    @property
    def display(self) -> str:
        return f"{self.tier} {self.rank} ({self.lp} LP)"


@dataclass
class SummonerProfile:
    riot_id: str
    puuid: str
    summoner_level: int
    profile_icon_id: int
    ranked: list[RankedEntry]
    recent_record: dict
    top_champions: list[dict]
    in_game: bool
    in_game_info: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _compute_streak(recent_results: list[bool]) -> str:
    """recent_results is newest-first. Return e.g. 'W3' or 'L2' or 'mixed'."""
    if not recent_results:
        return "n/a"
    first = recent_results[0]
    streak = 0
    for r in recent_results:
        if r == first:
            streak += 1
        else:
            break
    return f"{'W' if first else 'L'}{streak}"


def fetch_profile(
    client: RiotClient,
    game_name: str,
    tag_line: str,
    recent_count: int = 10,
) -> SummonerProfile:
    """Build a SummonerProfile in one go."""
    account = client.account_by_riot_id(game_name, tag_line)
    puuid = account["puuid"]

    summoner = client.summoner_by_puuid(puuid)
    league_entries = client.league_entries_by_puuid(puuid)

    ranked = [
        RankedEntry(
            queue=QUEUE_NAMES.get(e["queueType"], e["queueType"]),
            tier=e.get("tier", "UNRANKED"),
            rank=e.get("rank", ""),
            lp=e.get("leaguePoints", 0),
            wins=e.get("wins", 0),
            losses=e.get("losses", 0),
        )
        for e in league_entries
    ]

    match_ids = client.match_ids_by_puuid(puuid, count=recent_count)
    matches = [client.match_detail(mid) for mid in match_ids]

    recent_results: list[bool] = []
    champion_counter: Counter = Counter()
    champion_wins: Counter = Counter()

    for match in matches:
        participant = _participant_for_puuid(match, puuid)
        if not participant:
            continue
        if match.get("info", {}).get("gameDuration", 0) < 300:
            continue
        win = bool(participant.get("win"))
        recent_results.append(win)
        champ = participant.get("championName", "Unknown")
        champion_counter[champ] += 1
        if win:
            champion_wins[champ] += 1

    wins = sum(recent_results)
    losses = len(recent_results) - wins

    top_champions = [
        {
            "name": name,
            "games": games,
            "wins": champion_wins[name],
            "win_rate": champion_wins[name] / games if games else 0.0,
        }
        for name, games in champion_counter.most_common(3)
    ]

    live = client.active_game_by_puuid(puuid)
    in_game_info = None
    if live:
        in_game_info = {
            "game_mode": live.get("gameMode"),
            "game_type": live.get("gameType"),
            "game_length_seconds": live.get("gameLength"),
            "participants": [
                {
                    "champion_id": p.get("championId"),
                    "summoner_name": p.get("riotId", p.get("summonerName", "?")),
                    "team_id": p.get("teamId"),
                }
                for p in live.get("participants", [])
            ],
        }

    return SummonerProfile(
        riot_id=f"{game_name}#{tag_line}",
        puuid=puuid,
        summoner_level=summoner.get("summonerLevel", 0),
        profile_icon_id=summoner.get("profileIconId", 0),
        ranked=ranked,
        recent_record={
            "games": len(recent_results),
            "wins": wins,
            "losses": losses,
            "streak": _compute_streak(recent_results),
        },
        top_champions=top_champions,
        in_game=live is not None,
        in_game_info=in_game_info,
    )

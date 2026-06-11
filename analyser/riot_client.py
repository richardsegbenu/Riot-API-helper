"""Thin client for the Riot Games API.

Covers the endpoints needed to analyse a single summoner's recent ranked
games: account lookup by Riot ID, recent match IDs, and per-match
detail / timeline.

API key handling: never hardcoded. Pass via env var RIOT_API_KEY. Riot
development keys expire every 24 hours, which is a known quirk; the
client logs a clear error if the key is missing or rejected.

Region routing: Riot splits its API into "platform" routes (na1, euw1,
kr, ...) for live game state and "regional" routes (americas, europe,
asia, sea) for match/account data. We default to europe + euw1 for
this project. Override via constructor args.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


PLATFORM_TO_REGION = {
    # Americas
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    # Europe
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
    # Asia
    "kr": "asia", "jp1": "asia",
    # SEA
    "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
}


@dataclass
class RiotConfig:
    api_key: str
    platform: str = "euw1"
    region: str = "europe"
    request_timeout: float = 10.0

    @classmethod
    def from_env(cls, platform: str = "euw1") -> "RiotConfig":
        key = os.environ.get("RIOT_API_KEY", "")
        if not key:
            raise RuntimeError(
                "RIOT_API_KEY not set. Get a development key from "
                "https://developer.riotgames.com/ and export it before running."
            )
        region = PLATFORM_TO_REGION.get(platform, "europe")
        return cls(api_key=key, platform=platform, region=region)


class RiotAPIError(Exception):
    """Raised when the Riot API returns a non-200 we can't recover from."""


class RiotClient:
    """Minimal Riot API client with built-in rate-limit handling.

    Riot's development keys are limited to 20 requests / 1s and
    100 requests / 2min. We respect 429 responses with the
    Retry-After header rather than trying to do client-side limiting
    ourselves.
    """

    def __init__(self, config: RiotConfig | None = None) -> None:
        self.config = config or RiotConfig.from_env()
        self._session = requests.Session()
        self._session.headers.update({"X-Riot-Token": self.config.api_key})

    # ---- low-level ----

    def _get(self, url: str, params: dict | None = None):
        for attempt in range(4):
            resp = self._session.get(url, params=params, timeout=self.config.request_timeout)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "1"))
                logger.warning("Rate limited; sleeping %ss", wait)
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                raise RiotAPIError(f"Not found: {url}")
            if resp.status_code in (500, 502, 503, 504):
                wait = 2 ** attempt
                logger.warning("Riot %s; backing off %ss", resp.status_code, wait)
                time.sleep(wait)
                continue
            raise RiotAPIError(f"HTTP {resp.status_code} from Riot: {resp.text[:200]}")
        raise RiotAPIError(f"Gave up after {attempt + 1} retries: {url}")

    # ---- regional endpoints ----

    def account_by_riot_id(self, game_name: str, tag_line: str) -> dict:
        """Riot IDs are 'gameName#tagLine'. Returns puuid, gameName, tagLine."""
        url = (
            f"https://{self.config.region}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        return self._get(url)

    def match_ids_by_puuid(
        self,
        puuid: str,
        count: int = 20,
        queue: int | None = None,
        start: int = 0,
    ) -> list[str]:
        """Recent match IDs for a puuid.

        Queue codes (common ones):
            420 - Ranked Solo/Duo
            440 - Ranked Flex
            400 - Normal Draft
            450 - ARAM
        """
        url = (
            f"https://{self.config.region}.api.riotgames.com"
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        )
        params = {"count": count, "start": start}
        if queue is not None:
            params["queue"] = queue
        return self._get(url, params=params)

    def match_detail(self, match_id: str) -> dict:
        url = (
            f"https://{self.config.region}.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}"
        )
        return self._get(url)

    # ---- platform-routed endpoints (rank, live game, summoner) ----

    def summoner_by_puuid(self, puuid: str) -> dict:
        """Platform-routed: returns summoner-level info including profileIconId, summonerLevel."""
        url = (
            f"https://{self.config.platform}.api.riotgames.com"
            f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        )
        return self._get(url)

    def league_entries_by_puuid(self, puuid: str) -> list[dict]:
        """Ranked entries for a summoner. One entry per queue they're ranked in."""
        url = (
            f"https://{self.config.platform}.api.riotgames.com"
            f"/lol/league/v4/entries/by-puuid/{puuid}"
        )
        return self._get(url)

    def active_game_by_puuid(self, puuid: str) -> dict | None:
        """Current live game for a summoner, or None if they're not in one."""
        url = (
            f"https://{self.config.platform}.api.riotgames.com"
            f"/lol/spectator/v5/active-games/by-summoner/{puuid}"
        )
        try:
            return self._get(url)
        except RiotAPIError as exc:
            if "Not found" in str(exc):
                return None
            raise

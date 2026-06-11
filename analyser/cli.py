"""Personal LoL companion CLI.

Three subcommands covering what I check most often:

    analyse  - pull recent match history and break down by champion,
               role, and time of day. Find your best/worst patches.

    lookup   - fast summoner profile: rank, level, recent form, top
               champions, and whether they're currently in a game.

    draft    - quick counter-pick and synergy suggestions during
               champ select. Curated matchup table, no scraping.

Examples:
    riot analyse "MySummoner#EUW" --count 30 --queue 420
    riot lookup  "Faker#KR1"
    riot draft   --enemy Yasuo --enemy Zed --ally Vayne
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict

from analyser.draft import (
    DraftSuggestion,
    draft_advice,
    suggest_against_enemies,
    suggest_with_allies,
)
from analyser.lookup import fetch_profile
from analyser.report import render_analysis, render_draft_advice, render_lookup
from analyser.riot_client import RiotAPIError, RiotClient, RiotConfig
from analyser.stats import analyse_matches


def _parse_riot_id(value: str) -> tuple[str, str]:
    if "#" not in value:
        raise argparse.ArgumentTypeError(
            f"Riot ID must be 'gameName#tagLine', got {value!r}"
        )
    name, tag = value.rsplit("#", 1)
    return name.strip(), tag.strip()


def _make_client(args) -> RiotClient | None:
    try:
        return RiotClient(RiotConfig.from_env(platform=args.platform))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def _row_to_dict(row) -> dict:
    d = asdict(row)
    d["win_rate"] = row.win_rate
    d["kda"] = row.kda
    d["cs_per_minute"] = row.cs_per_minute
    d["avg_vision_score"] = row.avg_vision_score
    return d


def cmd_analyse(args) -> int:
    client = _make_client(args)
    if client is None:
        return 2

    try:
        game_name, tag_line = args.riot_id
        account = client.account_by_riot_id(game_name, tag_line)
        puuid = account["puuid"]

        print(f"Resolved {game_name}#{tag_line} -> puuid {puuid[:12]}...",
              file=sys.stderr)
        match_ids = client.match_ids_by_puuid(puuid, count=args.count, queue=args.queue)
        print(f"Fetched {len(match_ids)} recent match IDs", file=sys.stderr)

        matches = []
        for i, mid in enumerate(match_ids, 1):
            print(f"  [{i}/{len(match_ids)}] {mid}", file=sys.stderr, end="\r")
            matches.append(client.match_detail(mid))
        print(file=sys.stderr)
    except RiotAPIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = analyse_matches(matches, puuid)

    if args.json:
        payload = {
            "summoner": f"{game_name}#{tag_line}",
            "games_analysed": result.games_analysed,
            "overall": _row_to_dict(result.overall),
            "by_champion": [_row_to_dict(r) for r in result.by_champion],
            "by_role": [_row_to_dict(r) for r in result.by_role],
            "by_time_bucket": [_row_to_dict(r) for r in result.by_time_bucket],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_analysis(result, summoner_label=f"{game_name}#{tag_line}"))

    return 0


def cmd_lookup(args) -> int:
    client = _make_client(args)
    if client is None:
        return 2

    try:
        game_name, tag_line = args.riot_id
        profile = fetch_profile(client, game_name, tag_line, recent_count=args.recent)
    except RiotAPIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(profile.to_dict(), indent=2, default=str))
    else:
        print(render_lookup(profile))

    return 0


def cmd_draft(args) -> int:
    enemies = args.enemy or []
    allies = args.ally or []

    if not enemies and not allies:
        print("error: provide at least one --enemy or --ally champion",
              file=sys.stderr)
        return 2

    counters: list[DraftSuggestion] = suggest_against_enemies(enemies)
    synergies: list[DraftSuggestion] = suggest_with_allies(allies)

    if args.json:
        print(json.dumps(draft_advice(enemies, allies), indent=2))
    else:
        print(render_draft_advice(enemies, allies, counters, synergies))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="riot",
        description="Personal LoL companion CLI: match analysis, summoner lookup, draft helper.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--platform", default="euw1",
                        help="Platform routing (default: euw1; e.g. na1, kr, br1)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_analyse = sub.add_parser("analyse", help="Analyse recent match history")
    p_analyse.add_argument("riot_id", type=_parse_riot_id,
                           help="Riot ID in the form gameName#tagLine")
    p_analyse.add_argument("--count", type=int, default=20,
                           help="How many recent matches to fetch (default: 20, max: 100)")
    p_analyse.add_argument("--queue", type=int, default=None,
                           help="Queue filter (e.g. 420 for ranked solo)")
    p_analyse.add_argument("--json", action="store_true")
    p_analyse.set_defaults(func=cmd_analyse)

    p_lookup = sub.add_parser("lookup", help="Look up a summoner's profile, rank, and form")
    p_lookup.add_argument("riot_id", type=_parse_riot_id,
                          help="Riot ID in the form gameName#tagLine")
    p_lookup.add_argument("--recent", type=int, default=10,
                          help="How many recent games to use for form analysis (default: 10)")
    p_lookup.add_argument("--json", action="store_true")
    p_lookup.set_defaults(func=cmd_lookup)

    p_draft = sub.add_parser("draft", help="Suggest counter-picks and synergies in champ select")
    p_draft.add_argument("--enemy", action="append",
                         help="Enemy champion already locked (repeatable)")
    p_draft.add_argument("--ally", action="append",
                         help="Ally champion already locked (repeatable)")
    p_draft.add_argument("--json", action="store_true")
    p_draft.set_defaults(func=cmd_draft)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

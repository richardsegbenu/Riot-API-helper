# riot-companion

A personal League of Legends companion CLI: match history analysis, fast summoner lookups, and a draft helper for champ select. Built because the three things I check most often before/during/after games shouldn't take five browser tabs.

[![CI](https://github.com/YOUR_USERNAME/riot-companion/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/riot-companion/actions)

## Why

I play LoL. Before queue I scout the lobby, in champ select I want quick counter-pick options, and after a session I want to see whether my form is real or whether I'm just on tilt. There are great web tools for each of these (op.gg, u.gg, mobalytics) but I wanted something that lived in my terminal, ran with one command, and let me slice the data my own way.

Equally important: the Riot API is a fun thing to build against. Two-tier regional routing, dev keys that expire every 24 hours, aggressive rate limits - handling all that cleanly is most of the engineering work.

## Three things it does

### `analyse` - match history breakdown

```bash
riot analyse "MySummoner#EUW" --count 30 --queue 420
```

Pulls your recent ranked games and breaks them down by champion, role, and time of day.

### `lookup` - summoner profile

```bash
riot lookup "Faker#KR1"
```

Quick scouting card: rank in solo/duo and flex, recent W/L streak, top 3 champions played recently, and whether they're currently in a live game.

### `draft` - counter and synergy suggestions

```bash
riot draft --enemy Yasuo --enemy Zed --ally Vayne
```

The matchup table is hand-curated - only well-known, durable matchups that hold across patches.

## Getting started

1. Get a development API key from https://developer.riotgames.com/
2. Export it: `export RIOT_API_KEY=RGAPI-...`
3. Install: `pip install -r requirements.txt`
4. Pick a subcommand: `python -m analyser.cli lookup "YourName#TAG"`

Useful queue codes for `analyse --queue`:

| Code | Mode |
|---|---|
| 420 | Ranked Solo/Duo |
| 440 | Ranked Flex |
| 400 | Normal Draft |
| 450 | ARAM |

## Notable design choices

- **Stats computation is pure.** `analyse_matches(matches, puuid)` is a pure function of input. No API calls, no IO. The full test suite runs against synthetic fixtures, offline.
- **Rate limiting is reactive.** Respect `Retry-After` on 429s with exponential backoff for 5xx. No client-side token bucket.
- **Region routing handled centrally.** A `PLATFORM_TO_REGION` lookup means callers think in terms of "euw1" or "kr".
- **Short games filtered.** Anything under 5 minutes is treated as a remake and excluded.
- **Counter table is curated, not scraped.** Honest framing: matchups that hold across patches, not patch-specific stats.

## Architecture

```
analyser/
├── riot_client.py    Auth, retries, regional + platform routing
├── stats.py          Pure aggregation: by champion / role / time
├── lookup.py         Composes the client into a summoner profile
├── draft.py          Curated matchup table + suggestion ranking
├── report.py         Terminal rendering (plain text, JSON via --json)
└── cli.py            argparse wiring for the three subcommands
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests cover the Riot client (mocked HTTP), the stats logic (synthetic fixtures), the lookup composition, and the draft helper.

## Licence

MIT. The Riot API and the data it returns belong to Riot Games and are subject to their API terms. This project is not affiliated with or endorsed by Riot.

"""Render reports to the terminal.

Plain stdlib only - no `rich`, no `tabulate`. The output is intentionally
greppable: columns are space-padded, no fancy box-drawing.
"""

from __future__ import annotations

from analyser.draft import DraftSuggestion
from analyser.lookup import SummonerProfile
from analyser.stats import AnalysisResult, PerformanceRow


def _pct(n: float) -> str:
    return f"{n * 100:5.1f}%"


# ---- match history report ----

def _row_line(row: PerformanceRow, label_width: int = 14) -> str:
    return (
        f"{row.label:<{label_width}} "
        f"{row.games:>4}  "
        f"{_pct(row.win_rate)}  "
        f"KDA {row.kda:>4.1f}  "
        f"CS/m {row.cs_per_minute:>4.1f}  "
        f"VS {row.avg_vision_score:>5.1f}"
    )


def render_analysis(result: AnalysisResult, summoner_label: str | None = None) -> str:
    title = summoner_label or result.summoner_puuid[:12]
    lines = []
    lines.append(f"Match Analysis - {title}")
    lines.append("=" * 60)
    lines.append(f"Games analysed: {result.games_analysed}")
    lines.append("")

    lines.append("OVERALL")
    lines.append("-" * 60)
    lines.append(_row_line(result.overall, label_width=14))
    lines.append("")

    if result.by_champion:
        lines.append(f"BY CHAMPION  (min {result.by_champion[0].games}+ games)")
        lines.append("-" * 60)
        for row in result.by_champion[:15]:
            lines.append(_row_line(row))
        lines.append("")

    if result.by_role:
        lines.append("BY ROLE")
        lines.append("-" * 60)
        for row in result.by_role:
            lines.append(_row_line(row))
        lines.append("")

    if result.by_time_bucket:
        lines.append("BY TIME OF DAY (UTC)")
        lines.append("-" * 60)
        for row in result.by_time_bucket:
            lines.append(_row_line(row))
        lines.append("")

    return "\n".join(lines)


# ---- summoner lookup report ----

def render_lookup(profile: SummonerProfile) -> str:
    lines = []
    lines.append(f"Summoner: {profile.riot_id}")
    lines.append("=" * 60)
    lines.append(f"Level: {profile.summoner_level}")
    lines.append("")

    if profile.ranked:
        lines.append("RANKED")
        lines.append("-" * 60)
        for entry in profile.ranked:
            lines.append(
                f"  {entry.queue:<20} {entry.display:<25} "
                f"{entry.wins}W / {entry.losses}L  "
                f"({_pct(entry.win_rate)})"
            )
    else:
        lines.append("RANKED:  Unranked")
    lines.append("")

    r = profile.recent_record
    lines.append(f"RECENT FORM  (last {r['games']} games)")
    lines.append("-" * 60)
    lines.append(f"  {r['wins']}W / {r['losses']}L   Streak: {r['streak']}")
    lines.append("")

    if profile.top_champions:
        lines.append("TOP CHAMPIONS  (in recent games)")
        lines.append("-" * 60)
        for c in profile.top_champions:
            lines.append(
                f"  {c['name']:<14} {c['games']} games  "
                f"({c['wins']}W, {_pct(c['win_rate'])})"
            )
        lines.append("")

    if profile.in_game:
        info = profile.in_game_info or {}
        mins = (info.get("game_length_seconds") or 0) // 60
        lines.append(f"LIVE GAME - in {info.get('game_mode', '?')} for {mins} min")
        lines.append("-" * 60)
        team_a = [p for p in info.get("participants", []) if p["team_id"] == 100]
        team_b = [p for p in info.get("participants", []) if p["team_id"] == 200]
        for i in range(max(len(team_a), len(team_b))):
            left = team_a[i]["summoner_name"] if i < len(team_a) else ""
            right = team_b[i]["summoner_name"] if i < len(team_b) else ""
            lines.append(f"  {left:<25} vs  {right}")
    else:
        lines.append("LIVE GAME: not currently in a game")

    return "\n".join(lines)


# ---- draft helper report ----

def render_draft_advice(
    enemy_picks: list[str],
    ally_picks: list[str],
    counters: list[DraftSuggestion],
    synergies: list[DraftSuggestion],
) -> str:
    lines = []
    lines.append("Draft Helper")
    lines.append("=" * 60)
    if enemy_picks:
        lines.append(f"Enemy picks:  {', '.join(enemy_picks)}")
    if ally_picks:
        lines.append(f"Ally picks:   {', '.join(ally_picks)}")
    lines.append("")

    if counters:
        lines.append("COUNTER-PICKS  (against enemy team)")
        lines.append("-" * 60)
        for s in counters:
            lines.append(f"  {s.suggested:<14}  {s.reason}")
        lines.append("")
    elif enemy_picks:
        lines.append("No counter suggestions in the database for those enemy picks.")
        lines.append("")

    if synergies:
        lines.append("SYNERGY PICKS  (with your team)")
        lines.append("-" * 60)
        for s in synergies:
            lines.append(f"  {s.suggested:<14}  {s.reason}")
        lines.append("")
    elif ally_picks:
        lines.append("No synergy suggestions in the database for those ally picks.")
        lines.append("")

    if not counters and not synergies:
        lines.append("Nothing to suggest. Add enemy picks with --enemy or ally picks")
        lines.append("with --ally to get recommendations.")

    return "\n".join(lines)


# Backwards-compat alias.
render_report = render_analysis

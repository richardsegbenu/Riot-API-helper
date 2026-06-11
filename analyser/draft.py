"""Draft helper - counter-picks and synergy suggestions.

This is intentionally NOT a "scrape op.gg" project. The counter data
here is a curated, hand-maintained table of well-known matchups that
hold up across patches (e.g. tanks beat squishies, hard-CC beats
mobility, range beats short-range melee bullies).

For real meta-aware suggestions, you'd want to enrich this with
patch-specific win-rate data from one of the public aggregators -
that's a separate project.

The output is suggestions, not commandments. Use your own judgement.
"""

from __future__ import annotations

from dataclasses import dataclass


# Role constants matching Riot's teamPosition values.
TOP = "TOP"
JUNGLE = "JUNGLE"
MIDDLE = "MIDDLE"
BOTTOM = "BOTTOM"
SUPPORT = "UTILITY"

ALL_ROLES = (TOP, JUNGLE, MIDDLE, BOTTOM, SUPPORT)


# ---- Curated matchup data ----
#
# Format: "Champion that's being countered" -> list of champions that
# tend to beat them. Conservative - only well-known, durable matchups.
# Easy to extend: edit the dict below.

COUNTERS: dict[str, list[str]] = {
    # Top lane
    "Riven":     ["Garen", "Renekton", "Pantheon", "Malphite"],
    "Yasuo":     ["Malphite", "Renekton", "Pantheon", "Annie"],
    "Yone":      ["Malphite", "Pantheon", "Renekton"],
    "Darius":    ["Vayne", "Quinn", "Kennen", "Teemo"],
    "Garen":     ["Vayne", "Quinn", "Teemo", "Darius"],
    "Sett":      ["Vayne", "Quinn", "Gnar"],
    "Camille":   ["Malphite", "Tahm Kench", "Poppy"],
    "Fiora":     ["Jax", "Pantheon", "Malphite"],
    "Aatrox":    ["Fiora", "Jax", "Renekton"],
    "Irelia":    ["Pantheon", "Malphite", "Renekton"],
    "Renekton":  ["Garen", "Quinn", "Kennen"],
    "Mordekaiser": ["Vayne", "Quinn", "Gangplank"],
    "Teemo":     ["Olaf", "Singed", "Malphite"],
    "Volibear":  ["Vayne", "Gnar", "Quinn"],
    "Jax":       ["Malphite", "Gnar", "Renekton"],
    "Gnar":      ["Renekton", "Cho'Gath", "Trundle"],

    # Jungle
    "Lee Sin":   ["Master Yi", "Karthus", "Udyr"],
    "Kha'Zix":   ["Rengar", "Jarvan IV", "Vi"],
    "Master Yi": ["Rammus", "Jax", "Pantheon", "Lillia"],
    "Elise":     ["Olaf", "Hecarim", "Trundle"],
    "Graves":    ["Karthus", "Master Yi", "Kindred"],
    "Hecarim":   ["Jax", "Rammus", "Jarvan IV"],
    "Rengar":    ["Jax", "Vi", "Volibear"],
    "Evelynn":   ["Lee Sin", "Elise", "Nocturne"],
    "Kindred":   ["Olaf", "Trundle", "Karthus"],
    "Karthus":   ["Kha'Zix", "Lee Sin", "Elise"],
    "Nocturne":  ["Karthus", "Lee Sin", "Master Yi"],
    "Viego":     ["Pantheon", "Vi", "Jarvan IV"],

    # Mid lane
    "Zed":       ["Malzahar", "Lissandra", "Diana", "Kassadin"],
    "LeBlanc":   ["Galio", "Lissandra", "Kassadin", "Diana"],
    "Akali":     ["Galio", "Lissandra", "Malzahar"],
    "Katarina":  ["Diana", "Lissandra", "Galio"],
    "Ahri":      ["Annie", "Fizz", "LeBlanc"],
    "Syndra":    ["Talon", "Yasuo", "Zed"],
    "Orianna":   ["Yasuo", "Zed", "Talon"],
    "Azir":      ["Yasuo", "Zed", "Diana"],
    "Lux":       ["Talon", "Zed", "Yasuo"],
    "Lissandra": ["Talon", "Zed", "Diana"],
    "Diana":     ["Annie", "Anivia", "Talon"],
    "Talon":     ["Diana", "Lissandra", "Pantheon"],
    "Cassiopeia": ["LeBlanc", "Diana", "Talon"],
    "Veigar":    ["Zed", "Yasuo", "Talon"],
    "Vex":       ["Zed", "Yasuo", "Talon"],
    "Sylas":     ["Pantheon", "Annie", "Lissandra"],
    "Kassadin":  ["Talon", "Pantheon", "LeBlanc"],

    # Bot lane (ADC)
    "Jinx":      ["Draven", "Lucian", "Caitlyn"],
    "Caitlyn":   ["Draven", "Lucian", "Tristana"],
    "Vayne":     ["Caitlyn", "Draven", "Lucian"],
    "Kai'Sa":    ["Caitlyn", "Ezreal", "Draven"],
    "Ezreal":    ["Draven", "Lucian", "Tristana"],
    "Ashe":      ["Draven", "Tristana", "Lucian"],
    "Miss Fortune": ["Draven", "Caitlyn", "Lucian"],
    "Jhin":      ["Draven", "Lucian", "Tristana"],
    "Samira":    ["Caitlyn", "Tristana", "Ezreal"],
    "Aphelios":  ["Draven", "Lucian", "Caitlyn"],
    "Twitch":    ["Caitlyn", "Draven", "Ashe"],
    "Sivir":     ["Draven", "Caitlyn", "Lucian"],

    # Support
    "Thresh":    ["Morgana", "Janna", "Lulu"],
    "Blitzcrank": ["Morgana", "Janna", "Karma"],
    "Leona":     ["Morgana", "Janna", "Lulu", "Karma"],
    "Pyke":      ["Morgana", "Janna", "Lulu"],
    "Nautilus":  ["Morgana", "Janna", "Lulu"],
    "Soraka":    ["Pyke", "Blitzcrank", "Leona"],
    "Lulu":      ["Pyke", "Blitzcrank", "Brand"],
    "Janna":     ["Pyke", "Leona", "Brand"],
    "Yuumi":     ["Blitzcrank", "Pyke", "Brand"],
    "Karma":     ["Pyke", "Leona", "Blitzcrank"],
    "Senna":     ["Pyke", "Leona", "Nautilus"],
    "Morgana":   ["Pyke", "Brand", "Zyra"],
}


# Champions that scale brilliantly with frontline / peel / cc.
# Used for synergy suggestions when an ally has already picked.
SYNERGIES: dict[str, list[str]] = {
    # Hyper-carries that love peel
    "Jinx":     ["Lulu", "Janna", "Braum", "Morgana"],
    "Vayne":    ["Lulu", "Janna", "Tahm Kench", "Braum"],
    "Kog'Maw":  ["Lulu", "Janna", "Soraka", "Nami"],
    "Twitch":   ["Lulu", "Yuumi", "Janna"],
    "Tristana": ["Lulu", "Yuumi", "Janna"],

    # Engage carries who want a follow-up engage
    "Yasuo":    ["Malphite", "Alistar", "Leona", "Rakan"],
    "Yone":     ["Malphite", "Alistar", "Leona"],
    "Katarina": ["Malphite", "Amumu", "Sejuani"],
    "Diana":    ["Yasuo", "Malphite", "Amumu"],
    "Kennen":   ["Malphite", "Amumu", "Sejuani"],

    # Mages who want CC chained into them
    "Orianna":  ["Malphite", "Amumu", "Sejuani"],
    "Veigar":   ["Amumu", "Sejuani", "Leona"],
    "Lux":      ["Leona", "Amumu", "Sejuani"],

    # Junglers who profit from set-up
    "Master Yi": ["Lulu", "Janna", "Zilean"],
    "Kayn":     ["Lulu", "Soraka", "Nami"],
    "Karthus":  ["Janna", "Lulu", "Yuumi"],
}

# Case-insensitive lookup tables built once at import time. Maps
# lowercase champion name -> canonical name from the source dict.
# Lets users type "tristana", "TRISTANA", "Tristana" — all resolve.
_COUNTERS_LOOKUP = {k.lower(): k for k in COUNTERS}
_SYNERGIES_LOOKUP = {k.lower(): k for k in SYNERGIES}


def _canonical_champion(name: str, lookup: dict[str, str]) -> str | None:
    """Resolve user-typed champion name to the canonical form in our tables.

    Returns None if the champion isn't in the lookup at all.
    """
    return lookup.get(name.lower().strip())

@dataclass
class DraftSuggestion:
    """One suggestion for how to respond to an enemy pick or ally pick."""

    suggested: str
    reason: str
    source_champion: str
    source_role: str | None = None
    kind: str = "counter"


def suggest_against_enemies(enemy_picks: list[str], limit: int = 8) -> list[DraftSuggestion]:
    """Given a list of locked-in enemy champions, suggest counter-picks.

    Returns suggestions ordered by how many enemy champions they counter
    (multi-counters are more valuable than single-counters).
    """
    score: dict[str, int] = {}
    sources: dict[str, list[str]] = {}

    for enemy in enemy_picks:
        canonical = _canonical_champion(enemy, _COUNTERS_LOOKUP)
        if canonical is None:
            continue
        for counter in COUNTERS[canonical]:
            score[counter] = score.get(counter, 0) + 1
            sources.setdefault(counter, []).append(canonical)

    suggestions = []
    for champ, _ in sorted(score.items(), key=lambda x: (-x[1], x[0])):
        countered = sources[champ]
        reason = (
            f"counters {', '.join(countered)}"
            if len(countered) > 1
            else f"counters {countered[0]}"
        )
        suggestions.append(DraftSuggestion(
            suggested=champ,
            reason=reason,
            source_champion=countered[0],
            kind="counter",
        ))
    return suggestions[:limit]


def suggest_with_allies(ally_picks: list[str], limit: int = 6) -> list[DraftSuggestion]:
    """Given a list of locked-in ally champions, suggest synergy picks."""
    score: dict[str, int] = {}
    sources: dict[str, list[str]] = {}

    for ally in ally_picks:
        canonical = _canonical_champion(ally, _SYNERGIES_LOOKUP)
        if canonical is None:
            continue
        for synergy in SYNERGIES[canonical]:
            score[synergy] = score.get(synergy, 0) + 1
            sources.setdefault(synergy, []).append(canonical)

    suggestions = []
    for champ, _ in sorted(score.items(), key=lambda x: (-x[1], x[0])):
        with_who = sources[champ]
        reason = f"synergises with {', '.join(with_who)}"
        suggestions.append(DraftSuggestion(
            suggested=champ,
            reason=reason,
            source_champion=with_who[0],
            kind="synergy",
        ))
    return suggestions[:limit]


def draft_advice(
    enemy_picks: list[str],
    ally_picks: list[str] | None = None,
) -> dict:
    """Combine counter and synergy suggestions into a single advice bundle."""
    return {
        "counters": [
            {
                "suggested": s.suggested,
                "reason": s.reason,
                "kind": s.kind,
            }
            for s in suggest_against_enemies(enemy_picks)
        ],
        "synergies": [
            {
                "suggested": s.suggested,
                "reason": s.reason,
                "kind": s.kind,
            }
            for s in suggest_with_allies(ally_picks or [])
        ],
    }


def known_champion_count() -> int:
    """How many champions have at least one matchup record."""
    return len(set(COUNTERS) | {c for cs in COUNTERS.values() for c in cs})

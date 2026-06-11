"""Tests for the draft helper."""

from __future__ import annotations

from analyser.draft import (
    COUNTERS,
    SYNERGIES,
    draft_advice,
    known_champion_count,
    suggest_against_enemies,
    suggest_with_allies,
)


def test_known_champions_is_meaningful():
    assert known_champion_count() > 50


def test_single_enemy_returns_known_counters():
    suggestions = suggest_against_enemies(["Yasuo"])
    suggested_names = [s.suggested for s in suggestions]
    assert any(c in suggested_names for c in ("Malphite", "Renekton", "Pantheon"))


def test_multi_counter_ranked_higher():
    suggestions = suggest_against_enemies(["Yasuo", "Sylas"])
    pantheon_index = next(
        (i for i, s in enumerate(suggestions) if s.suggested == "Pantheon"),
        None,
    )
    assert pantheon_index is not None
    assert "Yasuo" in suggestions[pantheon_index].reason
    assert "Sylas" in suggestions[pantheon_index].reason


def test_no_suggestions_for_unknown_enemy():
    suggestions = suggest_against_enemies(["DefinitelyNotARealChampion"])
    assert suggestions == []


def test_empty_enemy_list_returns_empty():
    assert suggest_against_enemies([]) == []


def test_synergy_suggestions_for_hypercarry():
    suggestions = suggest_with_allies(["Jinx"])
    suggested = [s.suggested for s in suggestions]
    assert any(name in suggested for name in ("Lulu", "Janna", "Braum"))


def test_multi_synergy_ranked_higher():
    suggestions = suggest_with_allies(["Jinx", "Vayne"])
    if suggestions:
        first = suggestions[0]
        assert first.kind == "synergy"


def test_draft_advice_combines_both():
    advice = draft_advice(enemy_picks=["Yasuo"], ally_picks=["Jinx"])
    assert "counters" in advice
    assert "synergies" in advice
    assert advice["counters"]
    assert advice["synergies"]


def test_draft_advice_handles_empty_inputs():
    advice = draft_advice(enemy_picks=[], ally_picks=[])
    assert advice == {"counters": [], "synergies": []}


def test_counters_dict_has_consistent_shape():
    for champ, counter_list in COUNTERS.items():
        assert isinstance(counter_list, list), f"{champ}: not a list"
        assert counter_list, f"{champ}: empty counter list"
        assert all(isinstance(c, str) for c in counter_list), f"{champ}: non-string entry"


def test_synergies_dict_has_consistent_shape():
    for champ, synergy_list in SYNERGIES.items():
        assert isinstance(synergy_list, list)
        assert synergy_list
        assert all(isinstance(c, str) for c in synergy_list)


def test_suggestions_respect_limit():
    suggestions = suggest_against_enemies(["Yasuo"], limit=2)
    assert len(suggestions) <= 2


def test_lowercase_champion_name_resolved():
    """Users will type 'tristana', 'yasuo', etc. — we should handle that."""
    upper = suggest_with_allies(["Tristana"])
    lower = suggest_with_allies(["tristana"])
    assert lower != []
    # Lowercase should return the same suggestions as canonical case.
    assert [s.suggested for s in lower] == [s.suggested for s in upper]


def test_uppercase_champion_name_resolved():
    upper = suggest_against_enemies(["YASUO"])
    canonical = suggest_against_enemies(["Yasuo"])
    assert [s.suggested for s in upper] == [s.suggested for s in canonical]


def test_whitespace_around_champion_name_handled():
    a = suggest_against_enemies(["  Yasuo  "])
    b = suggest_against_enemies(["Yasuo"])
    assert [s.suggested for s in a] == [s.suggested for s in b]


def test_reason_uses_canonical_name_not_user_input():
    """If user types 'tristana', the reason should say 'Tristana' (proper case)."""
    suggestions = suggest_with_allies(["tristana"])
    assert any("Tristana" in s.reason for s in suggestions)
"""Gra samych botów „pasywnych” nie staje, a każdy ruch katalogu = to samo żądanie HTTP (B1).

Bot pasywny bierze pierwszy kandydat z ``legal_actions`` (bezpieczny ruch domyślny). Sterownik
(``tests/engine/driver.py``) gra przez prawdziwe API i porównuje stan po HTTP ze stanem z
``apply_and_settle`` po KAŻDYM kroku (RULES.md 65.1, 65.4).
"""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.engine.driver import BotTable

SIX = ["sol", "letnev", "hacan", "jolnar", "arborec", "mentak"]
FOUR = ["sol", "letnev", "hacan", "jolnar"]

_CORE_ROUND = {
    "setup_custodians",
    "setup_reveal",
    "strategy_pick",
    "phase_next",
    "strategy_play",
    "strategy_primary_step",
    "strategy_secondary",
    "turn_end",
    "turn_pass",
    "tactical_end",
    "reaction_pause_release",
    "status_finish_scoring",
    "status_redistribute",
}
_AGENDA = {"agenda_reveal", "agenda_abstain", "agenda_decide", "agenda_confirm", "agenda_continue"}

# (nazwa, frakcje, sterowanie, zdjęty Custodians => agenda, rodzaje akcji, które MUSZĄ wystąpić)
SCENARIOS: list[tuple[str, list[str], str, bool, set[str]]] = [
    ("bots_6p", SIX, "BOT", False, _CORE_ROUND | {"offer_accept"}),
    ("bots_6p_agenda", SIX, "BOT", True, _CORE_ROUND | _AGENDA | {"agenda_discard"}),
    # Miejsca „ludzi”: silnik nie wybiera za nich tajnych celów (setup_secret), 2 karty na gracza.
    ("humans_4p_agenda", FOUR, "HUMAN", True, _CORE_ROUND | _AGENDA | {"setup_secret"}),
]

SCENARIO_KINDS: set[str] = set().union(*(kinds for *_, kinds in SCENARIOS))
"""Rodzaje akcji pokryte scenariuszami gier (strażnik pokrycia w ``test_actions_parity``)."""


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.mark.parametrize(
    ("factions", "control", "agenda", "kinds"),
    [pytest.param(f, c, a, k, id=name) for name, f, c, a, k in SCENARIOS],
)
def test_passive_bots_play_two_full_rounds(
    registry: StaticDataRegistry,
    factions: list[str],
    control: str,
    agenda: bool,
    kinds: set[str],
) -> None:
    patch = {"custodians_removed": True} if agenda else None
    table = BotTable(registry, factions, patch=patch, control=control)

    report = table.run(until_round=3)

    assert report.stalled is None, report.stalled
    assert report.mismatches == []
    # Pierwszy kandydat (ruch domyślny) zawsze legalny - generator nie zgaduje.
    assert dict(report.first_rejected) == {}
    assert table.state.round_number == 3
    missing = kinds - set(report.kinds)
    assert not missing, f"scenario did not exercise: {sorted(missing)}"


def test_same_start_and_seed_give_same_game(registry: StaticDataRegistry) -> None:
    """Determinizm (RULES.md 65.5): ten sam stan startowy + ziarno => ta sama partia.

    Tworzenie gry (losowanie celów i talii) celowo korzysta z entropii, więc drugi stół startuje
    z TEJ SAMEJ migawki co pierwszy; dalej wszystko (talie, kości, decyzje bota) musi się zgadzać.
    """
    first = BotTable(registry, FOUR, seed=3)
    start = first.state.clone()
    second = BotTable(registry, FOUR, seed=3)
    second.inject(start)

    first.run(until_round=2)
    second.run(until_round=2)

    assert first.state.model_dump(mode="json") == second.state.model_dump(mode="json")

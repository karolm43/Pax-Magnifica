"""Eliminacja gracza (R_elimination, RULES.md 66) - wykrycie i skutki.

Gracz odpada, gdy spełnia JEDNOCZEŚNIE trzy warunki: brak sił naziemnych na planszy, brak
jednostki ze zdolnością PRODUCTION (flagowiec Arboreców produkuje, ale nie ma PRODUCTION) i brak
kontrolowanych planet. Skutki (``eliminate``):

- jednostki i żetony dowodzenia gracza schodzą z planszy (do pudełka),
- notki innych graczy, które trzymał (ręka i strefa gry), wracają do właścicieli; jego notki
  u innych graczy wracają do pudełka,
- karty akcji na stos odrzuconych, posiadane agendy (prawa „elect player” z nim) na odrzucone,
- karty strategii wracają do wspólnej puli (gracz znika z ``players``),
- tajne cele (zdobyte i niezdobyte) wracają do talii, talia jest tasowana,
- fragmenty reliktów na stosy odrzuconych swoich talii eksploracji, relikty purge (Notes),
- mówca przechodzi na gracza po lewej.

Gracz znika z ``players`` i ``seating_order`` (zostaje ślad ``EliminatedPlayer``), więc
kolejki tur, okien i faz same go pomijają. Liczba kart strategii liczy graczy ze startu gry
(``strategy_phase.pick_count``: 5+ graczy -> dalej po jednej karcie).

Moment sprawdzenia: koniec każdej tury fazy akcji (``turn_flow.end_turn``) - wszystkie drogi do
eliminacji (walka, inwazja, efekty kart) dzieją się w czyjejś turze. ⚠ ZAŁOŻENIE: eliminacja
w fazie agendy/statusu (efekt agendy) nie jest sprawdzana do końca następnej tury.
Niezrobione elementy frakcyjne (Mahact, Naalu „0”, jeńcy) - ``tests/rulings_status.json``.

Funkcje MUTUJĄ przekazany stan (klon wołającego).
"""

from __future__ import annotations

from src.core import (
    card_draw,
    command_tokens,
    exploration,
    promissory_notes,
    relic_fragments,
    relics,
    rules_hooks,
    secret_objectives,
    strategy_phase,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.game_state import EliminatedPlayer, GameState
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.objective_events import note_owner
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause

_GROUND_FORCES = ("infantry", "mech")


def _unit_types_on_board(state: GameState, player_id: str) -> set[str]:
    found: set[str] = set()
    for system in state.systems.values():
        found |= {bt for bt, n in system.space_units.get(player_id, {}).items() if n > 0}
        for planet_units in system.planet_units.values():
            found |= {bt for bt, n in planet_units.get(player_id, {}).items() if n > 0}
    return found


def _has_production_unit(
    registry: StaticDataRegistry, state: GameState, player_id: str, types: set[str]
) -> bool:
    player = state.players[player_id]
    for base_type in types:
        unit = resolve_unit_variant(registry, player.faction, player.technologies, base_type)
        if unit is not None and unit.production_value is not None:
            return True
    return False


def meets_conditions(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Czy gracz spełnia wszystkie trzy warunki eliminacji (R_elimination 1.1-1.3)."""
    if player_id == NEUTRAL_PLAYER_ID or player_id not in state.players:
        return False
    # Strażnik silnika: eliminowany może być tylko gracz rozstawiony na planszy (system domowy
    # leży na mapie). W prawdziwej grze dotyczy to każdego gracza; stan bez systemu domowego to
    # niepełny scenariusz (God-Mode, testy), w którym brak jednostek nie oznacza przegranej.
    home = state.players[player_id].home_position
    if home is None or home not in state.systems:
        return False
    owners = (owner for s in state.systems.values() for owner in s.planet_owners.values())
    if player_id in owners:
        return False
    if state.players[player_id].controlled_planets:
        return False
    types = _unit_types_on_board(state, player_id)
    if any(bt in _GROUND_FORCES for bt in types):
        return False
    # PRODUCTION spoza jednostek (Magmus Reactor Ω: supernowa z jednostką gracza - F_muaat).
    if rules_hooks.permits(rules_hooks.POINT_ELIMINATION_HAS_PRODUCTION, state, player_id):
        return False
    return not _has_production_unit(registry, state, player_id, types)


def _clear_board(state: GameState, player_id: str) -> None:
    """Jednostki i żetony dowodzenia gracza schodzą z planszy (do pudełka)."""
    for system in state.systems.values():
        for base_type, count in list(system.space_units.get(player_id, {}).items()):
            if count > 0:
                unit_ops.remove_units(state, system, "space", player_id, base_type, count)
        for planet in list(system.planet_units):
            units = system.planet_units[planet].get(player_id, {})
            for base_type, count in list(units.items()):
                if count > 0:
                    unit_ops.remove_units(
                        state, system, planet, player_id, base_type, count, UnitCause.REMOVED
                    )
        while player_id in system.command_tokens:
            command_tokens.remove_from_board(state, system, player_id)


def _settle_notes(state: GameState, registry: StaticDataRegistry, player_id: str) -> None:
    """R_elimination 4 / 4.1: cudze notki wracają do właścicieli, notki gracza do pudełka."""
    me = state.players[player_id]
    for note in list(me.private.promissory_notes):
        owner = note_owner(state, registry, note)
        if owner is not None and owner != player_id:
            promissory_notes.return_from_hand(state, player_id, owner, note)
        else:
            promissory_notes.discard_from_hand(state, player_id, note)
    for note in list(me.promissory_notes_in_play):
        owner = note_owner(state, registry, note)
        if owner is not None and owner != player_id:
            promissory_notes.return_from_play(state, player_id, owner, note)
        else:
            promissory_notes.remove_from_play(state, player_id, note)
    for other_id, other in state.players.items():
        if other_id == player_id:
            continue
        for note in list(other.private.promissory_notes):
            if note_owner(state, registry, note) == player_id:
                promissory_notes.discard_from_hand(state, other_id, note)
        for note in list(other.promissory_notes_in_play):
            if note_owner(state, registry, note) == player_id:
                promissory_notes.remove_from_play(state, other_id, note)


def _discard_agendas(state: GameState, player_id: str) -> list[str]:
    """R_elimination 3: agendy, które gracz posiada (prawa „elect player” z nim), odrzucone."""
    owned = [agenda for agenda, result in state.decks.agenda_laws.items() if result == player_id]
    for agenda in owned:
        del state.decks.agenda_laws[agenda]
        card_draw.discard_agenda(state, agenda)
    return owned


def _fragment_decks(registry: StaticDataRegistry, card_ids: list[str]) -> dict[str, str]:
    decks: dict[str, str] = {}
    for card_id in card_ids:
        try:
            card = exploration.card_def(registry, card_id)
        except ValueError:
            continue
        if card.type:
            decks[card_id] = card.type.lower()
    return decks


def _next_seat(state: GameState, player_id: str) -> str | None:
    seats = [pid for pid in state.seating_order if pid in state.players]
    if player_id not in seats or len(seats) < 2:
        return None
    return seats[(seats.index(player_id) + 1) % len(seats)]


def eliminate(state: GameState, registry: StaticDataRegistry, player_id: str) -> None:
    """Eliminuje gracza: wszystkie skutki R_elimination i usunięcie z gry (mutuje)."""
    player = state.players[player_id]
    _clear_board(state, player_id)
    _settle_notes(state, registry, player_id)
    _discard_agendas(state, player_id)
    card_draw.discard_chosen_action_cards(state, player_id, list(player.private.action_cards))
    secrets = [
        *player.private.secret_objectives, *player.scored_secrets,
        *player.private.secret_candidates,
    ]
    for objective_id in secrets:
        secret_objectives.return_to_deck(state, objective_id)
    relic_fragments.discard_all(
        state, player_id, _fragment_decks(registry, list(player.relic_fragments))
    )
    for relic_id in list(player.relics):
        relics.purge_relic(state, player_id, relic_id)
    if state.speaker_id == player_id:
        strategy_phase.set_speaker(state, _next_seat(state, player_id))
    triggers.drop_player_offers(state, player_id)
    state.eliminated_players = [
        *state.eliminated_players,
        EliminatedPlayer(
            player_id=player_id, faction=player.faction, color=player.color,
            display_name=player.display_name, home_position=player.home_position,
            round_number=state.round_number,
        ),
    ]
    del state.players[player_id]
    state.seating_order = [pid for pid in state.seating_order if pid != player_id]
    for other in state.players.values():
        other.transacted_with = [pid for pid in other.transacted_with if pid != player_id]


def check_all(state: GameState, registry: StaticDataRegistry | None) -> list[str]:
    """Eliminuje każdego gracza spełniającego warunki; zwraca wyeliminowanych (mutuje).

    Nigdy nie eliminuje ostatniego gracza w grze.
    """
    if registry is None:
        return []
    out: list[str] = []
    for player_id in sorted(state.players):
        if len(state.players) <= 1:
            break
        if meets_conditions(state, registry, player_id):
            eliminate(state, registry, player_id)
            out.append(player_id)
    return out

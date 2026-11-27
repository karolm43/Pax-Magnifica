"""Serializacja stanu gry do formatu ``web-data`` frontendu (ti4_web).

Frontend ``ti4_web`` renderuje planszę z JEDNEGO dokumentu HTTP
(``GET /api/public/game/{gameId}/web-data``) o kształcie ``PlayerDataResponse``.
Ten moduł buduje ten dokument z naszego ``GameState`` + ``HexGrid`` + rejestru,
emitując wyłącznie STAN (pozycje, jednostki, gracze) — statyczne katalogi
(definicje jednostek/planet/systemów) frontend ma wbudowane i rozwiązuje po ID.

Reguły mapowania (zweryfikowane w kodzie frontendu, nie z pamięci):

- Pozycje: ``tilePositions`` to lista napisów ``"<pozycja>:<systemId>"``. Frontend
  liczy piksele sam z ``tileCoordinates`` po kluczu pozycji AsyncTI4 — nasze pozycje
  używają tych samych identyfikatorów (``000``, ``101``…), więc nie wysyłamy ``(q,r,s)``.
- Jednostki: w ``tileUnitData`` jednostki są kluczowane przez ``entityId = asyncId``
  (``ff``, ``gf``, ``mf``, ``sd``, ``ca``…), zgrupowane per frakcja. Kod rozmieszczania
  frontendu rozpoznaje ``gf``/``mf``/``ff``/``sd`` po ``asyncId`` — nie po ID rejestru.
- Planety: ``tileUnitData[pos].planets`` kluczowane nazwą/ID planety zgodną ze
  statycznymi danymi systemu frontendu (to te same ID AsyncTI4 co w naszym rejestrze).
- Frakcja jednostek w ``space``/``planets`` to identyfikator frakcji gracza; gdy gracz
  nie ma przypisanej frakcji, używamy jego ``player_id`` jako klucza zastępczego.

Frontend oczekuje wielu pól opcjonalnych (cele, prawa, karty strategii, pula kart);
emitujemy je puste/domyślne, by viewer działał bez pełnej logiki rundy.
"""

from __future__ import annotations

import functools
import time
from typing import Any

from src.api import web_agenda, web_objectives, web_points, web_setup
from src.api.web_game import _build_game_state, _entity_key_map
from src.api.web_players import _build_player_data, _build_stat_tile_positions
from src.api.web_tiles import _build_tile_unit_data, _ring_count
from src.core import actor as actor_rules
from src.core import (
    faction_tokens,
    game_clock,
    initiative_zero,
    peek,
    positions,
    strategy_phase,
)
from src.core.expedition_state import EXPEDITION_SLICES
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import (
    is_space_unit,
)
from src.core.visibility import project_all_redacted, project_for_viewer, project_strict

# Wersja schematu dokumentu web-data wymagana przez frontend ti4_web
# (``REQUIRED_VERSION_SCHEMA`` w ``GameMapPage.tsx``). Dokument ze starszą/brakującą
# wersją powoduje ekran "Update Needed" zamiast renderu planszy.
WEB_DATA_SCHEMA_VERSION = 5

def _build_strategy_cards(
    state: GameState, registry: StaticDataRegistry, entity_keys: dict[str, str]
) -> list[dict[str, Any]]:
    """Buduje ``strategyCards`` dla web-data z aktywnego zestawu + stanu gry.

    Pola zgodne z typem frontendu (``StrategyCard``): ``initiative``, ``name``, ``id``,
    ``picked``, ``played``, ``exhausted``, ``tradeGoods``, ``pickedByFaction``.
    ``pickedByFaction`` używa klucza tożsamości (spójnie z ``playerData[].faction``).
    """
    owner_by_init: dict[int, str] = {}
    exhausted_by_init: dict[int, bool] = {}
    for player_id, player in state.players.items():
        for init in player.strategy_cards:
            owner_by_init[init] = player_id
            exhausted_by_init[init] = init in player.exhausted_strategy_cards
    cards: list[dict[str, Any]] = []
    for card in registry.strategy_card_set():
        owner_id = owner_by_init.get(card.initiative)
        exhausted = exhausted_by_init.get(card.initiative, False)
        cards.append(
            {
                "initiative": card.initiative,
                "name": card.name,
                "id": card.id,
                "picked": owner_id is not None,
                "played": exhausted,
                "exhausted": exhausted,
                "tradeGoods": state.strategy_card_tg.get(card.initiative, 0),
                "pickedByFaction": (
                    entity_keys.get(owner_id, owner_id) if owner_id else None
                ),
            }
        )
    return cards


def _empty_card_pool() -> dict[str, Any]:
    """Pusta struktura ``CardPoolData`` (viewer wymaga obecności pól)."""
    return {
        "secretObjectiveDeckSize": 0,
        "secretObjectiveFullDeckSize": 0,
        "secretObjectiveDeck": [],
        "secretObjectiveDiscard": [],
        "actionCardDeckSize": 0,
        "actionCardFullDeckSize": 0,
        "actionCardDiscardSize": 0,
        "actionCardPurgedSize": 0,
        "culturalExploreDeck": [],
        "culturalExploreDiscard": [],
        "industrialExploreDeck": [],
        "industrialExploreDiscard": [],
        "hazardousExploreDeck": [],
        "hazardousExploreDiscard": [],
        "frontierExploreDeck": [],
        "frontierExploreDiscard": [],
        "relicDeckSize": 0,
        "relicFullDeckSize": 0,
        "relicDeck": [],
        "relicDiscard": [],
        "agendaDeckSize": 0,
        "agendaFullDeckSize": 0,
        "agendaDiscardSize": 0,
        "agendaVariant": "standard",
        "technologyDeck": [],
    }


def _build_expeditions(
    state: GameState, entity_keys: dict[str, str]
) -> dict[str, Any]:
    """Struktura ``Expeditions`` frontendu: plaster -> ``completedBy`` (klucz tożsamości gracza).

    Plaster wolny = ``None``. Frontend rysuje żeton ekspedycji, dopóki któryś plaster jest wolny
    (``ExpeditionLayer``), a kontrolki zajętych plastrów w odpowiednich miejscach tarczy.
    """
    claims = state.expeditions.claims
    return {
        slice_id: {
            "completedBy": (
                entity_keys.get(claims[slice_id], claims[slice_id])
                if slice_id in claims
                else None
            )
        }
        for slice_id in EXPEDITION_SLICES
    }


def _build_chess_clock(
    state: GameState, entity_keys: dict[str, str], now: float
) -> dict[str, Any] | None:
    """Zegar szachowy (RULES.md 58) na chwilę budowy dokumentu — None, gdy wyłączony.

    Wartości są aktualne na ``now``; UI dolicza upływ od chwili ODBIORU dokumentu tylko
    holderowi z ``running=True`` (bez porównywania zegarów serwera i przeglądarki).
    """
    clock = state.clock
    if not clock.enabled:
        return None
    players = []
    for entry in game_clock.snapshot(state, now):
        player = state.players[entry.player_id]
        players.append(
            {
                "playerId": entry.player_id,
                "faction": entity_keys.get(entry.player_id, entry.player_id),
                "color": player.color,
                "name": player.display_name or player.faction or entry.player_id,
                "remainingMs": entry.remaining_ms,
                "turnMs": entry.turn_ms,
                "running": entry.running,
            }
        )
    return {
        "paused": clock.paused,
        "holderId": clock.holder_id,
        "initialMs": clock.initial_ms,
        "incrementMs": clock.increment_ms,
        "players": players,
    }


def _zero_token_key(state: GameState, entity_keys: dict[str, str]) -> str | None:
    """Klucz gracza z żetonem „0” Naalu (``None`` = nikt) - RULES.md 62.16."""
    holder = initiative_zero.holder(state)
    return entity_keys.get(holder, holder) if holder is not None else None


def _peek_payload(
    state: GameState, grid: HexGrid, viewer: str | None, entity_keys: dict[str, str]
) -> dict[str, Any] | None:
    """Podgląd M'aban viewera (``core/peek``) z kluczami graczy jak w ``playerData``."""
    found = peek.view(state, grid, viewer)
    if found is None:
        return None
    found["neighbors"] = {entity_keys.get(p, p): notes for p, notes in found["neighbors"].items()}
    return found


def _build_wait_reasons(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """``waitReasons`` (RULES.md 44.5): public, the same for every viewer."""
    return [
        {
            "playerId": r.player_id,
            "reasonCode": r.reason_code,
            "summary": r.summary,
            "blocking": r.blocking,
        }
        for r in actor_rules.describe_wait_reasons(state, registry)
    ]


def build_web_data(
    grid: HexGrid,
    registry: StaticDataRegistry,
    state: GameState,
    *,
    game_name: str,
    vps_to_win: int | None = None,
    viewing_player: str | None = None,
    now: float | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Serializuje stan gry do dokumentu ``PlayerDataResponse`` dla frontendu ti4_web.

    Dokument budowany jest z PROJEKCJI stanu do perspektywy jednego „gracza
    patrzącego" (``project_for_viewer``): ręce viewera są pełne, a prywatne ręce
    pozostałych graczy zredagowane do samych liczebności (R6.1, R6.5).

    Args:
        grid: Bieżąca mapa (źródło pozycji, systemów, anomalii).
        registry: Statyczne dane (planety — zasoby/wpływy).
        state: Bieżący stan gry (gracze, jednostki).
        game_name: Identyfikator gry wyświetlany/używany przez frontend.
        vps_to_win: Próg punktów zwycięstwa.
        viewing_player: Gracz, z którego perspektywy rzutujemy dokument (R6.6).
            ``None`` → używamy aktywnego gracza (``state.active_player_id``).
        now: Chwila (s UNIX) odczytu zegara szachowego; ``None`` → czas systemowy.
        strict: Gra sieciowa (RULES.md 44.3): ``project_strict`` z perspektywy ``viewing_player``
            (bez domyślnego „aktywnego gracza"; ``None`` = obserwator), ukryte talie i RNG.

    Returns:
        Słownik gotowy do serializacji JSON zgodny z ``PlayerDataResponse``.

    Perspektywa dokumentu (R6.6/R6.7):

    * jawny ``viewing_player`` → projekcja z jego perspektywy (pełna ręka viewera,
      reszta zredagowana);
    * brak ``viewing_player``, ale jest aktywny gracz → perspektywa aktywnego;
    * brak OBU (``active_player_id is None`` — normalny stan: między turami, po
      komplecie wyboru kart strategii, fazy bez aktywnego gracza) → dokument z
      rękami WSZYSTKICH graczy zredagowanymi (``project_all_redacted``). To NIE
      jest błąd — po prostu nikt nie ma w tym momencie wglądu w pełną rękę, więc
      pokazujemy same liczniki. Dokument buduje się normalnie.
    """
    # R6.6: brak jawnego viewera → aktywny gracz jako perspektywa domyślna.
    viewer = viewing_player or state.active_player_id
    if strict:
        projected = project_strict(state, viewing_player)
    # RULES.md 44.3: w sieci tylko projekcja ścisła (powyżej); poniżej tryb lokalny.
    # R6.1: projekcja PRZED serializacją. Gdy znamy viewera → jego perspektywa.
    # Gdy viewera brak (jawnego i aktywnego), a stan niepusty → redagujemy ręce
    # wszystkich (perspektywa „nikt nie patrzy"), zamiast rzucać — ``None`` to
    # poprawny stan gry. Pusty stan serializujemy wprost (brak rąk do redakcji).
    elif viewer is not None:
        projected = project_for_viewer(state, viewer)
    elif state.players:
        projected = project_all_redacted(state)
    else:
        projected = state

    # Jedna mapa klucz-tożsamości dla CAŁEGO dokumentu (jednostki, planety, heksy,
    # playerData). Spójny klucz eliminuje desync panel↔mapa (Bug 1/2).
    entity_keys = _entity_key_map(projected)
    tile_unit_data, tile_positions = _build_tile_unit_data(
        grid, registry, projected, entity_keys
    )
    return {
        "gameName": game_name,
        "gameRound": projected.round_number,
        "ringCount": _ring_count(grid),
        "vpsToWin": vps_to_win if vps_to_win is not None else projected.vps_to_win,
        # Wersja schematu danych oczekiwana przez frontend (ti4_web). Poniżej tej
        # wartości frontend blokuje render ekranem "Update Needed". Trzymamy stałą
        # zgodną z REQUIRED_VERSION_SCHEMA w GameMapPage.tsx.
        "versionSchema": WEB_DATA_SCHEMA_VERSION,
        "tilePositions": tile_positions,
        "tileUnitData": tile_unit_data,
        "playerData": web_agenda.with_revealed_secrets(
            _build_player_data(projected, registry, grid, entity_keys), state
        ),
        "statTilePositions": _build_stat_tile_positions(projected, grid, entity_keys),
        "gameState": {
            **_build_game_state(projected, registry, grid),
            # Covert Legislation: ukryta agenda tylko dla mówcy; Search Warrant: jawne tajne cele
            # właściciela; Checks and Balances: wybrana karta strategii idzie do innego gracza.
            "agendaCovertCard": web_agenda.covert_for_viewer(state, registry, viewer),
            "revealedSecrets": web_agenda.revealed_secrets(state),
            "strategyGivesCards": strategy_phase.gives_chosen_cards(state),
            # Stały podgląd ukrytych kart (M'aban Naalu - RULES.md 62.16): tylko dla viewera.
            "peek": _peek_payload(state, grid, viewing_player if strict else viewer, entity_keys),
            # Gracz z żetonem „0” Naalu (inicjatywa 0) - znacznik na karcie strategii.
            "initiativeZero": _zero_token_key(state, entity_keys),
            # Setup startowy — None po zakończeniu; kandydaci tylko dla jednego gracza.
            "setup": web_setup.build_setup_payload(state, viewing_player, own_only=strict)
            if strict
            else web_setup.build_setup_payload(state),
        },
        "lawsInPlay": web_agenda.build_laws_in_play(projected, registry, entity_keys),
        "strategyCards": _build_strategy_cards(projected, registry, entity_keys),
        "objectives": web_objectives.build_objectives(
            projected, registry, grid, entity_keys
        ),
        "scoreBreakdowns": web_points.build_score_breakdowns(
            projected, registry, grid, entity_keys
        ),
        # Tokens on system borders (Empyrean Void Tether, RULES.md 62.20) - ``BorderAnomalyLayer``.
        "borderAnomalies": build_border_anomalies(projected, grid),
        "cardPool": {
            **_empty_card_pool(),
            **web_objectives.card_pool_counts(projected, registry),
        },
        "expeditions": _build_expeditions(projected, entity_keys),
        # Computed from the FULL state (hand sizes, pending setup choosers); the function reads
        # public facts only - ``tests/test_wait_reasons.py`` guards that.
        "waitReasons": _build_wait_reasons(state, registry),
        # Zegar szachowy graczy (RULES.md 58) — None, gdy gra jest bez zegara.
        "chessClock": _build_chess_clock(
            projected, entity_keys, time.time() if now is None else now
        ),
    }


def entity_key_map(state: GameState) -> dict[str, str]:
    """Publiczny alias ``_entity_key_map`` — mapa ``player_id -> klucz tożsamości``.

    Używany poza modułem (np. router walki), by klucze stron walki były spójne z
    grupowaniem jednostek i ``playerData[].faction`` w web-data.
    """
    return _entity_key_map(state)


# Pomocniczo wyeksportowane dla testów/diagnostyki.
__all__ = ["build_web_data", "entity_key_map", "is_space_unit"]


@functools.lru_cache(maxsize=1)
def _border_directions() -> dict[tuple[int, int, int], int]:
    """Cube delta between two edge neighbours -> border direction of the first one, clockwise from
    north (0 = N ... 5 = NW - ``frontend/.../BorderAnomalyLayer``). Read from the AsyncTI4 position
    table (``core.positions``, the map's orientation): 101 is north of 000, the ring runs
    clockwise, so ``10<k>`` - ``000`` is direction ``k - 1``."""
    table = positions.load_positions()
    centre = table["000"]
    return {
        (h.q - centre.q, h.r - centre.r, h.s - centre.s): k - 1
        for k in range(1, 7)
        if (h := table.get(f"10{k}")) is not None
    }


def border_direction(grid: HexGrid, a: str, b: str) -> int | None:
    """Edge of ``a``'s hex that it shares with ``b`` (``None`` = not edge neighbours)."""
    if a not in grid.positions or b not in grid.positions:
        return None
    qa, ra, sa = grid.coordinates(a)
    qb, rb, sb = grid.coordinates(b)
    return _border_directions().get((qb - qa, rb - ra, sb - sa))


def build_border_anomalies(state: GameState, grid: HexGrid) -> list[dict[str, Any]]:
    """``[{tile, direction, type}]`` of every border token (Void Tether: ``void_tether``)."""
    found: list[dict[str, Any]] = []
    for a, b, _owner in faction_tokens.borders(state, faction_tokens.VOID_TETHER):
        direction = border_direction(grid, a, b)
        if direction is not None:
            found.append({"tile": a, "direction": direction, "type": "void_tether"})
    return found

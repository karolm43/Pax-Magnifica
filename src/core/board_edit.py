"""Edycja planszy God-Mode — czyste funkcje nad ``GameState`` (bez HTTP).

Operator (człowiek) ustawia stan fizycznej planszy bez sprawdzania zasad TI4:
jednostki w przestrzeni i na planetach, kontrola planet, pola gracza. To warstwa
``core`` (patrz docs/ARCHITEKTURA_KODU.md): funkcje przyjmują ``state`` (+ ``grid``/
``registry`` gdy potrzeba), zwracają NOWY ``GameState`` (przez ``clone``) albo rzucają
``ValueError`` (błąd domenowy, mapowany na HTTP w warstwie ``api``). Zero importów
FastAPI — dzięki temu te same funkcje wywoła i endpoint, i (w przyszłości) bot AI.

Reguły tożsamości/kontroli planet (opcja A, jedno źródło prawdy) opisano w RULES.md 11/12.
"""

from __future__ import annotations

from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import (
    ASYNC_ID_BY_BASE_TYPE,
    BASE_TYPE_BY_ASYNC_ID,
    is_space_unit,
    placement_allows_zone,
    zone_is_space,
)


def validate_base_type(base_type: str) -> None:
    """Sprawdza, że ``baseType`` jest w katalogu (inaczej cicho ginie w web-data).

    Raises:
        ValueError: Gdy typ spoza ``ASYNC_ID_BY_BASE_TYPE`` (Bug 5).
    """
    if base_type not in ASYNC_ID_BY_BASE_TYPE:
        raise ValueError(f"Unknown baseType: {base_type}")


def base_type_for_async(async_id: str) -> str:
    """Zwraca ``baseType`` dla ``asyncId`` z edytora.

    Raises:
        ValueError: Gdy ``asyncId`` nieznany.
    """
    base_type = BASE_TYPE_BY_ASYNC_ID.get(async_id)
    if base_type is None:
        raise ValueError(f"Unknown asyncId: {async_id}")
    return base_type


def system_id_for(position: str, grid: HexGrid) -> str:
    """System ID z grida dla pozycji (lub pusty, gdy brak systemu na pozycji)."""
    if position in grid.positions:
        return str(grid.system_id_at(position))
    return ""


def resolve_player_id(faction_key: str, state: GameState) -> str:
    """Mapuje klucz z ``tileUnitData`` na ``player_id`` (RULES.md 11).

    Priorytet: 1) dokładne ``player_id``; 2) frakcja, ale TYLKO gdy jednoznaczna.
    Przy kolizji frakcji nie zgadujemy — zwracamy klucz bez zmian.
    """
    if faction_key in state.players:
        return faction_key
    matches = [
        pid for pid, player in state.players.items() if player.faction == faction_key
    ]
    if len(matches) == 1:
        return matches[0]
    return faction_key


def _zone_bucket(system: SystemState, zone: str, player_id: str) -> dict[str, int]:
    """Modyfikowalny słownik jednostek gracza w strefie (``"space"`` / id planety)."""
    if zone == "space":
        return system.space_units.setdefault(player_id, {})
    by_player = system.planet_units.setdefault(zone, {})
    return by_player.setdefault(player_id, {})


def _prune_zone(system: SystemState, zone: str, player_id: str) -> None:
    """Usuwa puste słowniki jednostek po edycji (porządek)."""
    if zone == "space":
        if not system.space_units.get(player_id):
            system.space_units.pop(player_id, None)
        return
    by_player = system.planet_units.get(zone)
    if by_player is not None:
        if not by_player.get(player_id):
            by_player.pop(player_id, None)
        if not by_player:
            system.planet_units.pop(zone, None)


def _get_or_make_system(
    state: GameState, position: str, grid: HexGrid
) -> SystemState:
    """Zwraca system ze stanu lub tworzy nowy (z system_id z grida)."""
    return state.systems.get(position) or SystemState(
        position=position, system_id=system_id_for(position, grid)
    )


def planet_position(
    planet_id: str, state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> str | None:
    """Pozycja ``RPP`` systemu zawierającego daną planetę (grid+rejestr, potem stan)."""
    for position in grid.positions:
        system = registry.systems.get(system_id_for(position, grid))
        if system is not None and planet_id in system.planets:
            return str(position)
    for position, sys_state in state.systems.items():
        if planet_id in sys_state.added_planets:  # np. Thunder's Edge dołożony do systemu
            return str(position)
        system = registry.systems.get(sys_state.system_id)
        if system is not None and planet_id in system.planets:
            return str(position)
    return None


def recompute_planet_control(system: SystemState, planet: str) -> None:
    """Przelicza kontrolę planety po zmianie jednostek (reguła AsyncTI4, RULES.md 23).

    MUTUJE przekazany ``system`` (zakłada się, że to część klonu stanu). Odwzorowuje
    ``AddPlanetToPlayAreaService.addPlanetToPlayArea``:
    - zbiera graczy mających na planecie jednostki NAZIEMNE/struktury (myśliwce i inne
      jednostki kosmiczne są pomijane — filtr ``is_space_unit``);
    - jeśli DOKŁADNIE JEDEN gracz → nadaje mu kontrolę (``planet_owners[planet]``),
      nadpisując poprzedniego właściciela;
    - jeśli 0 graczy (planeta pusta) lub ≥2 (koegzystencja) → NIE zmienia właściciela.
      Kontrola jest „lepka": zostaje nawet bez jednostek, dopóki ktoś inny jej nie
      przejmie (to wierne odwzorowanie reguły TI4 — usunięcie ostatniej piechoty nie
      odbiera planety; utrata tylko przez przejęcie przez innego gracza).
    """
    by_player = system.planet_units.get(planet, {})
    owners_present: set[str] = set()
    for player_id, by_type in by_player.items():
        # Jednostka nadająca kontrolę = naziemna/struktura (nie kosmiczna).
        if any(count > 0 and not is_space_unit(bt) for bt, count in by_type.items()):
            owners_present.add(player_id)
    if len(owners_present) == 1:
        system.planet_owners[planet] = next(iter(owners_present))


# --- Operacje wysokiego poziomu (zwracają nowy stan) ---------------------------


def set_space_units(
    state: GameState,
    grid: HexGrid,
    position: str,
    changes: list[tuple[str, str, int]],
) -> GameState:
    """Ustawia liczbę jednostek w przestrzeni systemu (``changes`` = [(player, base, count)]).

    ``count <= 0`` usuwa dany typ. Waliduje ``baseType``.

    Raises:
        ValueError: Gdy któryś ``baseType`` spoza katalogu.
    """
    for _player, base_type, _count in changes:
        validate_base_type(base_type)
    new_state = state.clone()
    system = _get_or_make_system(new_state, position, grid)
    for player_id, base_type, count in changes:
        bucket = system.space_units.setdefault(player_id, {})
        if count <= 0:
            bucket.pop(base_type, None)
        else:
            bucket[base_type] = count
        if not bucket:
            system.space_units.pop(player_id, None)
    new_state.systems[position] = system
    return new_state


def set_planet_units(
    state: GameState,
    grid: HexGrid,
    position: str,
    planet: str,
    changes: list[tuple[str, str, int]],
    owner_id: str | None = None,
) -> GameState:
    """Ustawia jednostki naziemne na planecie (+ opcjonalnie właściciela).

    Raises:
        ValueError: Gdy któryś ``baseType`` spoza katalogu.
    """
    for _player, base_type, _count in changes:
        validate_base_type(base_type)
    new_state = state.clone()
    system = _get_or_make_system(new_state, position, grid)
    by_player = system.planet_units.setdefault(planet, {})
    for player_id, base_type, count in changes:
        bucket = by_player.setdefault(player_id, {})
        if count <= 0:
            bucket.pop(base_type, None)
        else:
            bucket[base_type] = count
        if not bucket:
            by_player.pop(player_id, None)
    if owner_id is not None:
        # Jawny właściciel od operatora ma priorytet (celowe ustawienie).
        system.planet_owners[planet] = owner_id
    else:
        # Brak jawnego właściciela → wyznacz kontrolę z jednostek (reguła AsyncTI4).
        recompute_planet_control(system, planet)
    new_state.systems[position] = system
    return new_state


def edit_units(
    state: GameState,
    grid: HexGrid,
    position: str,
    zone: str,
    faction_key: str,
    async_id: str,
    delta: int,
) -> GameState:
    """Dodaje/odejmuje jednostki w strefie systemu (delta, w terminach asyncId).

    Raises:
        ValueError: Gdy ``asyncId`` nieznany.
    """
    base_type = base_type_for_async(async_id)
    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)
    system = _get_or_make_system(new_state, position, grid)
    bucket = _zone_bucket(system, zone, player_id)
    new_count = max(0, bucket.get(base_type, 0) + delta)
    if new_count == 0:
        bucket.pop(base_type, None)
    else:
        bucket[base_type] = new_count
    _prune_zone(system, zone, player_id)
    # Zmiana jednostek na planecie może nadać kontrolę (zone != "space").
    if zone != "space":
        recompute_planet_control(system, zone)
    new_state.systems[position] = system
    return new_state


def move_units(
    state: GameState,
    grid: HexGrid,
    *,
    from_position: str,
    from_zone: str,
    to_position: str,
    to_zone: str,
    faction_key: str,
    async_id: str,
    count: int,
) -> GameState:
    """Przenosi jednostki między strefami/systemami (bez reguł RUCHU, z regułą UMIEJSCOWIENIA).

    Wspólny punkt wejścia przenoszenia dla UI (drag-and-drop) i przyszłego BOTA —
    czysta funkcja ``state -> state`` bez HTTP. NIE waliduje reguł ruchu TI4 (zasięg,
    fleet supply, blokady — to asystent, nie sędzia), ALE egzekwuje regułę UMIEJSCOWIENIA
    (RULES.md 26): statek tylko w przestrzeni, siła naziemna/struktura tylko na planecie.
    Dzięki temu ani gracz, ani bot nie postawią statku na planecie.

    Raises:
        ValueError: Gdy ``asyncId`` nieznany, ``count <= 0``, brak jednostek, lub gdy
            strefa docelowa łamie regułę umiejscowienia (statek na planetę / naziemne
            do przestrzeni).
    """
    base_type = base_type_for_async(async_id)
    if count <= 0:
        raise ValueError("count must be > 0")
    # Reguła umiejscowienia (RULES.md 26): statek nigdy na planetę; jednostka
    # naziemna/struktura nigdy do przestrzeni. Egzekwowane w core — chroni UI i bota.
    if not placement_allows_zone(base_type, to_zone):
        where = "space" if zone_is_space(to_zone) else f"planet {to_zone!r}"
        raise ValueError(
            f"Unit {async_id!r} ({base_type}) cannot be placed in {where} "
            f"- ships only in space, ground forces/structures only on a planet."
        )
    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)

    src = _get_or_make_system(new_state, from_position, grid)
    src_bucket = _zone_bucket(src, from_zone, player_id)
    available = src_bucket.get(base_type, 0)
    moved = min(available, count)
    if moved <= 0:
        raise ValueError("No units to move.")
    remaining = available - moved
    if remaining == 0:
        src_bucket.pop(base_type, None)
    else:
        src_bucket[base_type] = remaining
    _prune_zone(src, from_zone, player_id)
    # Usunięcie z planety źródłowej NIE odbiera kontroli (lepkość) — przeliczamy
    # i tak, by obsłużyć przejęcie, gdy została inna jednostka pojedynczego koloru.
    if from_zone != "space":
        recompute_planet_control(src, from_zone)
    new_state.systems[from_position] = src

    dst = _get_or_make_system(new_state, to_position, grid)
    dst_bucket = _zone_bucket(dst, to_zone, player_id)
    dst_bucket[base_type] = dst_bucket.get(base_type, 0) + moved
    # Dodanie jednostki naziemnej na planecie docelowej może nadać kontrolę.
    if to_zone != "space":
        recompute_planet_control(dst, to_zone)
    new_state.systems[to_position] = dst
    return new_state


def sync_controlled_planets(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    target: list[str],
) -> None:
    """Synchronizuje kontrolę planet gracza do ``planet_owners`` (opcja A, Bug 3).

    MUTUJE przekazany ``state`` (zakłada się, że to już klon). Odbiera własność planet
    spoza listy docelowej, nadaje własność planet z listy w ich systemach.
    """
    target_set = set(target)
    for sys_state in state.systems.values():
        for planet_id, owner in list(sys_state.planet_owners.items()):
            if owner == player_id and planet_id not in target_set:
                del sys_state.planet_owners[planet_id]
    for planet_id in target_set:
        position = planet_position(planet_id, state, grid, registry)
        if position is None:
            continue  # planeta spoza mapy — nie da się umiejscowić
        system = _get_or_make_system(state, position, grid)
        system.planet_owners[planet_id] = player_id
        state.systems[position] = system


def edit_player(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    updates: dict[str, object],
) -> GameState:
    """Edytuje pola gracza (tworzy, gdy nie istnieje). ``updates`` = pola do nadpisania.

    ``leader_states`` jest SCALANE z istniejącym (edycja jednego lidera nie kasuje
    pozostałych). ``controlled_planets`` jest synchronizowane do ``planet_owners``
    systemów (opcja A — jedno źródło prawdy).
    """
    new_state = state.clone()
    player = new_state.players.get(player_id) or PlayerState(player_id=player_id)
    for field, value in updates.items():
        if field == "leader_states" and isinstance(value, dict):
            merged = dict(player.leader_states)
            merged.update(value)
            player.leader_states = merged
        elif field == "relics" and isinstance(value, list):
            new_state.players[player_id] = player
            _set_player_relics(new_state, player_id, [str(r) for r in value])
        else:
            setattr(player, field, value)
    new_state.players[player_id] = player
    controlled = updates.get("controlled_planets")
    if controlled is not None and isinstance(controlled, list):
        sync_controlled_planets(new_state, grid, registry, player_id, controlled)
    return new_state


def _set_player_relics(state: GameState, player_id: str, relics: list[str]) -> None:
    """God-Mode: ustawia relikty przed graczem (bez reguł i bez hooków „when you gain/lose").

    Dodany relikt znika z talii/stosu odrzuconych i od innych graczy (karta jest unikalna).
    Zdjęty relikt wraca na spód talii (o ile jest już zasiana), żeby dało się go znów dobrać.
    Stan wyczerpania zostaje tylko dla reliktów, które gracz nadal ma.
    """
    player = state.players[player_id]
    wanted = list(dict.fromkeys(relics))  # bez duplikatów, kolejność zachowana
    decks = state.decks
    for relic in player.relics:
        if relic not in wanted and decks.relic_deck_seeded:
            if relic not in decks.relic_deck and relic not in decks.relic_discard:
                decks.relic_deck = [*decks.relic_deck, relic]
    for relic in wanted:
        decks.relic_deck = [r for r in decks.relic_deck if r != relic]
        decks.relic_discard = [r for r in decks.relic_discard if r != relic]
        for other_id, other in state.players.items():
            if other_id != player_id and relic in other.relics:
                other.relics = [r for r in other.relics if r != relic]
                other.exhausted_relics = [r for r in other.exhausted_relics if r != relic]
    player.relics = wanted
    player.exhausted_relics = [r for r in player.exhausted_relics if r in wanted]


def _toggle_in_list(items: list[str], value: str) -> list[str]:
    """Zwraca NOWĄ listę z przełączoną obecnością ``value`` (dodaj/usuń)."""
    if value in items:
        return [x for x in items if x != value]
    return [*items, value]


def toggle_planet_exhaust(
    state: GameState, player_id: str, planet_id: str
) -> GameState:
    """Przełącza stan wyczerpania planety gracza (exhausted ↔ ready).

    Operator/asystent: planeta wyczerpana po wydaniu jej zasobów/wpływów; „ready"
    po odświeżeniu (faza statusu). Nie waliduje, czy gracz kontroluje planetę —
    to narzędzie stołu (God-Mode). Reguła stanu: RULES.md — Status Phase.
    """
    new_state = state.clone()
    player = new_state.players.get(player_id) or PlayerState(player_id=player_id)
    player.exhausted_planets = _toggle_in_list(player.exhausted_planets, planet_id)
    new_state.players[player_id] = player
    return new_state


def toggle_tech_exhaust(state: GameState, player_id: str, tech_id: str) -> GameState:
    """Przełącza stan wyczerpania technologii gracza (exhausted ↔ ready)."""
    new_state = state.clone()
    player = new_state.players.get(player_id) or PlayerState(player_id=player_id)
    player.exhausted_technologies = _toggle_in_list(
        player.exhausted_technologies, tech_id
    )
    new_state.players[player_id] = player
    return new_state


# Dozwolone stany lidera (RULES.md — Leaders): zablokowany / gotowy / wyczerpany.
_LEADER_STATES: set[str] = {"locked", "unlocked", "exhausted"}


def set_leader_state(
    state: GameState, player_id: str, leader_id: str, leader_state: str
) -> GameState:
    """Ustawia stan jednego lidera (``locked``/``unlocked``/``exhausted``).

    Scala z istniejącym ``leader_states`` (nie kasuje pozostałych liderów).

    Raises:
        ValueError: Gdy ``leader_state`` spoza dozwolonych.
    """
    if leader_state not in _LEADER_STATES:
        raise ValueError(f"Unknown leader state: {leader_state}")
    new_state = state.clone()
    player = new_state.players.get(player_id) or PlayerState(player_id=player_id)
    merged = dict(player.leader_states)
    merged[leader_id] = leader_state
    player.leader_states = merged
    new_state.players[player_id] = player
    return new_state


def set_player_hand(
    state: GameState,
    player_id: str,
    *,
    action_cards: list[str] | None = None,
    secret_objectives: list[str] | None = None,
    promissory_notes: list[str] | None = None,
) -> GameState:
    """God-Mode: ustawia prywatną rękę gracza (karty akcji / sekrety / weksle).

    Ręka (``PlayerState.private``) jest TAJNA i nie da się jej edytować przez
    ``edit_player`` — to osobny kanał operatora, przydatny do testów UI „paska
    ręki". Podane listy NADPISUJĄ odpowiednie ręce; pominięte (``None``) zostają
    bez zmian. Zero walidacji istnienia kart (operator wie, co kładzie) — spójne z
    resztą God-Mode. Zwraca NOWY ``GameState`` (clone), więc edycja jest w historii
    (Undo cofa wgranie ręki).
    """
    new_state = state.clone()
    player = new_state.players.get(player_id) or PlayerState(player_id=player_id)
    if action_cards is not None:
        player.private.action_cards = list(action_cards)
    if secret_objectives is not None:
        player.private.secret_objectives = list(secret_objectives)
    if promissory_notes is not None:
        player.private.promissory_notes = list(promissory_notes)
    new_state.players[player_id] = player
    return new_state


def place_command_token(
    state: GameState,
    grid: HexGrid,
    position: str,
    faction_key: str,
) -> GameState:
    """God-Mode: kładzie żeton dowodzenia gracza w przestrzeni systemu (bez reguł).

    Nie zużywa puli taktycznej (to ręczna korekta operatora, nie aktywacja —
    aktywacja z pulą jest w ``core.tactical.activate_system``). Idempotentne:
    powtórne położenie nie duplikuje wpisu.
    """
    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)
    system = _get_or_make_system(new_state, position, grid)
    if player_id not in system.command_tokens:
        system.command_tokens.append(player_id)
    new_state.systems[position] = system
    return new_state


def remove_command_token(
    state: GameState,
    grid: HexGrid,
    position: str,
    faction_key: str,
) -> GameState:
    """God-Mode: zdejmuje żeton dowodzenia gracza z przestrzeni systemu (bez reguł)."""
    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)
    system = new_state.systems.get(position)
    if system is not None and player_id in system.command_tokens:
        system.command_tokens.remove(player_id)
        new_state.systems[position] = system
    return new_state

"""web-data: dane graczy (liderzy, zdolności, notki, technologie, kafelki statystyk).

Buduje ``playerData``; wydzielone z ``web_data.py``.
"""

from __future__ import annotations

from typing import Any

from src.api import web_objectives
from src.api.web_game import _color_of, _effective_active_id, _reaction_prefs
from src.api.web_player_units import (
    _controlled_planets_from_systems,
    _deployed_counts_by_player,
    _planet_economy,
    _unit_counts,
    _units_owned_for_faction,
)
from src.api.web_tiles import _ring_count
from src.core import (
    action_budget,
    agenda_phase,
    board_graph,
    capture,
    economy,
    faction_tokens,
    hand_limit,
    legendary_planets,
    planet_abilities,
    rules_hooks,
    tactical,
    tech_effects,
)
from src.core.army_strength import ArmyStrength, army_strength_by_player
from src.core.components import ComponentCategory
from src.core.game_state import GameState, PlayerState
from src.core.hex_grid import HexGrid
from src.core.neighbors import neighbors_by_player
from src.core.positions import load_positions
from src.core.registry import StaticDataRegistry


def _leader_type(leader_id: str, registry: StaticDataRegistry) -> str:
    """Typ lidera (``agent``/``commander``/``hero``) z POLA ``type`` danych.

    Czytamy typ z rejestru liderów, nie z końcówki id — id jak ``keleresherokuuasi``
    nie kończy się nazwą typu, więc zgadywanie po sufiksie je błędnie klasyfikowało
    (Keleres hero → „agent"). Awaryjnie (lider spoza rejestru) próbujemy sufiksu.
    """
    leader = registry.leaders.get(leader_id)
    if leader is not None:
        return leader.type
    lid = leader_id.lower()
    for ltype in ("commander", "hero", "agent"):
        if lid.endswith(ltype):
            return ltype
    return "agent"


def _alliance_leaders(
    state: GameState, player_id: str, own: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Commanderzy innych frakcji, których zdolność gracz ma (Alliance, Yin Ascendant).

    Ten sam wpis co własny lider (chip lidera w panelu), z ``alliance: True``; zawsze odblokowani
    („as though that faction's commander were unlocked”, RULES.md 61.2, 62.10).
    """
    from src.core.hooks import promissory_generic  # lokalnie: hooki ładują się z rejestrem

    have = {str(leader["id"]) for leader in own}
    ids = [
        *rules_hooks.granted_commanders(state, player_id),
        *promissory_generic.alliance_commanders(state, player_id),
    ]
    return [
        {
            "id": leader_id, "type": "commander", "tgCount": 0, "exhausted": False,
            "locked": False, "purged": False, "active": False, "alliance": True,
        }
        for leader_id in dict.fromkeys(ids)
        if leader_id not in have
    ]


def _player_leaders(
    faction_id: str | None,
    registry: StaticDataRegistry,
    states: dict[str, str] | None = None,
    trade_goods: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Buduje listę liderów gracza z danych frakcji (agent/commander/hero).

    Stan domyślny: agent gotowy, commander/hero zablokowani. ``states`` nadpisuje
    stan per lider (``"locked"``/``"unlocked"``/``"exhausted"``) — edycja God-Mode.
    ``trade_goods`` = trade goods lying on a leader card (Artuno the Betrayer, RULES.md 62.21).
    Typ lidera czytamy z danych lidera (``LeaderDef.type``), nie z końcówki id.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return []
    states = states or {}
    trade_goods = trade_goods or {}
    leaders: list[dict[str, Any]] = []
    for leader_id in faction.leaders:
        ltype = _leader_type(leader_id, registry)
        # Stan: override z leader_states albo domyślny (agent gotowy, reszta locked).
        default_state = "unlocked" if ltype == "agent" else "locked"
        state = states.get(leader_id, default_state)
        leaders.append(
            {
                "id": leader_id,
                "type": ltype,
                "tgCount": trade_goods.get(leader_id, 0),
                "exhausted": state == "exhausted",
                "locked": state == "locked",
                # Bohater po użyciu (RULES.md 61.1) — usunięty z gry.
                "purged": state == "purged",
                "active": False,
            }
        )
    return leaders


def _faction_abilities(
    faction_id: str | None, registry: StaticDataRegistry
) -> list[str]:
    """Lista ID zdolności frakcji gracza (pole ``abilities`` danych frakcji).

    Frontend renderuje je jako inskrypcje na karcie gracza (komponent ``Ability``),
    rozwiązując ID po swoich statycznych danych. Zdolności są STANOWE pasywnie:
    nie mają stanu locked/exhausted w stylu liderów — ich okno/efekt wynika z danych
    (``permanentEffect``/``window``), więc wysyłamy tylko identyfikatory. Sortujemy
    dla stabilności dokumentu.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return []
    return sorted(faction.abilities)


def _faction_promissory_notes(
    faction_id: str | None, registry: StaticDataRegistry
) -> list[str]:
    """Własna FRAKCYJNA promissory note gracza (pole ``promissoryNotes`` frakcji).

    Każdy gracz zaczyna grę z unikalną notką swojej frakcji (np. Sol ``ms`` =
    Military Support, Hacan ``convoys`` = Trade Convoys). To stały, JAWNY fakt
    (frakcja X ma notkę Y) — czytany WYŁĄCZNIE z danych frakcji
    (``FactionDef.promissory_notes``), nigdy z pamięci. Frontend renderuje je w
    sekcji loadoutu karty gracza (pole ``customPromissoryNotes``), rozwiązując ID
    po swoich statycznych danych notek (``getPromissoryNoteData``). Sortujemy dla
    stabilności dokumentu.

    UWAGA: to NIE jest ręka (``private.promissory_notes`` — tajna, licznik
    ``pnCount``) ani strefa gry (``promissory_notes_in_play`` — notki zagrane).
    To statyczny „identyfikator" notki frakcji, pokazywany jako loadout.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return []
    return sorted(faction.promissory_notes)


def _faction_techs(
    faction_id: str | None,
    technologies: list[str],
    registry: StaticDataRegistry,
) -> tuple[list[str], list[str]]:
    """Technologie frakcyjne gracza: (wszystkie, niezbadane).

    Źródło listy: pole ``factionTech`` danych frakcji (``FactionDef.faction_tech``).
    "Niezbadane" = technologie frakcyjne, których gracza nie ma na liście
    ``technologies`` (zbadane trafiają do zwykłego racka techów przez ``techs``).
    Frontend wyszarza niezbadane (prop ``unresearched`` komponentu ``Tech``).
    Sortujemy obie listy dla stabilności dokumentu.
    """
    faction = registry.factions.get(faction_id) if faction_id else None
    if faction is None:
        return [], []
    all_techs = sorted(faction.faction_tech)
    researched = {t.lower() for t in technologies}
    not_researched = sorted(t for t in all_techs if t.lower() not in researched)
    return all_techs, not_researched


def _player_breakthrough(
    faction_id: str | None,
    player: Any,
    registry: StaticDataRegistry,
) -> dict[str, Any] | None:
    """Buduje obiekt ``breakthrough`` dla gracza (lub None, gdy frakcja go nie ma).

    Przełom jest przypisany do frakcji przez pole ``faction`` w danych
    (``BreakthroughDef``). Mechanika Thunder's Edge: frakcje spoza tego dodatku nie
    mają przełomu → None (frontend chowa slot, gdy nikt nie ma przełomu). Stan
    (``unlocked``/``exhausted``/``tradeGoodsStored``) pochodzi z ``PlayerState``.

    Kształt pól zgodny z typem frontendu ``BreakthroughData``:
    ``breakthroughId``, ``unlocked``, ``exhausted``, ``tradeGoodsStored``.
    """
    if faction_id is None:
        return None
    breakthrough = registry.breakthrough_for_faction(faction_id)
    if breakthrough is None:
        return None
    return {
        "breakthroughId": breakthrough.id,
        "unlocked": player.breakthrough_unlocked,
        "exhausted": player.breakthrough_exhausted,
        "tradeGoodsStored": player.breakthrough_tg,
        # Karta odwrócona na karcie jednostki (Absolute Synergy, RULES.md 62.15).
        "flipped": player.breakthrough_flipped,
    }


def _player_home_position(player_id: str, state: GameState) -> str | None:
    """Pozycja slotu domowego gracza (kotwica heksa stat-area).

    A swapped home tile (Creuss hero) does not move the stat area: ``seat_position`` wins.

    Priorytet (Bug 9): jawny ``PlayerState.home_position`` z setupu — stabilny
    niezależnie od podbojów. Dopiero gdy go brak (np. gracz utworzony ręcznie
    w God-Mode bez setupu), awaryjnie szukamy pierwszego systemu, w którym gracz
    kontroluje planetę (dawne, niestabilne zachowanie).
    """
    player = state.players.get(player_id)
    if player is not None and player.home_position is not None:
        return player.seat_position or player.home_position
    for position, system in state.systems.items():
        if any(owner == player_id for owner in system.planet_owners.values()):
            return position
    return None


def _tile_ring(position: str) -> int:
    """Numer pierścienia pozycji (pierwsza cyfra ``RPP``; ``000`` = 0)."""
    if position.isdigit() and len(position) == 3:
        return int(position[0])
    return 99  # pozycje nienumeryczne (hyperlane/frac) — poza pierścieniami


def _three_nearby_stat_tiles(
    home_position: str,
    grid: HexGrid,
    taken: set[str],
    ring_count: int,
) -> list[str]:
    """Port algorytmu ``PlayerStatsHelper.findThreeNearbyStatTiles`` z AsyncTI4.

    Źródło (nie z pamięci): ``TI4_map_generator_bot`` →
    ``PlayerStatsHelper.findThreeNearbyStatTiles``. Algorytm:
    1. Kandydaci = PUSTE pozycje (brak systemu na mapie), pierścień ≤ ``ring_count+1``,
       nie zajęte przez innego gracza (``taken``).
    2. Kolejka priorytetowa wg odległości do slotu domowego + kara za pierścień.
    3. Dobieramy najbliższe aż powstanie zwarta trójka (jeden kafelek sąsiaduje
       z dwoma pozostałymi) i zwracamy ``[pivot, sąsiad, sąsiad]`` — pivot (środkowy)
       jest PIERWSZY, bo frontend kładzie na nim heks tożsamości frakcji (VP).

    Odległość liczymy w metryce kubicznej (proxy pikseli z oryginału) + ``ring*0.5``
    jako kara pierścienia — wystarczające, by odwzorować wybór i kolejność AsyncTI4.
    """
    coords = load_positions()
    home = coords.get(home_position)
    if home is None:
        return []
    occupied = grid.positions

    def cube_dist(pos_id: str) -> int:
        h = coords[pos_id]
        return (abs(h.q - home.q) + abs(h.r - home.r) + abs(h.s - home.s)) // 2

    candidates = [
        pos
        for pos in coords
        if pos not in occupied
        and pos not in taken
        and _tile_ring(pos) <= ring_count + 1
    ]
    # Sortuj wg odległości + lekka kara za dalszy pierścień (jak w oryginale).
    candidates.sort(key=lambda p: cube_dist(p) * 2 + _tile_ring(p))

    def adjacent(a: str, b: str) -> bool:
        ha, hb = coords[a], coords[b]
        return (abs(ha.q - hb.q) + abs(ha.r - hb.r) + abs(ha.s - hb.s)) // 2 == 1

    chosen: list[str] = []
    for nxt in candidates:
        chosen.append(nxt)
        # Czy któryś z wybranych sąsiaduje z dokładnie dwoma innymi (pivot)?
        for pivot in chosen:
            neighbors = [p for p in chosen if p != pivot and adjacent(pivot, p)]
            if len(neighbors) >= 2:
                return [pivot, neighbors[0], neighbors[1]]
    return []


def _build_stat_tile_positions(
    state: GameState, grid: HexGrid, entity_keys: dict[str, str]
) -> dict[str, list[str]]:
    """Buduje ``statTilePositions`` = ``{klucz: [pivot, sąsiad, sąsiad]}``.

    Dla każdego gracza bierze jego slot domowy i trzy pobliskie puste pozycje
    (algorytm AsyncTI4, ``_three_nearby_stat_tiles``) — pivot pierwszy. Zajęte
    pozycje są współdzielone między graczami (``taken``), by heksy się nie nakładały.
    Klucz wpisu to stabilny klucz tożsamości (``entity_keys``), spójny z grupowaniem
    jednostek i ``playerData[].faction`` (Bug 1: dawniej kolizja frakcji scalała heksy).
    """
    result: dict[str, list[str]] = {}
    taken: set[str] = set()
    ring_count = _ring_count(grid)
    # Deterministyczna kolejność graczy (po id) — stabilny podział pozycji.
    for player_id in sorted(state.players):
        home = _player_home_position(player_id, state)
        if home is None:
            continue
        positions = _three_nearby_stat_tiles(home, grid, taken, ring_count)
        if positions:
            taken.update(positions)
            result[entity_keys.get(player_id, player_id)] = positions
    return result


def _hand_count(player: PlayerState, key: str) -> int:
    """Liczebność prywatnej ręki gracza ``key`` w dokumencie web-data (R6.5, R4.4).

    Dokument buduje się z PROJEKCJI (``project_for_viewer``): ręce viewera pozostają
    pełnymi listami, a ręce pozostałych graczy są zredagowane (listy puste, liczebność
    w ``hidden_card_counts``). Dlatego:

    * gdy prywatna lista jest niepusta → to viewer, zwracamy jej realną długość;
    * w przeciwnym razie (gracz ≠ viewer po redakcji ALBO pusta ręka viewera) →
      liczebność z ``hidden_card_counts`` (0, gdy brak wpisu — pusta ręka, R5.3).

    Dzięki temu web-data nigdy nie ujawnia cudzych identyfikatorów kart (R6.1, R6.5),
    a liczniki są realne (dawne stałe 0 zastąpione faktyczną liczebnością).
    """
    hand = getattr(player.private, key)
    if hand:
        return len(hand)
    return player.hidden_card_counts.get(key, 0)


def _relic_fragment_cards(
    player: PlayerState, registry: StaticDataRegistry
) -> list[dict[str, str]]:
    """Fragmenty reliktów gracza jako ``{id, name}`` (nazwa z katalogu, fallback = id)."""
    cards: list[dict[str, str]] = []
    for fragment_id in player.relic_fragments:
        card = registry.catalog.get(ComponentCategory.EXPLORATION, fragment_id)
        name = (card.name if card is not None else None) or fragment_id
        cards.append({"id": fragment_id, "name": name})
    return cards


def _player_wormhole_links(
    state: GameState, grid: HexGrid, player_id: str
) -> dict[str, list[str]]:
    """``{wormhole system: [systems adjacent to it only for this player]}`` - the player's own
    adjacency layer (hook ``adjacency.extra_for_player``) seen from every wormhole system."""
    links: dict[str, list[str]] = {}
    for position in sorted(grid.all_wormhole_positions()):
        extra = board_graph.extra_adjacent_for_player(state, player_id, position, grid)
        if extra:
            links[position] = sorted(extra)
    return links


def _build_player_data(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    entity_keys: dict[str, str],
) -> list[dict[str, Any]]:
    """Buduje listę ``PlayerData`` (minimalny, kompletny dla viewera zestaw pól)."""
    players: list[dict[str, Any]] = []
    deployed_by_player = _deployed_counts_by_player(state)
    army_by_player = army_strength_by_player(state, registry)
    active_id = _effective_active_id(state)  # spójny z activePlayer (Bug 7)
    # Sąsiedzi (Neighbors) policzeni raz dla wszystkich graczy (RULES.md 2,
    # R_neighbors). Wynik to player_id; na kolory mapujemy przy serializacji
    # (``Neighbors.tsx`` czyta kolory i odwzorowuje je na frakcje).
    neighbor_ids_by_player = neighbors_by_player(state, grid)
    for player_id, player in sorted(state.players.items()):
        faction = entity_keys.get(player_id, player_id)
        # Pełna nazwa frakcji do WYŚWIETLANIA (displayName/flexibleDisplayName).
        # Czytamy ją z rejestru (pole ``FactionDef.name`` = ``factionName`` z assetów),
        # nigdy z pamięci. Lookup po realnym aliasie ``player.faction`` (nie po kluczu
        # tożsamości, który przy kolizji frakcji bywa ``player_id``). Fallback na klucz
        # ``faction``, gdy frakcja nieznana w rejestrze lub bez nazwy (null/neutral/
        # placeholder) — ścieżka bezpieczna, NIE rzuca. Pole ``faction`` (alias) zostaje
        # bez zmian: frontend używa go jako klucza i do grafiki ``/factions/{alias}.png``.
        faction_def = (
            registry.factions.get(player.faction) if player.faction else None
        )
        faction_display = (
            faction_def.name if faction_def is not None and faction_def.name else faction
        )
        # Opcja A: planety gracza WYLICZANE z planet_owners systemów (jedno źródło
        # prawdy), nie z player.controlled_planets — eliminuje desync panel↔mapa (Bug 3).
        controlled = _controlled_planets_from_systems(player_id, state)
        econ = _planet_economy(controlled, registry, state)
        leaders = _player_leaders(
            player.faction, registry, player.leader_states, player.leader_trade_goods
        )
        leaders += _alliance_leaders(state, player_id, leaders)
        units_owned = _units_owned_for_faction(
            player.faction,
            player.technologies,
            registry,
            player.breakthrough_unlocked,
            player.breakthrough_flipped,
        )
        unit_counts = _unit_counts(deployed_by_player.get(player_id, {}))
        army = army_by_player.get(player_id) or ArmyStrength()
        abilities = _faction_abilities(player.faction, registry)
        faction_techs, not_researched_ft = _faction_techs(
            player.faction, player.technologies, registry
        )
        faction_notes = _faction_promissory_notes(player.faction, registry)
        breakthrough = _player_breakthrough(player.faction, player, registry)
        # Sąsiedzi jako KOLORY (kontrakt viewera): z player_id na kolor przez
        # ``_color_of``; gracze bez jednoznacznego koloru są pomijani (viewer i tak
        # mapuje kolor→frakcja). Sortujemy dla stabilności dokumentu.
        neighbor_colors = sorted(
            color
            for neighbor_id in neighbor_ids_by_player.get(player_id, set())
            if (color := _color_of(state, neighbor_id)) is not None
        )
        players.append(
            {
                "discordId": player_id,
                "userName": player_id,
                "faction": faction,
                "color": player.color or "gray",
                "displayName": faction_display,
                "flexibleDisplayName": faction_display,
                # Model per-gracz (R6.2/R6.3/R6.4): nazwa wyświetlana gracza,
                # typ sterowania (HUMAN/BOT) i poziom trudności (str dla BOT,
                # None dla HUMAN). Pola addytywne — frontend AsyncTI4 je ignoruje,
                # nasze panele odczytają.
                "playerName": player.display_name,
                "controlType": player.control_type.value,
                "difficulty": player.difficulty,
                "personality": player.personality,
                "isSpeaker": state.speaker_id == player_id,
                "isTyrant": False,
                "passed": player.passed,
                # Puppets on a String: a passed player performing an extra action (still passed,
                # yet acting - C_action_cards/puppets-on-a-string/7). UI enables action buttons.
                "bonusAction": action_budget.in_bonus_action(state, player_id),
                # Czy gracz wykonał już akcję w BIEŻĄCEJ turze fazy akcji (RULES.md
                # 31.7). UI blokuje „End turn", dopóki to False i gracz nie spasował.
                "tookActionThisTurn": player.took_action_this_turn,
                # Ile akcji zostało w tej turze (bazowo 1; Fleet Logistics 2 - RULES.md 55.1).
                # UI odblokowuje przyciski akcji, dopóki > 0; End turn nadal wg tookActionThisTurn.
                "actionsLeft": action_budget.actions_left(state, player_id),
                "eliminated": False,
                "active": active_id == player_id,
                # Zasoby / liczniki (viewer czyta je w panelach gracza).
                "tg": player.trade_goods,
                # ``commodities`` = bieżące; ``commoditiesTotal`` = MAKSIMUM (commodity
                # value z karty frakcji). Wcześniej total = bieżące, więc panel zawsze
                # pokazywał „pełne" (np. 3/3) niezależnie od stanu — błąd. Teraz
                # pokazuje realne „bieżące / maks" (start: 0 / commodity_value).
                "commodities": player.commodities,
                "commoditiesTotal": economy.commodity_value(state, player_id),
                # Żetony dowodzenia (CC) — panele gracza + heks stat-area.
                "tacticalCC": player.tactical_cc,
                "fleetCC": player.fleet_cc,
                # Other players' tokens in the fleet pool (Mahact Edict, RULES.md 62.23): their
                # colours; counted in the fleet pool, never redistributed.
                "mahactEdict": [
                    state.players[o].color for o in player.foreign_fleet_tokens
                    if o in state.players
                ],
                # Il Na Viroset: the map lets this player activate systems with own tokens.
                "canActivateOwnTokens": tactical.can_activate_own_token(state, player_id, ""),
                "purgedTechs": list(player.purged_technologies),
                "strategicCC": player.strategic_cc,
                "ccReinf": player.cc_reinf,
                "totalVps": player.victory_points,
                # unitsOwned: realne ID posiadanych jednostek (baza generyczna +
                # frakcyjna, bez ulepszeń). NIGDY []! Pusta lista psuje lookupUnit
                # ([].includes zawsze False). Lista steruje też stanem "Upgraded":
                # skoro gracz ma tylko bazowe, panel nie pokazuje ich jako ulepszone.
                "unitsOwned": units_owned,
                "techs": list(player.technologies),
                # Technologie istotne dla okien UI (produkcja, ruch, walka...) - wskaźniki
                # „ta karta działa tutaj", także gdy nie ma w niej wyboru „may".
                "techEffects": tech_effects.active_techs(state, registry, player_id),
                # Wyczerpane technologie — tylko te, które gracz faktycznie posiada.
                "exhaustedTechs": [
                    t
                    for t in player.exhausted_technologies
                    if t in player.technologies
                ],
                # Zdolności frakcji + technologie frakcyjne (sekcja abilities karty
                # gracza). notResearchedFactionTechs frontend wyszarza; zbadane
                # frakcyjne są w ``techs`` (trafiają do racka techów).
                "abilities": abilities,
                # Wormholes linked ONLY for this player (Quantum Entanglement: alpha <-> beta,
                # RULES.md 61.7): hovering a wormhole draws these links for that player only.
                "wormholeLinks": _player_wormhole_links(state, grid, player_id),
                "factionTechs": faction_techs,
                "notResearchedFactionTechs": not_researched_ft,
                "planets": controlled,
                # Wyczerpane planety — tylko te, które gracz faktycznie kontroluje
                # (utrata planety czyści stan wyczerpania w widoku).
                "exhaustedPlanets": [
                    p for p in player.exhausted_planets if p in controlled
                ],
                "exhaustedPlanetAbilities": [],
                "relics": list(player.relics),
                "frontierCards": list(player.frontier_cards),
                # Przechwycone jednostki na arkuszu frakcji (RULES.md 61.5) - komponent Nombox.
                "nombox": capture.nombox(state, player.player_id),
                # Żetony sleeper w puli (Titans of Ul, RULES.md 61.6) - pasek żetonów gracza.
                "sleeperTokensReinf": _sleeper_supply(state, registry, player.player_id),
                "exhaustedRelics": [r for r in player.exhausted_relics if r in player.relics],
                # Karty zdolności legendarnych planet gracza (RULES.md 60): tekst z assetów, rodzaj
                # (ACTION = przycisk w akcji komponentu, reszta = oferty w oknie decyzji).
                "legendaryAbilities": [
                    {
                        "planet": planet_id,
                        "name": registry.planets[planet_id].legendary_ability_name,
                        "text": registry.planets[planet_id].legendary_ability_text or "",
                        "kind": (
                            "action"
                            if planet_abilities.is_action_planet(registry, planet_id)
                            else "passive"
                        ),
                        "exhausted": planet_id in player.exhausted_legendaries,
                    }
                    for planet_id in legendary_planets.legendary_planets_of(
                        state, registry, player_id
                    )
                ],
                # Fragmenty reliktów z eksploracji (id kart: crf*/hrf*/irf*/urf*) — front liczy je
                # po prefiksie i rysuje w player area.
                "fragments": list(player.relic_fragments),
                "leaders": leaders,
                "leaderIDs": [str(leader["id"]) for leader in leaders],
                # Przełom frakcji (Thunder's Edge). Pole opcjonalne we froncie —
                # emitujemy tylko gdy frakcja go ma (inaczej None i slot się chowa).
                "breakthrough": breakthrough,
                # Tajne cele: zdobyte (jawne) + znane niezdobyte (tylko ręka viewera).
                **web_objectives.secret_fields(player, registry),
                # Promissory notes w strefie gracza (jawne — RULES.md 2d). ODRĘBNE
                # od licznika ręki ``pnCount`` (ręka tajna). Puste do czasu logiki
                # zagrywania notek; dziś zasilane przez God-Mode.
                "promissoryNotesInPlayArea": list(player.promissory_notes_in_play),
                # Prawa w strefie gracza (wygrane wybory „Elect Player", RULES.md 51) - jawne.
                "lawsOwned": agenda_phase.owned_laws(state, registry, player_id),
                # Własna FRAKCYJNA notka gracza (loadout — każdy zaczyna z jedną,
                # np. Sol ``ms``, Hacan ``convoys``). Jawny fakt statyczny z danych
                # frakcji; frontend renderuje w sekcji loadoutu (abilities/techy).
                "customPromissoryNotes": faction_notes,
                "followedSCs": [],
                "unfollowedSCs": [],
                # Karty strategii gracza (numery inicjatywy) — kolejność tur w panelu faz.
                "scs": list(player.strategy_cards),
                "exhaustedSCs": list(player.exhausted_strategy_cards),
                # Sąsiedzi (Neighbors) jako kolory — RULES.md 2 / R_neighbors.
                "neighbors": neighbor_colors,
                # Transakcje (RULES.md 47): z kim gracz już transakcjonował w tej turze
                # (kolory), jawne fragmenty reliktów (id + nazwa z katalogu) oraz żetony
                # obietnic, które gracz TRZYMA: {kolor wystawcy: liczba}.
                "transactedWith": sorted(
                    c
                    for pid in player.transacted_with
                    if (c := _color_of(state, pid)) is not None
                ),
                "relicFragmentCards": _relic_fragment_cards(player, registry),
                "debtTokens": {
                    color: count
                    for issuer_id, count in state.debt_tokens.get(player_id, {}).items()
                    if (color := _color_of(state, issuer_id)) is not None
                },
                # Realne liczebności prywatnych rąk (R6.5, R4.4). Dla viewera —
                # długości jego list; dla innych — z hidden_card_counts wypełnionego
                # przez projekcję. Nigdy nie ujawniamy cudzych identyfikatorów kart.
                "soCount": _hand_count(player, "secret_objectives"),
                "pnCount": _hand_count(player, "promissory_notes"),
                "acCount": _hand_count(player, "action_cards"),
                # „Skip all reactions” (RULES.md 54.11) - prywatne: u innych projekcja daje False.
                "autoPassReactions": player.private.auto_pass_reactions,
                # Deklaracje pasu / wyciszenia (RULES.md 54.12) - prywatne jak wyżej.
                "reactionPrefs": _reaction_prefs(state, player, registry),
                # Limit kart akcji (Executive Sanctions itd.); None = bez limitu (panel dowódcy).
                "actionCardLimit": hand_limit.action_card_limit(state, player_id),
                "unitCounts": unit_counts,
                # Ekonomia planet z rejestru (reguła AsyncTI4, RULES.md 7).
                # resources/influence = dostępne (zakładamy wszystkie gotowe);
                # tot* = sumy łączne; optimal/flex per reguła getOptimal*.
                "resources": econ.resources,
                "influence": econ.influence,
                "totResources": econ.resources,
                "totInfluence": econ.influence,
                "optimalResources": econ.opt_res,
                "optimalInfluence": econ.opt_inf,
                "flexValue": econ.flex,
                "totOptimalResources": econ.opt_res,
                "totOptimalInfluence": econ.opt_inf,
                "totFlexValue": econ.flex,
                "crf": 0,
                "hrf": 0,
                "irf": 0,
                "urf": 0,
                "stasisInfantry": 0,
                "actualHits": 0,
                "expectedHitsTimes10": 0,
                # Siła armii (panel Army Strength + ranking 1/2/3) — core/army_strength.py.
                "spaceArmyRes": army.space_res,
                "groundArmyRes": army.ground_res,
                "spaceArmyHealth": army.space_health,
                "groundArmyHealth": army.ground_health,
                "spaceArmyCombat": army.space_combat,
                "groundArmyCombat": army.ground_combat,
            }
        )
    return players


def _sleeper_supply(state: GameState, registry: StaticDataRegistry, player_id: str) -> int:
    """Pula żetonów sleeper (tylko frakcja z Terragenesis/Awaken - reszta 0)."""
    player = state.players[player_id]
    faction = registry.factions.get(player.faction or "")
    if faction is None or "awaken" not in faction.abilities:
        return 0
    return faction_tokens.supply_left(state, player_id, faction_tokens.SLEEPER)

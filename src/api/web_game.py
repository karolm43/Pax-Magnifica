"""web-data: stan rundy (faza, aktywny gracz, okna, reakcje, walka, ``gameState``)."""

from __future__ import annotations

import zlib
from typing import Any

from src.api import web_agenda, web_objectives
from src.core import chronicle as chronicle_core
from src.core import (
    component_text,
    reaction_prefs,
    rules_hooks,
    strategy_phase,
    turn_flow,
)
from src.core import epilogue as epilogue_core
from src.core.components import ActionCardDef, ComponentCategory
from src.core.game_state import GameState, PlayerState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

# Mapowanie naszej 4-wartościowej fazy na string ``GamePhase`` frontendu
# (małe litery, z podfazami). Frontend indeksuje PHASE_CONFIGS dokładnie po tych
# wartościach — casing i granularność muszą się zgadzać (patrz GameStatePanel.tsx).
_PHASE_TO_WEB: dict[str, str] = {
    "STRATEGY": "strategy",
    "ACTION": "action",
    "STATUS": "status.scoring",
    "AGENDA": "agenda.voting",
}


def _epilogue_payload(state: GameState) -> dict[str, object] | None:
    """Stan głosowania epilogu (None, dopóki gra trwa)."""
    if state.winner_id is None:
        return None
    epilogue = state.epilogue
    return {
        "voters": epilogue_core.voters(state),
        # Drugie miejsce: jego głos rozstrzyga remis w głosowaniu.
        "runnerUp": epilogue_core.runner_up(state),
        "votes": dict(epilogue.votes) if epilogue is not None else {},
        "result": epilogue.result if epilogue is not None else None,
    }


def _to_web_phase(phase: object) -> str:
    """Zwraca string fazy w formacie frontendu (``GamePhase``)."""
    return _PHASE_TO_WEB.get(str(phase), "unknown")


def _effective_active_id(state: GameState) -> str | None:
    """Spójny identyfikator aktywnego gracza do WYŚWIETLENIA (Bug 7).

    Na poziomie STANU ``active_player_id`` w toczącej się partii nigdy nie jest None
    (RULES.md 31.4, „zawsze czyjaś tura"). To jest jednak projekcja DO FRONTENDU:
    gdy wskazany gracz jest spasowany, NIE podświetlamy go jako „active" (sprzeczne
    sygnały ``active`` + ``passed``), tylko zwracamy None jako kolor podświetlenia.

    Taka sytuacja powstaje teraz także normalnie: gdy w fazie akcji WSZYSCY spasują,
    silnik ustawia ``active_player_id`` na MÓWCĘ (ogłosi tranzycję — RULES.md 31.4),
    a mówca też ma ``passed=True``. Panel tury pokaże wtedy brak podświetlenia
    aktywnego, choć stan nadal wskazuje mówcę (``isSpeaker`` niesie tę informację).
    """
    active_id = state.active_player_id
    if active_id is None:
        return None
    player = state.players.get(active_id)
    if player is None or player.passed:
        return None
    return active_id


def _color_of(state: GameState, player_id: str | None) -> str | None:
    """Kolor gracza o danym id (lub None), gdy jednoznaczny.

    Frontend dopasowuje graczy w ``gameState`` po KOLORZE, więc kolor musi być
    jednoznaczny — przy kolizji kolorów (niepoprawny stan God-Mode) zwracamy None,
    by nie wskazać przypadkowego gracza (spójne z ``_active_color``).
    """
    if player_id is None:
        return None
    player = state.players.get(player_id)
    if player is None or player.color is None:
        return None
    same_color = sum(1 for p in state.players.values() if p.color == player.color)
    return player.color if same_color == 1 else None


def _active_color(state: GameState) -> str | None:
    """Kolor aktywnego gracza (frontend dopasowuje ``activePlayer`` po KOLORZE).

    Zwraca kolor TYLKO gdy jest jednoznaczny — gdy dwóch graczy dzieli ten sam
    kolor (niepoprawny stan God-Mode), dopasowanie po kolorze trafiłoby w obu, więc
    nie wskazujemy aktywnego (null) zamiast podświetlać przypadkowego gracza (Bug 7).
    """
    active_id = _effective_active_id(state)
    if active_id is None:
        return None
    player = state.players.get(active_id)
    if player is None or player.color is None:
        return None
    same_color = sum(
        1 for other in state.players.values() if other.color == player.color
    )
    if same_color != 1:
        return None
    return player.color


def _imperator_boost_active(state: GameState) -> bool:
    """Czy aktywny gracz ma teraz premię ruchu z kanału ``imperator`` (hook ``move_value``).

    Bez nazw frakcji: pytamy hook, czy kanał podnosi ruch (Imperator: system z planetą legendarną).
    """
    active = state.active_player_id
    if active is None or state.active_system is None or active not in state.players:
        return False
    point = rules_hooks.POINT_MOVEMENT_MOVE_VALUE
    ctx = {"base_type": "cruiser", "boost": False, "tempesta": False}
    with_bonus = rules_hooks.modify(point, state, active, 0, {**ctx, "imperator": True})
    return int(with_bonus) > int(rules_hooks.modify(point, state, active, 0, ctx))


def _pending_window(state: GameState) -> dict[str, Any] | None:
    """Buduje reprezentację otwartego okna czasowego dla frontendu (lub None).

    Tłumaczy ``GameState.pending_window`` na kształt panelu okna: typ okna,
    bieżący respondent i kolejka jako KOLORY graczy (frontend dopasowuje po
    kolorze, spójnie z ``activePlayer``), ile osób zostało oraz kontekst okna.
    Gdy kolor gracza jest niejednoznaczny (kolizja — niepoprawny stan God-Mode),
    wpada ``player_id`` jako fallback, by panel miał czym zaadresować odpowiedź.
    """
    window = state.pending_window
    if window is None:
        return None

    def ident(player_id: str) -> str:
        # Kolor, gdy jednoznaczny; inaczej player_id (żeby panel miał adres).
        color = _color_of(state, player_id)
        return color if color is not None else player_id

    responder = window.current_responder
    return {
        "windowType": window.window_type.value,
        "currentResponder": ident(responder) if responder is not None else None,
        # player_id bieżącego respondenta — panel adresuje nim odpowiedź (stabilne,
        # niezależne od kolizji kolorów).
        "currentResponderId": responder,
        "queue": [ident(pid) for pid in window.queue],
        "cursor": window.cursor,
        "remaining": max(len(window.queue) - window.cursor, 0),
        "responded": [ident(pid) for pid in window.responded],
        "context": dict(window.context),
        "isComplete": window.is_complete,
    }

def _pending_strategy(state: GameState) -> dict[str, Any] | None:
    """Reprezentacja trwającego wieloetapowego primary karty strategii (lub None).

    ``ownerId`` (player_id) adresuje odpowiedź, ``ownerColor`` dopasowuje gracza w UI.
    Szkic wyborów (``draft``) jest publiczny dla właściciela; pola prywatne kart
    (np. podgląd agendy) dojdą osobnym kanałem widoczności, nie tędy.
    """
    pending = state.pending_strategy
    if pending is None:
        return None
    return {
        "initiative": pending.initiative,
        "ownerId": pending.owner_id,
        "ownerColor": _color_of(state, pending.owner_id),
        "step": pending.step,
        # Klucze z prefiksem „_" są PRYWATNE (np. dobrane karty akcji w Politics) - nie
        # trafiają do publicznego dokumentu; właściciel dostaje je przez /strategy/options.
        "draft": {k: v for k, v in pending.draft.items() if not k.startswith("_")},
    }


def _reaction_prefs(
    state: GameState, player: PlayerState, registry: StaticDataRegistry
) -> dict[str, Any]:
    """Preferencje reakcji gracza dla UI: obowiązujące deklaracje (kategoria -> czas), wyciszenia
    z nazwami komponentów z assetów (RULES.md 54.12)."""
    prefs = player.private.reaction_prefs
    passes = {
        category: declaration.until
        for category, declaration in prefs.passes.items()
        if reaction_prefs.is_live(state, declaration)
    }
    if player.private.auto_pass_reactions:
        passes[reaction_prefs.ALL] = reaction_prefs.UNTIL_ALWAYS
    return {
        "passes": passes,
        "onlyInvolved": prefs.only_involved,
        "mutedCards": list(prefs.muted_cards),
        "mutedOffers": [
            {"key": key, "name": component_text.describe_component(registry, key)[0] or key}
            for key in prefs.muted_offers
        ],
    }


def _reaction_pause(state: GameState) -> dict[str, Any] | None:
    """Kontrakt ``reactionPause``: pauza w kluczowym oknie (``openedAt`` = czas serwera).

    Stan jest już projekcją: ``passed`` zawiera najwyżej patrzącego (RULES.md 54.11), a
    ``extended_by`` tylko jego id (inne prośby to puste zaślepki - liczba jest jawna).
    """
    pause = state.reaction_pause
    if pause is None:
        return None
    return {
        "key": pause.key,
        "label": pause.label,
        "event": pause.event,
        "subject": pause.subject,
        "subjectColor": _color_of(state, pause.subject) if pause.subject else None,
        "openedAt": pause.opened_at,
        "pauseSeconds": pause.seconds,
        "eligible": list(pause.eligible),
        "passed": [pid for pid in pause.passed if pid],
        "extensions": len(pause.extended_by),
        "askedForTime": [pid for pid in pause.extended_by if pid],
    }


def _held_play(state: GameState, registry: StaticDataRegistry) -> dict[str, Any] | None:
    """Kontrakt ``heldPlay``: karta czekająca na Sabotage (lub None).

    Identyfikatory graczy to ``player_id`` (adresują ``actor_id`` w ``/action-card/held/*``);
    addytywnie dochodzą kolory (``playerColor`` / ``eligibleColors`` / ``passedColors``).
    ``openedAt`` = czas serwera (s epoch). Karta jest jawna, więc tekst i nazwa z katalogu.
    """
    held = state.held_play
    if held is None:
        return None
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, held.card_id)
    return {
        "playerId": held.player_id,
        "playerColor": _color_of(state, held.player_id),
        "cardId": held.card_id,
        "cardName": (card.name if card is not None and card.name else held.card_id),
        "text": " ".join(card.texts.values()) if isinstance(card, ActionCardDef) else "",
        "openedAt": held.opened_at,
        "holdSeconds": held.seconds,
        "eligible": list(held.eligible),
        # Projekcja: najwyżej patrzący (pasy są prywatne, RULES.md 54.11).
        "passed": [pid for pid in held.passed if pid],
        "extensions": len(held.extended_by),
        "askedForTime": [pid for pid in held.extended_by if pid],
        "eligibleColors": [c for pid in held.eligible if (c := _color_of(state, pid))],
        # Sabotage na tę kartę czekające na Instinct Training (RULES.md 62.9) albo None.
        "counter": _held_counter(state, registry),
    }


def _held_counter(state: GameState, registry: StaticDataRegistry) -> dict[str, Any] | None:
    held = state.held_play
    counter = held.counter if held is not None else None
    if counter is None:
        return None
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, counter.card_id)
    return {
        "playerId": counter.player_id,
        "playerColor": _color_of(state, counter.player_id),
        "cardId": counter.card_id,
        "cardName": (card.name if card is not None and card.name else counter.card_id),
    }


def _active_combat(state: GameState) -> dict[str, Any] | None:
    """Kontrakt ``GameStateCombat`` AsyncTI4 dla trwającej walki (lub None).

    ``unitHolder`` = "space" albo id planety, ``participantColors`` = kolory stron.
    Panel „Game state" barwi się na „Combat", gdy pole jest niepuste.
    """
    combat = state.active_combat
    if combat is None:
        return None
    colors = [
        color
        for pid in (combat.attacker, combat.defender)
        if (color := _color_of(state, pid)) is not None
    ]
    return {
        "system": combat.position,
        "unitHolder": combat.planet or "space",
        "round": combat.round,
        "participantColors": colors,
    }


def _safe_pick_count(state: GameState) -> int | None:
    """Liczba kart strategii na gracza (``Pick_Count``) lub None, gdy nieobsługiwana.

    Woła czystą regułę ``strategy_phase.pick_count`` (2 przy 3–4 graczach, 1 przy
    5–8). Web-data serializuje DOWOLNY stan — także niepełny/God-Mode z liczbą
    graczy spoza 3..8 — więc NIE może rzucać: w takim przypadku łapiemy
    ``ValueError`` i zwracamy None (pole addytywne, frontend AsyncTI4 je ignoruje,
    nasz StrategyCardTable/StrategyCardPicker odczyta). RULES.md 13.
    """
    try:
        return strategy_phase.pick_count(state)
    except ValueError:
        return None


def _build_game_state(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid
) -> dict[str, Any]:
    """Buduje obiekt ``gameState`` — zasila panel faz + kolejność tur we froncie.

    Faza, aktywny gracz (kolor) oraz akcja taktyczna (E3): ``activeSystem`` =
    aktualnie aktywowany system, ``tacticalStep`` = bieżący krok (nasze rozszerzenie
    kontraktu — frontend AsyncTI4 je ignoruje, nasz panel taktyczny odczyta). Walka/
    agenda pozostają null do czasu ich logiki. Kolejność tur frontend wylicza z
    ``playerData`` (``active``/``passed``/``scs``).
    """
    return {
        "phase": web_agenda.web_phase(state) or _to_web_phase(state.phase),
        "activePlayer": _active_color(state),
        # Kolor gracza, którego jest TURA (``active_player_id``) — BEZ gaszenia
        # przez ``passed`` (w odróżnieniu od ``activePlayer``, który służy do
        # PODŚWIETLENIA i gaśnie dla spasowanego). To pole odpowiada na „czyja tura",
        # by panel sterowania turą (End turn/Pass) wiedział, dla kogo renderować,
        # nawet gdy aktywny gracz już spasował w tej fazie (zagrał kartę, spasował,
        # a okno secondary wciąż otwarte — RULES.md 31.4/31.6). Null tylko, gdy
        # realnie brak aktywnego (np. kolizja kolorów God-Mode) lub stan pusty.
        "activeTurnPlayer": _color_of(state, state.active_player_id),
        # Mówca (kolor) — otwiera wybór kart w fazie strategii (speaker order,
        # RULES.md 24). Nasze rozszerzenie kontraktu; panel tury je odczyta.
        "speaker": _color_of(state, state.speaker_id),
        # Liczba kart strategii na gracza (Pick_Count) — int lub None, gdy liczba
        # graczy spoza 3..8 (web-data nie rzuca). Pole ADDYTYWNE: panel/stół
        # strategii odczyta, frontend AsyncTI4 je ignoruje. RULES.md 13.
        "strategyPickCount": _safe_pick_count(state),
        # Kolejność miejsc przy stole jako KOLORY (speaker order wyznacza panel
        # tury rotacją od mówcy). Puste, gdy seating nieustalony.
        "seatingOrder": [
            color
            for pid in state.seating_order
            if (color := _color_of(state, pid)) is not None
        ],
        "turnStartedAt": None,
        # Zwycięzca (kolor) po zakończeniu gry — R_victory_points (próg VP albo brak celów).
        "winner": _color_of(state, state.winner_id),
        "winnerId": state.winner_id,
        # God-Mode: limit ręki kart akcji wyłączony (RULES.md 53.8) - przełącznik w menu God-Mode.
        "actionCardLimitDisabled": state.action_card_limit_disabled,
        # Koniec gry: powód ("victory_points" | "round_limit" | "no_objectives"), limit rund
        # i głosowanie epilogu (honorowe / niehonorowe) — dla ekranu zwycięstwa.
        "endReason": state.end_reason,
        "maxRounds": state.max_rounds,
        "epilogue": _epilogue_payload(state),
        # Wnioski z przebiegu partii (największa bitwa, zdrady…) — tylko po końcu gry.
        "highlights": (
            chronicle_core.highlights(state, registry) if state.winner_id is not None else []
        ),
        "agenda": None,
        # Stan fazy agendy (RULES.md 51: ujawnienie, głosowanie, wynik) - None poza zainicjowaną
        # fazą agendy. Nasze rozszerzenie kontraktu (kontraktowe ``agenda`` AsyncTI4 zostaje None).
        "agendaPhase": web_agenda.build_agenda_payload(state, registry),
        # Stan kroków fazy statusu (RULES.md 41) — None poza zainicjowaną fazą statusu.
        "status": web_objectives.build_status_payload(state, registry, grid),
        "activeSystem": state.active_system,
        "tacticalStep": (
            state.tactical_step.value if state.tactical_step is not None else None
        ),
        # Trwająca walka (RULES.md 39) — kontrakt AsyncTI4 ``GameStateCombat``; pełne dane
        # pola bitwy idą osobnym endpointem ``GET /tactical/battle``.
        "activeCombat": _active_combat(state),
        # Trwająca inwazja (RULES.md 40) — sygnał dla okna inwazji; pełne dane idą osobnym
        # endpointem ``GET /tactical/invasion``. Nasze rozszerzenie kontraktu.
        "activeInvasion": (
            {"system": state.invasion.position, "phase": state.invasion.phase.value}
            if state.invasion is not None
            else None
        ),
        # Trwająca eksploracja planet po Establish Control (RULES.md 46) — sygnał dla okna;
        # pełne dane idą endpointem `GET /exploration`. Nasze rozszerzenie kontraktu.
        "activeExploration": (
            {"system": state.exploration.position}
            if state.exploration is not None
            else None
        ),
        # Thunder's Edge (RULES.md 50) - sygnał dla okien: czekają żetony ingress albo położenie
        # Thunder's Edge; pełne dane idą endpointem `GET /thunders-edge`. Nasze rozszerzenie
        # kontraktu. ``fractureInPlay`` steruje układem mapy, ``lastRoll`` animacją rzutu.
        "thundersEdge": {
            "fractureInPlay": state.fracture.in_play,
            "pendingIngress": bool(state.fracture.pending),
            "pendingPlacement": state.expeditions.pending_placement is not None,
            "lastRoll": state.fracture.last_roll,
            "thundersEdgePosition": state.expeditions.thunders_edge_position,
        },
        # Ostatni rzut kośćmi poza walką (Fracture, karty akcji) - UI animuje go kośćmi
        # (`core.dice.record_table_roll`). Nasze rozszerzenie kontraktu.
        "tableRoll": state.table_roll,
        # Ostatnie rzuty (rosnące `seq`) - kilka w jednym żądaniu UI odtwarza po kolei.
        "tableRolls": state.table_rolls,
        # Ostatnie odsłonięcie reliktu z talii (fragmenty, The Fracture, eksploracja) - UI gra
        # widowisko u wszystkich (`core.relics.record_reveal`, RULES.md 59.8).
        "relicReveal": state.relic_reveal,
        # Jednorazowa produkcja z karty (Freelancers) — okno produkcji otwiera się poza krokiem
        # PRODUCTION (RULES.md 46). Nasze rozszerzenie kontraktu.
        "productionGrant": (
            {"system": state.production_grant.position, "source": state.production_grant.source}
            if state.production_grant is not None
            else None
        ),
        # Okno czasowe (timing window) — None, gdy żadne nie trwa. Nasze rozszerzenie
        # kontraktu (frontend AsyncTI4 je ignoruje, nasz panel okna odczyta). RULES.md 29.2.
        "pendingWindow": _pending_window(state),
        # Decyzje graczy (oferty technologii/zdolności, RULES.md 56): UI otwiera okno wyboru dla
        # każdego, kto ma coś do rozstrzygnięcia. Szczegóły (opcje) z GET /offers.
        # Czy w tej akcji taktycznej zużyto już premię Gravity Drive (UI chowa przełącznik).
        "gravityDriveUsed": state.gravity_drive_used,
        # Czy w tej akcji poruszono już statek (UI: „Undo last move” cofa wtedy ruch, a bez ruchu
        # - samą aktywację) i czy inwazja tej akcji jest już zamknięta (bez ponownego startu).
        "tacticalMoved": state.tactical_moved,
        "invasionResolved": state.invasion_resolved,
        # Czy aktywny gracz ma w tej akcji taktycznej premię „+1 do ruchu jednego statku" z karty
        # (Ionian Fuel Refinery) - UI pokazuje wtedy ten sam przełącznik co dla Gravity Drive.
        "extraMoveBoostActive": any(
            e.key == "planets:tempesta" and e.owner == state.active_player_id
            for e in state.active_effects
        ),
        "tempestaUsed": state.tempesta_used,
        # Premia „+1 do ruchu jednego statku” z przełomu Imperator (Winnu) — osobny przełącznik.
        "imperatorBoostActive": _imperator_boost_active(state),
        "imperatorUsed": state.imperator_used,
        # Efekty trwałe w grze (bohater „near the game board”, kości agenta, prawa rundy...):
        # panel „Active effects” przy planszy. ``owner`` = klucz tożsamości gracza (jak faction).
        "activeEffects": _active_effects(state, registry),
        "pendingOffers": [
            {"id": o.id, "playerId": o.player_id, "mandatory": o.mandatory, "label": o.label}
            for o in state.pending_offers
        ],
        # Wieloetapowe PRIMARY karty strategii (wybory aktywnego gracza) — None, gdy brak.
        "pendingStrategy": _pending_strategy(state),
        # Zagrana karta akcji czekająca na ewentualne Sabotage (hold-play, RULES.md 53.6) —
        # JAWNA (leży na stole). None, gdy brak okna.
        "heldPlay": _held_play(state, registry),
        # Pauza ochronna w kluczowym oknie reakcji (RULES.md 54.10) — JAWNA (bez informacji o
        # rękach: uprawnieni to gracze z kartą akcji, co jest jawne). None, gdy brak.
        "reactionPause": _reaction_pause(state),
        # Długość okien reakcji ustawiona przez hosta (RULES.md 54.11).
        "reactionWindowSeconds": state.reaction_window_seconds,
        # „Quick windows” hosta (RULES.md 54.12): okno kończy się, gdy wszyscy spasowali.
        "quickReactionWindows": state.quick_reaction_windows,
        # Stoły transakcji (RULES.md 47.1b): JAWNE tylko pary i Ready; zawartość daje
        # ``GET /transactions/state`` samym stronom.
        "transactionTables": [
            {
                "opener": t.opener,
                "partner": t.partner,
                "ready": list(t.ready),
                "prefilled": t.prefilled,
                # Skrót zawartości (bez treści) — klient odświeża stół, gdy się zmieni.
                "stamp": zlib.crc32(repr(sorted(t.sides.items())).encode()),
            }
            for t in state.transaction_tables
        ],
        # Setup startowy (tajne cele, żeton Custodians, odkrycie celów) dopisuje
        # ``build_web_data`` z PEŁNEGO stanu (``web_setup.build_setup_payload``). RULES.md 45.
        # Czy MÓWCA może już ogłosić przejście fazy — steruje widocznością „Next phase"
        # w panelu tury (akcja/status: dopiero po komplecie pasów/kroków; strategia:
        # po pełnym wyborze kart; agenda: zawsze). DECYZJA PROJEKTOWA 2026-11.
        "canAdvancePhase": turn_flow.can_advance_phase(state),
        # Czy wszyscy skończyli swoją część bieżącej fazy (pas/krok). Frontend
        # pokazuje na tej podstawie kontekstowy komunikat „Wszyscy spasowali…".
        "allPassed": turn_flow.all_passed(state),
    }

def _active_effects(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """Efekty trwałe do panelu przy planszy; ``owner`` jako klucz tożsamości gracza."""
    keys = _entity_key_map(state)
    return [
        {**row, "owner": keys.get(row["owner"], row["owner"]) if row["owner"] else None}
        for row in component_text.active_effects_view(state, registry)
    ]

def _entity_key_map(state: GameState) -> dict[str, str]:
    """Buduje mapę ``player_id -> klucz tożsamości`` używany w całym web-data.

    Frontend grupuje jednostki w ``tileUnitData``/``statTilePositions`` po stringu,
    który traktuje jak ``faction`` i dopasowuje do ``playerData[].faction`` w
    ``lookupUnit``. Dlatego klucz MUSI być ten sam we wszystkich miejscach i MUSI
    jednoznacznie wskazywać gracza — inaczej jednostki dwóch graczy dzielących tę
    samą frakcję (lub brak frakcji) scalają się w jeden wpis i znikają z mapy
    (Bug 1: ``faction OR None`` kolidowało w ``_entities_from_counts`` /
    ``_build_stat_tile_positions`` / ``_planet_controller``).

    Reguła: użyj ``faction``, gdy jest UNIKALNA w całej grze; w przeciwnym razie
    (kolizja frakcji albo brak frakcji) użyj stabilnego ``player_id``. Dzięki temu
    każdy gracz ma własny, niekolidujący klucz, a frontend i tak go znajdzie
    (ten sam klucz trafia do ``playerData[].faction``).
    """
    faction_counts: dict[str, int] = {}
    for player in state.players.values():
        if player.faction is not None:
            faction_counts[player.faction] = faction_counts.get(player.faction, 0) + 1
    result: dict[str, str] = {}
    for player_id, player in state.players.items():
        if player.faction is not None and faction_counts[player.faction] == 1:
            result[player_id] = player.faction
        else:
            result[player_id] = player_id
    return result

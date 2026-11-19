"""Akcja strategiczna: primary (wieloetapowe) + okno secondary kart strategii (E8-T3, E8-T5).

Rozstrzyga PRIMARY karty aktywnego gracza i otwiera OKNO CZASOWE ``STRATEGY_SECONDARY``
dla pozostałych graczy (kolejka od gracza po aktywnym, zgodnie z zegarem — RULES.md 30.1).
Każdy respondent okna wykonuje secondary („follow", z ewentualnym ``payload`` wyborów) albo
pasuje; po zamknięciu okna karta jest wyczerpana (uproszczenie: wyczerpujemy przy zagraniu,
bo w trakcie okna i tak nikt nie może jej użyć ponownie — patrz RULES.md 30.5).

Model (RULES.md 30.5, ``docs/PROJEKT_KARTY_STRATEGII.md``):

* **Primary jest krokowe.** Karta ze zdefiniowanymi ``primary_steps`` ustawia
  ``state.pending_strategy`` (krok + szkic wyborów). Aktywny gracz przesyła kolejne kroki
  (``submit_primary_step``); efekt primary stosuje się atomowo po OSTATNIM kroku, potem
  otwiera się okno secondary. Karta bez kroków stosuje primary od razu.
* **Secondary ma KOSZT** (``secondary_costs_token``): follow wydaje 1 żeton ze strategy pool
  (wraca do rezerwy), chyba że karta go nie wymaga (Leadership) albo gracz został wskazany
  przez aktywnego jako „free" (Trade) — wtedy secondary jest DARMOWE i OBOWIĄZKOWE.
* Spasowany gracz MOŻE robić secondary (R_action_phase) — kolejka nie pomija pasujących.
* Serwer jest autorytetem: primary tylko od ``owner_id``, secondary tylko od bieżącego
  respondenta okna. Funkcje są CZYSTE (``state -> state``, operują na klonie).

Definicje kart: pakiet ``core/strategy_cards`` (jedna karta = jeden moduł z ``SPEC``).
Karty bez wpisu mają domyślne zachowanie „brak efektu / bez kosztu".
"""

from __future__ import annotations

from typing import Any

from src.core import action_budget, command_tokens, exhaust, rules_hooks, timing, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, StrategyResolution, WindowType
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import CARDS, CardSpec, leadership, trade
from src.core.strategy_cards.base import CardContext, Draft

# Numery inicjatywy (z danych: zestaw ``te``); zgodność z rejestrem pilnują testy.
_LEADERSHIP_INITIATIVE = leadership.INITIATIVE
_TRADE_INITIATIVE = trade.INITIATIVE

# Klucz kontekstu okna: player_id graczy z DARMOWYM, obowiązkowym secondary (CSV).
_FREE_KEY = "free"
# Klucz kontekstu okna: respondent, który „follow" i czeka na koniec produkcji z karty
# (Warfare TE); kolejka stoi, dopóki produkcja się nie zakończy.
_AWAIT_PRODUCTION_KEY = "await_production"


def _spec(initiative: int) -> CardSpec:
    return CARDS.get(initiative, CardSpec())


# Klucz kontekstu okna: secondary otwarte bohaterem Winnu (Mathis Mathinus), nie akcją
# strategiczną gracza - Acquiescence nie działa (F_winnu/mathis-mathinus-imperial-seal/3).
HERO_KEY = "hero"

# Perfect Synthesis (bohater Naaz-Rokha, RULES.md 62.15): kolejne karty łańcucha secondary
# („5,3”) i żeton „z rezerwy zamiast z puli strategicznej”.
CHAIN_KEY = "then"
TOKEN_FROM_KEY = "token_from"
FROM_REINFORCEMENTS = "reinforcements"
# Pule arkusza, z których gracz bierze żeton, gdy rezerwa jest pusta (F_naaz_rokha hesh 5).
SHEET_POOLS: tuple[str, ...] = ("tactical", "fleet", "strategic")

NO_COST_KEY = "no_cost"  # gracze, którzy dostali darmowe (nieobowiązkowe) secondary w oknie
# Źródło darmowego secondary: "p1=abilities:master_of_trade;p2=promissory_notes:acq".
NO_COST_WHY_KEY = "no_cost_why"


def first_primary_step(initiative: int) -> str | None:
    """Pierwszy krok primary karty (``None`` = karta bez kroków, primary od razu)."""
    steps = _spec(initiative).primary_steps
    return steps[0] if steps else None


def secondary_without_token(state: GameState, player_id: str, initiative: int) -> bool:
    """Czy gracz rozstrzyga secondary BEZ żetonu (hook albo wpis ``no_cost`` okna) — RULES.md 62.6.

    W przeciwieństwie do „free” (Trade primary) takie secondary zostaje NIEOBOWIĄZKOWE.
    """
    window = state.pending_window
    if window is not None and window.window_type is WindowType.STRATEGY_SECONDARY:
        listed = {p for p in str(window.context.get(NO_COST_KEY, "")).split(",") if p}
        if player_id in listed:
            return True
    return rules_hooks.permits(
        rules_hooks.POINT_STRATEGY_SECONDARY_FREE, state, player_id,
        {"initiative": initiative, "owner": state.active_player_id},
    )


def _no_cost_source(state: GameState, player_id: str, initiative: int) -> str:
    """Komponent (``"<kategoria>:<id>"``), który zwalnia gracza z żetonu — do opisu w UI."""
    ctx = {"initiative": initiative, "owner": state.active_player_id}
    for hook in rules_hooks.hooks_at(
        rules_hooks.POINT_STRATEGY_SECONDARY_FREE, state, player_id
    ):
        if hook.kind is rules_hooks.HookKind.PERMIT and hook.fn(state, player_id, ctx):
            return hook.covers or ""
    return ""


def _encode_why(why: dict[str, str]) -> str:
    return ";".join(f"{pid}={src}" for pid, src in why.items() if src)


def _decode_why(raw: object) -> dict[str, str]:
    pairs = (item.split("=", 1) for item in str(raw or "").split(";") if "=" in item)
    return {pid: src for pid, src in pairs}


def _no_cost_context(state: GameState, queue: list[str], initiative: int) -> dict[str, str]:
    """Wpisy ``no_cost`` (+ źródło ``no_cost_why``) kontekstu okna — tylko gdy ktoś
    rozstrzyga secondary bez żetonu. Źródło pozwala UI napisać, CZEMU follow jest darmowy."""
    listed = [p for p in queue if secondary_without_token(state, p, initiative)]
    if not listed:
        return {}
    why = {p: _no_cost_source(state, p, initiative) for p in listed}
    return {NO_COST_KEY: ",".join(listed), NO_COST_WHY_KEY: _encode_why(why)}


def grant_no_cost(state: GameState, player_id: str, source: str = "") -> None:
    """Dopisuje gracza do darmowych secondary bieżącego okna (MUTUJE; Acquiescence).

    ``source`` (``"<kategoria>:<id>"``) trafia do ``no_cost_why`` — opis w oknie follow.
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        raise ValueError("No strategy card secondary is being resolved right now.")
    listed = [p for p in str(window.context.get(NO_COST_KEY, "")).split(",") if p]
    if player_id not in listed:
        listed.append(player_id)
    why = _decode_why(window.context.get(NO_COST_WHY_KEY))
    if source:
        why[player_id] = source
    window.context = {
        **window.context,
        NO_COST_KEY: ",".join(listed),
        NO_COST_WHY_KEY: _encode_why(why),
    }


def _free_players(context: dict[str, str | int]) -> set[str]:
    """Gracze z darmowym, obowiązkowym secondary (z kontekstu okna)."""
    raw = str(context.get(_FREE_KEY, ""))
    return {p for p in raw.split(",") if p}


def _finish_primary(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    initiative: int,
    draft: Draft,
    *,
    open_secondary: bool = True,
    secondary_players: list[str] | None = None,
) -> GameState:
    """Stosuje efekt primary (na klonie ``state``) i otwiera okno secondary.

    ``state`` MUSI być już klonem (mutowany w miejscu). Gdy NIE MA kogo pytać (gra solo /
    pozostali poza stołem), okna nie otwieramy — puste okno zostawałoby ustawione i
    blokowało End turn na stałe. ``open_secondary=False`` (Overrule): wykonujemy samo primary,
    bez okna secondary dla pozostałych graczy.
    """
    spec = _spec(initiative)
    action_ctx = {"player": owner_id, "initiative": initiative, "ability": "primary"}
    triggers.fire(state, GameEvent.STRATEGIC_ACTION, Moment.WHEN, subject=owner_id, ctx=action_ctx)
    if spec.primary is not None:
        spec.primary(state, ctx, owner_id, draft)
    # Oferty „after primary” (Peace Accords) nie otwierają własnego okna: czekają w oknie
    # secondary, a bez secondary dostają okno REACTION (RULES.md 62.9).
    after = triggers.fire(
        state, GameEvent.STRATEGIC_ACTION, Moment.AFTER, subject=owner_id, ctx=action_ctx,
        open_window=False,
    )
    state.pending_strategy = None
    if not open_secondary:
        triggers.open_offers_window(state, after, GameEvent.STRATEGIC_ACTION, Moment.AFTER)
        return state

    queue = timing.build_response_queue(state, owner_id)
    chosen_free = set(draft.get("free_players", []))
    if secondary_players is not None:
        # Bohater Winnu: secondary dla wskazanych bohaterem ORAZ dla wskazanych primary Trade
        # (ci MUSZĄ je rozstrzygnąć — F_winnu/mathis-mathinus-imperial-seal/2).
        queue = [p for p in queue if p in secondary_players or p in chosen_free]
    if not queue:
        triggers.open_offers_window(state, after, GameEvent.STRATEGIC_ACTION, Moment.AFTER)
        return state
    free = [p for p in queue if p in chosen_free]
    opened = timing.open_window(
        state,
        WindowType.STRATEGY_SECONDARY,
        queue,
        context={
            "initiative": initiative,
            _FREE_KEY: ",".join(free),
            # Czy follow kosztuje żeton (UI pokazuje koszt / blokuje Follow bez żetonu).
            "cost": 1 if spec.secondary_costs_token else 0,
            # Kto rozstrzyga secondary bez żetonu (Masters of Trade) - UI nie żąda żetonu.
            **_no_cost_context(state, queue, initiative),
            **({HERO_KEY: 1} if secondary_players is not None else {}),
        },
    )
    return _auto_resolve_free(opened, ctx)


def _auto_resolve_free(state: GameState, ctx: CardContext) -> GameState:
    """Rozstrzyga AUTOMATYCZNIE secondary graczy „free" (Trade), gdy przychodzi ich kolej.

    Wskazany gracz MUSI wykonać secondary (R_trade) i nie ma w nim żadnego wyboru (uzupełnienie
    commodities), więc nie pytamy go oknem - efekt stosujemy w jego kolejce (kolejność od
    lewej aktywnego zostaje zachowana). Zatrzymuje się na pierwszym nie-„free" respondencie.
    """
    current = state
    while True:
        window = current.pending_window
        if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
            return current
        responder = window.current_responder
        if responder is None or responder not in _free_players(window.context):
            return current
        spec = _spec(int(window.context.get("initiative", 0)))
        current = current.clone()
        if spec.secondary is not None:
            spec.secondary(current, ctx, responder, {})
        current = _advance_window(current, responder)


def play_strategy_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
    *,
    grid: HexGrid | None = None,
) -> GameState:
    """Akcja strategiczna: start rozstrzygania PRIMARY (RULES.md 30.1, 30.3, 30.5).

    Walidacja (silnik-sędzia): gracz istnieje i posiada kartę; faza ACTION; to jego tura;
    nie spasował; nie wykonał innej akcji w tej turze; karta nie jest wyczerpana; nie trwa
    okno ani wieloetapowe primary. Następnie karta jest oznaczana jako zagrana, a akcja
    tury jako wykonana. Karta z krokami ustawia ``pending_strategy`` (czeka na wybory);
    karta bez kroków stosuje primary od razu i otwiera okno secondary.

    Raises:
        ValueError: Gdy któryś warunek legalności nie jest spełniony.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    player = state.players[player_id]
    if initiative not in player.strategy_cards:
        raise ValueError(f"Player does not hold the initiative card {initiative}.")
    # SĘDZIA tury (RULES.md 30.3, R_action_phase): akcja strategiczna to JEDNA z akcji tury.
    if state.phase is not Phase.ACTION:
        raise ValueError("A strategic action can only be performed during the action phase.")
    if state.active_player_id != player_id:
        raise ValueError(f"It is not {player_id}'s turn (active: {state.active_player_id}).")
    if player.passed:
        raise ValueError("You have passed - you cannot perform a strategic action.")
    action_budget.require_free_action(state, player_id)
    if initiative in player.exhausted_strategy_cards:
        raise ValueError(f"Strategy card {initiative} was already played this round.")
    if (
        state.pending_window is not None
        or state.pending_strategy is not None
        or state.held_play is not None
    ):
        raise ValueError(
            "Another timing window is already open - resolve it before the strategic action."
        )

    new_state = state.clone()
    # Oznacz kartę jako zagraną (idempotentnie) + akcja strategiczna = akcja tury
    # (RULES.md 31.7: End turn przestaje być zablokowany „brakiem akcji").
    exhaust.exhaust_strategy_card(new_state, player_id, initiative)
    action_budget.register_action(new_state, player_id, strategic=True)

    spec = _spec(initiative)
    if spec.primary_steps:
        new_state.pending_strategy = StrategyResolution(
            initiative=initiative,
            owner_id=player_id,
            step=spec.primary_steps[0],
        )
        return new_state
    return _finish_primary(new_state, CardContext(registry, grid), player_id, initiative, {})


def submit_primary_step(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    payload: dict[str, Any],
    *,
    grid: HexGrid | None = None,
) -> GameState:
    """Przesyła wybór dla bieżącego kroku primary (tylko właściciel karty).

    Waliduje payload (dispatch karty), dopisuje go do szkicu i przechodzi do kolejnego
    kroku (liniowo wg ``primary_steps`` albo wg ``next_step`` karty); po ostatnim kroku
    stosuje primary i otwiera okno secondary.

    Raises:
        ValueError: Brak rozstrzygania primary, to nie właściciel, albo zły payload.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    pending = state.pending_strategy
    if pending is None:
        raise ValueError("No strategy card primary is awaiting a choice.")
    if player_id != pending.owner_id:
        raise ValueError(
            f"Only {pending.owner_id} can resolve this primary ability, not {player_id}."
        )
    spec = _spec(pending.initiative)
    if spec.on_step is None:
        raise ValueError("This card has no interactive primary steps.")

    ctx = CardContext(registry, grid)
    new_state = state.clone()
    assert new_state.pending_strategy is not None  # zachowane przez clone
    current = new_state.pending_strategy
    spec.on_step(new_state, ctx, player_id, current.step, current.draft, payload)

    if spec.next_step is not None:
        following = spec.next_step(current.step, current.draft)
    else:
        index = spec.primary_steps.index(current.step)
        following = spec.primary_steps[index + 1] if index + 1 < len(spec.primary_steps) else None
    if following is not None:
        current.step = following
        return new_state
    return _finish_primary(
        new_state,
        ctx,
        player_id,
        current.initiative,
        current.draft,
        open_secondary=not current.no_secondary,
        secondary_players=current.secondary_players,
    )


def begin_hero_primary(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
    secondary_players: list[str],
    *,
    grid: HexGrid | None = None,
) -> None:
    """Mathis Mathinus: PRIMARY dowolnej karty, potem secondary tylko dla wskazanych graczy.

    Mutuje ``state`` (klon roboczy). Karta strategii nie jest wyczerpywana (gracz jej nie ma).
    Wskazani płacą żeton jak zwykle (F_winnu). Karta z krokami ustawia ``pending_strategy``
    i kończy się w ``submit_primary_step``.
    """
    spec = _spec(initiative)
    if spec.primary_steps:
        state.pending_strategy = StrategyResolution(
            initiative=initiative,
            owner_id=player_id,
            step=spec.primary_steps[0],
            secondary_players=list(secondary_players),
        )
        return
    _finish_primary(
        state, CardContext(registry, grid), player_id, initiative, {}, open_secondary=False
    )
    queue = [
        p for p in timing.build_response_queue(state, player_id) if p in secondary_players
    ]
    if not queue:
        return
    opened = timing.open_window(
        state,
        WindowType.STRATEGY_SECONDARY,
        queue,
        context={
            "initiative": initiative,
            _FREE_KEY: "",
            "cost": 1 if spec.secondary_costs_token else 0,
            **_no_cost_context(state, queue, initiative),
            HERO_KEY: 1,
        },
    )
    state.pending_window = opened.pending_window


def begin_overrule_primary(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
    *,
    grid: HexGrid | None = None,
) -> None:
    """Overrule: gracz wykonuje PRIMARY karty ``initiative`` jako część akcji z karty akcji.

    Mutuje ``state`` (klon roboczy wołającego). NIE wyczerpuje karty strategii, NIE liczy
    akcji tury (akcją jest zagranie karty akcji) i NIE otwiera okna secondary. Karta z krokami
    ustawia ``pending_strategy`` z ``no_secondary`` (gracz dalej używa ``submit_primary_step``);
    karta bez kroków stosuje primary od razu.
    """
    spec = _spec(initiative)
    if spec.primary_steps:
        state.pending_strategy = StrategyResolution(
            initiative=initiative,
            owner_id=player_id,
            step=spec.primary_steps[0],
            no_secondary=True,
        )
        return
    _finish_primary(
        state, CardContext(registry, grid), player_id, initiative, {}, open_secondary=False
    )


def begin_strategize_secondary(
    state: GameState,
    player_id: str,
    initiative: int,
    *,
    then: list[int] | None = None,
    from_reinforcements: bool = False,
) -> None:
    """Strategize: gracz wykonuje SECONDARY karty ``initiative`` (jego własna odpowiedź).

    Mutuje ``state`` (klon roboczy). Otwiera okno ``STRATEGY_SECONDARY`` z kolejką z jednym
    respondentem - zagrywającym; dalej idzie zwykły ``resolve_secondary`` (koszt żetonu
    ze strategy pool poza Leadership, payload wyborów, produkcja Warfare).

    ``then`` = kolejne karty łańcucha (Perfect Synthesis: wybrane z góry, każda po zamknięciu
    poprzedniego okna); ``from_reinforcements`` = żeton z rezerwy zamiast z puli strategicznej.
    """
    spec = _spec(initiative)
    context: dict[str, str | int] = {
        "initiative": initiative,
        _FREE_KEY: "",
        "cost": 1 if spec.secondary_costs_token else 0,
    }
    if then:
        context[CHAIN_KEY] = ",".join(str(i) for i in then)
    if from_reinforcements:
        context[TOKEN_FROM_KEY] = FROM_REINFORCEMENTS
    opened = timing.open_window(state, WindowType.STRATEGY_SECONDARY, [player_id], context=context)
    state.pending_window = opened.pending_window


def _spend_reinforcement_token(state: GameState, player_id: str, pool: object) -> None:
    """Żeton „z rezerwy zamiast z puli strategicznej” (Perfect Synthesis): wydany żeton wraca do
    rezerwy - liczniki bez zmian, bez zdarzenia „wydano żeton z puli strategicznej” (Alliance
    Muaat nie daje TG - F_naaz_rokha hesh 6). Pusta rezerwa: żeton z wybranej puli arkusza (5)."""
    if state.players[player_id].cc_reinf >= 1:
        return
    if pool not in SHEET_POOLS:
        raise ValueError(
            "You have no command token in your reinforcements - choose a pool on your command "
            "sheet to spend a token from."
        )
    command_tokens.spend_to_reinforcements(state, player_id, str(pool))


def resolve_secondary(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    execute: bool,
    payload: dict[str, Any] | None = None,
    grid: HexGrid | None = None,
) -> GameState:
    """Rozstrzyga odpowiedź bieżącego respondenta w oknie secondary (RULES.md 30.1, 30.5).

    ``execute=True`` („follow") → opłata żetonem ze strategy pool (jeśli karta tego wymaga
    i gracz nie jest „free"), potem efekt secondary z wyborami z ``payload`` (planety do
    wydania, rozkład żetonów...). ``execute=False`` → PAS. Gracz „free" NIE może spasować
    (secondary Trade jest dla niego obowiązkowe). Kolejka okna przesuwa się o jeden; po
    dopełnieniu okno zamyka się automatycznie.

    Raises:
        ValueError: Brak okna secondary, zły respondent, brak żetonu w strategy pool, zły
            payload albo próba pasu przez gracza z obowiązkowym secondary. Stan bez zmian.
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        raise ValueError("No open strategy card secondary window.")
    expected = window.current_responder
    if expected is not None and player_id != expected:
        raise ValueError(
            f"It is now {expected}'s turn to respond, not {player_id} (out-of-order response)."
        )

    if window.context.get(_AWAIT_PRODUCTION_KEY):
        raise ValueError("Finish the production first (use 'Finish production').")
    initiative = int(window.context.get("initiative", 0))
    spec = _spec(initiative)
    is_free = player_id in _free_players(window.context)
    no_cost = secondary_without_token(state, player_id, initiative)

    new_state = state.clone()
    if execute:
        if (
            spec.secondary_costs_token and not is_free and not no_cost
            and window.context.get(TOKEN_FROM_KEY) == FROM_REINFORCEMENTS
        ):
            _spend_reinforcement_token(new_state, player_id, (payload or {}).get("token_pool"))
        elif spec.secondary_costs_token and not is_free and not no_cost:
            # Scepter of Emelpar (C_relics): gracz MOŻE wyczerpać relikt i wydać żeton z rezerwy.
            scepter = bool((payload or {}).get("scepter"))
            # STRATEGY_TOKEN_SPENT emituje sam ``spend_strategy_token`` (punkt centralny).
            command_tokens.spend_strategy_token(
                new_state,
                player_id,
                source=command_tokens.SOURCE_SCEPTER if scepter else command_tokens.SOURCE_POOL,
            )
        secondary_ctx = {"player": player_id, "initiative": initiative, "ability": "secondary"}
        triggers.fire(
            new_state, GameEvent.STRATEGIC_ACTION, Moment.WHEN, subject=player_id, ctx=secondary_ctx
        )
        if spec.secondary is not None:
            spec.secondary(new_state, CardContext(registry, grid), player_id, payload or {})
        triggers.fire(
            new_state,
            GameEvent.STRATEGIC_ACTION,
            Moment.AFTER,
            subject=player_id,
            ctx=secondary_ctx,
        )
    elif is_free:
        raise ValueError("The active player chose you - you must resolve this secondary ability.")

    grant = new_state.production_grant
    if execute and grant is not None and grant.standalone and grant.player_id == player_id:
        # Secondary otworzyło produkcję (Warfare TE): kolejka czeka na jej zakończenie.
        assert new_state.pending_window is not None
        new_state.pending_window.context = {
            **new_state.pending_window.context,
            _AWAIT_PRODUCTION_KEY: player_id,
        }
        return new_state

    return _auto_resolve_free(_advance_window(new_state, player_id), CardContext(registry, grid))


def _advance_window(state: GameState, player_id: str) -> GameState:
    """Przesuwa kolejkę okna secondary (waliduje respondenta) i zamyka je po dopełnieniu.

    Łańcuch Perfect Synthesis (``CHAIN_KEY``): po zamknięciu okna otwiera się secondary następnej
    karty dla tego samego gracza."""
    window = state.pending_window
    context = dict(window.context) if window is not None else {}
    new_state = timing.respond_current(state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        chain = [int(i) for i in str(context.get(CHAIN_KEY, "")).split(",") if i]
        if chain and new_state.pending_window is None:
            begin_strategize_secondary(
                new_state, player_id, chain[0], then=chain[1:],
                from_reinforcements=context.get(TOKEN_FROM_KEY) == FROM_REINFORCEMENTS,
            )
    return new_state


def after_standalone_production(state: GameState) -> GameState:
    """Wznawia kartę strategii po zakończeniu produkcji standalone (grant zniknął).

    Wołane z warstwy API po ``production.skip_grant`` („Finish production"). Jeśli trwała
    produkcja z primary (Construction, krok ``production``) - przechodzi do kroku
    ``resume_step`` ze szkicu. Jeśli trwała produkcja z secondary (Warfare TE) - kończy
    odpowiedź respondenta i przesuwa kolejkę okna. W innych przypadkach nic nie robi.
    """
    grant = state.production_grant
    if grant is not None and grant.standalone:
        return state  # produkcja wciąż trwa
    pending = state.pending_strategy
    if pending is not None and pending.step == "production":
        new_state = state.clone()
        assert new_state.pending_strategy is not None
        resumed = new_state.pending_strategy
        resumed.step = str(resumed.draft.pop("resume_step", resumed.step))
        return new_state
    window = state.pending_window
    if (
        window is not None
        and window.window_type is WindowType.STRATEGY_SECONDARY
        and window.context.get(_AWAIT_PRODUCTION_KEY)
    ):
        responder = str(window.context[_AWAIT_PRODUCTION_KEY])
        new_state = state.clone()
        assert new_state.pending_window is not None
        context = dict(new_state.pending_window.context)
        context.pop(_AWAIT_PRODUCTION_KEY, None)
        new_state.pending_window.context = context
        return _advance_window(new_state, responder)
    return state


def resume_after_limit_window(state: GameState) -> GameState:
    """Po zamknięciu okna limitu (FLEET_POOL / CAPACITY) wznawia secondary czekające na produkcję.

    Okno limitu otwiera się NAD oknem secondary (``suspended_window``, RULES.md 42.1), więc
    „Finish production” w trakcie usuwania nadwyżki nie widzi okna secondary. Po powrocie okna
    secondary z ``await_production`` i bez grantu respondent kończy odpowiedź (inaczej gra staje).
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        return state
    return after_standalone_production(state)


def step_options(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    grid: HexGrid | None = None,
) -> dict[str, Any] | None:
    """Dozwolone wybory dla UI gracza, który TERAZ musi odpowiedzieć (lub None).

    Zwraca opis bieżącego monitu: ``kind`` = ``primary`` (właściciel karty, krok z
    ``pending_strategy``) albo ``secondary`` (bieżący respondent okna), ``initiative``,
    ``step`` oraz ``options`` z modułu karty. Dane prywatne (np. podgląd agendy) karta
    zwraca wyłącznie dla ``player_id`` właściciela monitu — nigdy dla innych graczy.
    """
    ctx = CardContext(registry, grid)
    pending = state.pending_strategy
    if pending is not None and pending.owner_id == player_id:
        spec = _spec(pending.initiative)
        options = (
            spec.options(state, ctx, player_id, pending.step, pending.draft)
            if spec.options is not None
            else {}
        )
        return {
            "kind": "primary",
            "initiative": pending.initiative,
            "step": pending.step,
            "draft": dict(pending.draft),
            "options": options,
        }
    window = state.pending_window
    if (
        window is not None
        and window.window_type is WindowType.STRATEGY_SECONDARY
        and window.current_responder == player_id
    ):
        initiative = int(window.context.get("initiative", 0))
        spec = _spec(initiative)
        options = spec.options(state, ctx, player_id, None, {}) if spec.options is not None else {}
        return {
            "kind": "secondary",
            "initiative": initiative,
            "step": None,
            "draft": {},
            "options": options,
        }
    return None

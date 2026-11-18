"""Cele (objectives): setup talii, odkrywanie, punktowanie, punkty zwycięstwa (RULES.md 41).

Czyste funkcje nad ``GameState`` (``state -> state``). Źródło reguł: ``R_objective_cards``,
``R_victory_points``, ``R_status_phase`` (lokalny zrzut tirules2.com). Dane kart (nazwa,
punkty, faza) wyłącznie z katalogu komponentów (``registry.catalog``) — zero hardkodowania.

Zakres: przygotowanie celów w setupie (5 celów I etapu + 5 celów II etapu, dwa cele I etapu
odkryte), odkrycie kolejnego celu przez mówcę, zdobycie celu publicznego/tajnego z kontrolą
podstawowych wymagań (limity na fazę, kontrola planet w systemie domowym). SPRAWDZANIE
treści karty („kontroluj 4 planety o tej samej cesze") NIE jest tu modelowane — operator
potwierdza spełnienie wymagań (⚠️ ZAŁOŻENIE, RULES.md 41.4).
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from src.core import card_draw, secret_objectives, triggers, variants
from src.core.components import ComponentCategory, DeckDef, ObjectiveDef
from src.core.dice import next_rng
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, ObjectivesState
from src.core.hex_grid import HexGrid
from src.core.objective_payment import ObjectivePayment, pay_for_objective
from src.core.objective_progress import evaluate
from src.core.registry import StaticDataRegistry
from src.core.sources import AGENDA_STANDARD

# R_objective_cards: „Each game contains five stage I and five stage II public objective
# cards"; mówca odkrywa dwa cele I etapu w setupie.
PUBLIC_OBJECTIVES_PER_STAGE = 5
REVEALED_AT_SETUP = 2
# Setup: każdy gracz dobiera 2 tajne cele, zatrzymuje 1 (RULES.md 45).
SECRET_CANDIDATES = 2

# Typy talii w katalogu (``DeckDef.deck_type``).
_STAGE1_DECK = "public_stage_1_objective"
_STAGE2_DECK = "public_stage_2_objective"
_SECRET_DECK = "secret_objective"
_ACTION_DECK = "action_card"

# Faza punktowania zapisana w danych kart (``ObjectiveDef.phase``).
STATUS_PHASE_LABEL = "Status"


def game_variant_modules(state: GameState) -> list[variants.VariantModule]:
    """Moduły wariantów gry (``decks.variants`` + zgodność wstecz ``decks.agenda_variant``)."""
    return variants.game_modules(state.decks.variants, state.decks.agenda_variant)


def deck_card_ids(
    registry: StaticDataRegistry, deck_type: str, state: GameState | None = None
) -> list[str]:
    """Identyfikatory kart talii danego typu (np. pełna talia PoK/TE).

    Bez ``state``: NAJWIĘKSZA talia aktywnych źródeł. Katalog zawiera talie per źródło
    (base, pok, thunders_edge); kumulatywne są te większe (np. ``action_cards_te`` =
    base+pok+codexy+TE). Remis rozmiaru rozstrzyga PRIORYTET ŹRÓDŁA talii (RULES.md 14:
    nowsze rozszerzenie wygrywa), potem alias - ``agendas_pok`` i ``agendas_base_game``
    mają po 50 kart, remis nie może wybrać przestarzałej talii base.

    Ze ``state``: skład talii W TEJ GRZE - moduły wariantów (``core/variants``) mogą
    zastąpić całą talię albo podmienić pojedyncze karty (erraty).
    """
    if state is None:
        return variants.official_deck_ids(registry, deck_type)
    return variants.game_deck_ids(registry, deck_type, game_variant_modules(state))


def agenda_deck_ids(registry: StaticDataRegistry, variant: str = AGENDA_STANDARD) -> list[str]:
    """Karty talii agend dla starego pola ``agenda_variant`` (``standard`` albo np. ``absol``).

    Nieznany wariant albo brak talii -> ``ValueError``. Nowy kod: ``deck_card_ids(..., state)``.
    """
    module = variants.module_for_agenda_variant(variant)
    return variants.game_deck_ids(registry, "agenda", [module] if module else [])


def _in_any_deck(registry: StaticDataRegistry, deck_type: str, card_id: str) -> bool:
    """Czy karta należy do talii typu ``deck_type`` - oficjalnej albo któregoś modułu."""
    if card_id in variants.official_deck_ids(registry, deck_type):
        return True
    decks = registry.catalog.all(ComponentCategory.DECK)
    return any(
        isinstance(deck, DeckDef) and deck.deck_type == deck_type and card_id in deck.card_ids
        for deck in decks.values()
    ) or any(
        card_id in found
        for found in variants.replacement_map(
            registry, deck_type, variants.modules().values()
        ).values()
    )


def objective_def(
    registry: StaticDataRegistry, objective_id: str
) -> ObjectiveDef | None:
    """Definicja celu (publicznego albo tajnego) z katalogu lub ``None``."""
    for category in (ComponentCategory.PUBLIC_OBJECTIVE, ComponentCategory.SECRET_OBJECTIVE):
        found = registry.catalog.get(category, objective_id)
        if isinstance(found, ObjectiveDef):
            return found
    return None


def objective_stage(registry: StaticDataRegistry, objective_id: str) -> int | None:
    """Etap celu publicznego (1 albo 2) wg talii, do której należy; ``None`` gdy to nie cel."""
    if _in_any_deck(registry, _STAGE1_DECK, objective_id):
        return 1
    if _in_any_deck(registry, _STAGE2_DECK, objective_id):
        return 2
    return None


def setup_objectives(
    state: GameState,
    registry: StaticDataRegistry,
    rng: random.Random | None = None,
    *,
    interactive: bool = False,
) -> GameState:
    """Przygotowanie celów i talii w setupie (R_objective_cards).

    - losuje po 5 celów publicznych I i II etapu (kolejność = kolejność odkrywania),
    - tasuje talię tajnych celów,
    - tasuje talię kart akcji (gracze dobiorą pierwsze karty w pierwszej fazie statusu).

    Tryb domyślny (``interactive=False``, testy/skrót): mówca od razu odkrywa dwa cele I
    etapu, a każdy gracz dostaje JEDEN tajny cel. Tryb ``interactive=True`` (``/game/new``,
    RULES.md 45): wszystkie 5+5 celów zostaje ZAKRYTE (odkrywa je mówca kliknięciem), a każdy
    gracz dostaje DWA kandydujące tajne cele (``private.secret_candidates``) do wyboru.

    Wołane raz, po rozstawieniu graczy w ``/game/new``. Seedowalne przez ``rng``.
    """
    chooser = rng if rng is not None else random.Random()
    new_state = state.clone()

    stage1 = deck_card_ids(registry, _STAGE1_DECK, new_state)
    stage2 = deck_card_ids(registry, _STAGE2_DECK, new_state)
    count1 = min(PUBLIC_OBJECTIVES_PER_STAGE, len(stage1))
    count2 = min(PUBLIC_OBJECTIVES_PER_STAGE, len(stage2))
    drawn1 = chooser.sample(stage1, count1)
    drawn2 = chooser.sample(stage2, count2)
    reveal_count = 0 if interactive else min(REVEALED_AT_SETUP, len(drawn1))
    new_state.objectives = ObjectivesState(
        stage1_deck=drawn1[reveal_count:],
        stage2_deck=drawn2,
        revealed=drawn1[:reveal_count],
        # „Inne punkty": żeton Custodians (+1 VP) jest na stole od początku gry.
        custom_points={"custodians": 1},
    )

    secrets_deck = deck_card_ids(registry, _SECRET_DECK, new_state)
    chooser.shuffle(secrets_deck)
    secret_objectives.seed_deck(new_state, secrets_deck)
    for player_id in new_state.players:
        if not new_state.decks.secret_objective_deck:
            break
        if interactive:
            secret_objectives.deal_candidates(new_state, player_id, SECRET_CANDIDATES)
        else:
            secret_objectives.deal_one_to_hand(new_state, player_id)

    actions = deck_card_ids(registry, _ACTION_DECK, new_state)
    chooser.shuffle(actions)
    card_draw.seed_action_deck(new_state, actions)
    return new_state


def reveal_next_public(state: GameState) -> tuple[GameState, str | None]:
    """Mówca odkrywa następny cel publiczny; zwraca (nowy stan, id lub ``None``).

    Cele II etapu dopiero po odkryciu WSZYSTKICH celów I etapu (R_status_phase, krok 2).
    ``None`` = brak zakrytych celów → wołający kończy grę (R_objective_cards).
    """
    new_state = state.clone()
    objectives = new_state.objectives
    if objectives.stage1_deck:
        revealed_id = objectives.stage1_deck.pop(0)
    elif objectives.stage2_deck:
        revealed_id = objectives.stage2_deck.pop(0)
    else:
        return new_state, None
    objectives.revealed.append(revealed_id)
    # „When a public objective is revealed" (Neuraloop): hooki reagują na jawny cel.
    triggers.fire(
        new_state, GameEvent.OBJECTIVE_REVEALED, Moment.AFTER,
        ctx={"objective": revealed_id},
    )
    return new_state, revealed_id


def reveal_from_stage(state: GameState, stage: int) -> str | None:
    """Odkrywa wierzchni cel z talii etapu ``stage`` (MUTUJE; Incentive Program - RULES.md 51.6).

    W odróżnieniu od ``reveal_next_public`` etap wskazuje efekt karty, nie kolejność statusu.
    ``None`` = talia etapu pusta (nic się nie dzieje).
    """
    deck = state.objectives.stage1_deck if stage == 1 else state.objectives.stage2_deck
    if not deck:
        return None
    revealed_id = deck.pop(0)
    state.objectives.revealed.append(revealed_id)
    triggers.fire(
        state, GameEvent.OBJECTIVE_REVEALED, Moment.AFTER, ctx={"objective": revealed_id}
    )
    return revealed_id


def make_secret_public(state: GameState, objective_id: str) -> None:
    """Zdobyty tajny cel staje się celem publicznym (Classified Document Leaks, C_agendas).

    Pierwotny właściciel zachowuje punkt, nie może zdobyć celu ponownie (zapisany jako zdobywca
    celu publicznego) i cel przestaje liczyć się do jego limitu tajnych celów.
    """
    owner = next(
        (pid for pid, p in state.players.items() if objective_id in p.scored_secrets), None
    )
    if owner is None:
        raise ValueError(f"{objective_id} is not a scored secret objective.")
    from src.core import secret_objectives  # lokalnie: secret_objectives importuje ten moduł

    secret_objectives.release_scored(state, owner, objective_id)
    if objective_id not in state.objectives.revealed:
        state.objectives.revealed.append(objective_id)
    if not has_scored_public(state, owner, objective_id):
        record_public_score(state, owner, objective_id)
    triggers.fire(
        state, GameEvent.OBJECTIVE_REVEALED, Moment.AFTER, ctx={"objective": objective_id}
    )


RETIRED_KEY = "objectives:retired"  # efekt gry: cel w grze, ale nie do zdobycia


def retire(state: GameState, objective_id: str) -> None:
    """Cel publiczny zostaje w grze, ale nikt nie może go już zdobyć (MUTUJE ``state``).

    C_agendas (Classified Document Leaks): po odrzuceniu prawa wybrany tajny cel nie wraca do
    właściciela i „is no longer scorable as a public objective. It remains in play”.
    """
    from src.core import active_effects  # lokalnie: unika cyklu importów
    from src.core.game_events import Duration

    if not is_retired(state, objective_id):
        active_effects.add_effect(
            state, RETIRED_KEY, Duration.GAME, data={"objective": objective_id}
        )


def is_retired(state: GameState, objective_id: str) -> bool:
    """Czy odkryty cel jest wyłączony z punktowania (``retire``)."""
    return any(
        e.key == RETIRED_KEY and e.data.get("objective") == objective_id
        for e in state.active_effects
    )


def replace_revealed(state: GameState, registry: StaticDataRegistry, old_id: str) -> str | None:
    """Odrzuca odkryty cel publiczny i zastępuje go LOSOWYM celem z dowolnej talii celów.

    Neuraloop: nowy cel (nawet tajny) staje się jawnym celem publicznym na miejscu starego;
    odrzucony wraca do swojej talii DOPIERO po odkryciu zastępnika, a talia jest tasowana
    (C_relics). Zwraca id nowego celu albo ``None`` (brak kart do losowania). MUTUJE ``state``.
    """
    objectives = state.objectives
    decks = state.decks
    pool = [*objectives.stage1_deck, *objectives.stage2_deck, *decks.secret_objective_deck]
    if old_id not in objectives.revealed or not pool:
        return None
    rng = next_rng(state)
    new_id = rng.choice(pool)
    for deck in (objectives.stage1_deck, objectives.stage2_deck):
        if new_id in deck:
            deck.remove(new_id)
            break
    else:
        secret_objectives.remove_from_deck(state, new_id)
    objectives.revealed[objectives.revealed.index(old_id)] = new_id
    stage = objective_stage(registry, old_id)
    if stage is None:
        secret_objectives.return_to_deck(state, old_id)
    else:
        back = objectives.stage1_deck if stage == 1 else objectives.stage2_deck
        back.append(old_id)
        rng.shuffle(back)
    return new_id


def planet_owners(state: GameState) -> dict[str, str]:
    """Mapa ``planeta -> właściciel`` ze wszystkich systemów (źródło prawdy o kontroli)."""
    owners: dict[str, str] = {}
    for system in state.systems.values():
        owners.update(system.planet_owners)
    return owners


def controls_home_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> bool:
    """Czy gracz kontroluje KAŻDĄ planetę swojego systemu domowego (R_status_phase, Notes).

    Brak frakcji albo planet domowych w danych → brak wymagań (``True``). Stacje kosmiczne
    nie są planetami dla celów (R_space_stations), więc nie występują w ``home_planets``.
    """
    player = state.players.get(player_id)
    if player is None or player.faction is None:
        return True
    faction = registry.factions.get(player.faction)
    if faction is None or not faction.home_planets:
        return True
    owners = planet_owners(state)
    return all(owners.get(planet) == player_id for planet in faction.home_planets)


# Źródła VP spoza kart celów (klucze rejestru ``ObjectivesState.point_sources``).
SOURCE_CUSTODIANS = "custodians"
SOURCE_IMPERIAL = "strategy_cards:imperial"
SOURCE_SFTT = "promissory_notes:sftt"
# Punkty, które gracz może jeszcze stracić (tekst karty: „when you lose this card, lose 1
# victory point" - Shard of the Throne, Styx; SftT wraca do właściciela z utratą VP; Political
# Censure - utrata karty kosztuje 1 VP, C_agendas).
LOSABLE_POINT_SOURCES = frozenset(
    {"relics:shard", "planets:styx", SOURCE_SFTT, "agendas:censure"}
)


def award_points(
    state: GameState, player_id: str, points: int, *, source: str | None = None
) -> None:
    """Dodaje punkty zwycięstwa graczowi (mutuje stan) i ustala zwycięzcę po progu.

    R_victory_points: gra kończy się natychmiast, gdy gracz ma ``vps_to_win`` punktów.
    Pierwszy, który przekroczy próg, wygrywa (punktowanie idzie po jednym graczu naraz).
    ``source`` = skąd punkt spoza kart celów (relikt, agenda, planeta, notka...): zapis w
    rejestrze ``point_sources`` dla panelu punktów. Cele publiczne/tajne mają własny zapis.
    """
    player = state.players[player_id]
    player.victory_points += points
    if source is not None:
        ledger = state.objectives.point_sources.setdefault(source, {})
        net = ledger.get(player_id, 0) + points
        if net:
            ledger[player_id] = net
        else:
            ledger.pop(player_id, None)
    if state.winner_id is None and player.victory_points >= state.vps_to_win:
        state.winner_id = player_id
        state.end_reason = "victory_points"


def record_public_score(state: GameState, player_id: str, objective_id: str) -> None:
    """Zapisuje zdobycie celu publicznego (kto), bez zmiany punktów (mutuje stan)."""
    scorers = state.objectives.scored.setdefault(objective_id, [])
    scorers.append(player_id)


def has_scored_public(state: GameState, player_id: str, objective_id: str) -> bool:
    """Czy gracz już zdobył dany cel publiczny (każdy cel tylko raz na grę)."""
    return player_id in state.objectives.scored.get(objective_id, [])


def scoreable_public_objectives(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    *,
    ignore_phase: bool = False,
) -> list[str]:
    """Odkryte cele publiczne, które gracz MOŻE teraz zdobyć (spełnia wymagania karty).

    ``ignore_phase=True`` pomija warunek „cel fazy statusu" - dla primary Imperial, które
    pozwala zdobyć cel publiczny natychmiast, poza fazą statusu (R_imperial).
    """
    if not controls_home_planets(state, registry, player_id):
        return []
    result: list[str] = []
    for objective_id in state.objectives.revealed:
        definition = objective_def(registry, objective_id)
        if definition is None or (not ignore_phase and definition.phase != STATUS_PHASE_LABEL):
            continue
        if has_scored_public(state, player_id, objective_id) or is_retired(state, objective_id):
            continue
        if not evaluate(state, registry, grid, player_id, objective_id)[2]:
            continue
        result.append(objective_id)
    return result


def scoreable_secret_objectives(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid, player_id: str
) -> list[str]:
    """Tajne cele z ręki gracza, które może teraz zdobyć w fazie statusu."""
    player = state.players.get(player_id)
    if player is None:
        return []
    result: list[str] = []
    for objective_id in player.private.secret_objectives:
        definition = objective_def(registry, objective_id)
        if (
            definition is not None
            and definition.phase == STATUS_PHASE_LABEL
            and evaluate(state, registry, grid, player_id, objective_id)[2]
        ):
            result.append(objective_id)
    return result


def _name(registry: StaticDataRegistry, objective_id: str) -> str:
    definition = objective_def(registry, objective_id)
    return (definition.name if definition and definition.name else None) or objective_id


def _ensure_requirements(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
) -> None:
    """Twarda kontrola wymagań karty (``objective_progress``); niemodelowane → przepuszcza."""
    value, goal, ok = evaluate(state, registry, grid, player_id, objective_id)
    if not ok:
        raise ValueError(
            f"Objective requirements not met ({value}/{goal}): "
            f"{_name(registry, objective_id)}."
        )


def score_public(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
    *,
    ignore_phase: bool = False,
    payment: ObjectivePayment | None = None,
) -> GameState:
    """Gracz zdobywa odkryty cel publiczny (bez limitu na fazę — to sprawdza wołający).

    ``ignore_phase=True`` (primary Imperial) pozwala zdobyć cel poza fazą statusu.
    ``payment`` = jawna płatność za cele „Spend…" (``None`` => dobiera silnik).

    Raises:
        ValueError: Gdy gracz/cel nieznany, cel nieodkryty, już zdobyty przez gracza,
            nie jest celem fazy statusu, albo gracz nie kontroluje swoich planet domowych.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if objective_id not in state.objectives.revealed:
        raise ValueError("This public objective is not revealed.")
    definition = objective_def(registry, objective_id)
    if definition is None:
        raise ValueError(f"Unknown objective: {objective_id}")
    if has_scored_public(state, player_id, objective_id):
        raise ValueError("You have already scored this objective.")
    if is_retired(state, objective_id):
        raise ValueError("This objective is still in play but can no longer be scored.")
    if not ignore_phase and definition.phase != STATUS_PHASE_LABEL:
        raise ValueError("This objective is not scored in the status phase.")
    if not controls_home_planets(state, registry, player_id):
        raise ValueError(
            "You cannot score public objectives without controlling every planet "
            "in your home system."
        )
    _ensure_requirements(state, registry, grid, player_id, objective_id)
    new_state = pay_for_objective(state, registry, grid, player_id, objective_id, payment)
    record_public_score(new_state, player_id, objective_id)
    award_points(new_state, player_id, definition.points or 1)
    # „When you score a public objective” (Yin Ascendant, RULES.md 62.10).
    triggers.fire(
        new_state, GameEvent.OBJECTIVE_SCORED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "objective": objective_id, "secret": "false"},
    )
    return new_state


def score_secret(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
    payment: ObjectivePayment | None = None,
) -> GameState:
    """Gracz ujawnia i zdobywa tajny cel z ręki (cel fazy statusu).

    Raises:
        ValueError: Gdy gracz nieznany, celu nie ma na ręce albo nie jest to cel fazy statusu.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if objective_id not in player.private.secret_objectives:
        raise ValueError("This secret objective is not in your hand.")
    definition = objective_def(registry, objective_id)
    if definition is None:
        raise ValueError(f"Unknown objective: {objective_id}")
    if definition.phase != STATUS_PHASE_LABEL:
        raise ValueError("This secret objective is not scored in the status phase.")
    _ensure_requirements(state, registry, grid, player_id, objective_id)
    new_state = pay_for_objective(state, registry, grid, player_id, objective_id, payment)
    secret_objectives.score(new_state, player_id, objective_id)
    award_points(new_state, player_id, definition.points or 1)
    return new_state


def leaders_by_points(state: GameState, order: Sequence[str]) -> str | None:
    """Zwycięzca przy braku celów do odkrycia: najwięcej VP, remis → pierwszy wg ``order``.

    R_victory_points: „the tied player who is first in initiative order is the winner".
    """
    if not order:
        return None
    best = max(state.players[pid].victory_points for pid in order)
    for player_id in order:
        if state.players[player_id].victory_points == best:
            return player_id
    return None

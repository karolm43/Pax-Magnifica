# ruff: noqa: E501  (tabele reguł i opisów zdarzeń: długie wzorce są celowe)
"""Katalog zdarzeń gry i klasyfikator okien czasowych kart/zdolności (RULES.md 54).

Każda karta, zdolność, lider, technologia, relikt, notka i agenda opisuje GDZIE w grze coś robi
frazą typu „After you activate a system”, „At the start of the strategy phase”, „When an agenda is
revealed”. Ten moduł zamienia takie frazy na stabilny, maszynowy adres okna: ``(zdarzenie, moment)``
plus filtry kontekstu — ``WindowRef``. Silnik emituje zdarzenia (``core/triggers.py``), a hooki
rejestrują się na ``(zdarzenie, moment)`` (``rules_hooks.on_event``).

Moduł jest CZYSTY (zero stanu gry): definicje + klasyfikacja tekstu. Źródło reguł o czasie:
``docs/rules_tirules/R_abilities.md`` (sekcja Timing):
* „before"/„after" = tuż przed/po opisanym zdarzeniu; „when" = w chwili zdarzenia (zmienia je albo
  zastępuje); zdarzenia „when" mają pierwszeństwo przed „after", a „after" przed następnym „before”;
* zdolność można rozstrzygnąć raz na każde wystąpienie zdarzenia („at the start of combat” — w
  każdej walce).

Klasyfikacja po słowach kluczowych to HEURYSTYKA: raport ``docs/OKNA_CZASOWE.md`` (generowany)
pokazuje, co zostało przypisane, a co nie (przypadki szczególne do ręcznego przeglądu).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from src.core.timing_spec import TriggerKind, classify_trigger


class Moment(StrEnum):
    """Kiedy względem zdarzenia (R_abilities: Timing)."""

    BEFORE = "before"
    WHEN = "when"  # w chwili zdarzenia: modyfikuje lub zastępuje je
    AFTER = "after"
    START = "start"  # „at the start of ...”
    END = "end"  # „at the end of ...”
    DURING = "during"
    INSTEAD = "instead"  # „instead of ...” (zastąpienie, REPLACE)
    ANY = "any"  # „at any time”
    ACTION = "action"  # akcja komponentu („ACTION:”) - nie zdarzenie, tylko akcja gracza


class Duration(StrEnum):
    """Zakres trwania efektu trwałego (wygasa na końcu zakresu)."""

    TURN = "turn"
    TACTICAL_ACTION = "tactical_action"
    INVASION = "invasion"
    AGENDA = "agenda"  # „until after that agenda has been resolved”
    COMBAT = "combat"
    COMBAT_ROUND = "combat_round"
    PHASE = "phase"
    ROUND = "round"
    GAME = "game"  # do końca gry albo do ręcznego zdjęcia
    WHILE_IN_PLAY = "while_in_play"  # dopóki komponent leży w grze (źródło hooka)


class GameEvent(StrEnum):
    """Zdarzenia, na które mogą reagować karty i zdolności. Wartość = stabilny identyfikator."""

    # --- cykl życia ---
    SETUP = "game.setup"  # „during setup”, „when you create the game board”
    FACTION_IN_PLAY = "game.faction_in_play"
    STATE_CONDITION = "state.condition"  # „when you have 4 mechs ...” - warunek stanu spełniony
    ROUND = "round"
    PHASE = "phase"  # ctx: phase = strategy | action | status | agenda
    STATUS_STEP = "status.step"  # ctx: step
    TURN = "turn"
    SPEAKER_CHANGED = "speaker.changed"
    PLAYER_PASSED = "player.passed"
    LAST_PLAYER_PASSED = "player.last_passed"
    # --- karty strategii ---
    STRATEGY_CARD_CHOSEN = "strategy.card_chosen"
    STRATEGY_CARDS_RETURNED = "strategy.cards_returned"
    STRATEGIC_ACTION = "strategy.action"  # ctx: ability = primary | secondary, card
    STRATEGY_TOKEN_SPENT = "strategy.token_spent"
    # --- akcja taktyczna / ruch ---
    TACTICAL_ACTION = "tactical.action"
    SYSTEM_ACTIVATED = "tactical.system_activated"
    SHIPS_MOVED = "tactical.ships_moved"
    UNITS_COMMITTED = "tactical.units_committed"
    COMPONENT_ACTION = "component.action"
    # --- walka ---
    COMBAT = "combat"  # ctx: kind = space | ground
    COMBAT_ROUND = "combat.round"
    COMBAT_STEP = "combat.step"  # ctx: step
    COMBAT_ROLL = "combat.roll"  # ctx: kind
    HITS_ASSIGNED = "combat.hits_assigned"
    UNIT_SUSTAIN_DAMAGE = "unit.sustain_damage"
    UNIT_DESTROYED = "unit.destroyed"
    COMBAT_WON = "combat.won"
    RETREAT_DECLARED = "combat.retreat"
    INVASION = "invasion"
    UNIT_ABILITY_USED = "unit.ability_used"  # ctx: ability
    FACTION_ABILITY_USED = "faction.ability_used"  # np. Pillage użyte przeciw graczowi
    UNIT_PLACED = "unit.placed"  # struktura/jednostka postawiona (PDS, space dock)
    COMPONENT_READIED = "component.readied"
    COMPONENT_EXHAUSTED = "component.exhausted"
    COMBAT_HITS_PRODUCED = "combat.hits_produced"  # „each time hits are produced against ...”
    UNIT_GALVANIZED = "unit.galvanized"
    UNITS_COEXIST = "unit.coexist"
    # --- produkcja ---
    PRODUCTION_USED = "production.used"
    UNITS_PRODUCED = "production.units_produced"
    # --- planety ---
    PLANET_CONTROL_GAINED = "planet.control_gained"
    PLANET_CONTROL_LOST = "planet.control_lost"
    PLANET_EXPLORED = "planet.explored"
    PLANETS_EXHAUSTED = "planet.exhausted"
    # --- ekonomia / żetony / transakcje ---
    TRADE_GOODS_GAINED = "economy.trade_goods_gained"
    RESOURCES_SPENT = "economy.resources_spent"
    COMMODITIES_REPLENISHED = "economy.commodities_replenished"
    COMMODITIES_GIVEN = "economy.commodities_given"
    COMMAND_TOKENS_GAINED = "tokens.gained"
    COMMAND_TOKEN_PLACED = "tokens.placed"
    TRANSACTION = "transaction"
    # --- technologie ---
    TECHNOLOGY_RESEARCH = "technology.research"  # ctx: unit_upgrade
    TECHNOLOGY_GAINED = "technology.gained"
    TECHNOLOGY_SHARED = "technology.shared"
    # --- karty / cele ---
    ACTION_CARD_PLAYED = "cards.action_played"
    ACTION_CARDS_DRAWN = "cards.action_drawn"
    ACTION_CARD_DISCARDED = "cards.action_discarded"
    COMPONENT_GAINED = "component.gained"  # „when you gain this card”
    OBJECTIVE_REVEALED = "objective.revealed"
    OBJECTIVE_SCORED = "objective.scored"
    SECRET_OBJECTIVE_DISCARDED = "objective.secret_discarded"
    # --- agenda ---
    AGENDA_REVEALED = "agenda.revealed"
    AGENDA_VOTES_CAST = "agenda.votes_cast"
    AGENDA_OUTCOME_RESOLVED = "agenda.outcome_resolved"
    AGENDA_ELECTED = "agenda.elected"
    LAW_DISCARDED = "agenda.law_discarded"
    # --- czas dowolny ---
    ANY_TIME = "any_time"


@dataclass(frozen=True)
class EventInfo:
    """Opis zdarzenia: znaczenie, klucze kontekstu i miejsce emisji w silniku."""

    summary: str
    ctx_keys: tuple[str, ...] = ()
    emitted_by: str | None = None  # None = NIE podpięte w silniku (zdarzenie tylko zdefiniowane)


# Dokumentacja zdarzeń. ``emitted_by`` aktualizujemy razem z podpinaniem emisji (``core/triggers``).
EVENT_INFO: dict[GameEvent, EventInfo] = {
    GameEvent.SETUP: EventInfo(
        "Przygotowanie gry (tworzenie planszy, rozdanie kart).", (), "game_setup.reveal_objectives"
    ),
    GameEvent.STATE_CONDITION: EventInfo(
        "Warunek stanu spełniony (np. 4 mechy w systemie).", ("player",)
    ),
    GameEvent.SPEAKER_CHANGED: EventInfo(
        "Żeton mówcy zmienił właściciela.", ("player",), "strategy_phase.set_speaker"
    ),
    GameEvent.UNIT_PLACED: EventInfo(
        "Struktura/jednostka postawiona.", ("player", "base_type", "planet"), "unit_ops.place_units"
    ),
    GameEvent.COMPONENT_EXHAUSTED: EventInfo(
        "Komponent (np. agent) wyczerpany.", ("player", "component")
    ),
    GameEvent.COMBAT_HITS_PRODUCED: EventInfo(
        "Trafienia wyprodukowane przeciw graczowi.", ("player", "amount")
    ),
    GameEvent.COMPONENT_READIED: EventInfo("Komponent odświeżony.", ("player", "component")),
    GameEvent.FACTION_IN_PLAY: EventInfo(
        "Frakcja wchodzi do gry (setup, flip Obsidian).", ("faction",)
    ),
    GameEvent.ROUND: EventInfo("Początek/koniec rundy.", ("round",), "turn_flow.next_round"),
    GameEvent.PHASE: EventInfo("Początek/koniec fazy.", ("phase",), "turn_flow.next_phase"),
    GameEvent.STATUS_STEP: EventInfo("Krok fazy statusu (1-8).", ("step",)),
    GameEvent.TURN: EventInfo(
        "Początek/koniec tury gracza w fazie akcji.", ("player",), "turn_flow"
    ),
    GameEvent.PLAYER_PASSED: EventInfo("Gracz spasował.", ("player",), "turn_flow.pass_turn"),
    GameEvent.LAST_PLAYER_PASSED: EventInfo(
        "Ostatni gracz spasował.", ("player",), "turn_flow.pass_turn"
    ),
    GameEvent.STRATEGY_CARD_CHOSEN: EventInfo(
        "Gracz wybiera kartę strategii (faza strategii).",
        ("player", "initiative"),
        "strategy_phase.pick_strategy_card",
    ),
    GameEvent.STRATEGY_CARDS_RETURNED: EventInfo(
        "Karty strategii wracają na stół (status).", ("player",)
    ),
    GameEvent.STRATEGIC_ACTION: EventInfo(
        "Akcja strategiczna / jej ability primary-secondary.",
        ("player", "ability", "initiative"),
        "strategic_action",
    ),
    GameEvent.STRATEGY_TOKEN_SPENT: EventInfo(
        "Żeton z puli strategicznej wydany na secondary.",
        ("player",),
        "strategic_action.resolve_secondary",
    ),
    GameEvent.TACTICAL_ACTION: EventInfo(
        "Akcja taktyczna (początek/koniec).", ("player", "system"), "tactical.end_tactical_action"
    ),
    GameEvent.SYSTEM_ACTIVATED: EventInfo(
        "System aktywowany.", ("player", "position"), "tactical.activate_system"
    ),
    GameEvent.SHIPS_MOVED: EventInfo(
        "Statki weszły do aktywnego systemu.", ("player", "position"), "movement.move_ships"
    ),
    GameEvent.UNITS_COMMITTED: EventInfo(
        "Siły naziemne zaangażowane do lądowania.", ("player", "planet"), "invasion"
    ),
    GameEvent.COMPONENT_ACTION: EventInfo(
        "Akcja komponentu zagrana.", ("player", "component"), "action_cards.play_action_card"
    ),
    GameEvent.COMBAT: EventInfo(
        "Początek/koniec walki.",
        ("kind", "position", "attacker", "defender"),
        "battle.start_combat / battle._after_losses",
    ),
    GameEvent.COMBAT_ROUND: EventInfo(
        "Początek/koniec rundy walki.", ("kind", "round"), "battle.roll_round"
    ),
    GameEvent.COMBAT_STEP: EventInfo("Nazwany krok walki.", ("step", "kind")),
    GameEvent.COMBAT_ROLL: EventInfo(
        "Rzut (combat, AFB, space cannon, bombardment).", ("kind", "player"), "battle.roll_round"
    ),
    GameEvent.HITS_ASSIGNED: EventInfo(
        "Przypisanie trafień.", ("player", "kind"), "battle.assign_combat_hits"
    ),
    GameEvent.UNIT_SUSTAIN_DAMAGE: EventInfo(
        "Jednostka użyła Sustain Damage.", ("player", "base_type"), "battle.assign_combat_hits"
    ),
    GameEvent.UNIT_DESTROYED: EventInfo(
        "Jednostka zniszczona.", ("player", "base_type", "cause"), "unit_ops.remove_units"
    ),
    GameEvent.COMBAT_WON: EventInfo(
        "Gracz wygrał walkę.", ("player", "kind"), "battle._after_losses"
    ),
    GameEvent.RETREAT_DECLARED: EventInfo(
        "Odwrót ogłoszony.", ("player",), "battle.announce_retreat"
    ),
    GameEvent.INVASION: EventInfo("Początek inwazji.", ("position",), "invasion"),
    GameEvent.UNIT_ABILITY_USED: EventInfo(
        "Jednostka użyła zdolności (AFB, bombardment, space cannon).",
        ("ability", "player"),
        "battle / invasion / space_cannon",
    ),
    GameEvent.FACTION_ABILITY_USED: EventInfo(
        "Zdolność frakcji użyta (np. Pillage przeciw graczowi).", ("player", "ability")
    ),
    GameEvent.UNIT_GALVANIZED: EventInfo("Jednostka galvanize.", ("player",)),
    GameEvent.UNITS_COEXIST: EventInfo(
        "Jednostki zaczynają współistnieć na planecie.", ("planet",)
    ),
    GameEvent.PRODUCTION_USED: EventInfo(
        "Jednostki użyły PRODUCTION.", ("player", "position"), "production.produce"
    ),
    GameEvent.UNITS_PRODUCED: EventInfo(
        "Jednostki wyprodukowane.", ("player", "position"), "production.produce"
    ),
    GameEvent.PLANET_CONTROL_GAINED: EventInfo(
        "Gracz zdobył kontrolę nad planetą.", ("player", "planet"), "control.set_planet_control"
    ),
    GameEvent.PLANET_CONTROL_LOST: EventInfo(
        "Gracz stracił kontrolę nad planetą.", ("player", "planet"), "control.set_planet_control"
    ),
    GameEvent.PLANET_EXPLORED: EventInfo(
        "Planeta zbadana (karta eksploracji rozstrzygnięta; frontier nie emituje).",
        ("player", "planet", "deck", "card"),
        "exploration.resolve",
    ),
    GameEvent.PLANETS_EXHAUSTED: EventInfo("Planety wyczerpane (płatność).", ("player",)),
    GameEvent.TRADE_GOODS_GAINED: EventInfo(
        "Gracz zdobył trade goods.", ("player", "amount"), "economy.gain_trade_goods"
    ),
    GameEvent.RESOURCES_SPENT: EventInfo("Gracz wydał zasoby/wpływy.", ("player", "purpose")),
    GameEvent.COMMODITIES_REPLENISHED: EventInfo(
        "Commodities uzupełnione.", ("player",), "economy.replenish_commodities"
    ),
    GameEvent.COMMODITIES_GIVEN: EventInfo("Commodities oddane innemu graczowi.", ("player", "to")),
    GameEvent.COMMAND_TOKENS_GAINED: EventInfo(
        "Gracz zdobył żetony dowodzenia.", ("player", "amount")
    ),
    GameEvent.COMMAND_TOKEN_PLACED: EventInfo(
        "Żeton dowodzenia położony w systemie.", ("player", "position")
    ),
    GameEvent.TRANSACTION: EventInfo(
        "Transakcja (negocjacja/rozstrzygnięcie).",
        ("player", "partner"),
        "transaction.resolve_transaction",
    ),
    GameEvent.TECHNOLOGY_RESEARCH: EventInfo(
        "Badanie technologii.",
        ("player", "technology", "unit_upgrade"),
        "technology.apply_research",
    ),
    GameEvent.TECHNOLOGY_GAINED: EventInfo(
        "Zdobycie technologii.", ("player", "technology"), "technology.grant_technology"
    ),
    GameEvent.TECHNOLOGY_SHARED: EventInfo(
        "Technologia udostępniona innemu graczowi.", ("player", "technology")
    ),
    GameEvent.ACTION_CARD_PLAYED: EventInfo(
        "Zagranie karty akcji.", ("player", "card"), "action_cards.play_action_card"
    ),
    GameEvent.ACTION_CARDS_DRAWN: EventInfo(
        "Dobranie kart akcji.", ("player", "amount"), "card_draw.draw_action_card"
    ),
    GameEvent.ACTION_CARD_DISCARDED: EventInfo(
        "Odrzucenie karty akcji.", ("player", "card"), "card_draw._record_discards"
    ),
    GameEvent.COMPONENT_GAINED: EventInfo(
        "Gracz zdobył komponent (relikt, notka, technologia).",
        ("player", "component"),
        "relics / breakthrough / promissory_notes",
    ),
    GameEvent.OBJECTIVE_REVEALED: EventInfo(
        "Cel publiczny ujawniony.", ("objective",), "objectives.reveal_next_public"
    ),
    GameEvent.OBJECTIVE_SCORED: EventInfo(
        "Cel zdobyty.",
        ("player", "objective", "secret"),
    ),
    GameEvent.SECRET_OBJECTIVE_DISCARDED: EventInfo("Tajny cel odrzucony.", ("player",)),
    GameEvent.AGENDA_REVEALED: EventInfo(
        "Agenda ujawniona.", ("agenda",), "agenda_phase.reveal_agenda"
    ),
    GameEvent.AGENDA_VOTES_CAST: EventInfo(
        "Głosy oddane.", ("player", "outcome", "votes"), "agenda_phase.cast_vote"
    ),
    GameEvent.AGENDA_OUTCOME_RESOLVED: EventInfo(
        "Wynik agendy rozstrzygany.", ("agenda", "outcome"), "agenda_phase._resolve"
    ),
    GameEvent.AGENDA_ELECTED: EventInfo("Gracz wybrany jako wynik agendy.", ("player", "agenda")),
    GameEvent.LAW_DISCARDED: EventInfo("Prawo zdjęte z gry.", ("law",), "agenda_phase.repeal_law"),
    GameEvent.ANY_TIME: EventInfo("Dowolna chwila („at any time”).", ()),
}


def event_point(event: GameEvent, moment: Moment) -> str:
    """Nazwa punktu zaczepienia dla pary (zdarzenie, moment) w rejestrze hooków."""
    return f"event:{event.value}:{moment.value}"


@dataclass(frozen=True)
class WindowRef:
    """Maszynowy adres okna czasowego komponentu."""

    event: GameEvent
    moment: Moment
    ctx: tuple[tuple[str, str], ...] = ()  # filtry, np. (("phase", "strategy"),)
    would: bool = False  # „when you WOULD ...” - przed skutkiem (zastąpienie możliwe)
    once_per: str | None = None  # „once per combat/agenda phase”
    scope_hint: str | None = None  # „during agenda phase, after ...” - faza nadrzędna

    @property
    def point(self) -> str:
        return event_point(self.event, self.moment)

    def ctx_dict(self) -> dict[str, str]:
        return dict(self.ctx)


_MOMENT_BY_TRIGGER: dict[TriggerKind, Moment] = {
    TriggerKind.WHEN: Moment.WHEN,
    TriggerKind.AFTER: Moment.AFTER,
    TriggerKind.BEFORE: Moment.BEFORE,
    TriggerKind.INSTEAD: Moment.INSTEAD,
    TriggerKind.AT_START: Moment.START,
    TriggerKind.AT_END: Moment.END,
    TriggerKind.DURING: Moment.DURING,
    TriggerKind.ACTION: Moment.ACTION,
}

_E = GameEvent
_PHASES = r"(strategy|action|status|agenda)"
_UNIT = r"(?:units?|ships?|fighters?|infantry|ground forces|mechs?|dreadnoughts?|cruisers?|war ?suns?|flagship)"

# Reguły: (wzorzec na tekście w małych literach, zdarzenie, kontekst). Pierwsze trafienie wygrywa,
# więc reguły szczegółowe stoją przed ogólnymi.
_RULES: tuple[tuple[re.Pattern[str], GameEvent, tuple[tuple[str, str], ...]], ...] = tuple(
    (re.compile(pattern), event, ctx)
    for pattern, event, ctx in (
        # setup
        (
            r"during setup|create the game board|creating the galaxy|before creating|game setup",
            _E.SETUP,
            (),
        ),
        # agenda
        (r"\bis discarded\b.*\blaw\b|\blaw is discarded|discards? .*\blaw\b", _E.LAW_DISCARDED, ()),
        (r"(?:is|are) elected|elected as outcome|elected player", _E.AGENDA_ELECTED, ()),
        (
            r"\boutcome\b.*\b(?:resolved|would be resolved)|resolv(?:e|es|ing) (?:this |the |an? )?outcome|agendas? (?:is|are) resolved",
            _E.AGENDA_OUTCOME_RESOLVED,
            (),
        ),
        (
            r"after (?:all )?players? (?:have )?voted|all players have voted",
            _E.AGENDA_VOTES_CAST,
            (("scope", "all"),),
        ),
        (
            r"(?:speaker )?votes? on|\bcast(?:s|ing)? (?:at least \d+ )?votes?|\byou vote\b|\bvotes? for\b|"
            r"players vote|before players vote|cast votes",
            _E.AGENDA_VOTES_CAST,
            (),
        ),
        (
            r"agenda(?: card)? (?:is|are) revealed|this agenda is revealed|this card is revealed|reveal(?:s|ed)? (?:an? )?agenda",
            _E.AGENDA_REVEALED,
            (),
        ),
        # karty strategii
        (
            r"return(?:s|ed)? (?:your |their |a |the )?strategy cards?",
            _E.STRATEGY_CARDS_RETURNED,
            (),
        ),
        (
            r"chooses? (?:a |another )?strategy card|picks? (?:a )?strategy card|takes? (?:a )?strategy card",
            _E.STRATEGY_CARD_CHOSEN,
            (),
        ),
        (
            r"spend(?:s)? (?:a |1 |\d+ )?(?:command )?tokens? (?:from (?:your |their )?)?(?:the )?strategy pool|"
            r"spend(?:s)? (?:a |\d+ )?command tokens? (?:to resolve|during) .*secondary",
            _E.STRATEGY_TOKEN_SPENT,
            (),
        ),
        (r"strategic action", _E.STRATEGIC_ACTION, ()),
        (
            r"(?:primary|secondary)(?: or (?:primary|secondary))? ability|following .* secondary|follows? .* secondary",
            _E.STRATEGIC_ACTION,
            (),
        ),
        # status / fazy / tury
        (r"draw action cards step", _E.STATUS_STEP, (("step", "draw_action_cards"),)),
        (r"ready planets step", _E.STATUS_STEP, (("step", "ready_planets"),)),
        (
            r"gain(?:s|ing)? (?:\d+ )?command tokens? during (?:the )?status phase|gain command tokens step",
            _E.STATUS_STEP,
            (("step", "gain_command_tokens"),),
        ),
        (r"(?:last player passes|all players? (?:have )?passed)", _E.LAST_PLAYER_PASSED, ()),
        (r"speaker token", _E.SPEAKER_CHANGED, ()),
        (r"\bpasses\b|when you pass\b|\byou pass\b", _E.PLAYER_PASSED, ()),
        (
            r"(?:start|end) of (?:[\w']+ ){0,3}turn\b|\bstart of turn\b|\bend of turn\b|during of turns|"
            r"during (?:your |their )turn|during each of your turns|each of your turns",
            _E.TURN,
            (),
        ),
        (r"(?:start|end) of (?:(?!combat\b)[\w']+ ){0,3}round\b(?! of)", _E.ROUND, ()),
        (
            r"(?:start|end|beginning) of (?:the |a |each |next |your |their |player's |players |sol player's )*"
            + _PHASES
            + r" phase",
            _E.PHASE,
            (),
        ),
        (r"during (?:the )?" + _PHASES + r" phase", _E.PHASE, ()),
        # akcja taktyczna / ruch
        (
            r"perform(?:s)? (?:a |an )?tactical action|(?:resolve|resolved) (?:a |an )?tactical action|"
            r"(?:end|start) of (?:a |the |player's |players |your |each )?tactical actions?",
            _E.TACTICAL_ACTION,
            (),
        ),
        (
            r"perform(?:s)?(?: a| an)?(?: component)? action|you perform action",
            _E.COMPONENT_ACTION,
            (),
        ),
        (r"command tokens? (?:is|are) placed", _E.COMMAND_TOKEN_PLACED, ()),
        (
            r"activate(?:s|d)? (?:a |an |the )?(?:non-delta )?(?:wormhole|anomaly|system)|activating (?:a )?system|"
            r"activates? system",
            _E.SYSTEM_ACTIVATED,
            (),
        ),
        (r"faction ability is used|ability is used against", _E.FACTION_ABILITY_USED, ()),
        (
            r"\bmoves? (?:ships|units|war ?suns?|.*ships)|ships? move\b|moves? .* into",
            _E.SHIPS_MOVED,
            (),
        ),
        (
            r"commits?(?:ted)? .*(?:units|ground forces)|ground forces are committed|"
            r"\"commit ground forces\" step|commit ground forces",
            _E.UNITS_COMMITTED,
            (),
        ),
        (
            r"during (?:your |the |a |this )?(?:tactical )?actions?\b|end of this action|\btactical actions?\b",
            _E.TACTICAL_ACTION,
            (),
        ),
        # walka
        (
            r"(?:is|are) destroyed|destroy(?:ed)? (?:during|in)|last ship .* destroyed",
            _E.UNIT_DESTROYED,
            (),
        ),
        (
            r"\"announce retreats\" step|announce retreats",
            _E.COMBAT_STEP,
            (("step", "announce_retreats"),),
        ),
        (
            r"\"anti-fighter barrage\" step|anti-fighter barrage step",
            _E.COMBAT_STEP,
            (("step", "anti_fighter_barrage"),),
        ),
        (r"\"roll dice\" step", _E.COMBAT_STEP, (("step", "roll_dice"),)),
        (r"declares? retreat|declare retreat|\bretreat\b", _E.RETREAT_DECLARED, ()),
        (
            r"before (?:you )?assign|assign(?:s|ing)? hits?|hit would be assigned|hits? to ships",
            _E.HITS_ASSIGNED,
            (),
        ),
        (r"sustain damage", _E.UNIT_SUSTAIN_DAMAGE, ()),
        (r"\bwins?(?: or loses?)? (?:a |the )?(?:space |ground )?combat", _E.COMBAT_WON, ()),
        (
            r"uses? anti-fighter barrage|anti-fighter barrage (?:roll|dice)",
            _E.UNIT_ABILITY_USED,
            (("ability", "afb"),),
        ),
        (
            r"uses? (?:space cannon|bombardment)|bombardment, space cannon|space cannon,? .*roll|"
            r"(?:space cannon|bombardment|anti-fighter barrage) roll|use bombardment|use space cannon",
            _E.UNIT_ABILITY_USED,
            (("ability", "roll"),),
        ),
        (
            r"(?:rolls?|makes?) (?:dice )?(?:for )?(?:a )?(?:unit ability|roll for unit ability)|"
            r"roll for unit ability|unit ability",
            _E.UNIT_ABILITY_USED,
            (("ability", "roll"),),
        ),
        (
            r"(?:ground forces )?make combat rolls|roll dice|dice (?:is|are) rolled|die is rolled|you and opponent roll",
            _E.COMBAT_ROLL,
            (),
        ),
        (
            r"(?:start|end) of (?:the |a |each |first )*(?:round of )?(?:space |ground )?combat round|"
            r"round of (?:of )?(?:a |the )?(?:space |ground )?combat|combat round|space combat round|"
            r"ground combat round|first round of",
            _E.COMBAT_ROUND,
            (),
        ),
        (
            r"(?:start|end) of (?:invasion|the invasion) (?:combat|in system)|start of invasion",
            _E.INVASION,
            (),
        ),
        (
            r"(?:start|end) of (?:[\w']+ ){0,4}combat\b|during combat|"
            r"combat between players|(?:first )?round of space combat",
            _E.COMBAT,
            (),
        ),
        (r"galvaniz", _E.UNIT_GALVANIZED, ()),
        (
            r"\bplac(?:ing|es?) (?:an? |\d+ |1 or more )?(?:additional )?(?:pds|space docks?|structures?|units?)",
            _E.UNIT_PLACED,
            (),
        ),
        (r"card readies|readies\b", _E.COMPONENT_READIED, ()),
        (r"becomes exhausted|is exhausted|are exhausted", _E.COMPONENT_EXHAUSTED, ()),
        (r"hits? (?:are|is) produced", _E.COMBAT_HITS_PRODUCED, ()),
        (r"begin coexisting|coexist", _E.UNITS_COEXIST, ()),
        (r"during movement|\bmovement\b", _E.SHIPS_MOVED, ()),
        (r"enters play|enter play", _E.COMPONENT_GAINED, ()),
        (r"during this combat", _E.COMBAT, ()),
        (r"\binvasion\b", _E.INVASION, ()),
        # produkcja
        (r"\buses? production\b|\buse production\b|units? use production", _E.PRODUCTION_USED, ()),
        (r"\bproduces?\b|\bproduction\b", _E.UNITS_PRODUCED, ()),
        # planety
        (r"gains? control of|gained control of", _E.PLANET_CONTROL_GAINED, ()),
        (r"loses? control of", _E.PLANET_CONTROL_LOST, ()),
        (r"explores?\b|\bexplore\b", _E.PLANET_EXPLORED, ()),
        (r"exhausts? planets?", _E.PLANETS_EXHAUSTED, ()),
        # ekonomia
        (
            r"replenish(?:es)? (?:their |your )?commodities|refresh commodities|refreshes commodities",
            _E.COMMODITIES_REPLENISHED,
            (),
        ),
        (r"gives? .*commodities|give .*commodities", _E.COMMODITIES_GIVEN, ()),
        (r"gains? (?:\d+ )?trade goods?|gain trade goods", _E.TRADE_GOODS_GAINED, ()),
        (
            r"spends? (?:\d+ )?(?:resources|trade goods|influence)|spend resources",
            _E.RESOURCES_SPENT,
            (),
        ),
        (r"gains? (?:\d+ )?command tokens?", _E.COMMAND_TOKENS_GAINED, ()),
        (r"transactions?", _E.TRANSACTION, ()),
        # technologie
        (
            r"research(?:es)? .*unit upgrade|unit upgrade technology",
            _E.TECHNOLOGY_RESEARCH,
            (("unit_upgrade", "true"),),
        ),
        (r"\bresearch(?:es)?\b|would research", _E.TECHNOLOGY_RESEARCH, ()),
        (r"sharing tech|shares? .*technolog", _E.TECHNOLOGY_SHARED, ()),
        (
            r"gains? (?:a |the |that |another )?(?:player's )?technolog|would gain .*technolog|gains? technology",
            _E.TECHNOLOGY_GAINED,
            (),
        ),
        # karty / cele
        (r"plays? (?:an? )?action card", _E.ACTION_CARD_PLAYED, ()),
        (r"discards? (?:an? )?action card", _E.ACTION_CARD_DISCARDED, ()),
        (
            r"draws? (?:\d+ |or more )?(?:of )?(?:\d+ )?(?:or more )?action cards?",
            _E.ACTION_CARDS_DRAWN,
            (),
        ),
        (r"discards? (?:a |the )?secret objective", _E.SECRET_OBJECTIVE_DISCARDED, ()),
        (
            r"public objective is revealed|reveals? (?:a |the )?public objective",
            _E.OBJECTIVE_REVEALED,
            (),
        ),
        (
            r"(?:may |would )?scores? (?:a |the |player's |your )?(?:secret |public )?objective|you score|may score",
            _E.OBJECTIVE_SCORED,
            (),
        ),
        (r"faction comes into play", _E.FACTION_IN_PLAY, ()),
        (
            r"(?:gains?|receives?|gained|received) (?:this )?(?:card|relic|promissory)|you gain card|"
            r"when you (?:gain|receive) (?:this )?card|comes into play|when you receive",
            _E.COMPONENT_GAINED,
            (),
        ),
        (r"\bat time\b|at any time|any time", _E.ANY_TIME, ()),
        (
            r"(?:you|player) (?:have|has|control|controls) (?:at least )?\d+ ",
            _E.STATE_CONDITION,
            (),
        ),
    )
)

_ONCE_PER = re.compile(r"^once per (\w+(?: \w+)?),?\s*")
_NORMALIZE_WS = re.compile(r"\s+")
_WOULD = re.compile(r"\bwould\b")
_CONDITION_LEAD = re.compile(r"^if (?:you|player|they) (?:have|has|control|controls) ")
_DURING_THEN = re.compile(r"^during [^,]+?,\s*(after|when|before)\b")


def _norm(text: str) -> str:
    return _NORMALIZE_WS.sub(" ", text.lower().strip().rstrip(":,.")).replace("’", "'")


def classify_window(text: str | None) -> WindowRef | None:
    """Zamienia frazę okna na ``WindowRef``; ``None``, gdy nic nie pasuje.

    Przykłady: „After you activate a system” -> ``(SYSTEM_ACTIVATED, AFTER)``; „At the start of the
    strategy phase” -> ``(PHASE, START, phase=strategy)``; „ACTION:” -> ``(COMPONENT_ACTION, ACTION)``.
    """
    if not text or not text.strip():
        return None
    norm = _norm(text)
    once_per: str | None = None
    match = _ONCE_PER.match(norm)
    if match:
        once_per = match.group(1)
        norm = norm[match.end() :]
    scope_hint: str | None = None
    then = _DURING_THEN.match(norm)
    if then:  # „During the agenda phase, after ...” - okno to część po przecinku
        phase = re.match(r"during (?:the )?(\w+)", norm)
        scope_hint = phase.group(1) if phase else None
        norm = norm[norm.index(",") + 1 :].strip()
    if norm.startswith(("each time ", "whenever ")):
        rest = norm.split(" ", 2)[2] if norm.startswith("each time") else norm.split(" ", 1)[1]
        norm = "when " + rest
    trigger = classify_trigger(norm)
    moment = _MOMENT_BY_TRIGGER.get(trigger)
    if moment is None and norm.startswith("if ") and _CONDITION_LEAD.search(norm):
        return WindowRef(_E.STATE_CONDITION, Moment.WHEN, once_per=once_per)
    if moment is Moment.ACTION:
        return WindowRef(_E.COMPONENT_ACTION, Moment.ACTION, once_per=once_per)
    if moment is None:
        if re.match(r"(?:at )?(?:any|all) time|at time", norm):
            return WindowRef(_E.ANY_TIME, Moment.ANY, once_per=once_per)
        return None
    for pattern, event, ctx in _RULES:
        found = pattern.search(norm)
        if found is None:
            continue
        extra = list(ctx)
        if event is _E.PHASE:
            phase_match = re.search(_PHASES, found.group(0))
            if phase_match:
                extra.append(("phase", phase_match.group(1)))
        return WindowRef(
            event, moment, tuple(extra), bool(_WOULD.search(norm)), once_per, scope_hint
        )
    return None


# --- Czas trwania i trwałość w tekstach (nie w polu okna) ---------------------------------------

_DURATION_RULES: tuple[tuple[re.Pattern[str], Duration], ...] = tuple(
    (re.compile(p), d)
    for p, d in (
        (
            r"until the end of (?:the |this |your )?(?:tactical action|action)\b|\bthis (?:tactical )?action\b",
            Duration.TACTICAL_ACTION,
        ),
        (r"until the end of (?:the |this )?invasion|\bthis invasion\b", Duration.INVASION),
        (
            r"until after (?:that|this|the) agenda (?:has been |is )?resolved|\bthis agenda\b",
            Duration.AGENDA,
        ),
        (
            r"until the end of (?:the |this |your )?(?:combat round|round of combat)",
            Duration.COMBAT_ROUND,
        ),
        (r"until the end of (?:the |this )?combat|\bthis combat\b", Duration.COMBAT),
        (
            r"until the end of (?:the |this |your )?turn|this turn|for the (?:rest of the )?turn",
            Duration.TURN,
        ),
        (
            r"until the end of (?:the |this )?(?:strategy|action|status|agenda) phase|"
            r"for the (?:rest of the )?(?:strategy|action|status|agenda) phase",
            Duration.PHASE,
        ),
        (
            r"until the end of (?:the |this )?round|for the (?:rest of the )?round|this round",
            Duration.ROUND,
        ),
        (r"for the rest of the game|permanently", Duration.GAME),
        (
            r"while (?:this |the |that )?(?:card|law|agenda|token)(?: is)? in (?:your |the )?(?:common )?play(?: area)?|"
            r"while this law is in play|as long as (?:this )?(?:card|law)",
            Duration.WHILE_IN_PLAY,
        ),
    )
)
_DEFERRED = re.compile(
    r"at the start of (?:the |your |their )?next (strategy|action|status|agenda) phase|"
    r"at the start of (?:your |their )?(next) turn|at start of (next) turn"
)
_OPTIONAL = re.compile(r"\bmay\b")
# Zdanie otwierane frazą czasu: gdziekolwiek w tekście komponentu.
_CLAUSE = re.compile(
    r"(?:^|(?<=[.!?:;\n]))\s*((?:when|whenever|after|before|each time|at the (?:start|end) of|"
    r"at the (?:start|end)|during|instead of|once per)\b[^.:\n]{0,160})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Clause:
    """Klauzula czasowa znaleziona w tekście komponentu."""

    text: str
    window: WindowRef | None
    optional: bool


def find_durations(text: str | None) -> list[Duration]:
    """Zakresy trwania wspomniane w tekście (kolejność wystąpienia, bez duplikatów)."""
    if not text:
        return []
    low = _norm(text)
    found: list[Duration] = []
    for pattern, duration in _DURATION_RULES:
        if pattern.search(low) and duration not in found:
            found.append(duration)
    return found


def deferred_phase(text: str | None) -> str | None:
    """Odroczony wyzwalacz: faza („...next strategy phase”) albo ``next`` dla „...next turn”."""
    match = _DEFERRED.search(_norm(text)) if text else None
    if match is None:
        return None
    return next((g for g in match.groups() if g), None)


def _window_part(raw: str) -> str:
    """Część klauzuli opisująca OKNO (do pierwszego przecinka; dłuższa dla „once per”/„during X, after”)."""
    low = _norm(raw)
    keep = 2 if (_ONCE_PER.match(low) or _DURING_THEN.match(low)) else 1
    return ",".join(raw.split(",")[:keep])


def find_clauses(text: str | None) -> list[Clause]:
    """Wszystkie klauzule czasowe w tekście komponentu (okna wewnątrz opisu efektu)."""
    if not text:
        return []
    clauses: list[Clause] = []
    for found in _CLAUSE.finditer(text):
        raw = found.group(1).strip()
        window = classify_window(_window_part(raw))
        optional = bool(_OPTIONAL.search(_norm(text[found.start() : found.end() + 120])))
        clauses.append(Clause(raw, window, optional))
    return clauses

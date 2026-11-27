"""Rejestr hooków reguł: wyjątki frakcji, technologii i kart BEZ edycji reguły bazowej.

RULES.md 43.1: reguła bazowa nie zna wyjątków. W miejscu, na które coś może wpływać, wywołuje
PUNKT ZACZEPIENIA (``point``, napis), a wyjątek rejestruje się osobno (pakiet ``core/hooks/``)
jako ``(źródło, punkt, rodzaj, funkcja)``. Hook jest CZYSTĄ funkcją ``(state, player_id, ctx)``.

Hook obowiązuje gracza tylko wtedy, gdy ten POSIADA jego źródło (frakcja, technologia, ...) —
patrz ``owned_sources``. Kolejność wielu hooków na jednym punkcie jest deterministyczna
(RULES.md 43.1 pkt 5): REPLACE, FORBID, PERMIT, MODIFY, TRIGGER, PERSISTENT, a w obrębie rodzaju
kolejność rejestracji.

API: ``forbidden`` (FORBID), ``permits`` (PERMIT), ``modify`` (MODIFY) — pytania „w miejscu”;
``on_event`` rejestruje hooki zdarzeń (TRIGGER/REPLACE), które uruchamia ``core/triggers.fire``
(RULES.md 54). PERSISTENT = efekt trwały w ``GameState.active_effects`` (``core/active_effects``),
będący źródłem hooków (``SOURCE_EFFECT``) do czasu wygaśnięcia.

God-Mode omija hooki tak jak resztę reguł (RULES.md 43.1 pkt 11).
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from src.core.game_events import GameEvent, Moment, event_point
from src.core.game_state import GameState

# Punkty zaczepienia (nazwy). Dopisuj tu, gdy reguła bazowa dostaje nowy punkt.
POINT_PRODUCTION_FORBIDS = "production.forbids"  # FORBID -> typy jednostek (ctx: producer_type)
POINT_MOVEMENT_ENTER_ASTEROIDS = "movement.enter_asteroids"  # PERMIT -> bool
POINT_MOVEMENT_MOVE_VALUE = "movement.move_value"  # MODIFY -> delta (ctx: base_type)
# PERMIT (ctx: position, from, base_type = typ ruszającego statku albo "" gdy nieznany)
POINT_MOVEMENT_PASS_FOREIGN_SHIPS = "movement.pass_foreign_ships"
POINT_COMBAT_ROLL_MODIFIER = "combat.roll_modifier"  # MODIFY -> +N do wyniku rzutu
# ctx: kind, position, planet, defender, base_type
POINT_COMBAT_EXTRA_DICE = "combat.extra_dice"  # MODIFY -> delta kości na jednostkę (ctx jak wyżej)
# MODIFY -> dodatkowe trafienia strony po rzutach obu stron (ctx: kind, opponent_hits, own_hits);
# Valkyrie Particle Weave (RULES.md 62.1).
POINT_COMBAT_EXTRA_HITS = "combat.extra_hits"
# MODIFY -> dodatkowe kości dla GRUPY jednostek łącznie (nie na egzemplarz), ctx: kind, base_type;
# agent Letnev „that ship rolls 1 additional die" (RULES.md 62.2).
POINT_COMBAT_BONUS_DICE = "combat.bonus_dice"
# MODIFY -> +X do wyników kości JEDNEJ jednostki danego typu (ctx: kind, base_type); Gravleash.
POINT_COMBAT_SINGLE_UNIT_BONUS = "combat.single_unit_bonus"
# MODIFY -> o ile więcej trafień anuluje jedno użycie Sustain Damage (Non-Euclidean Shielding).
POINT_COMBAT_SUSTAIN_CANCELS = "combat.sustain_cancels"
# MODIFY -> +N do pojemności puli floty w każdym systemie (Armada).
POINT_FLEET_POOL_CAPACITY = "fleet_pool.capacity"
# PERMIT -> statki niemyśliwskie gracza nie są ograniczone pulą floty (Darktalon Treilla).
POINT_FLEET_POOL_UNLIMITED = "fleet_pool.unlimited"
# PERMIT -> jednostki INNYCH graczy w systemie (ctx: position) tracą PLANETARY SHIELD (Arc
# Secundus).
POINT_STRIPS_PLANETARY_SHIELD = "invasion.strips_planetary_shield"
# PERMIT -> w inwazji Space Cannon nie strzela w jednostki gracza (L4 Disruptors).
POINT_SPACE_CANNON_DEFENSE_IMMUNE = "space_cannon.defense_immune"
POINT_COMBAT_REROLL_MISSES = "combat.reroll_misses"  # PERMIT -> przerzut chybień (ctx: base_type)
# PERMIT -> trafienia z rzutu AFB właściciela hooka są wyprodukowane przeciw WSZYSTKIM statkom
# przeciwnika, nie tylko myśliwcom (Waylay; przypisuje je przeciwnik w kroku ASSIGN).
POINT_COMBAT_AFB_ALL_SHIPS = "combat.afb_all_ships"
POINT_AGENDA_VOTE_MODIFIER = "agenda.vote_modifier"  # MODIFY -> delta głosów (ctx: agenda_id)
POINT_PRODUCTION_VALUE = "production.value"  # MODIFY -> delta PRODUCTION jednostki
# ctx: base_type, zone
POINT_PRODUCTION_TOTAL_VALUE = "production.total_value"  # MODIFY -> delta SUMY PRODUCTION gracza
POINT_MOVEMENT_ALPHA_BETA_ADJACENT = "movement.alpha_beta_adjacent"  # PERMIT (Lost Star Chart)
POINT_MOVEMENT_IGNORE_ANOMALIES = "movement.ignore_anomalies"  # PERMIT (Nav Suite)
# PERMIT: ignoruj efekty anomalii w ruchu, ale szczelina nadal daje +1 do ruchu - tylko bez rzutu
# (Circlet of the Void, C_relics: „still applies the movement bonus … gravity rifts”).
POINT_MOVEMENT_IGNORE_ANOMALIES_KEEP_RIFT = "movement.ignore_anomalies_keep_rift"
POINT_SPACE_CANNON_OFFENSE_IMMUNE = "space_cannon.offense_immune"  # PERMIT (Solar Flare)
POINT_PRODUCTION_COST = "production.cost"  # MODIFY -> delta łącznego kosztu zamówienia
POINT_PAYMENT_COMMODITIES_AS_TG = "payment.commodities_as_trade_goods"  # PERMIT -> bool
# Space Cannon: modyfikator wyniku rzutów PRZECIWKO właścicielowi hooka (pytamy właściciela CELU;
# ctx: shooter) - np. Antimass Deflectors: -1 do wyniku każdej kości.
POINT_SPACE_CANNON_ROLL_MODIFIER = "space_cannon.roll_modifier"
# Space Cannon: dodatkowe kości dla JEDNEJ jednostki strzelca przy jednym użyciu (Plasma Scoring).
POINT_SPACE_CANNON_EXTRA_DICE = "space_cannon.extra_dice"
# Bombardment: dodatkowe kości dla JEDNEJ jednostki przy jednym użyciu (Plasma Scoring).
POINT_BOMBARDMENT_EXTRA_DICE = "bombardment.extra_dice"

# Bombardment: statki niefighterowe BEZ własnego Bombardment zyskują go (Blitz: BOMBARDMENT 6).
# Hook FORBID użyty jako „zbiór wartości": zwraca napisy z progiem trafienia (np. {"6"}); silnik
# bierze najniższy próg (pytamy atakującego).
POINT_BOMBARDMENT_GRANTED = "bombardment.granted_hits_on"

# Bombardment: modyfikator wyniku każdej kości rzutu PRZECIW planecie właściciela hooka
# (pytamy kontrolującego planetę; Bunker: -4). ctx: planet, attacker.
POINT_BOMBARDMENT_ROLL_MODIFIER = "bombardment.roll_modifier"

# PDS gracza ``ctx["victim"]`` traci PLANETARY SHIELD i SPACE CANNON (Disable). PERMIT pytany
# o KAŻDEGO gracza przy stole (właściciel efektu odpowiada, czyje PDS wyłącza).
POINT_PDS_DISABLED = "space_cannon.pds_disabled"
# Mnożnik trafień z rzutów (bazowo 1; X-89 ΩΩ: ×2). ctx: kind = ground | space | bombardment.
POINT_COMBAT_HIT_MULTIPLIER = "combat.hit_multiplier"
# PERMIT -> inwazja zaczyna się od Commit Ground Forces (bez Bombardment): Tekklar Conditioning.
POINT_INVASION_SKIP_BOMBARDMENT = "invasion.skip_bombardment"
# PERMIT -> inwazja otwiera Commit Ground Forces, choć w przestrzeni nie ma sił naziemnych: gracz
# może lądować prosto z planet (G'hom Sek'kus, F_norr). Pytany o aktywnego gracza.
POINT_INVASION_COMMIT_FROM_PLANETS = "invasion.commit_from_planets"
# Bombardment wolno rzucać także przeciw planecie cudzej BEZ sił naziemnych (X-89 ΩΩ).
POINT_BOMBARD_EMPTY_PLANETS = "bombardment.empty_planets"  # PERMIT -> bool
# Odwrót do sąsiedniego systemu bez cudzych jednostek, także bez własnej obecności
# (Dark Energy Tap).
POINT_RETREAT_ANYWHERE = "retreat.anywhere"  # PERMIT -> bool
# Specjalności technologii planet działają bez wyczerpywania, także na wyczerpanych planetach
# (Psychoarchaeology).
POINT_TECHNOLOGY_SPECIALTY_FREE = "technology.specialty_without_exhaust"  # PERMIT -> bool
# Liczba akcji gracza w jego turze fazy akcji (bazowo 1; Fleet Logistics: +1).
POINT_TURN_ACTIONS = "turn.actions"
# Gracz właśnie rozpoczął akcję (``action_budget.register_action``); hooki PERSISTENT uruchamiane
# przez ``run_persistent`` (ctx: strategic = czy to akcja strategiczna). Np. Extreme Duress.
POINT_ACTION_STARTED = "turn.action_started"
# Transakcja może obejmować relikty, karty akcji i nieodsłonięte tajne cele (Black Market Dealings);
# PERMIT -> bool (pytamy obu uczestników transakcji; ctx: partner).
POINT_TRANSACTION_EXTRA_ITEMS = "transaction.extra_items"
# Relikty, które WOLNO wymienić w transakcji z mocy własnego tekstu („may be exchanged as part of
# a transaction”: The Silver Flame). Hook FORBID jako zbiór id posiadanych takich reliktów.
POINT_TRANSACTION_TRADABLE_RELICS = "transaction.tradable_relics"
# Transakcja z graczem, który NIE jest sąsiadem (Guild Ships, Trade Convoys); PERMIT -> bool
# (pytamy obu stron; ctx: partner). Nie czyni graczy sąsiadami (F_hacan).
POINT_TRANSACTION_ANY_PLAYER = "transaction.any_player"
# W transakcji można wymieniać karty akcji (Arbiters); PERMIT -> bool (obie strony; ctx: partner).
POINT_TRANSACTION_ACTION_CARDS = "transaction.action_cards"
# Planety, których kartę gracz może oddać w transakcji (Pride of Kenara); FORBID jako zbiór id
# planet (pytamy oddającego). Jego jednostki z planety idą na inną jego planetę (RULES.md 62.6).
POINT_TRANSACTION_PLANETS = "transaction.planets"
# PERMIT -> secondary karty strategii bez wydania żetonu ze strategy pool (ctx: initiative, owner);
# Masters of Trade (Trade), Acquiescence (karta Winnu) — RULES.md 62.6, 62.7.
POINT_STRATEGY_SECONDARY_FREE = "strategy.secondary_free"
# PERMIT -> łączny koszt jednostek w tym użyciu PRODUCTION = 0 (Harrugh Gefhara); limity zostają.
POINT_PRODUCTION_FREE = "production.free"
# PERMIT -> zdjęcie żetonu Custodians bez wydawania wpływu (Blood Ties, RULES.md 62.7).
POINT_CUSTODIANS_FREE = "custodians.free"
# Planety z zamienionymi wartościami zasobów i wpływu (Hegemonic Trade Policy); FORBID jako zbiór
# id planet, pytamy KONTROLUJĄCEGO planetę (RULES.md 62.7).
POINT_PLANET_SWAP_VALUES = "planet.swap_values"
# Faza statusu: liczba kart akcji dobieranych przez gracza (bazowo 1; Neural Motivator: +1).
POINT_STATUS_ACTION_CARDS = "status.action_cards"
# Faza statusu: liczba żetonów dowodzenia zdobywanych przez gracza (bazowo 2; Hyper Metabolism: +1).
POINT_STATUS_COMMAND_TOKENS = "status.command_tokens"

# Commodity value gracza (bazowo z arkusza frakcji; Dynamis Core: +2). MODIFY -> delta.
POINT_COMMODITY_VALUE = "economy.commodity_value"

# Space Cannon nadany jednostce BEZ własnego (Lightrail Ordnance: stocznia). Hook FORBID jako zbiór
# napisów "<base_type>:<próg trafienia>:<kości na jednostkę>"; strzela też na sąsiednie systemy.
POINT_SPACE_CANNON_GRANTED = "space_cannon.granted"

# Sustain Damage nadany statkom niemyśliwskim bez własnego (Metali Void Shielding). PERMIT -> bool.
POINT_COMBAT_GRANTED_SUSTAIN = "combat.granted_sustain"
# AFB nadany właścicielowi hooka (Metali Void Armaments): FORBID jako zbiór "<próg>:<kości>".
POINT_COMBAT_AFB_GRANTED = "combat.afb_granted"
# Właściciel może w KAŻDEJ rundzie walki przerzucić kości z +1 do wyniku (Thalnos). PERMIT.
POINT_COMBAT_REROLL_PLUS_ONE = "combat.reroll_plus_one"
# Zmiana wyniku DOWOLNEJ kości o ±1 po rzucie (Heart of Ixth). Hook FORBID jako zbiór id GOTOWYCH
# reliktów, którymi wolno to zrobić (silnik wyczerpuje wskazany relikt).
POINT_DIE_ADJUST = "dice.adjust_result"

# Zamiast wydać żeton z puli strategicznej gracz może wydać żeton z rezerwy (Scepter of Emelpar).
# Hook FORBID jako zbiór id GOTOWYCH reliktów, którymi wolno (silnik wyczerpuje wskazany).
POINT_STRATEGY_TOKEN_FROM_REINFORCEMENTS = "command_tokens.strategy_from_reinforcements"

# Ruch i transport z systemów zawierających WŁASNY żeton dowodzenia (Dominus Orb). PERMIT -> bool.
POINT_MOVEMENT_IGNORE_OWN_CC = "movement.ignore_own_command_token"
# PERMIT -> statki niemyśliwskie mają wartość ruchu równą najwyższej spośród statków ruszających
# z tego samego systemu (Gravleash Maneuvers, RULES.md 62.2).
POINT_MOVEMENT_MATCH_HIGHEST = "movement.match_highest"

# Ignorowanie 1 prerekwizytu przy badaniu przez wyczerpanie reliktu (Prophet's Tears).
# Hook FORBID jako zbiór id GOTOWYCH reliktów; skip w planie badania: ``relic:<id>``.
POINT_TECHNOLOGY_IGNORE_PREREQUISITE = "technology.ignore_prerequisite"

# MODIFY -> ile symboli prerekwizytu koloru ``ctx["color"]`` gracz ma dodatkowo (karta „satisfies
# a green technology prerequisite”: Brother Omar, RULES.md 62.10).
POINT_TECHNOLOGY_VIRTUAL_PREREQUISITES = "technology.virtual_prerequisites"
# PERMIT -> gracz może zwrócić 1 swoją piechotę do rezerwy, by zignorować WSZYSTKIE prerekwizyty
# badanej technologii (ctx: technology); skip ``infantry:<pozycja>|<strefa>`` (Brother Omar).
POINT_TECHNOLOGY_INFANTRY_SKIP = "technology.infantry_skip"

# Synergia dla WSZYSTKICH czterech typów technologii (The Quantumcore). PERMIT -> bool.
POINT_TECHNOLOGY_SYNERGY_ALL = "technology.synergy_all"

# Limit tajnych celów gracza (bazowo 3; The Obsidian: +1). MODIFY -> delta.
POINT_SECRET_OBJECTIVE_LIMIT = "objectives.secret_limit"

# MODIFY -> dodatkowe trafienia z JEDNEJ kości rzutu combat wg wyniku przed modyfikatorami
# (ctx: kind, base_type, natural); flagowiec Jol-Nar (RULES.md 62.3).
POINT_COMBAT_NATURAL_EXTRA_HITS = "combat.natural_extra_hits"
# MODIFY -> ile brakujących symboli prerekwizytów badanie ignoruje bez kosztu (ctx: unit_upgrade
# = "true" | "false"); Analytical (RULES.md 62.3).
POINT_TECHNOLOGY_FREE_IGNORES = "technology.free_prerequisite_ignores"
# PERMIT -> po wydaniu żetonu na secondary karty strategii gracz rozstrzyga primary (ctx:
# initiative); Brilliant (RULES.md 62.3).
POINT_STRATEGY_SECONDARY_AS_PRIMARY = "strategy.secondary_as_primary"
# FORBID -> pozycje dodatkowo sąsiadujące z ``ctx["position"]`` w RUCHU gracza (warstwa ruchu,
# graf mapy bez zmian); Spatial Conduit Cylinder (RULES.md 62.3).
POINT_MOVEMENT_EXTRA_ADJACENT = "movement.extra_adjacent"
# FORBID -> positions additionally adjacent to ``ctx["position"]`` ONLY for this player,
# persistently (ctx: position, grid: HexGrid | None); map graph untouched. Read solely via
# ``board_graph.extra_adjacent_for_player`` (RULES.md 61.7, e.g. Quantum Entanglement).
POINT_ADJACENCY_EXTRA_FOR_PLAYER = "adjacency.extra_for_player"
# FORBID -> positions that are NOT adjacent to ``ctx["position"]`` for this player although the
# lower layers make them adjacent (layer 4 of RULES.md 61.7: Empyrean Void Tether - "other players
# do not treat those systems as adjacent"); ctx: position, grid. Read solely via
# ``board_graph.cut_adjacent_for_player``.
POINT_ADJACENCY_CUT_FOR_PLAYER = "adjacency.cut_for_player"
# FORBID -> ``"<position>|<TYPE>"`` wormholes carried by the player's units (Hil Colish: "This
# ship's system contains a delta wormhole"); read ONLY via ``board_graph.unit_wormholes``
# (map sync + ``wormholes_at``), RULES.md 62.19.
POINT_BOARD_UNIT_WORMHOLES = "board.unit_wormholes"
# PERMIT -> game effects (laws: Enforced Travel Ban, Nexus Sovereignty) cannot block this
# player's wormhole movement (Creuss Quantum Entanglement); read in
# ``movement_paths.wormhole_link_blocked`` (RULES.md 62.19).
POINT_MOVEMENT_WORMHOLE_LAWS_IMMUNE = "movement.wormhole_laws_immune"
# PERMIT -> the player's ship ``ctx["base_type"]`` moves before or after the other ships (Hil
# Colish): the Ion Storm it used flips right after its move (C_exploration_cards ion-storm 2.1).
POINT_MOVEMENT_MOVES_SEPARATELY = "movement.moves_separately"
# FORBID -> wormhole types the ACTIVE player treats ``ctx["position"]`` as having during their
# tactical action (Lazax Gate Folding: Mecatol Rex "as if it has both an alpha and beta wormhole");
# read only via ``board_graph.wormhole_list`` (F_winnu 2.4: Dimensional Splicer there).
POINT_SYSTEM_ACTION_WORMHOLES = "system.action_wormholes"
# PERMIT -> myśliwce i siły naziemne do łącznej capacity produkowanych statków nie liczą się do
# limitu PRODUCTION; Bellum Gloriosum (RULES.md 62.4).
POINT_PRODUCTION_FREE_CARGO = "production.free_cargo"
# PERMIT -> w płatnym badaniu z karty Technology wolno wyczerpać planetę ze specjalnością
# zamiast płacić (kolor musi pasować); Specialist Compounds (RULES.md 62.3).
POINT_TECHNOLOGY_SPECIALTY_PAYS = "technology.specialty_pays"
# PERMIT -> jednostki gracza ``ctx["victim"]`` w strefie ``ctx["zone"]`` (``space`` albo id
# planety) systemu ``ctx["position"]`` nie mogą użyć SUSTAIN DAMAGE. Pytany KAŻDY inny gracz
# (właściciel efektu); Fourth Moon, Moll Terminus (RULES.md 62.8).
POINT_COMBAT_SUSTAIN_DENIED = "combat.sustain_denied"
# MODIFY -> ile zasobów/wpływu jest wart 1 trade good w płatności (bazowo 1; Mirror Computing:
# +1). Nie dotyczy wymogu wydania samych TG (RULES.md 62.8).
POINT_PAYMENT_TRADE_GOOD_VALUE = "payment.trade_good_value"
# --- Prawa agend (RULES.md 51.6) ---
# PERMIT -> gracz głosuje 1 głosem bez wyczerpywania planet, bez dodatkowych głosów
# (Representative Government).
POINT_AGENDA_SINGLE_VOTE = "agenda.single_vote"
# MODIFY -> delta limitu kart akcji w ręce (ctx: base; Executive Sanctions).
POINT_HAND_LIMIT = "hand_limit.action_cards"
# PERMIT -> the player has no action card hand limit at all; read BEFORE ``POINT_HAND_LIMIT``, so
# no game effect can lower it (Crafty, RULES.md 62.22).
POINT_HAND_LIMIT_UNLIMITED = "hand_limit.unlimited"
# FORBID -> powody, dla których gracz nie może zagrywać kart akcji (Political Censure).
POINT_ACTION_CARDS_FORBIDDEN = "action_cards.forbidden"
# MODIFY -> maks. liczba żetonów w fleet pool (baza 0 = bez limitu; Fleet Regulations).
POINT_FLEET_POOL_TOKEN_CAP = "fleet_pool.token_cap"
# PERMIT -> brak limitu PDS na planecie (Homeland Defense Act).
POINT_PDS_UNLIMITED = "limits.pds_unlimited"
# FORBID -> rodzaje planet, których nie wolno bombardować (``cultural``…; Conventions of War).
POINT_BOMBARDMENT_FORBIDDEN_TRAITS = "bombardment.forbidden_traits"
# FORBID -> typy wormholi bez efektu w ruchu; ctx: ``position`` (system z wormholem) albo brak
# (Enforced Travel Ban - wszędzie, Nexus Sovereignty - tylko Wormhole Nexus).
POINT_MOVEMENT_WORMHOLES_BLOCKED = "movement.wormholes_blocked"
# PERMIT -> jednostki mogą przelatywać przez mgławice (Shared Research).
POINT_MOVEMENT_THROUGH_NEBULA = "movement.through_nebula"
# PERMIT -> a ship starting its move in a nebula keeps its move value (Empyrean Voidborn:
# "Nebulae do not affect your ships' movement"); read in ``movement.move_value``.
POINT_MOVEMENT_NEBULA_IGNORED = "movement.nebula_ignored"
# MODIFY -> delta liczby myśliwców/piechoty za jeden koszt (ctx: base_type; Regulated Conscription).
POINT_PRODUCTION_UNITS_PER_COST = "production.units_per_cost"
# FORBID -> typy jednostek gracza, które tracą SUSTAIN DAMAGE (Publicize Weapon Schematics).
POINT_UNIT_SUSTAIN_LOST = "units.sustain_lost"
# FORBID -> limit odświeżanych planet w kroku 3 fazy agendy (liczby jako napisy; Checks and
# Balances „Against": 3). Gracz z limitem wybiera planety w decyzji (``COMPONENT_READIED``).
POINT_PLANETS_READY_LIMIT = "agenda.planets_ready_limit"
# PERMIT -> wybrana karta strategii trafia do innego gracza (Checks and Balances).
POINT_STRATEGY_GIVE_CHOSEN = "strategy.give_chosen_card"
# PERMIT -> badanie technologii przez kartę Technology bez wydawania zasobów (Minister of Sciences).
POINT_TECHNOLOGY_SC_FREE = "technology.strategy_card_free"
# --- Xxcha Kingdom (RULES.md 62.9) ---
# PERMIT -> gracz wydaje wpływ jak zasoby i zasoby jak wpływ (Archon's Gift): planeta wnosi do
# płatności większą z dwóch wartości; tylko WYDAWANIE, nie inne efekty (F_xxcha).
POINT_PAYMENT_FLEX_SPEND = "payment.flex_spend"
# MODIFY -> dodatkowe głosy za KAŻDĄ planetę wyczerpaną do głosowania (Elder Qanoj: +1; planeta
# z 0 wpływu też może wtedy głosować - F_xxcha).
POINT_AGENDA_VOTES_PER_PLANET = "agenda.votes_per_planet"
# PERMIT -> efekty gry nie mogą zabronić graczowi głosowania (Elder Qanoj).
POINT_AGENDA_VOTE_UNBLOCKABLE = "agenda.vote_unblockable"
# PERMIT -> gracz może anulować zagraną kartę akcji bez karty w ręce (Instinct Training; jawne:
# technologia gotowa + żeton w strategy pool). ctx: ``player`` (zagrywający), ``card``.
POINT_ACTION_CARD_CANCELLER = "action_cards.canceller"
# --- Argent Flight (RULES.md 62.11) ---
# PERMIT -> gracz zawsze głosuje PIERWSZY w fazie agendy, także jako mówca (Zeal).
POINT_AGENDA_VOTE_FIRST = "agenda.vote_first"
# MODIFY -> dodatkowe kości AFB dla JEDNEJ grupy jednostek gracza przy jednym rzucie AFB
# (commander Argent, Strike Wing Ambuscade; odpowiednik ``space_cannon.extra_dice``).
POINT_COMBAT_AFB_EXTRA_DICE = "combat.afb_extra_dice"
# PERMIT -> trafienia AFB gracza ponad liczbę myśliwców przeciwnika uszkadzają statki przeciwnika
# z SUSTAIN DAMAGE wybrane przez gracza (Raid Formation).
POINT_COMBAT_AFB_RAID = "combat.afb_raid"
# FORBID jako zbiór "<base_type>:<najniższy wynik>": każdy wynik AFB tej grupy >= progu niszczy też
# 1 piechotę przeciwnika w przestrzeni aktywnego systemu (Strike Wing Alpha II: "destroyer:9").
POINT_COMBAT_AFB_INFANTRY_KILL = "combat.afb_infantry_kill"
# PERMIT -> inni gracze (``ctx["mover"]``) nie mogą przelatywać statkami przez system
# ``ctx["position"]``. Pytany KAŻDY gracz poza ruszającym (Aerie Hololattice).
POINT_MOVEMENT_PASSAGE_BLOCKED = "movement.passage_blocked"
# MODIFY -> wartość PRODUCTION samej PLANETY gracza (``ctx["planet"]``, ``position``) - planeta
# produkuje „jak jednostka” (Aerie Hololattice: planeta ze strukturą gracza = PRODUCTION 1).
POINT_PRODUCTION_PLANET_VALUE = "production.planet_value"
# --- L1Z1X Mindnet (RULES.md 62.12) ---
# PERMIT -> przy przejęciu planety cudze struktury NIE są niszczone od razu (Assimilate wymienia je
# w hooku „gain control”; czego nie wymieni, niszczy sam).
POINT_CONTROL_STRUCTURES_REPLACED = "control.structures_replaced"
# PERMIT -> Planetary Shield nie blokuje BOMBARDMENT gracza (2RAM); jednostki nadal mają tarczę.
POINT_BOMBARDMENT_IGNORES_SHIELD = "bombardment.ignores_planetary_shield"
# FORBID -> typy sił naziemnych gracza, które bombardują „jak statek”, gdy nie walczą (Annihilator).
POINT_BOMBARDMENT_GROUND_UNITS = "bombardment.ground_units"
# FORBID -> typy jednostek gracza, których trafienia w walce kosmicznej muszą trafić statki
# przeciwnika inne niż myśliwce, o ile się da ([0.0.1]: flagowiec i pancerniki).
POINT_COMBAT_HITS_TO_NON_FIGHTERS = "combat.hits_to_non_fighters"
# FORBID jako zbiór "<karta>:<koszt>": wyczerpanie karty i OSOBNA zapłata kosztu zasobami ignoruje
# WSZYSTKIE prerekwizyty badanej technologii (Inheritance Systems: "is:2").
POINT_TECHNOLOGY_PAID_IGNORE_ALL = "technology.paid_ignore_all"
# --- Embers of Muaat (RULES.md 62.13) ---
# PERMIT -> statki gracza przelatują PRZEZ supernowe (węzeł pośredni trasy; Gashlai Physiology).
POINT_MOVEMENT_THROUGH_SUPERNOVA = "movement.through_supernova"
# PERMIT -> jednostki gracza wchodzą DO supernowej (cel ruchu, odwrót, wejście sił; Magmus Reactor).
POINT_MOVEMENT_INTO_SUPERNOVA = "movement.into_supernova"
# MODIFY -> wartość PRODUCTION samego SYSTEMU (``ctx["position"]``) „jak jednostki” gracza -
# producent w przestrzeni (Magmus Reactor: supernowa z jednostką gracza = PRODUCTION 5).
POINT_PRODUCTION_SYSTEM_VALUE = "production.system_value"
# PERMIT -> gracz ma zdolność PRODUCTION na planszy spoza jednostek (warunek eliminacji, Magmus Ω).
POINT_ELIMINATION_HAS_PRODUCTION = "elimination.has_production"
# --- Clan of Saar (RULES.md 62.14) ---
# PERMIT -> struktura gracza (``ctx["base_type"]``) stoi w PRZESTRZENI i rusza się / wycofuje jak
# statek, a zablokowana ginie (Floating Factory) - ``core/floating_structures``.
POINT_UNIT_FLOATING_STRUCTURE = "units.floating_structure"
# PERMIT -> gracz-właściciel hooka zabrania INNEMU graczowi (``ctx["activator"]``) aktywować system
# ``ctx["position"]`` (Chaos Mapping) - sprawdzane w ``tactical.activate_system``.
POINT_TACTICAL_ACTIVATION_BLOCKED = "tactical.activation_blocked"
# MODIFY -> docelowa wartość ruchu JEDNEGO statku (``ctx``: ``from``, ``base_type``); 0 = brak.
# Silnik bierze max(własna, docelowa) po regule mgławicy, przed premiami (Captain Mendosa).
POINT_MOVEMENT_SINGLE_SHIP_VALUE = "movement.single_ship_value"
# PERMIT -> gracz zdobywa cele bez kontroli planet swojego systemu domowego (Nomadic).
POINT_OBJECTIVES_IGNORE_HOME_CONTROL = "objectives.ignore_home_control"
# --- Naaz-Rokha Alliance (RULES.md 62.15) ---
# PERMIT -> gracz eksplorujący planetę ``ctx["planet"]`` może dobrać 1 dodatkową kartę i wybrać
# jedną do rozstrzygnięcia (Distant Suns) - ``exploration.extra_draw_allowed``.
POINT_EXPLORATION_EXTRA_DRAW = "exploration.extra_draw"
# FORBID (zbiór id wariantów) -> siły naziemne gracza w PRZESTRZENI systemu ``ctx["position"]``,
# które teraz walczą w walce kosmicznej jak statki, z wartościami podanego wariantu (Z-Grav
# Eidolon, Eidolon Maximum) - ``ship_roles`` (walka kosmiczna, Assault Cannon, cele).
POINT_COMBAT_SPACE_GROUND_VARIANT = "combat.space_ground_variant"
# PERMIT -> siła naziemna gracza (``ctx["base_type"]``) w przestrzeni rusza się i wycofuje jak
# statek ze swoją wartością ruchu (Eidolon Maximum) - ``floating_structures.moves_as_ship``.
POINT_UNIT_GROUND_MOVES_AS_SHIP = "units.ground_moves_as_ship"
# FORBID (typy jednostek) -> efekty gry nie mogą STAWIAĆ tych jednostek gracza (Eidolon Maximum:
# „Game effects cannot place or produce your mechs”) - ``unit_ops.place_units``,
# ``board_reinforcements.can_place``.
POINT_UNIT_PLACE_FORBIDDEN = "units.place_forbidden"
# FORBID (typy jednostek) -> jednostki gracza, którym NIE wolno przypisać trafień ze zdolności
# jednostek (Space Cannon, bombardowanie; Eidolon Maximum) - ``battle.ability_hit_targets``.
POINT_COMBAT_ABILITY_HIT_IMMUNE = "combat.ability_hit_immune"
# --- Naalu Collective (RULES.md 62.16) ---
# PERMIT -> myśliwce gracza ponad pojemność liczą się do puli floty zamiast przepadać (Fighter II
# ma to z aliasu ``ff2``; Hybrid Crystal Fighter II - hook) - ``capacity`` / ``fleet_pool``.
POINT_FLEET_POOL_FIGHTERS_OVERFLOW = "fleet_pool.fighters_overflow"
# MODIFY -> delta liczby myśliwców ponad pojemność, które razem liczą się jako 1 statek puli floty
# (baza 1; Hybrid Crystal Fighter II: +1 = „count as 1/2 of a ship”) - ``fleet_pool``.
POINT_FLEET_POOL_FIGHTERS_PER_SHIP = "fleet_pool.fighters_per_ship"
# FORBID (typy jednostek) -> statki gracza, które w inwazji w systemie ``ctx["position"]`` lądują
# i walczą na planetach jak siły naziemne (Matriarch: myśliwce) - ``ship_roles.ground_force_types``.
POINT_INVASION_GROUND_FORCE_TYPES = "invasion.ground_force_types"
# FORBID (rodzaje podglądu) -> ukryte informacje, które gracz widzi stale (M'aban:
# ``neighbors_promissory``, ``agenda_top``, ``agenda_bottom``) - ``core/peek.py``.
POINT_INFO_PEEK = "info.peek"
# --- Capture (RULES.md 61.5) i Vuil'raith Cabal (62.17) ---
# PERMIT -> gracz przechwytuje zniszczoną jednostkę (ctx: player = właściciel, base_type,
# position, zone) - ``capture.on_destroyed`` (Devour, The Terror Between, Reanimator).
POINT_CAPTURE_DESTROYED = "capture.destroyed"
# FORBID (pozycje) -> systemy, które jednostki gracza czynią gravity rift (Dimensional Tear) -
# ``map_anomalies.extra_anomalies`` -> ``HexGrid.sync_extra_anomalies``.
POINT_MAP_GRAVITY_RIFTS = "map.gravity_rifts"
# FORBID (pozycje) -> szczeliny, za które statki gracza nie rzucają (Dimensional Tear) -
# ``movement_paths.rift_roll_nodes``.
POINT_MOVEMENT_RIFT_NO_ROLL = "movement.rift_no_roll"
# PERMIT -> w tym ruchu statki gracza nie rzucają za żadną szczelinę i dostają JEDNO dodatkowe +1,
# gdy trasa wychodzi z/przechodzi przez szczelinę (Crucible) - ``movement_paths.rift_bonus``.
POINT_MOVEMENT_RIFT_EXTRA_BONUS = "movement.rift_extra_bonus"
# PERMIT -> gracz produkuje jednostki, zwracając przechwycone tego typu zamiast zasobów
# (Amalgamation) - ``production.produce`` (``captured``).
POINT_PRODUCTION_CAPTURED_FREE = "production.captured_free"
# MODIFY -> ile myśliwców/piechoty w kroku produkcji nie liczy się do limitu PRODUCTION (That Which
# Molds Flesh: +2) - ``production.free_small_units``.
POINT_PRODUCTION_FREE_SMALL_UNITS = "production.free_small_units"
# PERMIT -> zwrot 1 przechwyconej jednostki typu ulepszanej jednostki ignoruje wszystkie
# prerekwizyty ulepszenia (Riftmeld) - ``technology`` (skip ``captured:<właściciel>``).
POINT_TECHNOLOGY_CAPTURED_SKIP = "technology.captured_skip"
# PERMIT -> zdobyty przełom wprowadza The Fracture bez rzutu (Al'raith Ix Ianovar) -
# ``expeditions.gain_breakthrough``.
POINT_BREAKTHROUGH_FRACTURE_NO_ROLL = "breakthrough.fracture_no_roll"
# --- Titans of Ul (RULES.md 62.18) ---
# FORBID (typy struktur) -> struktury gracza, które są TEŻ siłami naziemnymi (Hel-Titan: ``pds``) -
# ``ship_roles.structure_ground_forces`` (obrońcy planety, walka naziemna, bombardowanie).
POINT_UNIT_STRUCTURE_GROUND_FORCES = "units.structure_ground_forces"
# PERMIT -> gracz może postawić 1 mecha i 1 piechotę zamiast PDS (Hecatoncheires: DEPLOY) -
# ``strategy_cards.common.place_structure(instead_mech=True)``.
POINT_STRUCTURE_PDS_AS_MECH = "structures.pds_as_mech"
# PERMIT -> gdy jednostki gracza używają PRODUCTION, może zdobyć 1 TG przed zapłatą (Tungstantus) -
# ``production.produce(commander_trade_good=True)``.
POINT_PRODUCTION_GAIN_TRADE_GOOD = "production.gain_trade_good"
# FORBID -> positions a MOVING unit treats as adjacent to every system on its route (ctx:
# ``position``, ``base_type``) - movement only, not board adjacency (Memoria, RULES.md 62.21).
POINT_MOVEMENT_UNIT_EXTRA_ADJACENT = "movement.unit_extra_adjacent"
# FORBID -> base types the player produces without spending resources: their cost is left out of
# the order's total (Navarch Feng: the flagship, RULES.md 62.21).
POINT_PRODUCTION_FREE_TYPES = "production.free_types"
# FORBID -> ``"<base_type>|<hits_on>|<dice>|<afb_hits_on>|<afb_dice>"``: ONE ship of that group
# fights with these values and may use SUSTAIN DAMAGE (The Cavalry, RULES.md 62.21).
POINT_COMBAT_CHAMPION = "combat.champion"
# FORBID -> base types of the player's NON-ship units in the space area of their space combat
# that may use SUSTAIN DAMAGE to cancel hits against their ships (Quantum Manipulator, 62.21).
POINT_COMBAT_HIT_SHIELDS = "combat.hit_shields"

# Rodzaje źródeł hooka (kto "posiada" wyjątek).
SOURCE_FACTION = "faction"
SOURCE_TECHNOLOGY = "technology"
SOURCE_AGENDA = "agenda"  # prawo w grze (decks.agenda_laws) - obowiązuje KAŻDEGO gracza
SOURCE_PROMISSORY = "promissory"  # notka leżąca w strefie gracza (promissory_notes_in_play)
SOURCE_RELIC = "relic"  # relikt przed graczem (PlayerState.relics)
SOURCE_LEADER = "leader"  # lider odblokowany lub gotowy (stan domyślny z danych frakcji)
SOURCE_BREAKTHROUGH = "breakthrough"  # odblokowany przełom frakcji
SOURCE_EFFECT = "effect"  # efekt trwały z magazynu (GameState.active_effects)
# Legendarna planeta kontrolowana przez gracza (karta zdolności legendarnej, RULES.md 60).
SOURCE_PLANET = "planet"
# Jednostka frakcyjna z polem ``ability`` (flagowiec, mech, ulepszenie frakcyjne) — id WARIANTU,
# którego gracz używa (RULES.md 61.3). Hook sam sprawdza, czy jednostka jest w danym systemie.
SOURCE_UNIT = "unit"
# Zasada ogólna z elementu planszy (Entropic Scar - RULES.md 1.5): źródło posiada KAŻDY gracz,
# a hook sam sprawdza warunek (np. statki w bliźnie). Rejestracja: ``declare_rule_source``.
SOURCE_RULE = "rule"
_RULE_SOURCES: set[str] = set()


def declare_rule_source(rule_id: str) -> HookSource:
    """Zgłasza zasadę ogólną jako źródło hooków posiadane przez każdego gracza."""
    _RULE_SOURCES.add(rule_id)
    return HookSource(SOURCE_RULE, rule_id)


class HookKind(Enum):
    """Rodzaj hooka; kolejność wartości = kolejność rozstrzygania (RULES.md 43.1 pkt 5)."""

    REPLACE = 0
    FORBID = 1
    PERMIT = 2
    MODIFY = 3
    TRIGGER = 4
    PERSISTENT = 5


@dataclass(frozen=True)
class HookSource:
    """Komponent, który wnosi wyjątek (np. frakcja ``arborec``, technologia ``amd``)."""

    kind: str
    component_id: str


HookFn = Callable[[GameState, str, Mapping[str, Any]], Any]
# Warunek hooka zdarzenia sprawdzany w chwili wyzwolenia: (stan, gracz, kontekst) -> bool.
ConditionFn = Callable[[GameState, str, Mapping[str, Any]], bool]
# Efekt jednorazowy komponentu (np. karty akcji): (stan-klon, rejestr, gracz, parametry) -> None.
# Mutuje przekazany klon; błąd walidacji = ValueError (wołający pracuje na klonie).
# ``registry`` typowany jako Any, by uniknąć cyklu importów (registry importuje ten moduł).
EffectFn = Callable[[GameState, Any, str, Mapping[str, Any]], None]


@dataclass(frozen=True)
class Hook:
    """Jeden zarejestrowany wyjątek."""

    point: str
    source: HookSource
    kind: HookKind
    fn: HookFn
    seq: int  # kolejność rejestracji (rozstrzyga remis w obrębie rodzaju)
    covers: str | None = None  # "<kategoria>:<id>" komponentu, który hook implementuje
    # --- tylko hooki zdarzeń (``on_event``) ---
    optional: bool = False  # „you may ...” -> oferta zamiast automatycznego uruchomienia
    where: tuple[tuple[str, str], ...] = ()  # filtr kontekstu zdarzenia (np. phase=strategy)
    condition: ConditionFn | None = None  # warunek sprawdzany przy wyzwoleniu
    label: str = ""  # opis dla UI/oferty
    # Wybór gracza (RULES.md 56): opis wejść formularza (liczy legalne opcje silnik). Z ``optional``
    # = oferta „may" (można odmówić); z ``decide`` = decyzja OBOWIĄZKOWA: gdy wybór jest realny,
    # silnik pyta gracza (nigdy nie wybiera za niego), a gdy opcja jest jedna - stosuje ją od razu.
    inputs: OfferInputsFn | None = None
    decide: bool = False
    # Kto podejmuje decyzję, jeśli to NIE właściciel źródła (np. ofiara Assault Cannon).
    decider: DeciderFn | None = None
    # Moduł wariantu (źródło, np. "black_spectrum"): hook działa TYLKO w grze, w której ten
    # moduł nałożył erratę na komponent ``covers``/źródła; ``None`` = wersja oficjalna
    # (wyłączana, gdy komponent podmieniono). Patrz ``variant_active`` i core/variants.py.
    variant: str | None = None


# Opis wyborów gracza dla efektu (formularz UI): (stan, rejestr, gracz) -> lista wejść.
InputsFn = Callable[[GameState, Any, str], list[dict[str, Any]]]
# Opis wyborów dla oferty/decyzji hooka zdarzenia: (stan, rejestr, decydent, kontekst) -> wejścia.
OfferInputsFn = Callable[[GameState, Any, str, Mapping[str, Any]], list[dict[str, Any]]]
# Wskazanie decydenta: (stan, właściciel źródła, kontekst) -> id gracza.
DeciderFn = Callable[[GameState, str, Mapping[str, Any]], str]

_REGISTRY: list[Hook] = []
_EFFECTS: dict[str, EffectFn] = {}
_INPUTS: dict[str, InputsFn] = {}
# Efekty/wejścia/zdolności WERSJI WARIANTU komponentu: (źródło modułu, klucz) -> funkcja.
_VARIANT_EFFECTS: dict[tuple[str, str], EffectFn] = {}
_VARIANT_INPUTS: dict[tuple[str, str], InputsFn] = {}
_VARIANT_ABILITIES: dict[tuple[str, str], EffectFn] = {}
_VARIANT_ABILITY_INPUTS: dict[tuple[str, str], InputsFn] = {}
_DATA_DRIVEN: set[str] = set()
# Zdolności technologii używane NIE jako akcja (np. Psychoarchaeology) - RULES.md 57.
_ABILITIES: dict[str, EffectFn] = {}
_ABILITY_INPUTS: dict[str, InputsFn] = {}
_loaded = False


def register(
    point: str,
    source: HookSource,
    kind: HookKind,
    covers: str | None = None,
    *,
    variant: str | None = None,
) -> Callable[[HookFn], HookFn]:
    """Dekorator rejestrujący funkcję jako hook na ``point`` dla ``source``.

    ``covers`` (``"<kategoria>:<id>"``, np. ``"technologies:amd"``) wskazuje komponent,
    którego efekt hook realizuje; na tej podstawie rejestr efektów oznacza go jako
    IMPLEMENTED i powstaje raport pokrycia (H3). Brak = hook bez przypisanego komponentu.
    ``variant`` = źródło modułu wariantu, którego wersję komponentu hook realizuje.
    """

    def decorate(fn: HookFn) -> HookFn:
        _REGISTRY.append(
            Hook(point, source, kind, fn, len(_REGISTRY), covers, variant=variant)
        )
        return fn

    return decorate


def on_event(
    event: GameEvent,
    moment: Moment,
    source: HookSource,
    *,
    kind: HookKind = HookKind.TRIGGER,
    optional: bool = False,
    where: Mapping[str, str] | None = None,
    condition: ConditionFn | None = None,
    covers: str | None = None,
    label: str = "",
    inputs: OfferInputsFn | None = None,
    decide: bool = False,
    decider: DeciderFn | None = None,
    variant: str | None = None,
) -> Callable[[HookFn], HookFn]:
    """Rejestruje hook ZDARZENIA: ``fn(state, player_id, ctx)`` odpalane przez ``triggers.fire``.

    * ``kind=TRIGGER`` (domyślnie): reakcja. ``optional=False`` = obowiązkowa (komponent w grze),
      ``optional=True`` = „you may” -> oferta w oknie REACTION dla posiadacza publicznego źródła.
    * ``kind=REPLACE``: „instead of” — ``fn`` zwraca prawdę, gdy zastąpiła zdarzenie (wołający
      pomija wtedy swój krok); opcjonalny REPLACE też staje się ofertą.
    * ``where``: filtr kontekstu (np. ``{"phase": "strategy"}``); ``condition``: warunek
      sprawdzany przy wyzwoleniu.
    * ``covers``: komponent, który hook realizuje (status IMPLEMENTED w rejestrze efektów).
    * ``inputs`` / ``decide`` / ``decider``: decyzje gracza (RULES.md 56) - patrz ``Hook``. Hook z
      ``decide`` czyta wybór z ``ctx["params"]`` (gdy wyboru nie ma, ``params`` zawiera jedyną
      legalną odpowiedź), a ``ctx["decider"]`` to gracz podejmujący decyzję.
    """
    if kind not in (HookKind.TRIGGER, HookKind.REPLACE):
        raise ValueError("Event hooks must be TRIGGER or REPLACE.")
    where_items = tuple(sorted((k, str(v)) for k, v in (where or {}).items()))

    def decorate(fn: HookFn) -> HookFn:
        _REGISTRY.append(
            Hook(
                event_point(event, moment), source, kind, fn, len(_REGISTRY), covers,
                optional, where_items, condition, label, inputs, decide, decider,
                variant,
            )
        )
        return fn

    return decorate


def register_effect(
    component_key: str, *, variant: str | None = None
) -> Callable[[EffectFn], EffectFn]:
    """Rejestruje efekt jednorazowy komponentu (``\"<kategoria>:<id>\"``), np. karty akcji.

    Komponent z efektem jest IMPLEMENTED (``covered_components``). Jeden efekt na komponent.
    ``variant`` = efekt wersji z modułu wariantu (core/variants.py).
    """

    def decorate(fn: EffectFn) -> EffectFn:
        if variant is not None:
            _register_variant(_VARIANT_EFFECTS, variant, component_key, fn)
            return fn
        if component_key in _EFFECTS:
            raise ValueError(f"Effect already registered for {component_key}.")
        _EFFECTS[component_key] = fn
        return fn

    return decorate


def register_effect_inputs(
    component_key: str, *, variant: str | None = None
) -> Callable[[InputsFn], InputsFn]:
    """Rejestruje opis wyborów gracza dla efektu komponentu (patrz ``hooks/action_card_inputs``)."""

    def decorate(fn: InputsFn) -> InputsFn:
        if variant is not None:
            _register_variant(_VARIANT_INPUTS, variant, component_key, fn)
            return fn
        if component_key in _INPUTS:
            raise ValueError(f"Inputs already registered for {component_key}.")
        _INPUTS[component_key] = fn
        return fn

    return decorate


def register_ability(
    tech_id: str, *, variant: str | None = None
) -> Callable[[EffectFn], EffectFn]:
    """Rejestruje zdolność technologii używaną poza akcją (``technologies:<id>`` = pokryta)."""

    def decorate(fn: EffectFn) -> EffectFn:
        if variant is not None:
            _register_variant(_VARIANT_ABILITIES, variant, tech_id, fn)
            return fn
        if tech_id in _ABILITIES:
            raise ValueError(f"Ability already registered for {tech_id}.")
        _ABILITIES[tech_id] = fn
        _DATA_DRIVEN.add(f"technologies:{tech_id}")
        return fn

    return decorate


def register_ability_inputs(
    tech_id: str, *, variant: str | None = None
) -> Callable[[InputsFn], InputsFn]:
    """Rejestruje opis wyborów zdolności technologii (formularz w UI)."""

    def decorate(fn: InputsFn) -> InputsFn:
        if variant is not None:
            _VARIANT_ABILITY_INPUTS[(variant, tech_id)] = fn
            return fn
        _ABILITY_INPUTS[tech_id] = fn
        return fn

    return decorate


def ability_for(tech_id: str) -> tuple[EffectFn, InputsFn | None] | None:
    """Zdolność technologii używana poza akcją albo ``None`` (wersja wariantu, gdy podmieniona)."""
    _ensure_loaded()
    variant = replaced_by(f"technologies:{tech_id}")
    if variant is not None:
        fn = _VARIANT_ABILITIES.get((variant, tech_id))
        return None if fn is None else (fn, _VARIANT_ABILITY_INPUTS.get((variant, tech_id)))
    fn = _ABILITIES.get(tech_id)
    return None if fn is None else (fn, _ABILITY_INPUTS.get(tech_id))


def all_abilities() -> list[str]:
    """Id technologii z zarejestrowaną zdolnością poza akcją."""
    _ensure_loaded()
    return sorted(_ABILITIES)


def inputs_for(component_key: str) -> InputsFn | None:
    """Opis wyborów efektu albo ``None`` (efekt bez parametrów lub brak efektu)."""
    _ensure_loaded()
    variant = replaced_by(component_key)
    if variant is not None:
        return _VARIANT_INPUTS.get((variant, component_key))
    return _INPUTS.get(component_key)


def effect_for(component_key: str) -> EffectFn | None:
    """Efekt jednorazowy komponentu albo ``None`` (brak = MANUAL, rozstrzyga operator).

    Komponent podmieniony erratą modułu wariantu ma efekt tylko z ``register_effect(...,
    variant=<źródło>)`` - oficjalny efekt nie pasuje już do jego tekstu.
    """
    _ensure_loaded()
    variant = replaced_by(component_key)
    if variant is not None:
        return _VARIANT_EFFECTS.get((variant, component_key))
    return _EFFECTS.get(component_key)


def _register_variant(
    table: dict[tuple[str, str], Any], variant: str, key: str, fn: Any
) -> None:
    if (variant, key) in table:
        raise ValueError(f"Variant {variant!r} effect already registered for {key}.")
    table[(variant, key)] = fn


# Rodzaj źródła hooka -> kategoria komponentu (klucz ``"<kategoria>:<id>"`` errat wariantów).
_SOURCE_CATEGORY: dict[str, str] = {
    SOURCE_TECHNOLOGY: "technologies",
    SOURCE_RELIC: "relics",
    SOURCE_LEADER: "leaders",
    SOURCE_BREAKTHROUGH: "breakthroughs",
    SOURCE_PROMISSORY: "promissory_notes",
    SOURCE_AGENDA: "agendas",
    SOURCE_UNIT: "units",
    SOURCE_PLANET: "planets",
}


def replaced_by(component_key: str) -> str | None:
    """Źródło modułu, którego errata podmieniła komponent w bieżącej grze, albo ``None``."""
    registry = _BOUND_REGISTRY
    replaced = getattr(registry, "variant_replaced", None) if registry is not None else None
    return replaced.get(component_key) if replaced else None


def hook_component_key(hook: Hook) -> str | None:
    """Komponent hooka: ``covers`` albo klucz z rodzaju i id źródła."""
    if hook.covers is not None:
        return hook.covers
    category = _SOURCE_CATEGORY.get(hook.source.kind)
    return f"{category}:{hook.source.component_id}" if category else None


def variant_active(hook: Hook) -> bool:
    """Czy hook obowiązuje w bieżącej grze: wersja hooka = wersja komponentu w grze.

    Oficjalny hook (``variant=None``) działa, dopóki komponentu nie podmieniono; hook wariantu
    działa tylko, gdy ten moduł podmienił komponent.
    """
    key = hook_component_key(hook)
    current = replaced_by(key) if key is not None else None
    return hook.variant == current


def _ensure_loaded() -> None:
    """Leniwie importuje pakiet ``core.hooks`` (jego moduły rejestrują się przy imporcie)."""
    global _loaded
    if not _loaded:
        _loaded = True
        import src.core.hooks  # noqa: F401  (import dla efektu ubocznego: rejestracja)


def all_hooks() -> list[Hook]:
    """Wszystkie zarejestrowane hooki (po załadowaniu pakietu ``core.hooks``)."""
    _ensure_loaded()
    return list(_REGISTRY)


def hook_by_seq(seq: int) -> Hook | None:
    """Hook o danym numerze rejestracji (do rozstrzygania ofert) albo ``None``."""
    _ensure_loaded()
    return next((h for h in _REGISTRY if h.seq == seq), None)


def declare_superseded(*component_keys: str) -> None:
    """Oznacza wersje kart zastąpione errata (np. Magen Defense Grid bez Ω).

    Talia gry zawiera tylko najnowszą wersję (``technology.generic_pool``), więc starsze nie
    wchodzą do rozgrywki i nie potrzebują hooka; liczą się jako pokryte w raporcie.
    """
    _DATA_DRIVEN.update(component_keys)


def declare_player_option(*component_keys: str) -> None:
    """Oznacza komponenty zrealizowane jako JAWNY wybór gracza w regule bazowej (parametr akcji).

    Np. Graviton Laser System (``exhaust_gls`` przy strzale Space Cannon) i AI Development
    Algorithm (``exhaust_aida`` przy produkcji): gracz świadomie włącza efekt, więc nie ma
    hooka, a komponent liczy się jako pokryty w raporcie.
    """
    _DATA_DRIVEN.update(component_keys)


def declare_data_driven(*component_keys: str) -> None:
    """Oznacza komponenty, których efekt w całości wynika z DANYCH (statystyki z assetów).

    Np. ulepszenia jednostek: liczby (koszt, walka, ruch, pojemność, Space Cannon...) czyta silnik
    z wariantu jednostki (``combat.resolve_unit_variant``), więc nie potrzeba hooka. Komponent
    liczy się jako pokryty (IMPLEMENTED) w raporcie, ale NIE ma funkcji hooka.
    """
    _DATA_DRIVEN.update(component_keys)


def declare_core_rule(*component_keys: str) -> None:
    """Oznacza komponenty, których efekt realizuje sama reguła bazowa w ``core/`` (bez hooka).

    Np. Covert Legislation: ukrytą agendę dobiera i rozstrzyga ``agenda_phase`` (RULES.md 51.6).
    """
    _DATA_DRIVEN.update(component_keys)


def covered_components() -> frozenset[str]:
    """Klucze ``"<kategoria>:<id>"`` komponentów, które mają zarejestrowany hook."""
    _ensure_loaded()
    covered = {h.covers for h in _REGISTRY if h.covers is not None and h.variant is None}
    return frozenset(covered | set(_EFFECTS) | _DATA_DRIVEN)


def covered_variant_components() -> frozenset[tuple[str, str]]:
    """(źródło modułu, ``"<kategoria>:<id>"``) wersji wariantów, które mają hook lub efekt."""
    _ensure_loaded()
    found = {
        (h.variant, h.covers)
        for h in _REGISTRY
        if h.variant is not None and h.covers is not None
    }
    return frozenset(found | set(_VARIANT_EFFECTS) | set(_VARIANT_ABILITIES))


# Podgląd skutku efektu (UI: „dotyczy: …"): (stan, rejestr, gracz) -> krótki tekst.
PreviewFn = Callable[[GameState, Any, str], str]
_PREVIEWS: dict[str, PreviewFn] = {}


def register_effect_preview(component_key: str) -> Callable[[PreviewFn], PreviewFn]:
    """Rejestruje podgląd skutku efektu liczony z bieżącego stanu (pole ``summary`` formularza)."""

    def decorate(fn: PreviewFn) -> PreviewFn:
        if component_key in _PREVIEWS:
            raise ValueError(f"Preview already registered for {component_key}.")
        _PREVIEWS[component_key] = fn
        return fn

    return decorate


def preview_for(component_key: str) -> PreviewFn | None:
    """Podgląd skutku komponentu albo ``None``."""
    _ensure_loaded()
    return _PREVIEWS.get(component_key)


def all_previews() -> list[str]:
    """Klucze komponentów z zarejestrowanym podglądem."""
    _ensure_loaded()
    return sorted(_PREVIEWS)


def all_input_keys() -> list[str]:
    """Klucze komponentów z zarejestrowanym formularzem wyborów."""
    _ensure_loaded()
    return sorted(_INPUTS)


_BOUND_REGISTRY: Any = None


def bind_registry(registry: Any) -> None:
    """Wiąże rejestr danych statycznych (ustawia go ``StaticDataRegistry``).

    Dane statyczne (frakcje, liderzy, przełomy) są niezmienne i identyczne dla każdej instancji,
    więc dopuszczamy jeden globalny dostęp — bez niego ``owned_sources`` nie znałoby domyślnych
    stanów liderów ani przełomu frakcji, a każdy punkt zaczepienia musiałby dostać ``registry``.
    Stanu GRY tu nie ma.
    """
    global _BOUND_REGISTRY
    _BOUND_REGISTRY = registry
    _unit_sources_cached.cache_clear()


def bound_registry() -> Any:
    """Powiązany rejestr danych statycznych (``None`` przed pierwszą inicjalizacją)."""
    return _BOUND_REGISTRY


def _registry_sources(player: Any) -> set[HookSource]:
    """Źródła wymagające danych statycznych: rodzina frakcji, liderzy, przełom."""
    registry = _BOUND_REGISTRY
    sources: set[HookSource] = set()
    if registry is None or player.faction is None:
        return sources
    faction = registry.factions.get(player.faction)
    if faction is not None:
        sources.add(HookSource(SOURCE_FACTION, registry.faction_family(faction)))
        for leader_id in faction.leaders:
            leader = registry.leaders.get(leader_id)
            default = "unlocked" if leader is not None and leader.type == "agent" else "locked"
            # Zablokowany i purge'owany lider nie jest źródłem (RULES.md 61.1).
            if player.leader_states.get(leader_id, default) not in ("locked", "purged"):
                sources.add(HookSource(SOURCE_LEADER, leader_id))
    if player.breakthrough_unlocked:
        breakthrough = registry.breakthrough_for_faction(player.faction)
        if breakthrough is not None:
            sources.add(HookSource(SOURCE_BREAKTHROUGH, breakthrough.id))
    return sources


# Filtry zdolności jednostek: (stan, gracz) -> typy bazowe, których jednostki frakcyjne tracą
# wydrukowane zdolności (Articles of War: mechy - RULES.md 51.6). Rejestrowane przez moduły
# hooków; czytają stan bezpośrednio (bez hooków - inaczej rekurencja przez ``owned_sources``).
UnitAbilityFilter = Callable[[GameState, str], frozenset[str]]
_UNIT_ABILITY_FILTERS: list[UnitAbilityFilter] = []


def register_unit_ability_filter(fn: UnitAbilityFilter) -> UnitAbilityFilter:
    """Rejestruje filtr zdolności jednostek (patrz ``_UNIT_ABILITY_FILTERS``)."""
    _UNIT_ABILITY_FILTERS.append(fn)
    return fn


def _suppressed_unit_types(state: GameState, player_id: str) -> frozenset[str]:
    _ensure_loaded()
    found: set[str] = set()
    for fn in _UNIT_ABILITY_FILTERS:
        found |= fn(state, player_id)
    return frozenset(found)


def unit_abilities_lost(state: GameState, player_id: str, base_type: str) -> bool:
    """Czy jednostki ``base_type`` gracza straciły wydrukowane zdolności (poza SUSTAIN DAMAGE)."""
    return base_type in _suppressed_unit_types(state, player_id)


# Leader proxies: (state, player) -> {leader id: proxy leader id}. A leader the player does NOT own
# that they may use as if it were theirs, its state being the proxy's (Ssruu: every other
# player's agent resolves to ``yssarilagent``, RULES.md 62.22). Registered by hook modules; they
# read the state directly (no hooks - ``owned_sources`` calls them).
LeaderProxyFn = Callable[[GameState, str], Mapping[str, str]]
_LEADER_PROXIES: list[LeaderProxyFn] = []


def register_leader_proxy(fn: LeaderProxyFn) -> LeaderProxyFn:
    """Registers a leader proxy provider (see ``_LEADER_PROXIES``)."""
    _LEADER_PROXIES.append(fn)
    return fn


def leader_proxies(state: GameState, player_id: str) -> dict[str, str]:
    """``{borrowed leader id: proxy leader id}`` the player may use (RULES.md 62.22)."""
    _ensure_loaded()
    if player_id not in state.players:
        return {}
    found: dict[str, str] = {}
    for fn in _LEADER_PROXIES:
        found.update(fn(state, player_id))
    return found


def leader_proxy(state: GameState, player_id: str, leader_id: str) -> str:
    """The leader whose state stands for ``leader_id`` for this player (itself without a proxy)."""
    return leader_proxies(state, player_id).get(leader_id, leader_id)


def _unit_base_type(unit_id: str) -> str:
    registry = _BOUND_REGISTRY
    unit = registry.units.get(unit_id) if registry is not None else None
    return str(unit.base_type) if unit is not None else ""


def _unit_sources(player: Any) -> frozenset[HookSource]:
    """Warianty jednostek frakcyjnych ze zdolnością, których gracz używa (RULES.md 61.3)."""
    if _BOUND_REGISTRY is None or player.faction is None:
        return frozenset()
    return _unit_sources_cached(
        player.faction, tuple(sorted(player.technologies)), bool(player.breakthrough_unlocked),
        bool(player.breakthrough_flipped),
    )


@functools.lru_cache(maxsize=512)
def _unit_sources_cached(
    faction_id: str, technologies: tuple[str, ...], breakthrough: bool, flipped: bool = False
) -> frozenset[HookSource]:
    from src.core.combat import resolve_unit_variant  # lokalnie: combat importuje rules_hooks

    registry = _BOUND_REGISTRY
    if registry is None:
        return frozenset()
    base_types = {unit.base_type for unit in registry.units.values()}
    found: set[HookSource] = set()
    for base_type in base_types:
        unit = resolve_unit_variant(
            registry, faction_id, list(technologies), base_type, breakthrough, flipped
        )
        if unit is not None and unit.faction and unit.ability:
            found.add(HookSource(SOURCE_UNIT, unit.id))
    return frozenset(found)


def _promissory_sources(state: GameState, player_id: str) -> set[HookSource]:
    """Szablony notek w strefie (``<color>_sftt``) + commanderzy z Alliance (RULES.md 61.2)."""
    registry = _BOUND_REGISTRY
    player = state.players[player_id]
    if registry is None or not player.promissory_notes_in_play:
        return set()
    from src.core import promissory_play  # lokalnie: promissory_play importuje ten moduł
    from src.core.hooks import promissory_generic

    sources: set[HookSource] = set()
    for note_id in player.promissory_notes_in_play:
        try:
            template, _owner = promissory_play.resolve(state, registry, note_id)
        except ValueError:
            continue
        sources.add(HookSource(SOURCE_PROMISSORY, template))
    sources.update(
        HookSource(SOURCE_LEADER, leader_id)
        for leader_id in promissory_generic.alliance_commanders(state, player_id)
    )
    return sources


def granted_commanders(state: GameState, player_id: str) -> list[str]:
    """Id commanderów innych frakcji z efektów trwałych gracza (Yin Ascendant) - dla widoku."""
    return sorted({src.component_id for src in _granted_commanders(state, player_id)})


def _granted_commanders(state: GameState, player_id: str) -> set[HookSource]:
    """Commanderzy innych frakcji z efektów trwałych gracza (``data.commanders``) — działają „tak,
    jakby byli odblokowani” (Yin Ascendant, RULES.md 62.10)."""
    return {
        HookSource(SOURCE_LEADER, str(leader_id))
        for effect in state.active_effects
        if effect.owner == player_id
        for leader_id in effect.data.get("commanders") or ()
    }


def _legendary_sources(player: Any) -> set[HookSource]:
    """Karty zdolności legendarnych planet, które gracz ma (kontroluje ich planety)."""
    registry = _BOUND_REGISTRY
    if registry is None:
        return set()
    sources: set[HookSource] = set()
    for planet_id in player.controlled_planets:
        planet = registry.planets.get(planet_id)
        if planet is not None and planet.legendary_ability_name:
            sources.add(HookSource(SOURCE_PLANET, planet_id))
    return sources


def owned_sources(state: GameState, player_id: str) -> frozenset[HookSource]:
    """Źródła wyjątków gracza (RULES.md 54).

    Publiczne i zawsze widoczne dla wszystkich: frakcja (i jej rodzina), technologie, relikty przed
    graczem, notki w jego strefie, odblokowani liderzy, odblokowany przełom, prawa w grze
    (``decks.agenda_laws`` - obowiązują KAŻDEGO gracza; hook prawa sprawdza w kontekście, kogo
    dotyczy) oraz efekty trwałe z magazynu (własne i globalne).

    Karty NA RĘCE (karty akcji, ukryte notki) NIE są źródłami — gra się nimi przez STOP
    (RULES.md 43.4), żeby pytanie nie zdradzało ręki. Liderzy i przełom wymagają
    ``bind_registry`` (dane statyczne); bez niego są pomijani.
    """
    player = state.players.get(player_id)
    if player is None:
        return frozenset()
    sources: set[HookSource] = {HookSource(SOURCE_TECHNOLOGY, t) for t in player.technologies}
    sources.update(HookSource(SOURCE_PROMISSORY, n) for n in player.promissory_notes_in_play)
    sources.update(_promissory_sources(state, player_id))
    sources.update(_granted_commanders(state, player_id))
    sources.update(HookSource(SOURCE_LEADER, lid) for lid in leader_proxies(state, player_id))
    suppressed = _suppressed_unit_types(state, player_id)
    sources.update(
        src for src in _unit_sources(player)
        if not suppressed or _unit_base_type(src.component_id) not in suppressed
    )
    sources.update(HookSource(SOURCE_RELIC, r) for r in player.relics)
    sources.update(_legendary_sources(player))
    sources.update(HookSource(SOURCE_AGENDA, law) for law in state.decks.agenda_laws)
    if state.agenda is not None and state.agenda.resolving is not None:
        # Rozstrzygana agenda (także dyrektywa i „Against”) obowiązuje każdego gracza, dopóki
        # trwa jej efekt (decyzje graczy) - RULES.md 51.6.
        sources.add(HookSource(SOURCE_AGENDA, state.agenda.resolving))
    sources.update(
        HookSource(SOURCE_EFFECT, e.key)
        for e in state.active_effects
        if e.owner is None or e.owner == player_id
    )
    if player.faction is not None:
        sources.add(HookSource(SOURCE_FACTION, player.faction))
    sources.update(_registry_sources(player))
    sources.update(HookSource(SOURCE_RULE, rule) for rule in _RULE_SOURCES)
    return frozenset(sources)


def hooks_at(point: str, state: GameState, player_id: str) -> list[Hook]:
    """Hooki punktu ``point`` należące do gracza, w deterministycznej kolejności."""
    _ensure_loaded()
    owned = owned_sources(state, player_id)
    found = [
        h for h in _REGISTRY if h.point == point and h.source in owned and variant_active(h)
    ]
    return sorted(found, key=lambda h: (h.kind.value, h.seq))


def forbidden(
    point: str, state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> frozenset[str]:
    """Suma zakazów ze wszystkich hooków FORBID punktu (każdy zwraca iterowalne napisy)."""
    context = ctx or {}
    result: set[str] = set()
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.FORBID:
            result.update(hook.fn(state, player_id, context))
    return frozenset(result)


def permits(
    point: str, state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> bool:
    """Czy którykolwiek hook PERMIT punktu zezwala (brak hooków = ``False``)."""
    context = ctx or {}
    return any(
        bool(hook.fn(state, player_id, context))
        for hook in hooks_at(point, state, player_id)
        if hook.kind is HookKind.PERMIT
    )


def run_persistent(
    point: str, state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> int:
    """Uruchamia hooki PERSISTENT punktu (efekt trwały reaguje na zdarzenie silnika).

    Zwraca liczbę uruchomionych hooków. Hook MUTUJE ``state`` (klon wołającego).
    """
    context = ctx or {}
    count = 0
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.PERSISTENT:
            hook.fn(state, player_id, context)
            count += 1
    return count


def modify[N: (int, float)](
    point: str,
    state: GameState,
    player_id: str,
    base: N,
    ctx: Mapping[str, Any] | None = None,
) -> N:
    """Przepuszcza ``base`` przez hooki MODIFY (każdy: ``fn(...) -> delta`` dodawana do wyniku).

    Typ wyniku = typ ``base`` (int dla liczb całkowitych, float dla kosztów ułamkowych).
    """
    context = ctx or {}
    total = float(base)
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.MODIFY:
            total += float(hook.fn(state, player_id, context))
    result: int | float = int(total) if isinstance(base, int) else total
    return cast(N, result)


@contextmanager
def temporary_hooks() -> Iterator[None]:
    """Testy: rejestracje dokonane w bloku znikają po wyjściu (rejestr wraca do stanu sprzed)."""
    _ensure_loaded()
    snapshot = list(_REGISTRY)
    effects = dict(_EFFECTS)
    inputs = dict(_INPUTS)
    try:
        yield
    finally:
        _REGISTRY[:] = snapshot
        _EFFECTS.clear()
        _EFFECTS.update(effects)
        _INPUTS.clear()
        _INPUTS.update(inputs)

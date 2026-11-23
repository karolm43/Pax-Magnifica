"""Kronika partii: rejestr bitew, podbojów i transakcji + „wnioski" do podsumowania.

Czyste funkcje nad ``GameState``. To warstwa PREZENTACYJNA (statystyki końcowe) — niczego nie
rozstrzyga w regułach TI4. Zapis dzieje się w trzech miejscach silnika: koniec walki
(``battle``), przejęcie planety (``invasion``) i transakcja (``transaction``).

⚠️ Definicja „zdrady" (decyzja użytkownika): atak (walka albo przejęcie planety) na gracza,
z którym napastnik miał weksel Alliance / Support for the Throne / Ceasefire (w dowolnym
kierunku). Transakcje są liczone tylko do „Dyplomaty".
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.core import achievements, chronicle_awards, chronicle_feats, objectives
from src.core.game_state import ActiveCombat, GameState
from src.core.registry import StaticDataRegistry

# Tytuły i progi osiągnięć: assets/config/achievements.json (core/achievements.py).
_p = achievements.param


# Weksle „paktu" (po sufiksie id karty; id = ``<kolor wystawcy>_<sufiks>``): Ceasefire,
# Alliance, Support for the Throne (także warianty ``*_sftt`` z dodatków).
_PACT_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("_cf", "Ceasefire"),
    ("_an", "Alliance"),
    ("_sftt", "Support for the Throne"),
)


def pact_between(state: GameState, a: str, b: str) -> str | None:
    """Nazwa weksla paktu między graczami (w dowolnym kierunku, w ręce albo w strefie gry).

    Gracz „ma pakt" z drugim, gdy trzyma jego Ceasefire / Alliance / Support for the Throne.
    """
    for holder_id, issuer_id in ((a, b), (b, a)):
        holder = state.players.get(holder_id)
        issuer = state.players.get(issuer_id)
        if holder is None or issuer is None or not issuer.color:
            continue
        prefix = f"{issuer.color}_"
        for note in [*holder.promissory_notes_in_play, *holder.private.promissory_notes]:
            if not note.startswith(prefix):
                continue
            for suffix, name in _PACT_SUFFIXES:
                if note.endswith(suffix):
                    return name
    return None


def record_deal(state: GameState, a: str, b: str, a_gave: int = 0, b_gave: int = 0) -> None:
    """Zapisuje transakcję: ``a_gave`` / ``b_gave`` = trade goods + commodities od strony."""
    state.chronicle.deals.append(
        {"round": state.round_number, "a": a, "b": b, "a_gave": a_gave, "b_gave": b_gave}
    )


def snapshot_round(state: GameState) -> None:
    """Zapisuje migawkę VP bieżącej rundy (nadpisuje, jeśli runda ma już wpis)."""
    entry = {
        "round": state.round_number,
        "vp": {pid: p.victory_points for pid, p in state.players.items()},
    }
    rounds = state.chronicle.rounds
    if rounds and rounds[-1]["round"] == state.round_number:
        rounds[-1] = entry
    else:
        rounds.append(entry)


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _ranks(vp: dict[str, int]) -> dict[str, int]:
    """Miejsce każdego gracza (1 = najwięcej VP; remis dzieli miejsce)."""
    return {pid: 1 + sum(1 for other in vp.values() if other > mine) for pid, mine in vp.items()}


def record_battle(state: GameState, combat: ActiveCombat) -> None:
    """Zapisuje zakończoną walkę (kosmiczną/naziemną). Mutuje stan."""
    losses = {combat.attacker: 0, combat.defender: 0}
    lost_types: dict[str, dict[str, int]] = {combat.attacker: {}, combat.defender: {}}
    for entry in combat.log:
        for pid, lost in (entry.get("losses") or {}).items():
            if pid in losses:
                losses[pid] += sum(int(n) for n in lost.values())
                for base_type, n in lost.items():
                    if int(n) > 0:
                        lost_types[pid][str(base_type)] = lost_types[pid].get(
                            str(base_type), 0
                        ) + int(n)
    state.chronicle.battles.append(
        {
            "round": state.round_number,
            "kind": combat.kind,
            "position": combat.position,
            "planet": combat.planet,
            "attacker": combat.attacker,
            "defender": combat.defender,
            "winner": combat.winner,
            "rounds": combat.round,
            "losses": losses,
            "lost_types": lost_types,
            "pact": (pact := pact_between(state, combat.attacker, combat.defender)),
            "betrayal": pact is not None,
            "retreated": sorted(combat.retreated),
            "survivors": _survivors(state, combat),
        }
    )


def _survivors(state: GameState, combat: ActiveCombat) -> int:
    """Ile jednostek zwycięzcy zostało na polu bitwy (bez struktur na planecie)."""
    system = state.systems.get(combat.position)
    if combat.winner is None or system is None:
        return 0
    if combat.kind == "ground" and combat.planet:
        units = system.planet_units.get(combat.planet, {}).get(combat.winner, {})
        return sum(n for bt, n in units.items() if bt not in _STRUCTURES)
    return sum(system.space_units.get(combat.winner, {}).values())


def battle_history(state: GameState) -> list[dict[str, Any]]:
    """Historia bitew dla UI („co się tu wydarzyło”): ``camelCase``, kolejność chronologiczna.

    Warstwa PREZENTACYJNA — dane do narracji (``battleLore.ts``) i listy w teczce systemu.
    ``id`` = numer bitwy w partii (stabilny, od 0); ``lostTypes`` = straty wg typu bazowego.
    """
    out: list[dict[str, Any]] = []
    for i, b in enumerate(state.chronicle.battles):
        out.append(
            {
                "id": i,
                "round": b["round"],
                "kind": b["kind"],
                "position": b["position"],
                "planet": b["planet"],
                "attacker": b["attacker"],
                "defender": b["defender"],
                "winner": b["winner"],
                "rounds": b["rounds"],
                "losses": dict(b["losses"]),
                "lostTypes": {pid: dict(t) for pid, t in b.get("lost_types", {}).items()},
                "betrayal": bool(b.get("betrayal")),
            }
        )
    return out


def record_conquest(state: GameState, by: str, from_player: str, planet: str) -> None:
    """Zapisuje przejęcie planety innemu graczowi (mutuje stan)."""
    state.chronicle.conquests.append(
        {
            "round": state.round_number,
            "by": by,
            "from": from_player,
            "planet": planet,
            "pact": (pact := pact_between(state, by, from_player)),
            "betrayal": pact is not None,
        }
    )


# --------------------------------------------------------------------------- wnioski


def _top(counts: dict[str, int]) -> list[str]:
    """Gracze z najwyższym (dodatnim) wynikiem — pusta lista, gdy brak lidera lub remis."""
    if not counts:
        return []
    best = max(counts.values())
    leaders = [p for p, n in counts.items() if n == best]
    return leaders if best > 0 and len(leaders) == 1 else []


_Adder = Callable[..., None]
_Namer = Callable[[str], str]


def _race_highlights(state: GameState, who: _Namer, add: _Adder) -> None:
    """Wnioski z wyścigu o punkty (migawki rund) i z hojności przy stole (transakcje)."""
    chron = state.chronicle
    snaps = [dict(s["vp"]) for s in chron.rounds]
    rounds_no = [int(s["round"]) for s in chron.rounds]
    final = {pid: p.victory_points for pid, p in state.players.items()}
    if rounds_no and rounds_no[-1] == state.round_number:
        snaps[-1] = final
    else:
        snaps.append(final)
        rounds_no.append(state.round_number)
    winner = state.winner_id
    ranks = [_ranks(s) for s in snaps]

    if len(state.players) >= 3 and len(snaps) >= 2:
        climbs = {
            pid: max(r[pid] for r in ranks) - ranks[-1][pid]
            for pid in state.players
            if all(pid in r for r in ranks)
        }
        top = _top(climbs)
        if top and climbs[top[0]] >= _p("comeback", "min_places"):
            worst = max(r[top[0]] for r in ranks)
            add(
                "comeback",
                f"{who(top[0])} climbed from {_ordinal(worst)} place to "
                f"{_ordinal(ranks[-1][top[0]])}.",
                top,
                stat=f"{_ordinal(worst)} to {_ordinal(ranks[-1][top[0]])}",
            )

        led = {
            pid: sum(
                1
                for s in snaps[:-1]
                if s[pid] == max(s.values()) > 0 and list(s.values()).count(s[pid]) == 1
            )
            for pid in state.players
            if pid != winner
        }
        fallen = _top(led)
        if fallen:
            add(
                "fallen_favorite",
                f"{who(fallen[0])} led the race in {led[fallen[0]]} round"
                f"{'s' if led[fallen[0]] > 1 else ''} but never reached the throne.",
                fallen,
                stat=f"led {led[fallen[0]]} rounds",
            )

    gains: dict[str, tuple[int, int]] = {}
    previous = dict.fromkeys(state.players, 0)
    for rnd, snap in zip(rounds_no, snaps, strict=True):
        for pid, vp in snap.items():
            gain = vp - previous.get(pid, 0)
            if gain > gains.get(pid, (0, 0))[0]:
                gains[pid] = (gain, rnd)
        previous = snap
    best = max(gains.items(), key=lambda kv: kv[1][0], default=None)
    if best and best[1][0] >= _p("round_to_remember", "min_vp"):
        add(
            "round_to_remember",
            f"{who(best[0])} scored {best[1][0]} victory points in round {best[1][1]}.",
            [best[0]],
            stat=f"+{best[1][0]} VP",
        )

    if (
        winner
        and len(snaps) >= _p("wire_to_wire", "min_rounds")
        and all(s[winner] == max(s.values()) for s in snaps if winner in s)
        and any(s[winner] > 0 for s in snaps)
    ):
        add(
            "wire_to_wire",
            f"{who(winner)} was never behind in the race for the throne.",
            [winner],
            stat=f"{len(snaps)} rounds",
        )

    given: dict[str, int] = {}
    for d in chron.deals:
        given[d["a"]] = given.get(d["a"], 0) + int(d.get("a_gave", 0))
        given[d["b"]] = given.get(d["b"], 0) + int(d.get("b_gave", 0))
    generous = _top(given)
    if generous and given[generous[0]] >= _p("benefactor", "min_given"):
        add(
            "benefactor",
            f"{who(generous[0])} handed over {given[generous[0]]} trade goods and "
            f"commodities to other players.",
            generous,
            stat=f"{given[generous[0]]} given",
        )


_STRUCTURES = ("pds", "spacedock")
_MECATOL_IDS = ("mr", "mrte")


def _board_highlights(
    state: GameState, registry: StaticDataRegistry, who: _Namer, add: _Adder
) -> None:
    """Wnioski z końcowego obrazu planszy: Mecatol, legendy, domy, struktury, obecność."""
    owners = objectives.planet_owners(state)

    throne = next((owners[p] for p in _MECATOL_IDS if p in owners), None)
    if throne:
        add(
            "throne_room",
            f"{who(throne)} held Mecatol Rex when the game ended.",
            [throne],
            stat="Mecatol Rex",
        )

    legends: dict[str, int] = {}
    for planet_id, owner in owners.items():
        planet = registry.planets.get(planet_id)
        if planet and planet.legendary_ability_name:
            legends[owner] = legends.get(owner, 0) + 1
    top = _top(legends)
    if top and legends[top[0]] >= _p("legend_collector", "min_legends"):
        add(
            "legend_collector",
            f"{who(top[0])} controlled {legends[top[0]]} legendary planets.",
            top,
            stat=f"{legends[top[0]]} legends",
        )

    hunted: dict[str, int] = {}
    exiled: list[str] = []
    for pid, player in state.players.items():
        faction = registry.factions.get(player.faction) if player.faction else None
        homes = list(faction.home_planets) if faction else []
        if homes and all(owners.get(h) not in (None, pid) for h in homes):
            exiled.append(pid)
        for planet_id in homes:
            holder = owners.get(planet_id)
            if holder and holder != pid:
                hunted[holder] = hunted.get(holder, 0) + 1
    hunter = _top(hunted)
    if hunter:
        add(
            "homeworld_hunter",
            f"{who(hunter[0])} held {hunted[hunter[0]]} homeworld"
            f"{'s' if hunted[hunter[0]] > 1 else ''} of other players.",
            hunter,
            stat=f"{hunted[hunter[0]]} homeworlds",
        )
    if exiled:
        add(
            "exile",
            f"{who(exiled[0])} ended the game without a single one of their own homeworlds.",
            exiled[:1],
            stat="0 homeworlds",
        )

    structures: dict[str, int] = {}
    presence: dict[str, set[str]] = {}
    for position, system in state.systems.items():
        for pid in system.space_units:
            presence.setdefault(pid, set()).add(position)
        for per_player in system.planet_units.values():
            for pid, units in per_player.items():
                presence.setdefault(pid, set()).add(position)
                structures[pid] = structures.get(pid, 0) + sum(
                    n for bt, n in units.items() if bt in _STRUCTURES
                )
    builder = _top(structures)
    if builder and structures[builder[0]] >= _p("master_builder", "min_structures"):
        add(
            "master_builder",
            f"{who(builder[0])} raised {structures[builder[0]]} PDS and space docks.",
            builder,
            stat=f"{structures[builder[0]]} structures",
        )
    spread = _top({pid: len(s) for pid, s in presence.items()})
    if spread and len(presence[spread[0]]) >= _p("everywhere", "min_systems"):
        add(
            "everywhere",
            f"{who(spread[0])} had forces in {len(presence[spread[0]])} different systems.",
            spread,
            stat=f"{len(presence[spread[0]])} systems",
        )


def highlights(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """Wnioski z przebiegu partii: ``{key, title, detail, players}`` (angielski tekst dla UI)."""
    chron = state.chronicle

    def who(pid: str) -> str:
        player = state.players.get(pid)
        faction = registry.factions.get(player.faction) if player and player.faction else None
        return faction.name if faction else (player.display_name if player else pid)

    def where(battle: dict[str, Any]) -> str:
        planet = registry.planets.get(battle["planet"]) if battle["planet"] else None
        return planet.name if planet else f"system {battle['position']}"

    out: list[dict[str, Any]] = []

    def add(key: str, detail: str, players: list[str], stat: str = "") -> None:
        if achievements.enabled(key):
            out.append(
                {
                    "key": key,
                    "title": achievements.title(key),
                    "detail": detail,
                    "players": players,
                    "stat": stat,
                }
            )

    battles = chron.battles
    total_lost = [sum(b["losses"].values()) for b in battles]

    if battles:
        i = max(range(len(battles)), key=lambda k: total_lost[k])
        b = battles[i]
        if total_lost[i] >= _p("greatest_battle", "min_units_lost"):
            kind = "ground battle" if b["kind"] == "ground" else "space battle"
            add(
                "greatest_battle",
                f"{who(b['attacker'])} against {who(b['defender'])} at {where(b)}, round "
                f"{b['round']}: {total_lost[i]} units lost in a single {kind}.",
                [b["attacker"], b["defender"]],
                stat=f"{total_lost[i]} units lost",
            )

        j = max(range(len(battles)), key=lambda k: battles[k]["rounds"])
        longest = battles[j]
        if longest["rounds"] >= _p("longest_battle", "min_rounds"):
            add(
                "longest_battle",
                f"{who(longest['attacker'])} and {who(longest['defender'])} fought "
                f"{longest['rounds']} rounds of combat at {where(longest)}.",
                [longest["attacker"], longest["defender"]],
                stat=f"{longest['rounds']} rounds",
            )

        crush = [
            (k, battles[k])
            for k in range(len(battles))
            if battles[k]["winner"] == battles[k]["attacker"]
            and battles[k]["losses"][battles[k]["winner"]] == 0
            and total_lost[k] >= _p("crushing_victory", "min_kills")
        ]
        if crush:
            k, c = max(crush, key=lambda t: total_lost[t[0]])
            add(
                "crushing_victory",
                f"{who(c['winner'])} destroyed {total_lost[k]} units at {where(c)} "
                f"without losing a single one.",
                [c["winner"]],
                stat=f"{total_lost[k]} kills, 0 lost",
            )

        walls = [
            (k, battles[k])
            for k in range(len(battles))
            if battles[k]["winner"] == battles[k]["defender"]
            and battles[k]["losses"][battles[k]["defender"]] == 0
            and total_lost[k] >= _p("unbreakable_wall", "min_kills")
        ]
        if walls:
            k, w = max(walls, key=lambda t: total_lost[t[0]])
            add(
                "unbreakable_wall",
                f"{who(w['defender'])} held {where(w)} against {who(w['attacker'])}, "
                f"destroying {total_lost[k]} attackers without a single loss.",
                [w["defender"]],
                stat=f"{total_lost[k]} kills, 0 lost",
            )

        pyrrhic = [
            (k, battles[k])
            for k in range(len(battles))
            if battles[k]["winner"]
            and battles[k]["losses"][battles[k]["winner"]]
            >= _p("pyrrhic_victory", "min_own_losses")
            and battles[k]["losses"][battles[k]["winner"]]
            > total_lost[k] - battles[k]["losses"][battles[k]["winner"]]
        ]
        if pyrrhic:
            k, p = max(pyrrhic, key=lambda t: total_lost[t[0]])
            add(
                "pyrrhic_victory",
                f"{who(p['winner'])} took {where(p)}, but lost "
                f"{p['losses'][p['winner']]} units doing it, more than the enemy.",
                [p["winner"]],
                stat=f"{p['losses'][p['winner']]} units lost",
            )

        # Zwycięstwa wg rodzaju walki oraz bilans (niepokonani).
        wins: dict[str, dict[str, int]] = {"space": {}, "ground": {}}
        played: dict[str, int] = {}
        won: dict[str, int] = {}
        pair_fights: dict[frozenset[str], int] = {}
        for b in battles:
            for pid in (b["attacker"], b["defender"]):
                played[pid] = played.get(pid, 0) + 1
            if b["winner"]:
                wins[b["kind"]][b["winner"]] = wins[b["kind"]].get(b["winner"], 0) + 1
                won[b["winner"]] = won.get(b["winner"], 0) + 1
            pair = frozenset((b["attacker"], b["defender"]))
            pair_fights[pair] = pair_fights.get(pair, 0) + 1
        for kind, key, text in (
            ("space", "lord_of_the_void", "space battles"),
            ("ground", "ground_master", "ground battles"),
        ):
            top = _top(wins[kind])
            if top and wins[kind][top[0]] >= _p(key, "min_wins"):
                add(
                    key,
                    f"{who(top[0])} won {wins[kind][top[0]]} {text}.",
                    top,
                    stat=f"{wins[kind][top[0]]} wins",
                )
        unbeaten = [
            p
            for p, n in played.items()
            if n >= _p("undefeated", "min_battles") and won.get(p, 0) == n
        ]
        if unbeaten:
            add(
                "undefeated",
                f"{who(unbeaten[0])} won every one of their {played[unbeaten[0]]} battles.",
                unbeaten[:1],
                stat=f"{played[unbeaten[0]]} wins, 0 losses",
            )
        rivalry = max(pair_fights, key=lambda p: pair_fights[p])
        if pair_fights[rivalry] >= _p("rivalry", "min_clashes"):
            a, b2 = sorted(rivalry)
            add(
                "rivalry",
                f"{who(a)} and {who(b2)} clashed {pair_fights[rivalry]} times.",
                [a, b2],
                stat=f"{pair_fights[rivalry]} clashes",
            )

        mutual = [b for b in battles if b["winner"] is None and sum(b["losses"].values()) > 0]
        if mutual:
            m = max(mutual, key=lambda b: sum(b["losses"].values()))
            add(
                "mutual_destruction",
                f"{who(m['attacker'])} and {who(m['defender'])} destroyed each other "
                f"completely at {where(m)}. Nobody held the field.",
                [m["attacker"], m["defender"]],
                stat=f"{sum(m['losses'].values())} units lost",
            )

    # Zdrady: ataki na byłych partnerów handlowych (walki + podboje).
    betrayals = [b for b in battles if b["betrayal"]] + [
        c for c in chron.conquests if c["betrayal"]
    ]
    if betrayals:
        traitors: dict[str, int] = {}
        for e in betrayals:
            by = e.get("attacker") or e["by"]
            traitors[by] = traitors.get(by, 0) + 1
        worst = _top(traitors) or [max(traitors, key=lambda p: traitors[p])]
        victim_counts: dict[str, int] = {}
        for e in betrayals:
            if (e.get("attacker") or e["by"]) == worst[0]:
                v = e.get("defender") or e["from"]
                victim_counts[v] = victim_counts.get(v, 0) + 1
        victim = max(victim_counts, key=lambda p: victim_counts[p])
        n = traitors[worst[0]]
        pact = next(
            e["pact"]
            for e in betrayals
            if (e.get("attacker") or e["by"]) == worst[0]
            and (e.get("defender") or e["from"]) == victim
        )
        add(
            "betrayal",
            f"{who(worst[0])} struck {who(victim)} while holding a {pact} promissory note"
            f" between them" + (f" ({n} treacherous attacks in total)." if n > 1 else "."),
            [worst[0], victim],
            stat=str(pact),
        )

    attacks: dict[str, int] = {}
    defended: dict[str, int] = {}
    for b in battles:
        attacks[b["attacker"]] = attacks.get(b["attacker"], 0) + 1
        defended[b["defender"]] = defended.get(b["defender"], 0) + 1
    for pid in _top(attacks):
        if attacks[pid] >= _p("warmonger", "min_attacks"):
            add(
                "warmonger",
                f"{who(pid)} started {attacks[pid]} battles.",
                [pid],
                stat=f"{attacks[pid]} battles",
            )
    for pid in _top(defended):
        if defended[pid] >= _p("besieged", "min_attacked"):
            add(
                "besieged",
                f"{who(pid)} was attacked {defended[pid]} times.",
                [pid],
                stat=f"{defended[pid]} attacks",
            )

    conquered: dict[str, int] = {}
    for c in chron.conquests:
        conquered[c["by"]] = conquered.get(c["by"], 0) + 1
    for pid in _top(conquered):
        add(
            "conqueror",
            f"{who(pid)} took {conquered[pid]} planet{'s' if conquered[pid] > 1 else ''} "
            f"from other players.",
            [pid],
            stat=f"{conquered[pid]} planets",
        )

    deals: dict[str, int] = {}
    for d in chron.deals:
        for pid in (d["a"], d["b"]):
            deals[pid] = deals.get(pid, 0) + 1
    for pid in _top(deals):
        add(
            "diplomat",
            f"{who(pid)} made {deals[pid]} deals at the table.",
            [pid],
            stat=f"{deals[pid]} deals",
        )
    if chron.deals:
        loners = [pid for pid in state.players if pid not in deals]
        if len(loners) == 1:
            add(
                "hermit",
                f"{who(loners[0])} never made a single deal while everyone else traded.",
                loners,
                stat="0 deals",
            )

    # Planeta, która najczęściej zmieniała właściciela.
    per_planet: dict[str, list[str]] = {}
    for c in chron.conquests:
        per_planet.setdefault(c["planet"], []).append(c["by"])
    if per_planet:
        planet_id = max(per_planet, key=lambda p: len(per_planet[p]))
        takers = per_planet[planet_id]
        if len(takers) >= _p("torn_world", "min_captures"):
            planet = registry.planets.get(planet_id)
            add(
                "torn_world",
                f"{planet.name if planet else planet_id} changed hands {len(takers)} times.",
                list(dict.fromkeys(takers)),
                stat=f"{len(takers)} captures",
            )

    _race_highlights(state, who, add)
    _board_highlights(state, registry, who, add)
    chronicle_awards.extra_highlights(state, registry, who, add)
    chronicle_feats.feats(state, registry, who, add)

    if not battles and state.winner_id:
        add(
            "peaceful_galaxy",
            "Not a single battle was fought. The throne was won by wits alone.",
            [state.winner_id],
            stat="0 battles",
        )
    if battles and state.winner_id and not attacks.get(state.winner_id, 0):
        add(
            "quiet_victory",
            f"{who(state.winner_id or '')} won the throne without starting a single battle.",
            [state.winner_id or ""],
            stat="0 battles started",
        )
    return out

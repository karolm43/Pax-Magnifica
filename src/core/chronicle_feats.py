"""Osiągnięcia kroniki: zdrada i cwaniactwo, polityka przy stole, pamiętne walki, imperium.

Trzeci moduł wniosków (po ``chronicle`` i ``chronicle_awards``) — korzysta z zapisów
``core/chronicle_log.py`` (agendy, ostrzał spoza walki, pasy, mówca, karty, eksploracje,
Mecatol, War Suny). Warstwa PREZENTACYJNA: niczego nie rozstrzyga w regułach TI4.

⚠️ ZAŁOŻENIA (decyzja projektowa, nie reguła gry):
- „Oathbreaker" = atak na gracza, z którym napastnik DO TEJ RUNDY zawarł najwięcej transakcji
  (jedyny lider, co najmniej ``min_deals``). Atak przy wekslu paktu to osobne „The Great Betrayal".
- „Kingmaker" = zwycięzca trzyma w strefie gry Support for the Throne tego gracza; w braku —
  gracz, który w ostatniej rundzie zaatakował wicelidera (sam nie będąc zwycięzcą).
- „Master of Stalling" = ostatni pas w rundzie fazy akcji.
- „Last Stand" = wygrana bitwa, po której zwycięzcy została dokładnie 1 jednostka (bez struktur).
"""

from __future__ import annotations

from collections.abc import Callable

from src.core import achievements
from src.core.components import ComponentCategory
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

_Adder = Callable[..., None]
_Namer = Callable[[str], str]

# Progi: assets/config/achievements.json (core/achievements.py).
_p = achievements.param

_GIANTS = ("warsun", "flagship")
_FIRE_TEXT = {
    "space_cannon": "space cannon",
    "bombardment": "bombardment",
    "defense": "space cannon",
}


def _top(counts: dict[str, int]) -> str | None:
    """Jedyny lider z dodatnim wynikiem (remis albo same zera = brak)."""
    if not counts:
        return None
    best = max(counts.values())
    leaders = [p for p, n in counts.items() if n == best]
    return leaders[0] if best > 0 and len(leaders) == 1 else None


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _planet_name(registry: StaticDataRegistry, planet_id: str) -> str:
    planet = registry.planets.get(planet_id)
    return planet.name if planet else planet_id


def _attacks(state: GameState) -> list[tuple[int, str, str]]:
    """Ataki (bitwy i podboje) chronologicznie w obrębie rundy: ``(runda, napastnik, ofiara)``."""
    out = [(int(b["round"]), b["attacker"], b["defender"]) for b in state.chronicle.battles]
    out += [(int(c["round"]), c["by"], c["from"]) for c in state.chronicle.conquests]
    return sorted(out, key=lambda e: e[0])


# --------------------------------------------------------------------------- Treachery


def _treachery(state: GameState, registry: StaticDataRegistry, who: _Namer, add: _Adder) -> None:
    chron = state.chronicle

    for rnd, attacker, victim in _attacks(state):
        partners: dict[str, int] = {}
        for d in chron.deals:
            if int(d["round"]) > rnd or attacker not in (d["a"], d["b"]):
                continue
            other = d["b"] if d["a"] == attacker else d["a"]
            partners[other] = partners.get(other, 0) + 1
        best = _top(partners)
        if best == victim and partners[best] >= _p("oathbreaker", "min_deals"):
            add(
                "oathbreaker",
                f"{who(attacker)} turned on {who(victim)}, their closest trading partner "
                f"({_plural(partners[best], 'deal')}), in round {rnd}.",
                [attacker, victim],
                stat=f"round {rnd}",
            )
            break

    seen: dict[tuple[str, int], str] = {}
    for c in chron.conquests:
        key = (c["planet"], int(c["round"]))
        if key in seen and seen[key] != c["by"]:
            add(
                "vulture",
                f"{who(c['by'])} swooped on {_planet_name(registry, c['planet'])} in round "
                f"{c['round']}, right after {who(seen[key])} had bled for it.",
                [c["by"]],
                stat=_planet_name(registry, c["planet"]),
            )
            break
        seen.setdefault(key, c["by"])

    winner = state.winner_id
    if winner and winner in state.players:
        held = state.players[winner].promissory_notes_in_play
        giver = next(
            (
                pid
                for pid, p in state.players.items()
                if pid != winner
                and p.color
                and any(n.startswith(f"{p.color}_") and n.endswith("_sftt") for n in held)
            ),
            None,
        )
        if giver:
            add(
                "kingmaker",
                f"{who(winner)} took the throne holding the Support for the Throne "
                f"of {who(giver)}.",
                [giver, winner],
                stat="Support for the Throne",
            )
        else:
            final = {pid: p.victory_points for pid, p in state.players.items() if pid != winner}
            runner = max(final, key=lambda p: final[p]) if final else None
            last = state.round_number
            hitter = next(
                (
                    b["attacker"]
                    for b in chron.battles
                    if int(b["round"]) == last
                    and b["defender"] == runner
                    and b["attacker"] not in (winner, runner)
                ),
                None,
            )
            if hitter and runner:
                add(
                    "kingmaker",
                    f"{who(hitter)} attacked {who(runner)} in the final round and cleared "
                    f"the road to the throne for {who(winner)}.",
                    [hitter, winner],
                    stat=f"round {last}",
                )

    def is_sabotage(card_id: str) -> bool:
        card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
        return card is not None and (card.name or "").strip().lower() == "sabotage"

    sabotage = {
        pid: sum(1 for card in cards if is_sabotage(card))
        for pid, cards in chron.cards_played.items()
    }
    saboteur = _top(sabotage)
    if saboteur and sabotage[saboteur] >= _p("saboteur", "min_cards"):
        add(
            "saboteur",
            f"{who(saboteur)} cancelled {_plural(sabotage[saboteur], 'action card')} "
            f"of other players with Sabotage.",
            [saboteur],
            stat=f"{sabotage[saboteur]} Sabotage",
        )


# --------------------------------------------------------------------------- Table


def _table(state: GameState, who: _Namer, add: _Adder) -> None:
    chron = state.chronicle

    spoke: dict[str, int] = {}
    for pid in chron.speakers.values():
        spoke[pid] = spoke.get(pid, 0) + 1
    voice = _top(spoke)
    if voice and spoke[voice] >= _p("voice_of_council", "min_rounds"):
        add(
            "voice_of_council",
            f"{who(voice)} held the speaker token for {spoke[voice]} rounds.",
            [voice],
            stat=f"{spoke[voice]} rounds",
        )

    won: dict[str, int] = {}
    lost: dict[str, int] = {}
    for agenda in chron.agendas:
        for pid, vote in agenda["votes"].items():
            if int(vote.get("votes", 0)) <= 0:
                continue
            bucket = won if vote.get("outcome") == agenda["outcome"] else lost
            bucket[pid] = bucket.get(pid, 0) + 1
    senate = _top(won)
    if senate and won[senate] >= _p("senate_master", "min_wins"):
        add(
            "senate_master",
            f"{who(senate)} voted with the winning side on {_plural(won[senate], 'agenda')}.",
            [senate],
            stat=f"{won[senate]} won votes",
        )
    rebel = _top(lost)
    if rebel and lost[rebel] >= _p("dissident", "min_losses"):
        add(
            "dissident",
            f"{who(rebel)} was outvoted in the Council {lost[rebel]} times.",
            [rebel],
            stat=f"{lost[rebel]} lost votes",
        )

    last_pass: dict[int, str] = {}
    for entry in chron.passes:
        last_pass[int(entry["round"])] = entry["player"]
    stalls: dict[str, int] = {}
    for pid in last_pass.values():
        stalls[pid] = stalls.get(pid, 0) + 1
    staller = _top(stalls)
    if staller and stalls[staller] >= _p("staller", "min_rounds"):
        add(
            "staller",
            f"{who(staller)} was the last to pass in {stalls[staller]} rounds.",
            [staller],
            stat=f"{stalls[staller]} rounds",
        )

    if len(state.players) >= _p("silk_road", "min_players"):
        partners: dict[str, set[str]] = {}
        deals: dict[str, int] = {}
        for d in chron.deals:
            partners.setdefault(d["a"], set()).add(d["b"])
            partners.setdefault(d["b"], set()).add(d["a"])
            for pid in (d["a"], d["b"]):
                deals[pid] = deals.get(pid, 0) + 1
        traders = [
            pid
            for pid in state.players
            if set(state.players) - {pid} <= partners.get(pid, set())
        ]
        if traders:
            pid = max(traders, key=lambda p: deals.get(p, 0))
            add(
                "silk_road",
                f"{who(pid)} made a deal with every other player at the table.",
                [pid],
                stat=f"{len(state.players) - 1} partners",
            )


# --------------------------------------------------------------------------- War


def _war(state: GameState, registry: StaticDataRegistry, who: _Namer, add: _Adder) -> None:
    chron = state.chronicle
    battles = chron.battles

    giants: dict[str, int] = {}
    for b in battles:
        for victim, killer in ((b["attacker"], b["defender"]), (b["defender"], b["attacker"])):
            lost = b.get("lost_types", {}).get(victim, {})
            n = sum(int(lost.get(bt, 0)) for bt in _GIANTS)
            if n:
                giants[killer] = giants.get(killer, 0) + n
    slayer = _top(giants)
    if slayer and giants[slayer] >= _p("giant_slayer", "min_kills"):
        add(
            "giant_slayer",
            f"{who(slayer)} brought down {giants[slayer]} enemy war sun"
            f"{'s' if giants[slayer] > 1 else ''} and flagships.",
            [slayer],
            stat=f"{giants[slayer]} giants",
        )

    stands = [
        b
        for b in battles
        if b["winner"]
        and int(b.get("survivors", 0)) == 1
        and sum(b["losses"].values()) - b["losses"].get(b["winner"], 0)
        >= _p("last_stand", "min_enemy_lost")
    ]
    if stands:
        b = max(stands, key=lambda x: sum(x["losses"].values()))
        loser = b["defender"] if b["winner"] == b["attacker"] else b["attacker"]
        planet = registry.planets.get(b["planet"]) if b["planet"] else None
        where = planet.name if planet else f"system {b['position']}"
        add(
            "last_stand",
            f"{who(b['winner'])} won at {where} against {who(loser)} with a single unit "
            f"left standing.",
            [b["winner"]],
            stat="1 survivor",
        )

    defeats: dict[str, int] = {}
    for b in battles:
        if b["winner"]:
            loser = b["defender"] if b["winner"] == b["attacker"] else b["attacker"]
            if loser in state.players:
                defeats[loser] = defeats.get(loser, 0) + 1
    bag = _top(defeats)
    if bag and defeats[bag] >= _p("punching_bag", "min_losses"):
        add(
            "punching_bag",
            f"{who(bag)} lost {defeats[bag]} battles and still saw the end of the war.",
            [bag],
            stat=f"{defeats[bag]} defeats",
        )

    retreats: dict[str, int] = {}
    for b in battles:
        for pid in b.get("retreated", []):
            retreats[pid] = retreats.get(pid, 0) + 1
    runner = _top(retreats)
    if runner and retreats[runner] >= _p("tactical_retreat", "min_retreats"):
        add(
            "tactical_retreat",
            f"{who(runner)} retreated from {retreats[runner]} battles to fight another day.",
            [runner],
            stat=f"{retreats[runner]} retreats",
        )

    fire: dict[str, int] = {}
    kinds: dict[str, dict[str, int]] = {}
    for f in chron.fire:
        fire[f["by"]] = fire.get(f["by"], 0) + int(f["units"])
        per = kinds.setdefault(f["by"], {})
        per[f["kind"]] = per.get(f["kind"], 0) + int(f["units"])
    gunner = _top(fire)
    if gunner and fire[gunner] >= _p("rain_of_fire", "min_units"):
        main = max(kinds[gunner], key=lambda k: kinds[gunner][k])
        add(
            "rain_of_fire",
            f"{who(gunner)} destroyed {fire[gunner]} enemy units with "
            f"{_FIRE_TEXT.get(main, main)} fire, outside of combat.",
            [gunner],
            stat=f"{fire[gunner]} units",
        )


# --------------------------------------------------------------------------- Empire & Race


def _empire(state: GameState, who: _Namer, add: _Adder) -> None:
    chron = state.chronicle

    breakers = state.objectives.scored.get("custodians") or []
    if breakers:
        add(
            "first_to_throne",
            f"{who(breakers[0])} removed the Custodians token and opened Mecatol Rex.",
            [breakers[0]],
            stat="Custodians",
        )

    gained: dict[str, int] = {}
    for e in chron.mecatol:
        if e["gained"]:
            gained[e["player"]] = int(e["round"])
        elif gained.get(e["player"]) == int(e["round"]):
            add(
                "mecatol_tourist",
                f"{who(e['player'])} took Mecatol Rex and lost it again in round {e['round']}.",
                [e["player"]],
                stat=f"round {e['round']}",
            )
            break

    explorer = _top(chron.explorations)
    if explorer and chron.explorations[explorer] >= _p("void_walker", "min_explorations"):
        n = chron.explorations[explorer]
        add(
            "void_walker",
            f"{who(explorer)} explored {n} times, more than anyone else.",
            [explorer],
            stat=f"{n} explorations",
        )

    played = {pid: len(cards) for pid, cards in chron.cards_played.items()}
    shark = _top(played)
    if shark and played[shark] >= _p("card_shark", "min_cards"):
        add(
            "card_shark",
            f"{who(shark)} played {played[shark]} action cards.",
            [shark],
            stat=f"{played[shark]} cards",
        )

    forger = _top(chron.peak_warsuns)
    if forger and chron.peak_warsuns[forger] >= _p("sun_forger", "min_warsuns"):
        n = chron.peak_warsuns[forger]
        add(
            "sun_forger",
            f"{who(forger)} had {n} war suns on the board at once.",
            [forger],
            stat=f"{n} war suns",
        )

    snap = next((s for s in chron.rounds if int(s["round"]) == 2), None)
    if snap is not None and len(state.players) >= _p("late_bloomer", "min_players"):
        final = {pid: p.victory_points for pid, p in state.players.items()}
        ranks = {pid: 1 + sum(1 for v in final.values() if v > mine) for pid, mine in final.items()}
        bloomers = sorted(
            (pid for pid, vp in snap["vp"].items() if vp == 0 and ranks.get(pid, 99) <= 3),
            key=lambda p: (ranks[p], p != state.winner_id),
        )
        if bloomers:
            pid = bloomers[0]
            place = {1: "1st", 2: "2nd", 3: "3rd"}[ranks[pid]]
            add(
                "late_bloomer",
                f"{who(pid)} had no points after round 2 and still finished {place}.",
                [pid],
                stat=f"0 VP to {place}",
            )


def feats(state: GameState, registry: StaticDataRegistry, who: _Namer, add: _Adder) -> None:
    """Dopisuje osiągnięcia tego modułu (wywoływane z ``chronicle.highlights``)."""
    _treachery(state, registry, who, add)
    _table(state, who, add)
    _war(state, registry, who, add)
    _empire(state, who, add)


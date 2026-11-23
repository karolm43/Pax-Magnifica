"""Dodatkowe osiągnięcia kroniki: pierwsza krew, blitzkrieg, upadek stolicy, obrona domu,
walka o prowadzenie, finisz „na włosa" i pacyfista.

Oddzielony od ``chronicle`` (rejestr + podstawowe wnioski), żeby ten plik nie rósł bez końca.
Tak jak tamten to warstwa PREZENTACYJNA — niczego nie rozstrzyga w regułach. Funkcja
``extra_highlights`` dostaje te same ``who`` / ``add`` co reszta wniosków w ``highlights``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

_Adder = Callable[..., None]
_Namer = Callable[[str], str]

_MIN_BLITZ = 3  # tyle podbitych planet jednego gracza w jednej rundzie
_MIN_LEAD_CHANGES = 3
_MIN_PACIFIST_DEALS = 2
_MIN_PACIFIST_BATTLES = 3  # w całej partii, żeby „pokój" coś znaczył


def _homes(state: GameState, registry: StaticDataRegistry, pid: str) -> list[str]:
    player = state.players.get(pid)
    faction = registry.factions.get(player.faction) if player and player.faction else None
    return list(faction.home_planets) if faction else []


def _where(registry: StaticDataRegistry, battle: dict[str, Any]) -> str:
    planet = registry.planets.get(battle["planet"]) if battle["planet"] else None
    return planet.name if planet else f"system {battle['position']}"


def _vp_snapshots(state: GameState) -> list[dict[str, int]]:
    """Migawki VP po rundach z końcowym stanem (jak w ``chronicle._race_highlights``)."""
    chron = state.chronicle
    snaps = [dict(s["vp"]) for s in chron.rounds]
    rounds_no = [int(s["round"]) for s in chron.rounds]
    final = {pid: p.victory_points for pid, p in state.players.items()}
    if rounds_no and rounds_no[-1] == state.round_number:
        snaps[-1] = final
    else:
        snaps.append(final)
    return snaps


def _battle_awards(
    state: GameState, registry: StaticDataRegistry, who: _Namer, add: _Adder
) -> None:
    battles = state.chronicle.battles

    first = next((b for b in battles if b["winner"]), None)
    if first is not None:
        add(
            "first_blood",
            "First Blood",
            f"{who(first['winner'])} won the first battle of the game at "
            f"{_where(registry, first)}, in round {first['round']}.",
            [first["winner"]],
            stat=f"round {first['round']}",
        )

    # Dom pod ostrzałem: obrońca wygrał walkę o własną planetę-dom.
    for b in battles:
        defender = b["defender"]
        if (
            b["winner"] == defender
            and b["kind"] == "ground"
            and b["planet"]
            and b["planet"] in _homes(state, registry, defender)
        ):
            add(
                "home_sweet_home",
                "Home Sweet Home",
                f"{who(defender)} held their own homeworld, {_where(registry, b)}, "
                f"against {who(b['attacker'])}.",
                [defender],
                stat="homeworld held",
            )
            break

    # Upadek stolicy: ktokolwiek zdobył planetę-dom innego gracza (zdarzenie, nie stan końcowy).
    for c in state.chronicle.conquests:
        if c["planet"] in _homes(state, registry, c["from"]):
            planet = registry.planets.get(c["planet"])
            add(
                "capital_sacker",
                "Sacker of Capitals",
                f"{who(c['by'])} took {planet.name if planet else c['planet']}, "
                f"the homeworld of {who(c['from'])}, in round {c['round']}.",
                [c["by"], c["from"]],
                stat=f"round {c['round']}",
            )
            break

    # Blitzkrieg: najwięcej podbitych planet jednego gracza w jednej rundzie.
    per_round: dict[tuple[str, int], int] = {}
    for c in state.chronicle.conquests:
        key = (c["by"], int(c["round"]))
        per_round[key] = per_round.get(key, 0) + 1
    if per_round:
        (by, rnd), n = max(per_round.items(), key=lambda kv: kv[1])
        if n >= _MIN_BLITZ:
            add(
                "blitzkrieg",
                "Blitzkrieg",
                f"{who(by)} conquered {n} planets from other players in round {rnd} alone.",
                [by],
                stat=f"{n} planets in a round",
            )

    # Pacyfista: umowy zamiast wojny (nie dotyczy zwycięzcy — ten ma „Quiet Victory").
    attacks: dict[str, int] = {}
    deals: dict[str, int] = {}
    for b in battles:
        attacks[b["attacker"]] = attacks.get(b["attacker"], 0) + 1
    for d in state.chronicle.deals:
        for pid in (d["a"], d["b"]):
            deals[pid] = deals.get(pid, 0) + 1
    if len(battles) >= _MIN_PACIFIST_BATTLES:
        peaceful = [
            pid
            for pid in state.players
            if pid != state.winner_id
            and not attacks.get(pid)
            and deals.get(pid, 0) >= _MIN_PACIFIST_DEALS
        ]
        if peaceful:
            pid = max(peaceful, key=lambda p: deals[p])
            add(
                "pacifist",
                "The Pacifist",
                f"{who(pid)} never started a battle and made {deals[pid]} deals "
                f"while the others went to war.",
                [pid],
                stat=f"{deals[pid]} deals, 0 attacks",
            )


def _race_awards(state: GameState, who: _Namer, add: _Adder) -> None:
    snaps = _vp_snapshots(state)

    # Walka o prowadzenie: ile razy zmienił się JEDYNY lider wyścigu.
    leaders: list[str] = []
    for snap in snaps:
        top = max(snap.values(), default=0)
        at_top = [pid for pid, vp in snap.items() if vp == top]
        if top > 0 and len(at_top) == 1:
            leaders.append(at_top[0])
    changes = sum(1 for prev, cur in zip(leaders, leaders[1:], strict=False) if prev != cur)
    if changes >= _MIN_LEAD_CHANGES:
        add(
            "lead_changes",
            "A Throne Contested",
            f"The lead in the race for the throne changed hands {changes} times.",
            list(dict.fromkeys(leaders))[:3],
            stat=f"{changes} lead changes",
        )

    # Finisz na włosa: zwycięzca przed drugim graczem o najwyżej 1 VP.
    winner = state.winner_id
    if winner and len(state.players) >= 2:
        final = {pid: p.victory_points for pid, p in state.players.items()}
        others = {pid: vp for pid, vp in final.items() if pid != winner}
        runner = max(others, key=lambda p: others[p])
        gap = final[winner] - final[runner]
        if gap <= 1 and final[winner] > 0:
            add(
                "photo_finish",
                "Photo Finish",
                f"{who(winner)} took the throne "
                + (
                    f"by a single point over {who(runner)}."
                    if gap == 1
                    else f"on a tie-break against {who(runner)}."
                ),
                [winner, runner],
                stat="+1 VP" if gap == 1 else "tie-break",
            )


def extra_highlights(
    state: GameState, registry: StaticDataRegistry, who: _Namer, add: _Adder
) -> None:
    """Dopisuje dodatkowe osiągnięcia (wywoływane z ``chronicle.highlights``)."""
    _battle_awards(state, registry, who, add)
    _race_awards(state, who, add)

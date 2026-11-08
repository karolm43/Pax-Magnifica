"""Kronika partii: rejestr bitew, podbojów i transakcji + „wnioski" do podsumowania.

Czyste funkcje nad ``GameState``. To warstwa PREZENTACYJNA (statystyki końcowe) — niczego nie
rozstrzyga w regułach TI4. Zapis dzieje się w trzech miejscach silnika: koniec walki
(``battle``), przejęcie planety (``invasion``) i transakcja (``transaction``).

⚠️ Definicja „zdrady" (decyzja użytkownika): atak (walka albo przejęcie planety) na gracza,
z którym napastnik miał weksel Alliance / Support for the Throne / Ceasefire (w dowolnym
kierunku). Transakcje są liczone tylko do „Dyplomaty".
"""

from __future__ import annotations

from typing import Any

from src.core.game_state import ActiveCombat, GameState
from src.core.registry import StaticDataRegistry

# Progi, by wniosek nie pojawiał się z byle powodu.
_MIN_BIG_BATTLE = 3  # tyle jednostek łącznie musi zginąć, by bitwa była „wielka"
_MIN_CRUSHING = 4  # tyle jednostek zwycięzca musi zniszczyć bez strat


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


def record_deal(state: GameState, a: str, b: str) -> None:
    """Zapisuje transakcję między dwoma graczami (mutuje stan)."""
    state.chronicle.deals.append({"round": state.round_number, "a": a, "b": b})


def record_battle(state: GameState, combat: ActiveCombat) -> None:
    """Zapisuje zakończoną walkę (kosmiczną/naziemną). Mutuje stan."""
    losses = {combat.attacker: 0, combat.defender: 0}
    for entry in combat.log:
        for pid, lost in (entry.get("losses") or {}).items():
            if pid in losses:
                losses[pid] += sum(int(n) for n in lost.values())
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
            "pact": (pact := pact_between(state, combat.attacker, combat.defender)),
            "betrayal": pact is not None,
        }
    )


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

    def add(key: str, title: str, detail: str, players: list[str]) -> None:
        out.append({"key": key, "title": title, "detail": detail, "players": players})

    battles = chron.battles
    total_lost = [sum(b["losses"].values()) for b in battles]

    if battles:
        i = max(range(len(battles)), key=lambda k: total_lost[k])
        b = battles[i]
        if total_lost[i] >= _MIN_BIG_BATTLE:
            kind = "ground battle" if b["kind"] == "ground" else "space battle"
            add(
                "greatest_battle",
                "The Greatest Battle",
                f"{who(b['attacker'])} against {who(b['defender'])} at {where(b)}, round "
                f"{b['round']}: {total_lost[i]} units lost in a single {kind}.",
                [b["attacker"], b["defender"]],
            )

        j = max(range(len(battles)), key=lambda k: battles[k]["rounds"])
        longest = battles[j]
        if longest["rounds"] >= 3:
            add(
                "longest_battle",
                "The Endless War",
                f"{who(longest['attacker'])} and {who(longest['defender'])} fought "
                f"{longest['rounds']} rounds of combat at {where(longest)}.",
                [longest["attacker"], longest["defender"]],
            )

        crush = [
            (k, battles[k])
            for k in range(len(battles))
            if battles[k]["winner"]
            and battles[k]["losses"][battles[k]["winner"]] == 0
            and total_lost[k] >= _MIN_CRUSHING
        ]
        if crush:
            k, c = max(crush, key=lambda t: total_lost[t[0]])
            add(
                "crushing_victory",
                "A Crushing Victory",
                f"{who(c['winner'])} destroyed {total_lost[k]} units at {where(c)} "
                f"without losing a single one.",
                [c["winner"]],
            )

        mutual = [b for b in battles if b["winner"] is None]
        if mutual:
            m = max(mutual, key=lambda b: sum(b["losses"].values()))
            add(
                "mutual_destruction",
                "Mutual Annihilation",
                f"{who(m['attacker'])} and {who(m['defender'])} destroyed each other "
                f"completely at {where(m)}. Nobody held the field.",
                [m["attacker"], m["defender"]],
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
            "The Great Betrayal",
            f"{who(worst[0])} struck {who(victim)} while holding a {pact} promissory note"
            f" between them" + (f" ({n} treacherous attacks in total)." if n > 1 else "."),
            [worst[0], victim],
        )

    attacks: dict[str, int] = {}
    defended: dict[str, int] = {}
    for b in battles:
        attacks[b["attacker"]] = attacks.get(b["attacker"], 0) + 1
        defended[b["defender"]] = defended.get(b["defender"], 0) + 1
    for pid in _top(attacks):
        if attacks[pid] >= 2:
            add("warmonger", "The Warmonger", f"{who(pid)} started {attacks[pid]} battles.", [pid])
    for pid in _top(defended):
        if defended[pid] >= 2:
            add(
                "besieged",
                "Under Siege",
                f"{who(pid)} was attacked {defended[pid]} times.",
                [pid],
            )

    conquered: dict[str, int] = {}
    for c in chron.conquests:
        conquered[c["by"]] = conquered.get(c["by"], 0) + 1
    for pid in _top(conquered):
        add(
            "conqueror",
            "The Conqueror",
            f"{who(pid)} took {conquered[pid]} planet{'s' if conquered[pid] > 1 else ''} "
            f"from other players.",
            [pid],
        )

    deals: dict[str, int] = {}
    for d in chron.deals:
        for pid in (d["a"], d["b"]):
            deals[pid] = deals.get(pid, 0) + 1
    for pid in _top(deals):
        add("diplomat", "The Diplomat", f"{who(pid)} made {deals[pid]} deals at the table.", [pid])

    if battles and state.winner_id and not attacks.get(state.winner_id, 0):
        add(
            "quiet_victory",
            "The Quiet Victory",
            f"{who(state.winner_id or '')} won the throne without starting a single battle.",
            [state.winner_id or ""],
        )
    return out

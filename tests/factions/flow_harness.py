"""Harness scenariuszy frakcji przez PRAWDZIWE API (RULES.md 62.0, decyzja użytkownika 2026-11-12).

Scenariusz = nowa gra przez ``/game/new`` + setup, sytuacja ułożona God-Mode ``/god-mode/patch``
(jednostki, planety, liderzy, technologie, ręka notek), a potem PRAWDZIWY przebieg przez
endpointy gry (aktywacja, ruch, walka, inwazja, koniec tury, faza statusu). Sprawdzamy to, co widzi
gracz: decyzję w ``/offers``, kartę „Available now” (``/faction-component/available-now``),
zagrywalność notki/akcji i skutek po użyciu.

Każdy scenariusz oznacza ``@covers("<kategoria>:<id>", ...)`` komponenty, których dostępność
sprawdza. ``test_flow_coverage.py`` wymaga scenariusza dla KAŻDEGO interaktywnego komponentu
każdej zaimplementowanej frakcji (oferta, użycie w oknie, ACTION, notka) - także przyszłych.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.setup_helpers import finish_setup

Json = dict[str, Any]

COVERS_ATTR = "__flow_covers__"


def covers(*component_keys: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Oznacza scenariusz: sprawdza dostępność tych komponentów w prawdziwym przebiegu."""

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, COVERS_ATTR, tuple(component_keys))
        return fn

    return decorate


class Flow:
    """Gra 2-osobowa: ``me`` = testowana frakcja, ``other`` = rywal; faza akcji, tura ``me``."""

    def __init__(
        self, registry: StaticDataRegistry, faction: str, other: str = "", third: str = ""
    ) -> None:
        """``third`` = an optional third faction (``self.third``) for effects that need a combat
        or a deal between two players other than ``me`` (The Cavalry, RULES.md 62.21)."""
        self.registry = registry
        other = other or ("sol" if faction != "sol" else "letnev")
        # Sterowany zegar serwera: okna reakcji trwają stały czas (RULES.md 54.11), więc scenariusz
        # „przeczekuje” je przesunięciem czasu zamiast prawdziwego czekania.
        self.clock = [1_000_000.0]
        self.client = TestClient(
            create_app(
                registry=registry, store=EventStore(":memory:"), now=lambda: self.clock[0]
            )
        )
        seats = [{"faction_id": faction}, {"faction_id": other}]
        if third:
            seats.append({"faction_id": third})
        resp = self.client.post("/game/new", json={"players": seats})
        assert resp.status_code == 200, resp.text
        finish_setup(self.client)
        state = self.state()
        order = state["seating_order"]
        self.me = next(p for p in order if state["players"][p]["faction"] == faction)
        rivals = [p for p in order if p != self.me]
        self.other = next(
            (p for p in rivals if state["players"][p]["faction"] == other), rivals[0]
        )
        self.third = next((p for p in order if p not in (self.me, self.other)), "")
        self.home = str(state["players"][self.me]["home_position"])
        self.other_home = str(state["players"][self.other]["home_position"])

        def to_action(s: Json) -> None:
            # Przy 2 graczach każdy ma 2 karty strategii (faza strategii kompletna).
            for i, pid in enumerate(order):
                s["players"][pid]["strategy_cards"] = [2 * i + 1, 2 * i + 2]

        self.edit(to_action, phase="ACTION", active=self.me)
        resp = self.client.post("/god-mode/patch", json={"rng_seed": 7})  # powtarzalne kości
        assert resp.status_code == 200, resp.text

    # ------------------------------------------------------------------- stan i God-Mode

    def state(self) -> Json:
        return self.client.get("/state").json()["state"]  # type: ignore[no-any-return]

    def edit(
        self, fn: Callable[[Json], None] | None = None, *, phase: str | None = None,
        active: str | None = None,
    ) -> None:
        """Zmienia ``players``/``systems`` funkcją ``fn`` i zapisuje przez God-Mode patch."""
        state = self.state()
        if fn is not None:
            fn(state)
        body: Json = {"players": state["players"], "systems": state["systems"]}
        if phase is not None:
            body["phase"] = phase
        if active is not None:
            body["active_player_id"] = active
        resp = self.client.post("/god-mode/patch", json=body)
        assert resp.status_code == 200, resp.text

    def player(self, fn: Callable[[Json], None], pid: str | None = None) -> None:
        self.edit(lambda s: fn(s["players"][pid or self.me]))

    def space(self, position: str, pid: str, units: dict[str, int]) -> None:
        def put(s: Json) -> None:
            s["systems"][position]["space_units"][pid] = dict(units)

        self.edit(put)

    def ground(self, position: str, planet: str, pid: str, units: dict[str, int],
               owner: bool = True) -> None:
        def put(s: Json) -> None:
            system = s["systems"][position]
            system["planet_units"].setdefault(planet, {})[pid] = dict(units)
            if owner:
                system["planet_owners"][planet] = pid

        self.edit(put)

    def clear_space(self, position: str) -> None:
        self.edit(lambda s: s["systems"][position].__setitem__("space_units", {}))

    def grid(self) -> HexGrid:
        return grid_from_state(GameState.model_validate(self.state()), self.registry)

    def plain_pair(self) -> tuple[str, str]:
        """Dwa sąsiednie zwykłe systemy (bez domów i anomalii)."""
        grid = self.grid()
        state = self.state()
        homes = {str(p["home_position"]) for p in state["players"].values()}

        def plain(pos: str) -> bool:
            return pos in state["systems"] and pos not in homes and not grid.anomalies_at(pos)

        return next(
            (a, b) for a in sorted(state["systems"]) if plain(a)
            for b in sorted(grid.neighbors(a)) if plain(b)
        )

    def planets(self, position: str) -> list[str]:
        system_id = self.state()["systems"][position]["system_id"]
        return list(self.registry.systems[system_id].planets)

    # --------------------------------------------------------------------- przebieg gry

    # Ścieżki, które grają W pauzie ochronnej (RULES.md 54.10) - przed nimi nikt nie pasuje.
    _REACTING = ("/action-card/", "/promissory/", "/reaction-pause/", "/hold/", "/god-mode")

    def pass_reactions(self) -> None:
        """Pauza ochronna w kluczowym oknie: nikt nie reaguje, upływa stały czas okna (54.11)."""
        pause = self.state().get("reaction_pause")
        while pause:
            self.clock[0] += float(pause["seconds"]) + 1
            resp = self.client.post("/reaction-pause/release", json={"actor_id": self.me})
            assert resp.status_code == 200, resp.text
            pause = self.state().get("reaction_pause")

    def finish_hold(self) -> None:
        """Okno Sabotage: nikt nie anuluje karty, upływa stały czas okna (54.11)."""
        held = self.state().get("held_play")
        if held:
            self.clock[0] += float(held["seconds"]) + 1
            resp = self.client.post("/action-card/held/release", json={"actor_id": self.me})
            assert resp.status_code == 200, resp.text

    def post(self, path: str, body: Json | None = None, ok: bool = True) -> Any:
        if not path.startswith(self._REACTING):
            self.pass_reactions()
        resp = self.client.post(path, json=body if body is not None else {})
        if ok:
            assert resp.status_code == 200, f"{path}: {resp.text}"
        return resp

    def transact(
        self, give: Json | None = None, receive: Json | None = None,
        partner: str | None = None, ok: bool = True,
    ) -> Any:
        """Stół transakcji (RULES.md 47.1b): ja kładę ``give``, partner ``receive``, oba Ready.

        ``ok=False``: zwraca odpowiedź na położenie MOJEJ strony (np. 422) i zamyka stół.
        """
        other = partner or self.other
        pair = {"player_id": self.me, "partner_id": other}
        self.post("/transactions/table/open", pair)
        resp = self.post("/transactions/table/side", {**pair, "side": give or {}}, ok=ok)
        if not ok:
            self.post("/transactions/table/close", pair)
            return resp
        back = {"player_id": other, "partner_id": self.me}
        self.post("/transactions/table/side", {**back, "side": receive or {}})
        self.post("/transactions/table/ready", pair)
        return self.post("/transactions/table/ready", back)

    def activate(self, position: str) -> None:
        self.post("/tactical/activate", {"position": position})

    def move(self, source: str, target: str, ships: dict[str, int],
             cargo: list[Json] | None = None) -> None:
        faction = self.state()["players"][self.me]["faction"]
        self.post("/tactical/move", {
            "faction": faction, "fromPosition": source,
            "ships": [{"baseType": bt, "count": n} for bt, n in ships.items()],
            "cargo": cargo or [], "route": [source, target],
        })

    def end_turn(self, pid: str | None = None) -> None:
        self.post("/turn/end", {"player_id": pid or self.me})

    def battle(self) -> Json:
        return self.client.get("/tactical/battle").json()  # type: ignore[no-any-return]

    # ---------------------------------------------------------------- co widzi gracz

    def offers(self, pid: str | None = None) -> list[Json]:
        return self.client.get(  # type: ignore[no-any-return]
            "/offers", params={"player_id": pid or self.me}
        ).json()["offers"]

    def offer(self, name: str, pid: str | None = None) -> Json:
        found = [o for o in self.offers(pid) if name in o["name"] or name in o["label"]]
        assert found, f"No offer '{name}' for {pid or self.me}: {self.offers(pid)}"
        return found[0]

    def has_offer(self, name: str, pid: str | None = None) -> bool:
        return any(name in o["name"] or name in o["label"] for o in self.offers(pid))

    def accept(self, name: str, params: Json | None = None, pid: str | None = None) -> None:
        offer = self.offer(name, pid)
        self.post("/offers/accept", {
            "actor_id": pid or self.me, "offer_id": offer["id"], "params": params or {},
        })

    def decline_all(self) -> None:
        for pid in (self.me, self.other):
            for offer in self.offers(pid):
                if not offer["mandatory"]:
                    self.post("/offers/decline", {"actor_id": pid, "offer_id": offer["id"]})

    def available(self) -> set[str]:
        rows = self.client.get("/faction-component/available-now").json()["components"]
        return {f"{r['player_id']}:{r['component_id']}" for r in rows}

    def playable(self, pid: str | None = None) -> dict[str, Json]:
        rows = self.client.get(
            "/faction-component/playable", params={"player_id": pid or self.me}
        ).json()["components"]
        return {r["component_id"]: r for r in rows}

    def use(self, kind: str, component: str, params: Json | None = None,
            pid: str | None = None) -> Any:
        return self.post("/faction-component/play", {
            "player_id": pid or self.me, "kind": kind, "component_id": component,
            "params": params or {},
        })

    def notes_playable(self, pid: str) -> dict[str, Json]:
        rows = self.client.get("/promissory/playable", params={"player_id": pid}).json()["notes"]
        return {r["note_id"]: r for r in rows}

    def play_note(self, pid: str, note: str, params: Json | None = None) -> Any:
        return self.post("/promissory/play", {
            "player_id": pid, "note_id": note, "params": params or {},
        })

    def give_note(self, template: str, to: str) -> str:
        """Notkę frakcji ``me`` (szablon) dostaje gracz ``to`` do ręki; zwraca id karty."""
        def put(s: Json) -> None:
            mine = s["players"][self.me]["private"]["promissory_notes"]
            if template in mine:
                mine.remove(template)
            s["players"][to]["private"]["promissory_notes"].append(template)

        self.edit(put)
        return template

    # ------------------------------------------------------------------ kroki i walka

    def to_step(self, step: str) -> None:
        """``/tactical/step/next`` aż do kroku ``step`` (pomija puste kroki jak UI)."""
        for _ in range(8):
            if self.state()["tactical_step"] == step:
                return
            self.post("/tactical/step/next")
        raise AssertionError(f"Did not reach step {step}: {self.state()['tactical_step']}")

    def assign_auto(self) -> None:
        """Każda strona pokrywa wymagane trafienia: Sustain Damage, potem nieuszkodzone, potem
        uszkodzone jednostki (``required`` jest kluczowane frakcją, jak w UI)."""
        view = self.battle()
        for faction, need in (view.get("required") or {}).items():
            if int(need) <= 0 or faction != view.get("assigning"):
                continue  # straty przypisuje strona, której teraz kolej (jak w UI)
            side = view["attacker"] if view["attacker"]["faction"] == faction else view["defender"]
            left = int(need)
            sustain: list[Json] = []
            destroy: list[Json] = []
            damaged: list[Json] = []
            fresh_left: dict[str, int] = {}
            for unit in side["units"]:
                take = min(left, int(unit.get("sustainable") or 0))
                if take:
                    sustain.append({"baseType": unit["baseType"], "count": take})
                    left -= take
                fresh_left[unit["baseType"]] = (
                    int(unit["count"]) - int(unit.get("damaged") or 0) - take
                )
            for unit in side["units"]:
                take = min(left, fresh_left[unit["baseType"]])
                if take:
                    destroy.append({"baseType": unit["baseType"], "count": take})
                    left -= take
            for unit in side["units"]:
                take = min(left, int(unit.get("damaged") or 0))
                if take:
                    damaged.append({"baseType": unit["baseType"], "count": take})
                    left -= take
            self.post("/tactical/battle/assign", {
                "faction": faction, "sustain": sustain, "destroy": destroy,
                "destroyDamaged": damaged,
            })

    def resolve_fleet_pool(self) -> bool:
        """Okno puli floty (RULES.md 42.1 - także w trakcie walki): usuń podpowiedź silnika."""
        window = self.state().get("pending_window") or {}
        if window.get("window_type") != "FLEET_POOL":
            return False
        view = self.client.get("/tactical/fleet-pool").json()
        self.post("/tactical/fleet-pool/resolve", {
            "faction": view["player"],
            "remove": [{"baseType": bt, "count": n} for bt, n in view["suggestion"].items()],
        })
        return True

    def fight(self, stop: Callable[[], bool] | None = None, rounds: int = 12) -> None:
        """Prowadzi walkę (AFB, rzuty, straty) aż ``stop()`` albo koniec walki."""
        for _ in range(rounds * 4):
            if stop is not None and stop():
                return
            if self.resolve_fleet_pool():
                continue
            view = self.battle()
            step = view.get("step")
            if not view.get("active") or step in (None, "DONE"):
                return
            if step == "AFB":
                self.post("/tactical/battle/afb")
            elif step == "ROLL":
                self.post("/tactical/battle/roll")
            elif step == "ASSIGN":
                self.assign_auto()
            elif step == "TRIGGERS":
                self.decline_all()
            elif step == "ANNOUNCE":
                self.post("/tactical/battle/announce-retreat",
                          {"faction": self.me, "announce": False}, ok=False)
                self.post("/tactical/battle/announce-retreat",
                          {"faction": self.other, "announce": False}, ok=False)
            else:
                raise AssertionError(f"Unexpected combat step {step}")
        raise AssertionError("Combat did not finish.")

    # ------------------------------------------------------------ gotowe sytuacje

    def invade_own_home(self, attackers: int = 2, defenders: int = 1) -> str:
        """Przeciwnik trzyma jedną planetę domu ``me``; ``me`` ma piechotę na drugiej planecie i
        ``attackers`` piechoty na transportowcu. Aktywacja domu → INVASION. Zwraca planetę celu."""
        target, source = self.planets(self.home)[0], self.planets(self.home)[1]

        def setup(s: Json) -> None:
            system = s["systems"][self.home]
            system["planet_units"] = {
                source: {self.me: {"infantry": 3}},
                target: {self.other: {"infantry": defenders}},
            }
            system["planet_owners"] = {source: self.me, target: self.other}
            system["space_units"] = {self.me: {"carrier": 1, "infantry": attackers}}

        self.edit(setup)
        self.activate(self.home)
        self.to_step("INVASION")
        if self.state()["invasion"] is None:
            self.post("/tactical/invasion/begin")
        return target

    def ground_combat(self, attackers: int = 2, defenders: int = 1) -> str:
        """Inwazja na własny dom aż do startu walki naziemnej. Zwraca planetę walki."""
        target = self.invade_own_home(attackers, defenders)
        self.post("/tactical/invasion/commit", {"commits": [
            {"planet": target, "baseType": "infantry", "count": attackers},
        ]})
        for _ in range(4):
            if self.state()["invasion"]["phase"] == "GROUND_COMBAT":
                break
            self.post("/tactical/invasion/next")
        self.post("/tactical/battle/start", {"planet": target})
        return target

    def space_combat(self, mine: dict[str, int], theirs: dict[str, int]) -> str:
        """Obie floty w zwykłym systemie, aktywacja, krok SPACE_COMBAT i start walki."""
        position, _ = self.plain_pair()
        self.space(position, self.me, mine)
        self.space(position, self.other, theirs)
        self.activate(position)
        self.to_step("SPACE_COMBAT")
        self.start_space_combat()
        return position

    def start_space_combat(self) -> None:
        """Entering SPACE_COMBAT starts the combat (RULES.md 19.1); by hand only if it did not."""
        if self.state()["active_combat"] is None:
            self.post("/tactical/battle/start", {})

    def pass_and_end(self, pid: str) -> None:
        """Gracz ``pid`` (aktywny) pasuje i kończy turę - następny zaczyna swoją.

        Pas wymaga zagranej karty strategii, więc God-Mode oznacza ją jako wyczerpaną.
        """
        def played(p: Json) -> None:
            p["exhausted_strategy_cards"] = list(p["strategy_cards"])

        self.player(played, pid)
        self.post("/turn/pass", {"player_id": pid})
        self.post("/turn/end", {"player_id": pid})

    def other_turn(self) -> None:
        """Tura przechodzi na rywala: ``me`` robi akcję taktyczną (aktywacja zwykłego systemu)
        i kończy turę BEZ pasu, więc po pasie rywala znów zaczyna się tura ``me``."""
        position, _ = self.plain_pair()
        self.activate(position)
        self.end_turn()

    def set_tile(self, position: str, system_id: str) -> None:
        """God-Mode: inny kafel na pozycji (rzadka mapa startowa nie ma planet poza domami)."""
        def put(s: Json) -> None:
            s["systems"][position]["system_id"] = system_id

        self.edit(put)

    def neighbor_of(self, position: str) -> str:
        """Sąsiad pozycji na planszy (do podmiany kafla - anomalia znika razem z kaflem)."""
        homes = {str(p["home_position"]) for p in self.state()["players"].values()}
        return next(p for p in sorted(self.grid().neighbors(position))
                    if p in self.state()["systems"] and p not in homes)

    def to_status(self) -> None:
        """Koniec fazy akcji (God-Mode ``/phase/skip``) - wejście w fazę statusu."""
        self.post("/phase/skip")
        assert self.state()["phase"] == "STATUS"

    def finish_status(self) -> None:
        """Prawdziwe kroki statusu: koniec punktacji, rozdział żetonów (cała pula na taktyczne),
        „Next phase” - koniec fazy statusu (okna „at the end of the status phase”)."""
        for pid in self.state()["seating_order"]:
            self.post("/status/finish-scoring", {"player_id": pid}, ok=False)
        state = self.state()
        unassigned = (state.get("status") or {}).get("unassigned_cc", {})
        for pid in state["seating_order"]:
            p = state["players"][pid]
            self.post("/status/redistribute", {
                "player_id": pid,
                "tactical": p["tactical_cc"] + int(unassigned.get(pid, 0)),
                "fleet": p["fleet_cc"], "strategic": p["strategic_cc"],
            })
        self.post("/phase/next", {"player_id": state["speaker_id"]})

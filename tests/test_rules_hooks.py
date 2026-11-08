"""Testy szkieletu hooków (RULES.md 43): rejestr, kolejność, zakazy/pozwolenia, migracja Arborec."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import production, rules_hooks
from src.core.game_state import GameState, PlayerState
from src.core.hooks.technologies import ANTIMASS_ALIAS
from src.core.rules_hooks import HookKind, HookSource

POINT = "test.point"


def _state(faction: str | None = None, techs: list[str] | None = None) -> GameState:
    player = PlayerState(
        player_id="p1", color="red", faction=faction, technologies=list(techs or [])
    )
    return GameState(players={"p1": player})


def test_hook_dziala_tylko_dla_posiadacza_zrodla() -> None:
    with rules_hooks.temporary_hooks():
        src = HookSource(rules_hooks.SOURCE_FACTION, "testfaction")

        @rules_hooks.register(POINT, src, HookKind.PERMIT)
        def _permit(_s: GameState, _p: str, _c: Mapping[str, Any]) -> bool:
            return True

        assert rules_hooks.permits(POINT, _state("testfaction"), "p1")
        assert not rules_hooks.permits(POINT, _state("other"), "p1")  # bez wyjątku -> baza
        assert not rules_hooks.permits(POINT, _state(None), "p1")


def test_rejestr_wraca_po_temporary_hooks() -> None:
    before = len(rules_hooks._REGISTRY)
    with rules_hooks.temporary_hooks():
        rules_hooks.register(
            POINT, HookSource(rules_hooks.SOURCE_FACTION, "x"), HookKind.FORBID
        )(lambda _s, _p, _c: ("a",))
        assert len(rules_hooks._REGISTRY) == before + 1
    assert len(rules_hooks._REGISTRY) == before


def test_kolejnosc_rodzajow_i_modyfikatory_sumuja_sie() -> None:
    with rules_hooks.temporary_hooks():
        src = HookSource(rules_hooks.SOURCE_FACTION, "f")
        reg = rules_hooks.register
        reg(POINT, src, HookKind.MODIFY)(lambda _s, _p, _c: 2)
        reg(POINT, src, HookKind.FORBID)(lambda _s, _p, _c: ())
        reg(POINT, src, HookKind.MODIFY)(lambda _s, _p, _c: -1)
        state = _state("f")
        kinds = [h.kind for h in rules_hooks.hooks_at(POINT, state, "p1")]
        assert kinds == [HookKind.FORBID, HookKind.MODIFY, HookKind.MODIFY]
        assert rules_hooks.modify(POINT, state, "p1", 10) == 11


def test_zakazy_roznych_zrodel_sie_lacza() -> None:
    with rules_hooks.temporary_hooks():
        reg = rules_hooks.register
        reg(POINT, HookSource(rules_hooks.SOURCE_FACTION, "f"), HookKind.FORBID)(
            lambda _s, _p, _c: ("infantry",)
        )
        reg(POINT, HookSource(rules_hooks.SOURCE_TECHNOLOGY, "t"), HookKind.FORBID)(
            lambda _s, _p, _c: ("fighter",)
        )
        state = _state("f", ["t"])
        assert rules_hooks.forbidden(POINT, state, "p1") == {"infantry", "fighter"}


def test_pusty_punkt_nie_zmienia_zachowania() -> None:
    state = _state("f", ["t"])
    assert rules_hooks.forbidden("no.such.point", state, "p1") == frozenset()
    assert not rules_hooks.permits("no.such.point", state, "p1")
    assert rules_hooks.modify("no.such.point", state, "p1", 5) == 5


def test_arborec_dok_nie_produkuje_piechoty_przez_hook() -> None:
    arborec = _state("arborec")
    assert production.forbidden_types(arborec, "p1", "spacedock") == ("infantry",)
    assert production.forbidden_types(arborec, "p1", "infantry") == ()
    assert production.forbidden_types(_state("sol"), "p1", "spacedock") == ()
    assert production.forbidden_types(_state(None), "p1", "spacedock") == ()


def test_antimass_zezwala_na_asteroidy_przez_hook() -> None:
    point = rules_hooks.POINT_MOVEMENT_ENTER_ASTEROIDS
    assert rules_hooks.permits(point, _state(None, [ANTIMASS_ALIAS]), "p1")
    assert not rules_hooks.permits(point, _state(None, []), "p1")

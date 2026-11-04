"""Testy rejestru efektów (zadanie 7.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import config
from src.core.components import (
    ActionCardDef,
    ComponentCatalog,
    ComponentCategory,
    ComponentRef,
)
from src.core.effects_registry import (
    EffectRegistry,
    EffectStatus,
    coverage,
    resolve_action_card_ref,
)

CAT = ComponentCategory.ACTION_CARD


def _card(card_id: str, automation: str | None = None) -> ActionCardDef:
    return ActionCardDef(id=card_id, source="base", automationID=automation)


def _catalog() -> ComponentCatalog:
    return ComponentCatalog({CAT: {"a": _card("a", "auto_a"), "b": _card("b")}})


def test_domyslny_status_i_niemutowalnosc() -> None:
    ref = ComponentRef(CAT, "a")
    reg = EffectRegistry()
    new = reg.with_status(ref, EffectStatus.MANUAL)
    assert reg.status_of(ref) is EffectStatus.NOT_IMPLEMENTED
    assert new.status_of(ref) is EffectStatus.MANUAL


def test_load_brak_pliku_to_pusty_rejestr(tmp_path: Path) -> None:
    assert EffectRegistry.load(tmp_path / "brak.json").statuses == {}


def test_load_i_bledy(tmp_path: Path) -> None:
    ok = tmp_path / "ok.json"
    ok.write_text('{"action_cards:a": "implemented"}', encoding="utf-8")
    assert EffectRegistry.load(ok).status_of(ComponentRef(CAT, "a")) is EffectStatus.IMPLEMENTED
    bad = tmp_path / "bad.json"
    bad.write_text('{"action_cards:a": "nope"}', encoding="utf-8")
    with pytest.raises(ValueError):
        EffectRegistry.load(bad)


def test_poczatkowy_plik_konfiguracyjny_jest_pusty() -> None:
    assert EffectRegistry.load(config.EFFECTS_STATUS_PATH).statuses == {}


def test_coverage() -> None:
    reg = EffectRegistry().with_status(ComponentRef(CAT, "a"), EffectStatus.IMPLEMENTED)
    row = coverage(_catalog(), reg)[CAT]
    assert (row.total, row.implemented, row.manual, row.percent_implemented) == (2, 1, 0, 50.0)


def test_resolve_action_card_ref() -> None:
    cat = _catalog()
    assert resolve_action_card_ref(cat, "auto_a") == ComponentRef(CAT, "a")
    assert resolve_action_card_ref(cat, "b") == ComponentRef(CAT, "b")
    assert resolve_action_card_ref(cat, "nieznany") is None

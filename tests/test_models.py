"""Testy modeli Pydantic na realnych assetach AsyncTI4."""

from __future__ import annotations

import json

from src import config
from src.core.models import PlanetDef, SystemDef, UnitDef


def test_parse_base_units() -> None:
    """Wszystkie jednostki z baseUnits.json parsują się do UnitDef."""
    raw = json.loads((config.UNITS_DATA_DIR / "baseUnits.json").read_text(encoding="utf-8"))
    units = [UnitDef.model_validate(entry) for entry in raw]

    assert len(units) > 0
    by_id = {u.id: u for u in units}

    cruiser = by_id["cruiser"]
    assert cruiser.name == "Cruiser I"
    assert cruiser.move_value == 2
    assert cruiser.cost == 2
    assert cruiser.combat_hits_on == 7
    assert cruiser.is_ship is True
    assert cruiser.upgrades_to_unit_id == "cruiser2"


def test_parse_system_mecatol() -> None:
    """System Mecatol Rex (18) parsuje się do SystemDef."""
    raw = json.loads((config.SYSTEMS_DIR / "18.json").read_text(encoding="utf-8"))
    system = SystemDef.model_validate(raw)

    assert system.id == "18"
    assert system.name == "Mecatol Rex"
    assert system.planets == ["mr"]
    assert system.wormholes == []
    assert system.source == "base"


def test_parse_system_with_wormhole() -> None:
    """System Quann (25) ma wormhole BETA."""
    raw = json.loads((config.SYSTEMS_DIR / "25.json").read_text(encoding="utf-8"))
    system = SystemDef.model_validate(raw)

    assert system.id == "25"
    assert "BETA" in system.wormholes
    assert system.planets == ["quann"]


def test_parse_planet_mecatol() -> None:
    """Planeta Mecatol Rex parsuje się do PlanetDef z pominięciem pól UI."""
    raw = json.loads((config.PLANETS_DIR / "mr.json").read_text(encoding="utf-8"))
    planet = PlanetDef.model_validate(raw)

    assert planet.id == "mr"
    assert planet.name == "Mecatol Rex"
    assert planet.resources == 1
    assert planet.influence == 6
    assert planet.planet_type == "MR"
    assert planet.source == "base"


def test_parse_planet_quann() -> None:
    """Planeta Quann: zasoby/wpływy i typ kulturowy."""
    raw = json.loads((config.PLANETS_DIR / "quann.json").read_text(encoding="utf-8"))
    planet = PlanetDef.model_validate(raw)

    assert planet.id == "quann"
    assert planet.resources == 2
    assert planet.influence == 1
    assert planet.planet_type == "CULTURAL"

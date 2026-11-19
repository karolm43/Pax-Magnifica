"""Entropic Scar - anomalia Thunder's Edge (RULES.md 1.5, ``R_entropic_scars``).

Jedno miejsce odpowiedzi „czy system jest blizną entropiczną” dla wszystkich punktów centralnych
zdolności jednostek. Źródło reguły: tekst zasady z assetów AsyncTI4
(``assets/data/rules/thundersedge.json`` - ``entropicScar``) i zrzut tirules2
(``docs/rules_tirules/R_entropic_scars.md``):

- zdolności jednostek (Sustain Damage, Production, Planetary Shield, Space Cannon, Bombardment,
  Deploy, Anti-Fighter Barrage) nie działają PRZEZ jednostki w bliźnie ani PRZECIW nim; zdolności
  tekstowe (flagowce, technologie, karty) działają normalnie;
- żeton wormhole, który miałby trafić do blizny, wraca do puli;
- na starcie fazy statusu gracz ze statkami w bliźnie może wydać żeton z puli strategii na
  technologię frakcyjną (``hooks/entropic_scar.py``).

Flaga w danych: ``isScar`` kafla (``SystemDef.is_scar`` -> anomalia ``ENTROPIC_SCAR``).
"""

from __future__ import annotations

from typing import Any

from src.core import rules_hooks
from src.core.game_state import GameState

SCAR = "ENTROPIC_SCAR"


def is_scar(state: GameState, position: str | None, registry: Any = None) -> bool:
    """Czy system na ``position`` jest blizną entropiczną (z danych kafla w stanie gry).

    ``registry`` domyślnie = rejestr związany z hookami (``rules_hooks.bind_registry``); bez
    rejestru (testy jednostkowe bez danych) żaden system nie jest blizną.
    """
    if position is None:
        return False
    system = state.systems.get(position)
    reg = registry if registry is not None else rules_hooks.bound_registry()
    if system is None or reg is None:
        return False
    definition = reg.systems.get(system.system_id)
    return definition is not None and SCAR in definition.anomalies


def unit_abilities_blocked(state: GameState, position: str | None, registry: Any = None) -> bool:
    """Czy w systemie nie wolno użyć zdolności jednostek (ani przez, ani przeciw jednostkom).

    Wszystkie zdolności jednostek dotyczą jednostek w JEDNYM systemie (strzelec i cel albo
    producent), więc wystarczy zapytać o system jednostek; Space Cannon z sąsiedztwa sprawdza
    oba końce (``space_cannon``).
    """
    return is_scar(state, position, registry)


def accepts_wormhole_token(state: GameState, position: str, registry: Any = None) -> bool:
    """Czy w systemie wolno położyć żeton wormhole (w bliźnie wraca do puli - R_entropic_scars)."""
    return not is_scar(state, position, registry)


def scar_positions(state: GameState, registry: Any = None) -> list[str]:
    """Pozycje blizn entropicznych na planszy (posortowane)."""
    return sorted(p for p in state.systems if is_scar(state, p, registry))


def scars_with_ships(state: GameState, player_id: str, registry: Any = None) -> list[str]:
    """Blizny, w których gracz ma STATKI (siły naziemne się nie liczą - R_entropic_scars 5.2)."""
    from src.core.unit_catalog import is_space_unit  # lokalnie: lekki moduł danych

    return [
        position
        for position in scar_positions(state, registry)
        if any(
            count > 0 and is_space_unit(base_type)
            for base_type, count in state.systems[position].space_units.get(player_id, {}).items()
        )
    ]

"""Technologie ogólne wpływające na dane okno gry - wskaźniki „aktywna technologia" dla UI.

Gracz ma widzieć, że technologia działa, NAWET gdy nie jest to opcja „may" (np. Sarween Tools
tnie koszt w produkcji, Antimass Deflectors osłabia Space Cannon, Hyper Metabolism daje żeton).
Ten moduł NIE liczy żadnych efektów (robią to hooki w ``core/hooks/``) - tylko mówi, w których
OKNACH UI karta jest istotna i w jakim jest stanie. Treść karty UI bierze z assetów, nie stąd.

Konteksty (okna): ``production``, ``movement``, ``combat``, ``spaceCannon``, ``invasion``,
``agenda``, ``fleet``, ``status``, ``turn``, ``technology``.

Funkcja CZYSTA (bez HTTP); ``api/web_data`` dokleja wynik do danych gracza.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


@dataclass(frozen=True)
class TechContexts:
    """Okna, w których technologia jest istotna, i czy da się ją wyczerpać."""

    contexts: tuple[str, ...]
    exhausts: bool = False


# Klucz = alias z assets/data/technologies (nie z pamięci); lista = generic_pool. Test pilnuje,
# że każda technologia ogólna ma wpis (nowa technologia bez wpisu = czerwony test).
TECH_CONTEXTS: dict[str, TechContexts] = {
    # Propulsion
    "amd": TechContexts(("movement", "spaceCannon")),
    "det": TechContexts(("movement",)),
    "fl": TechContexts(("turn",)),
    "gd": TechContexts(("movement",)),
    "lwd": TechContexts(("movement",)),
    "sr": TechContexts(("production", "turn"), exhausts=True),
    # Biotic
    "bs": TechContexts(("turn",), exhausts=True),
    "dxa": TechContexts(("invasion",)),
    "hm": TechContexts(("status",)),
    "nm": TechContexts(("status",)),
    "pa": TechContexts(("technology",), exhausts=True),
    "x89c4": TechContexts(("invasion",)),
    # Cybernetic
    "gls": TechContexts(("spaceCannon",), exhausts=True),
    "ie": TechContexts(("production",), exhausts=True),
    "pi": TechContexts(("agenda", "turn"), exhausts=True),
    "sdn": TechContexts(("movement",), exhausts=True),
    "st": TechContexts(("production",)),
    "td": TechContexts(("turn",), exhausts=True),
    # Warfare
    "aida": TechContexts(("production", "technology"), exhausts=True),
    "asc": TechContexts(("combat",)),
    "da": TechContexts(("combat",)),
    "md": TechContexts(("combat", "invasion")),
    "ps": TechContexts(("spaceCannon", "invasion")),
    "sar": TechContexts(("production", "invasion"), exhausts=True),
    # Ulepszenia jednostek: statystyki liczy wariant jednostki, więc NIE pokazujemy ich jako
    # wskaźników w oknach (puste konteksty; wpis jest, by test pokrycia pilnował nowych kart).
    "ff2": TechContexts(()),
    "inf2": TechContexts(()),
    "pds2": TechContexts(()),
    "sd2": TechContexts(()),
    "ws": TechContexts(()),
    "cv2": TechContexts(()),
    "cr2": TechContexts(()),
    "dd2": TechContexts(()),
    "dn2": TechContexts(()),
}


def active_techs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Posiadane technologie ogólne istotne dla okien UI: ``{alias, name, contexts, state}``.

    ``state``: ``exhausted`` (wyczerpana), ``ready`` (da się wyczerpać i jest gotowa) albo
    ``active`` (działa stale). Kolejność jak w ``player.technologies``.
    """
    player = state.players.get(player_id)
    if player is None:
        return []
    exhausted = set(player.exhausted_technologies)
    result: list[dict[str, Any]] = []
    for alias in player.technologies:
        entry = TECH_CONTEXTS.get(alias)
        if entry is None or not entry.contexts:
            continue
        tech = registry.technologies.get(alias)
        if alias in exhausted:
            tech_state = "exhausted"
        elif entry.exhausts:
            tech_state = "ready"
        else:
            tech_state = "active"
        result.append(
            {
                "alias": alias,
                "name": tech.name if tech is not None else alias,
                "contexts": list(entry.contexts),
                "state": tech_state,
            }
        )
    return result

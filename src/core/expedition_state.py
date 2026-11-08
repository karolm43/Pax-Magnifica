"""Stan modułu Thunder's Edge: ekspedycje, The Fracture i Thunder's Edge (RULES.md 50).

Osobny plik, żeby ``game_state.py`` nie puchł. Modele są serializowane razem z
``GameState`` (Undo/Redo/migawki), więc wszystko, co ma przeżyć cofnięcie, leży tutaj.
Mapa (``HexGrid``) NIE jest w stanie gry — kafle The Fracture są do niej dosynchronizowane
ze stanu przy każdym odczycie (``core/fracture.sync_grid``), tak jak żetony wormhole.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Sześć plastrów żetonu ekspedycji w kolejności ZGODNEJ Z RUCHEM WSKAZÓWEK ZEGARA od góry
# (R_expedition). Identyfikatory zgodne z kontraktem frontendu (``Expeditions`` w web-data).
EXPEDITION_SLICES: tuple[str, ...] = (
    "fiveRes",  # wydaj 5 zasobów
    "actionCards",  # odrzuć 2 karty akcji
    "fiveInf",  # wydaj 5 wpływu
    "secret",  # odrzuć 1 niepunktowany tajny cel
    "techSkip",  # wyczerp planetę ze specjalnością technologiczną
    "tradeGoods",  # wydaj 3 trade goods
)


class IngressChoice(BaseModel):
    """Oczekujący wybór żetonów ingress dla jednego koloru technologii.

    Lista kandydatów NIE jest trzymana — wynika ze stanu mapy w chwili wyboru
    (``core/fracture.ingress_candidates``), bo każdy położony żeton zmienia pulę.
    """

    model_config = ConfigDict(extra="forbid")

    color: str  # "BIOTIC" | "PROPULSION" | "CYBERNETIC" | "WARFARE" (jak ``technology.COLORS``)
    remaining: int  # ile żetonów jeszcze trzeba położyć dla tego koloru


class FractureState(BaseModel):
    """Stan The Fracture: czy weszła do gry, kto ją wprowadził i co czeka na wybór."""

    model_config = ConfigDict(extra="forbid")

    in_play: bool = False
    # Gracz, który wprowadził Fracture (wybiera ingress) — None, gdy jeszcze nie weszła.
    entered_by: str | None = None
    # Id przełomu, z którego synergii liczono ingress (None = cztery kolory po jednym).
    breakthrough_id: str | None = None
    # Wybory ingress do dokonania przez ``entered_by`` (puste = wszystko położone).
    pending: list[IngressChoice] = Field(default_factory=list)
    # Ostatni rzut na wejście Fracture: {"playerId", "result", "success"} (None = brak).
    last_roll: dict[str, Any] | None = None
    # Dziennik zdarzeń modułu (rzuty, wejście Fracture, ingress, relikty) — dla panelu.
    log: list[dict[str, Any]] = Field(default_factory=list)


class ThundersEdgePlacement(BaseModel):
    """Oczekujące położenie Thunder's Edge po 6. plastrze (R_expedition)."""

    model_config = ConfigDict(extra="forbid")

    # Gracz, który wziął ostatni plaster — kładzie planetę (i przy remisie wybiera, kto stawia
    # piechotę).
    player_id: str
    # Liczba zajętych plastrów per gracz (do liczby piechoty).
    counts: dict[str, int] = Field(default_factory=dict)
    # Gracze z największą liczbą plastrów (jeden = bez wyboru).
    leaders: list[str] = Field(default_factory=list)


class ExpeditionState(BaseModel):
    """Stan ekspedycji i Thunder's Edge."""

    model_config = ConfigDict(extra="forbid")

    # plaster -> gracz, który go zajął (brak wpisu = wolny).
    claims: dict[str, str] = Field(default_factory=dict)
    # Gracz, który wykonał ekspedycję w BIEŻĄCEJ turze (limit: 1 plaster na turę). Czyszczone
    # przy oddaniu tury i zmianie fazy.
    performed_by: str | None = None
    # Oczekujące położenie Thunder's Edge (None = brak).
    pending_placement: ThundersEdgePlacement | None = None
    # Pozycja systemu z Thunder's Edge (None = jeszcze nie weszło do gry).
    thunders_edge_position: str | None = None

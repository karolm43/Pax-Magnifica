"""Zgłoszenia „Report bug": zrzut + opis + stan na dysku hosta (także od gościa z sieci)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.bug_reports import decode_png
from src.api.seats import SEAT_TOKEN_HEADER
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry

HOST = "host-token-for-tests"
REMOTE = {"X-Forwarded-For": "10.147.17.5"}
# Najmniejszy poprawny PNG (1×1 px).
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
PNG_URL = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()


def _state() -> GameState:
    return GameState(
        round_number=3,
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", faction="arborec", color="green"),
            "p2": PlayerState(player_id="p2", faction="sol", color="blue"),
        },
    )


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _app(
    registry: StaticDataRegistry, reports: Path | None, *, network: bool = False
) -> TestClient:
    app = create_app(
        registry=registry,
        store=EventStore(":memory:"),
        initial_state=_state(),
        network=network,
        host_token=HOST,
        bug_reports_dir=reports,
    )
    return TestClient(app)


def test_local_report_writes_all_files(registry: StaticDataRegistry, tmp_path: Path) -> None:
    client = _app(registry, tmp_path)
    res = client.post(
        "/bug-report",
        json={
            "description": "Karta Warfare nie daje się kliknąć",
            "screenshot": PNG_URL,
            "client": {"url": "http://localhost:5173/game", "consoleErrors": ["boom"]},
        },
        headers={"X-Actor-Id": "p1"},
    )
    assert res.status_code == 200, res.text
    folder = tmp_path / res.json()["report_id"]
    assert folder.name.endswith("_p1")
    assert (folder / "screenshot.png").read_bytes() == PNG_1PX
    report = (folder / "report.md").read_text(encoding="utf-8")
    assert "Karta Warfare nie daje się kliknąć" in report
    assert "p1 (arborec)" in report and "3 / ACTION" in report and "boom" in report
    state = json.loads((folder / "state.json").read_text(encoding="utf-8"))
    assert state["round_number"] == 3
    assert (
        json.loads((folder / "client.json").read_text(encoding="utf-8"))["reporter"]
        == "p1 (arborec)"
    )


def test_network_guest_report_lands_on_host_disk(
    registry: StaticDataRegistry, tmp_path: Path
) -> None:
    client = _app(registry, tmp_path, network=True)
    seats = client.get("/network/seats", headers={SEAT_TOKEN_HEADER: HOST}).json()["seats"]
    token = next(s["token"] for s in seats if s["player_id"] == "p2")
    res = client.post(
        "/bug-report",
        json={"description": "lag", "client": {}},
        headers={SEAT_TOKEN_HEADER: token, **REMOTE, "X-Actor-Id": "p1"},  # podszycie ignorowane
    )
    assert res.status_code == 200, res.text
    folder = tmp_path / res.json()["report_id"]
    assert folder.name.endswith("_p2")
    assert not (folder / "screenshot.png").exists()
    # Bez tokenu z innego komputera — odmowa, nic nie zapisane poza tym jednym raportem.
    assert client.post("/bug-report", json={"description": "x"}, headers=REMOTE).status_code == 401
    assert len(list(tmp_path.iterdir())) == 1


def test_disabled_and_invalid_reports(registry: StaticDataRegistry, tmp_path: Path) -> None:
    assert _app(registry, None).post("/bug-report", json={"description": "x"}).status_code == 503
    client = _app(registry, tmp_path)
    assert client.post("/bug-report", json={"description": "  "}).status_code == 422
    bad = client.post(
        "/bug-report", json={"description": "x", "screenshot": "data:image/png;base64,AAAA"}
    )
    assert bad.status_code == 422
    assert list(tmp_path.iterdir()) == []  # zły zrzut => brak katalogu


def test_decode_png_rejects_other_formats() -> None:
    with pytest.raises(ValueError):
        decode_png("data:image/jpeg;base64," + base64.b64encode(b"x").decode())
    assert decode_png(PNG_URL) == PNG_1PX

"""Pomocnik testów: domyka setup startowy gry przez API (RULES.md 45).

``/game/new`` zostawia grę w setupie (wybór tajnych celów, żeton Custodians, odkrycie
celów). Testy sprawdzające fazy gry wołają ``finish_setup(client)`` zaraz po ``/game/new``.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def finish_setup(client: TestClient) -> None:
    """Wybiera pierwszy kandydujący tajny cel za każdego gracza, kładzie żeton, odkrywa cele."""
    for _ in range(64):  # bezpiecznik przed pętlą nieskończoną
        state: dict[str, Any] = client.get("/state").json()["state"]
        setup = state["setup"]
        if setup is None:
            return
        speaker = state["speaker_id"]
        if setup["stage"] == "SECRETS":
            chooser = next(
                pid
                for pid in state["seating_order"]
                if pid not in setup["secrets_chosen"]
                and state["players"][pid]["private"]["secret_candidates"]
            )
            candidate = state["players"][chooser]["private"]["secret_candidates"][0]
            resp = client.post(
                "/setup/secret", json={"player_id": chooser, "objective_id": candidate}
            )
        elif setup["stage"] == "CUSTODIANS":
            resp = client.post("/setup/custodians", json={"player_id": speaker})
        else:
            resp = client.post("/setup/reveal-objectives", json={"player_id": speaker})
        assert resp.status_code == 200, resp.text
    raise AssertionError("Setup did not finish.")

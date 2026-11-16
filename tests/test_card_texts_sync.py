"""Teksty kart aktywnych talii na froncie = teksty z assetów silnika (wersje TE / Codex).

Gracz czyta kartę w ręce z danych frontu, a silnik rozgrywa ją z assetów - muszą mówić to samo
(np. Hack Election Ω z Thunder's Edge: „During this agenda, you vote last.").
Naprawa: ``uv run python scripts/sync_card_texts.py``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from src.core.registry import StaticDataRegistry

ROOT = Path(__file__).resolve().parent.parent


def test_teksty_kart_na_froncie_zgodne_z_assetami() -> None:
    spec = importlib.util.spec_from_file_location("sync", ROOT / "scripts" / "sync_card_texts.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.diffs(StaticDataRegistry()) == []

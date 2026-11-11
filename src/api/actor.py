"""Tożsamość wykonawcy żądania (RULES.md 44.1a) — JEDYNY punkt jej odczytu w ``api/``.

Dziś aktor przychodzi w nagłówku ``X-Actor-Id`` (brak = tryb zaufany, jedno okno lokalne).
W etapie N1 (RULES.md 44.2) ``get_actor`` czyta token miejsca przy stole i mapuje go na
``player_id``, a ``require_host`` sprawdza rolę hosta — routery się wtedy nie zmieniają.

Każdy endpoint zmieniający stan ma DOKŁADNIE jedną z zależności: ``ActorId`` (akcja gracza
albo stołu — uprawnienia sprawdza ``core/actor.py``) albo ``HostOnly`` (God-Mode / operator).
Pilnuje tego ``tests/test_actor_guard.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

ACTOR_HEADER = "X-Actor-Id"


def get_actor(
    x_actor_id: Annotated[str | None, Header(alias=ACTOR_HEADER)] = None,
) -> str | None:
    """Zwraca ``player_id`` wykonawcy albo ``None`` (tryb zaufany).

    N1: tu wchodzi weryfikacja tokenu (brak/zły token → 401) — w trybie sieciowym NIGDY ``None``.
    """
    actor = (x_actor_id or "").strip()
    return actor or None


def require_host() -> None:
    """Uprawnienie operatora/hosta (God-Mode, Undo/Redo, edycja, nowa gra).

    Tryb lokalny: operator jest hostem, więc przepuszcza. N1: rola ``host`` z tokenu, inaczej 403.
    """


ActorId = Annotated[str | None, Depends(get_actor)]
"""Parametr routera: aktor żądania (``None`` = tryb zaufany)."""

HostOnly = Depends(require_host)
"""Zależność trasy (``dependencies=[HostOnly]``): akcja operatora/hosta."""

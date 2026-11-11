"""Tożsamość wykonawcy żądania (RULES.md 44.1a, 44.2) — JEDYNY punkt jej odczytu w ``api/``.

Tożsamość (``seats.Identity``) ustala middleware w ``app.py`` z tokenu miejsca (tryb sieciowy)
i kładzie ją w ``request.state.identity``. Tu zamieniamy ją na:

- ``ActorId`` — aktor akcji: tryb lokalny = nagłówek ``X-Actor-Id`` (brak = tryb zaufany);
  tryb sieciowy = gracz z tokenu (nagłówek ``X-Actor-Id`` jest ignorowany), host bez miejsca
  = operator (tryb zaufany);
- ``HostOnly`` — God-Mode / operator: tryb sieciowy wymaga roli host (inaczej 403);
- ``require_view`` / ``viewer_player`` — czyje prywatne dane wolno pokazać w GET (RULES.md 44.3).

Każdy endpoint zmieniający stan ma DOKŁADNIE jedną z zależności ``ActorId`` / ``HostOnly``
(pilnuje ``tests/test_actor_guard.py``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from src.api.seats import LOCAL, Identity
from src.core.actor import ActorError

ACTOR_HEADER = "X-Actor-Id"


def identity_of(request: Request) -> Identity:
    """Tożsamość żądania ustalona przez middleware (domyślnie tryb lokalny)."""
    identity = getattr(request.state, "identity", None)
    return identity if isinstance(identity, Identity) else LOCAL


def get_actor(
    request: Request,
    x_actor_id: Annotated[str | None, Header(alias=ACTOR_HEADER)] = None,
) -> str | None:
    """Zwraca ``player_id`` wykonawcy albo ``None`` (tryb zaufany)."""
    identity = identity_of(request)
    if identity.network:
        return identity.player_id
    actor = (x_actor_id or "").strip()
    return actor or None


def require_host(request: Request) -> None:
    """Uprawnienie operatora/hosta (God-Mode, Undo/Redo, edycja, nowa gra, zaproszenia)."""
    identity = identity_of(request)
    if identity.network and not identity.host:
        raise ActorError("Only the host can do this.")


def require_view(request: Request, player_id: str | None) -> None:
    """GET z prywatnymi danymi gracza: w sieci tylko własne (host-operator widzi wszystko)."""
    identity = identity_of(request)
    if identity.sees_everything or player_id is None:
        return
    if player_id != identity.player_id:
        raise ActorError(f"You can only see your own private information, not {player_id!r}.")


def viewer_player(request: Request, requested: str | None) -> str | None:
    """Gracz, z którego perspektywy budujemy odpowiedź: w sieci zawsze własny (z tokenu)."""
    identity = identity_of(request)
    if identity.sees_everything:
        return requested
    return identity.player_id


ActorId = Annotated[str | None, Depends(get_actor)]
"""Parametr routera: aktor żądania (``None`` = tryb zaufany)."""

HostOnly = Depends(require_host)
"""Zależność trasy (``dependencies=[HostOnly]``): akcja operatora/hosta."""

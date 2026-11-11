"""Strażnik RULES.md 44.1a: każdy endpoint zmieniający stan jest sklasyfikowany.

Dokładnie jedna z zależności: ``get_actor`` (akcja gracza/stołu, z parametrem ``actor``,
który router RZECZYWIŚCIE używa) albo ``require_host`` (God-Mode / operator).
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from src.api.actor import get_actor, public_join, require_host
from src.api.app import create_app

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def _calls(dependant: Dependant) -> Iterator[Callable[..., Any]]:
    for dep in dependant.dependencies:
        if dep.call is not None:
            yield dep.call
        yield from _calls(dep)


def _flatten(routes: list[Any]) -> Iterator[APIRoute]:
    """Trasy aplikacji, także z dołączonych routerów (FastAPI >=0.145 opakowuje je)."""
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        inner = getattr(r, "original_router", None)
        if inner is not None:
            yield from _flatten(list(inner.routes))


def _mutating_routes() -> list[APIRoute]:
    app = create_app()
    return [r for r in _flatten(list(app.routes)) if set(r.methods or ()) & _MUTATING]


def _route_id(r: APIRoute) -> str:
    return f"{sorted(r.methods or ())[0]} {r.endpoint.__module__.rsplit('.', 1)[-1]}:{r.path}"


_ROUTES = _mutating_routes()


@pytest.mark.parametrize("route", _ROUTES, ids=[_route_id(r) for r in _ROUTES])
def test_route_has_exactly_one_actor_class(route: APIRoute) -> None:
    calls = list(_calls(route.dependant))
    if public_join in calls:  # jedyna trasa publiczna: dołączenie do lobby (RULES.md 44.6)
        assert route.path == "/lobby/join", route.path
        return
    kinds = [c for c in calls if c in (get_actor, require_host)]
    assert len(kinds) == 1, f"{route.path}: wymagane jedno z ActorId/HostOnly: {kinds}"


@pytest.mark.parametrize("route", _ROUTES, ids=[_route_id(r) for r in _ROUTES])
def test_actor_parameter_is_used(route: APIRoute) -> None:
    """Parametr ``actor`` nie może wisieć martwo — router przekazuje go do ``core/actor``."""
    if get_actor not in list(_calls(route.dependant)):
        return
    fn = route.endpoint
    params = inspect.signature(fn).parameters
    assert "actor" in params, f"{route.path}: parametr ActorId musi nazywać się 'actor'"
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    func = tree.body[0]
    assert isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef))
    used = any(
        isinstance(n, ast.Name) and n.id == "actor" and isinstance(n.ctx, ast.Load)
        for stmt in func.body
        for n in ast.walk(stmt)
    )
    assert used, f"{route.path}: parametr 'actor' nie jest używany"


def test_guard_sees_many_routes() -> None:
    assert len(_ROUTES) >= 95

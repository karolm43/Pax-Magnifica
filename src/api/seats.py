"""Miejsca przy stole i tożsamość klienta (RULES.md 44.2) — etap N1.

Tryb lokalny (domyślny): brak tokenów, jedno okno, operator widzi i robi wszystko; aktor
z nagłówka ``X-Actor-Id`` (RULES.md 44.1a). Tryb sieciowy (``create_app(network=True)``):
każde żądanie musi nieść token miejsca (nagłówek ``X-Seat-Token`` albo ``?token=`` dla
WebSocketu). Token → ``Identity`` (gracz i/lub host). Tokeny żyją w pamięci procesu (jak stan
gry — trwałość to N3); NIE trafiają do ``GameState``, więc nigdy nie są rozsyłane.

Role: host (God-Mode, zaproszenia, opcjonalnie też miejsce przy stole) i gracz (jedno miejsce).
Host bez miejsca jest operatorem: widzi pełny stan i działa w trybie zaufanym.
"""

from __future__ import annotations

import hmac
import secrets
from contextvars import ContextVar
from dataclasses import dataclass

SEAT_TOKEN_HEADER = "X-Seat-Token"
TOKEN_QUERY = "token"


@dataclass(frozen=True)
class Identity:
    """Kto stoi za żądaniem."""

    network: bool
    player_id: str | None = None
    host: bool = False

    @property
    def sees_everything(self) -> bool:
        """Pełny stan bez projekcji: tryb lokalny albo host-operator bez miejsca."""
        return not self.network or (self.host and self.player_id is None)

    @property
    def view_key(self) -> str:
        """Klucz projekcji (połączenia z tym samym kluczem dostają ten sam widok)."""
        return "*" if self.sees_everything else (self.player_id or "")


LOCAL = Identity(network=False)

current_identity: ContextVar[Identity] = ContextVar("current_identity", default=LOCAL)
"""Tożsamość bieżącego żądania (ustawia middleware); czyta ją m.in. ``StateService.envelope``."""


def _new_token() -> str:
    return secrets.token_urlsafe(18)


class SeatRegistry:
    """Tokeny miejsc i hosta. W trybie lokalnym ``resolve`` zawsze zwraca ``LOCAL``."""

    def __init__(self, *, network: bool = False, host_token: str | None = None) -> None:
        self.network = network
        self.host_token = (host_token or _new_token()) if network else ""
        self._seat_tokens: dict[str, str] = {}  # player_id -> token
        self.host_seat: str | None = None

    # --- Odczyt tożsamości -------------------------------------------------------------

    def resolve(self, token: str | None) -> Identity | None:
        """Token → tożsamość; ``None`` = nieznany/brak tokenu w trybie sieciowym (→ 401)."""
        if not self.network:
            return LOCAL
        if not token:
            return None
        if hmac.compare_digest(token, self.host_token):
            return Identity(network=True, player_id=self.host_seat, host=True)
        for player_id, seat_token in self._seat_tokens.items():
            if hmac.compare_digest(token, seat_token):
                if player_id == self.host_seat:
                    return Identity(network=True, player_id=player_id, host=True)
                return Identity(network=True, player_id=player_id)
        return None

    # --- Zarządzanie (host) ------------------------------------------------------------

    def seat_tokens(self, player_ids: list[str]) -> dict[str, str]:
        """Tokeny dla podanych graczy (brakujące są tworzone; usunięci gracze tracą token)."""
        self._seat_tokens = {
            pid: self._seat_tokens.get(pid) or _new_token() for pid in player_ids
        }
        return dict(self._seat_tokens)

    def rotate(self, player_id: str) -> str:
        """Nowy token miejsca (stary link przestaje działać — np. wyciekł)."""
        self._seat_tokens[player_id] = _new_token()
        return self._seat_tokens[player_id]

    def set_host_seat(self, player_id: str | None) -> None:
        """Host siada przy stole jako ``player_id`` (``None`` = operator bez miejsca)."""
        self.host_seat = player_id

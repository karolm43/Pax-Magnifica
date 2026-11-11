"""Miejsca przy stole, lobby i tożsamość klienta (RULES.md 44.2, 44.6) — etapy N1/N3/lobby.

Host = komputer, na którym działa serwer (żądanie z loopbacku, także przez proxy Vite —
patrz ``app.py::_is_local``): zawsze rola host, bez tokenu. Tryb sieciowy (lobby otwarte):
inni gracze dołączają przez ``POST /lobby/join`` (imię → token członka lobby), a host przy
starcie gry przypisuje członków do miejsc (``bind``) — od tej chwili token członka = token
miejsca. Token wędruje w nagłówku ``X-Seat-Token`` albo ``?token=`` (WebSocket).

Tokeny NIE trafiają do ``GameState`` (nigdy nie są rozsyłane); trwałość: JSON w metadanych
pliku partii (``persist`` po każdej zmianie) — linki i dołączeni gracze przeżywają restart.
"""

from __future__ import annotations

import hmac
import json
import secrets
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass

SEAT_TOKEN_HEADER = "X-Seat-Token"
TOKEN_QUERY = "token"
MAX_MEMBERS = 8
MAX_NAME = 40


@dataclass(frozen=True)
class Identity:
    """Kto stoi za żądaniem."""

    network: bool
    player_id: str | None = None
    host: bool = False
    member_id: str | None = None

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


@dataclass
class Member:
    """Gracz, który dołączył do lobby (zanim/odkąd ma miejsce przy stole)."""

    member_id: str
    name: str
    token: str


class SeatRegistry:
    """Tokeny miejsc, lobby i host. Tryb lokalny (lobby zamknięte): tylko ten komputer."""

    def __init__(
        self,
        *,
        network: bool = False,
        host_token: str | None = None,
        saved: str | None = None,
        persist: Callable[[str], None] | None = None,
    ) -> None:
        """``saved`` = JSON z ``to_json`` (wznowienie); jawny ``host_token`` ma pierwszeństwo."""
        self._persist = persist
        self._explicit_network = network
        self._explicit_host_token = host_token
        self.load(saved)

    def load(self, saved: str | None) -> None:
        """Wczytuje rejestr z zapisu partii (np. po „Load game")."""
        data: dict[str, object] = json.loads(saved) if saved else {}
        self.network = self._explicit_network or bool(data.get("network"))
        stored_host = str(data.get("host_token") or "")
        self.host_token = self._explicit_host_token or stored_host or _new_token()
        seats = data.get("seats")
        self._seat_tokens: dict[str, str] = (
            {str(k): str(v) for k, v in seats.items()} if isinstance(seats, dict) else {}
        )
        host_seat = data.get("host_seat")
        self.host_seat: str | None = host_seat if isinstance(host_seat, str) else None
        members = data.get("members")
        self._members: dict[str, Member] = {}
        if isinstance(members, list):
            for raw in members:
                if isinstance(raw, dict):
                    m = Member(str(raw["member_id"]), str(raw["name"]), str(raw["token"]))
                    self._members[m.member_id] = m
        if self.host_token != stored_host:
            self._save()

    def to_json(self) -> str:
        """Stan rejestru do zapisu w pliku partii."""
        return json.dumps(
            {
                "network": self.network,
                "host_token": self.host_token,
                "seats": self._seat_tokens,
                "host_seat": self.host_seat,
                "members": [vars(m) for m in self._members.values()],
            }
        )

    def _save(self) -> None:
        if self._persist is not None:
            self._persist(self.to_json())

    # --- Odczyt tożsamości -------------------------------------------------------------

    def resolve(self, token: str | None, *, local: bool = False) -> Identity | None:
        """Token / pochodzenie → tożsamość; ``None`` = obcy bez ważnego tokenu (→ 401/403).

        Tryb lokalny: ten komputer = operator (``LOCAL``), obcy — brak dostępu.
        Tryb sieciowy: ważny token wygrywa (także na tym komputerze — test kilku kart),
        bez tokenu ten komputer = host (z ewentualnym miejscem ``host_seat``).
        """
        if not self.network:
            return LOCAL if local else None
        if token:
            if hmac.compare_digest(token, self.host_token):
                return self._host()
            member_id = next(
                (
                    m.member_id
                    for m in self._members.values()
                    if hmac.compare_digest(token, m.token)
                ),
                None,
            )
            for player_id, seat_token in self._seat_tokens.items():
                if hmac.compare_digest(token, seat_token):
                    host = player_id == self.host_seat
                    return Identity(
                        network=True, player_id=player_id, host=host, member_id=member_id
                    )
            if member_id is not None:
                return Identity(network=True, member_id=member_id)
        return self._host() if local else None

    def _host(self) -> Identity:
        return Identity(network=True, player_id=self.host_seat, host=True)

    # --- Lobby ------------------------------------------------------------------------

    def set_network(self, enabled: bool) -> None:
        """Otwiera/zamyka lobby (tryb sieciowy). Zamknięte = tylko ten komputer."""
        self.network = enabled
        self._save()

    def members(self) -> list[Member]:
        return list(self._members.values())

    def member_seat(self, member_id: str) -> str | None:
        """Miejsce (``player_id``) przypisane członkowi lobby, jeśli gra już wystartowała."""
        member = self._members.get(member_id)
        if member is None:
            return None
        return next((pid for pid, tok in self._seat_tokens.items() if tok == member.token), None)

    def join(self, name: str) -> Member:
        """Nowy członek lobby. Raises: ``ValueError`` (lobby zamknięte / pełne / złe imię)."""
        clean = " ".join(name.split())[:MAX_NAME]
        if not self.network:
            raise ValueError("No network game is open on this server.")
        if not clean:
            raise ValueError("Enter your name.")
        if len(self._members) >= MAX_MEMBERS:
            raise ValueError("The lobby is full.")
        member = Member(member_id=f"m{secrets.token_hex(4)}", name=clean, token=_new_token())
        self._members[member.member_id] = member
        self._save()
        return member

    def kick(self, member_id: str) -> None:
        """Usuwa członka lobby (jego token przestaje działać, także jako token miejsca)."""
        member = self._members.pop(member_id, None)
        if member is not None:
            self._seat_tokens = {
                pid: tok for pid, tok in self._seat_tokens.items() if tok != member.token
            }
            self._save()

    def bind(self, assignments: dict[str, str]) -> None:
        """Przypisuje miejsca: ``{player_id: member_id | "host"}`` (start gry z lobby).

        Członek dostaje miejsce pod SWOIM tokenem (nie musi niczego klikać); ``host`` siada
        jako ten gracz. Raises: ``ValueError`` dla nieznanego członka.
        """
        for player_id, who in assignments.items():
            if who == "host":
                self.host_seat = player_id
                continue
            member = self._members.get(who)
            if member is None:
                raise ValueError(f"Unknown lobby member: {who}")
            self._seat_tokens[player_id] = member.token
        self._save()

    # --- Zarządzanie miejscami (host) ---------------------------------------------------

    def seat_tokens(self, player_ids: list[str]) -> dict[str, str]:
        """Tokeny dla podanych graczy (brakujące są tworzone; usunięci gracze tracą token)."""
        before = dict(self._seat_tokens)
        self._seat_tokens = {
            pid: self._seat_tokens.get(pid) or _new_token() for pid in player_ids
        }
        if self._seat_tokens != before:
            self._save()
        return dict(self._seat_tokens)

    def rotate(self, player_id: str) -> str:
        """Nowy token miejsca (stary link przestaje działać — np. wyciekł)."""
        self._seat_tokens[player_id] = _new_token()
        self._save()
        return self._seat_tokens[player_id]

    def set_host_seat(self, player_id: str | None) -> None:
        """Host siada przy stole jako ``player_id`` (``None`` = operator bez miejsca)."""
        self.host_seat = player_id
        self._save()

    def persist_now(self) -> None:
        """Zapisuje rejestr do BIEŻĄCEGO pliku partii (np. po przejściu do nowego pliku)."""
        self._save()

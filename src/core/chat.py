"""Czat przy stole i szepty (whisper) — RULES.md 47.6 (decyzja użytkownika 2026-11-17).

Czat NIE jest stanem gry: żyje obok ``GameState`` (Undo/Redo go nie cofa, zapis partii trzyma go
w metadanych). R_deals: gracze negocjują i zawierają umowy w dowolnej chwili, także z nie-sąsiadami
— czat to miejsce tych rozmów.

* Wiadomość publiczna (``to is None``) — treść widzą wszyscy.
* Szept (``to = player_id``) — treść widzą TYLKO nadawca i adresat; pozostali widzą sam fakt
  „X szepcze do Y” (decyzja użytkownika: „gracze widzą, że whisperujesz”).

Funkcje CZYSTE; czas wstrzykiwany (``now``), nigdy ``time.time()`` w ``core/``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

MAX_LENGTH = 500
"""Najdłuższa wiadomość (znaki) — czat ma być krótki i nieinwazyjny."""

MAX_MESSAGES = 500
"""Ile ostatnich wiadomości trzyma dziennik (starsze odpadają)."""


@dataclass(frozen=True)
class ChatMessage:
    """Jedna wiadomość: numer, nadawca, adresat szeptu (``None`` = do wszystkich), treść, czas."""

    seq: int
    sender: str
    text: str
    at: float
    to: str | None = None


@dataclass(frozen=True)
class ChatLog:
    """Dziennik czatu partii (niezmienny; ``post`` zwraca nowy)."""

    messages: tuple[ChatMessage, ...] = field(default_factory=tuple)

    @property
    def last_seq(self) -> int:
        return self.messages[-1].seq if self.messages else 0

    def to_json(self) -> str:
        return json.dumps([asdict(m) for m in self.messages])

    @classmethod
    def from_json(cls, raw: str | None) -> ChatLog:
        if not raw:
            return cls()
        try:
            items = json.loads(raw)
        except ValueError:
            return cls()
        return cls(
            tuple(
                ChatMessage(
                    seq=int(m["seq"]),
                    sender=str(m["sender"]),
                    text=str(m["text"]),
                    at=float(m["at"]),
                    to=None if m.get("to") is None else str(m["to"]),
                )
                for m in items
                if isinstance(m, dict)
            )
        )


def post(
    log: ChatLog,
    players: set[str] | list[str],
    sender: str,
    text: str,
    now: float,
    to: str | None = None,
) -> ChatLog:
    """Dopisuje wiadomość ``sender`` (szept, gdy ``to``); zwraca nowy dziennik.

    Raises:
        ValueError: Nieznany nadawca/adresat, szept do siebie, pusta albo za długa treść.
    """
    known = set(players)
    if sender not in known:
        raise ValueError(f"Unknown player: {sender}")
    if to is not None:
        if to not in known:
            raise ValueError(f"Unknown player: {to}")
        if to == sender:
            raise ValueError("You cannot whisper to yourself.")
    body = text.strip()
    if not body:
        raise ValueError("The message is empty.")
    if len(body) > MAX_LENGTH:
        raise ValueError(f"The message is too long (max {MAX_LENGTH} characters).")
    message = ChatMessage(seq=log.last_seq + 1, sender=sender, text=body, at=now, to=to)
    return ChatLog((*log.messages, message)[-MAX_MESSAGES:])


def visible(log: ChatLog, viewer: str | None, *, sees_everything: bool) -> list[dict[str, Any]]:
    """Wiadomości z perspektywy ``viewer``: cudzy szept bez treści (``text = None``).

    ``sees_everything`` (tryb lokalny / host-operator bez miejsca) widzi wszystko.
    """
    out: list[dict[str, Any]] = []
    for m in log.messages:
        private = m.to is not None and not sees_everything and viewer not in (m.sender, m.to)
        out.append(
            {
                "seq": m.seq,
                "sender": m.sender,
                "to": m.to,
                "whisper": m.to is not None,
                "text": None if private else m.text,
                "at": m.at,
            }
        )
    return out

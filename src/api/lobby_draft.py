"""Wspólny szkic kreatora nowej gry — lobby na żywo (RULES.md 44.5a).

Szkic to stan kreatora współdzielony przez hosta i gości::

    {"slots": [...], "owners": [...], "mapString": str, "step": int, "version": int}

- ``slots`` — pola jak ``SetupSlot`` we froncie (nazwa, człowiek/bot, frakcja, technologie,
  kolor, miejsce…). Serwer zna tylko klucze potrzebne do pilnowania reguł lobby.
- ``owners`` — kto steruje slotem: ``"host"``, ``member_id`` gościa albo ``None`` (bot /
  wolne miejsce dla dołączającego).

Host zmienia wszystko; gość — tylko pola SWOJEGO slotu (``GUEST_FIELDS``). Frakcja, kolor
i miejsce przy stole nie mogą się powtórzyć. Czyste funkcje na kopiach — rejestr (``seats``)
zapisuje wynik dopiero, gdy wszystko jest poprawne.
"""

from __future__ import annotations

import copy
from typing import Any

RANDOM_FACTION = "__random__"  # jak ``RANDOM_FACTION`` w kreatorze frontu
GUEST_FIELDS = frozenset({"factionId", "startingTech", "color", "seat", "name"})
"""Pola slotu, które gość może zmieniać (tylko w swoim slocie)."""

Draft = dict[str, Any]


class DraftPermissionError(PermissionError):
    """Gość próbuje zmienić coś poza swoim slotem (``api/`` → 403)."""


def new_draft(raw: Draft, previous_version: int) -> Draft:
    """Pełny szkic od hosta (start lobby / zmiana liczby graczy). Raises: ``ValueError``."""
    slots = raw.get("slots")
    if not isinstance(slots, list) or not slots or not all(isinstance(s, dict) for s in slots):
        raise ValueError("The draft has no player slots.")
    owners = raw.get("owners")
    owner_list = list(owners) if isinstance(owners, list) else []
    owner_list = (owner_list + [None] * len(slots))[: len(slots)]
    draft: Draft = {
        "slots": copy.deepcopy(slots),
        "owners": owner_list,
        "mapString": str(raw.get("mapString") or ""),
        "step": int(raw.get("step") or 0),
        "version": previous_version + 1,
    }
    check_unique(draft)
    return draft


def slot_of(draft: Draft, who: str | None) -> int | None:
    """Indeks slotu sterowanego przez ``who`` (``"host"`` / ``member_id``)."""
    owners: list[str | None] = draft["owners"]
    return owners.index(who) if who is not None and who in owners else None


def apply_patch(draft: Draft, who: str, is_host: bool, patch: Draft) -> Draft:
    """Zmiana szkicu (na kopii). Raises: ``ValueError`` (reguły), ``DraftPermissionError``."""
    result = copy.deepcopy(draft)
    if not is_host and set(patch) - {"slots"}:
        raise DraftPermissionError("Only the host changes the map, the steps and the player order.")
    if is_host and "mapString" in patch:
        result["mapString"] = str(patch["mapString"] or "")
    if is_host and "step" in patch:
        result["step"] = int(patch["step"])
    if is_host and "swap" in patch:
        _swap_players(result, patch["swap"])
    changes = patch.get("slots") or {}
    if not isinstance(changes, dict):
        raise ValueError("Invalid slot changes.")
    mine = slot_of(result, who)
    slots: list[Draft] = result["slots"]
    owners: list[str | None] = result["owners"]
    for key, fields in changes.items():
        index = int(key)
        if not 0 <= index < len(slots) or not isinstance(fields, dict):
            raise ValueError(f"Invalid slot {key}.")
        if not is_host:
            if index != mine:
                raise DraftPermissionError("You can only change your own seat.")
            if set(fields) - GUEST_FIELDS:
                raise DraftPermissionError("You can only change your faction, color and seat.")
        slots[index].update(fields)
        if fields.get("controlType") == "BOT" and owners[index] not in (None, "host"):
            owners[index] = None  # slot zamieniony na bota — gość czeka na wolne miejsce
    check_unique(result)
    result["version"] = int(draft.get("version", 0)) + 1
    return result


def _swap_players(draft: Draft, pair: Any) -> None:
    """Zamiana numerów dwóch graczy (host): sloty RAZEM z właścicielami (kto tam siedzi).

    Miejsce przy stole, kolor i frakcja jadą ze slotem, więc osoba zostaje przy swoim
    miejscu — zmienia się tylko jej numer gracza (gracz 1 = mówca na start).
    Raises: ``ValueError``.
    """
    if not isinstance(pair, list) or len(pair) != 2:
        raise ValueError("Swap needs two player numbers.")
    i, j = int(pair[0]), int(pair[1])
    slots: list[Draft] = draft["slots"]
    owners: list[str | None] = draft["owners"]
    if not (0 <= i < len(slots) and 0 <= j < len(slots)):
        raise ValueError("Invalid players to swap.")
    slots[i], slots[j] = slots[j], slots[i]
    owners[i], owners[j] = owners[j], owners[i]


def normalize_owners(draft: Draft, members: dict[str, str]) -> None:
    """Porządkuje właścicieli (w miejscu): host na 1. wolnym, goście na wolnych slotach-ludziach.

    ``members`` = ``{member_id: imię}``. Właściciele spoza lobby są zdejmowani; gość bez
    slotu dostaje pierwsze wolne miejsce człowieka (z jego imieniem). Brak miejsc — czeka.
    """
    slots: list[Draft] = draft["slots"]
    owners: list[str | None] = draft["owners"]
    for i, owner in enumerate(owners):
        if owner is not None and owner != "host" and owner not in members:
            owners[i] = None
    if "host" not in owners and owners and owners[0] is None:
        owners[0] = "host"
    for member_id, name in members.items():
        if member_id in owners:
            continue
        free = next(
            (
                i
                for i, slot in enumerate(slots)
                if owners[i] is None and slot.get("controlType", "HUMAN") == "HUMAN"
            ),
            None,
        )
        if free is None:
            break
        owners[free] = member_id
        slots[free]["name"] = name


def check_unique(draft: Draft) -> None:
    """Frakcja, kolor i miejsce przy stole — każde najwyżej raz. Raises: ``ValueError``."""
    for key, label in (("factionId", "faction"), ("color", "color"), ("seat", "seat")):
        seen: set[str] = set()
        for slot in draft["slots"]:
            value = slot.get(key)
            if value in (None, "", RANDOM_FACTION):
                continue
            if str(value) in seen:
                raise ValueError(f"That {label} is already taken.")
            seen.add(str(value))

"""Warstwa API Custodian Engine (FastAPI + WebSocket).

Wystawia stan gry (``GameState``), geometrię mapy (``HexGrid``) oraz operacje
God-Mode (nadpisanie/patch stanu) i Undo/Redo (``EventStore``). Zmiany stanu są
rozsyłane do podłączonych klientów przez WebSocket, co pozwala frontendowi
(React + Zustand) utrzymywać synchronizację z backendem.
"""

from __future__ import annotations

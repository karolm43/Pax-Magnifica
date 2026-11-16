"""Punkt wejścia serwera API: ``uv run python -m src.api``.

Uruchamia aplikację FastAPI na Uvicornie (domyślnie ``127.0.0.1:8000``).
Przeznaczone do ręcznego uruchamiania w terminalu podczas developmentu — nie
jest odpalane automatycznie przez agenta.

Przed startem zwalnia port (health-check): osierocony proces z poprzedniej sesji
często trzymał port 8000 (``Errno 10048``) i serwował STARY kod. Zabijamy go, by
nowy serwer na pewno wystartował ze świeżym kodem.

Gra sieciowa (RULES.md 44.2): ``uv run python -m src.api --network`` — każde żądanie wymaga
tokenu miejsca; przy starcie drukowany jest link hosta. Token hosta można przypiąć zmienną
``CUSTODIAN_HOST_TOKEN`` (ten sam link po restarcie). Graczom zdalnym udostępnia się FRONT
(``npm run dev -- --host``), który przez proxy woła backend na 127.0.0.1 — backend zostaje lokalny.

Zapis partii (RULES.md 44.4): stan, historia (Undo), mapa i tokeny miejsc są zapisywane na bieżąco
do pliku SQLite (domyślnie ``saves/game.db``) — restart serwera wznawia partię. ``--save PLIK``
wybiera inny plik (np. osobny na każdą partię), ``--fresh`` odkłada stary zapis i zaczyna od zera.
Zapis, którego nie da się wczytać (np. po zmianie schematu), jest odkładany jako ``*.broken-*``.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from src.api.app import create_app
from src.api.saves import SaveManager
from src.core import game_clock
from src.core.event_store import EventStore

HOST = "127.0.0.1"
PORT = 8000
SAVES_DIR = Path("saves")
BUG_REPORTS_DIR = Path("bug_reports")
"""Zgłoszenia „Report bug" od wszystkich graczy (także z sieci) lądują na dysku hosta."""



def _port_in_use(host: str, port: int) -> bool:
    """Sprawdza, czy ktoś nasłuchuje na ``host:port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _free_port_windows(port: int) -> None:
    """Ubija procesy trzymające ``port`` na Windows (netstat + taskkill).

    Działa best-effort: błędy są ignorowane (brak uprawnień, brak procesu).
    Na nie-Windows jest no-op — tam zwykle wystarcza, że poprzedni proces
    został zatrzymany poprawnie.
    """
    if sys.platform != "win32":
        return
    try:
        output = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        return

    pids: set[str] = set()
    needle = f":{port}"
    for line in output.splitlines():
        parts = line.split()
        # Format: Proto  Local  Foreign  State  PID
        if len(parts) >= 5 and parts[1].endswith(needle) and parts[3] == "LISTENING":
            pids.add(parts[4])

    for pid in pids:
        if pid == "0":
            continue
        subprocess.run(
            ["taskkill", "/F", "/PID", pid],
            capture_output=True,
            text=True,
            check=False,
        )


def _ensure_port_free(host: str, port: int) -> None:
    """Zwalnia port przed startem (jeśli zajęty) i czeka chwilę na zwolnienie."""
    if not _port_in_use(host, port):
        return
    print(f"[health-check] Port {port} is busy - releasing orphaned process...")
    _free_port_windows(port)
    for _ in range(10):
        if not _port_in_use(host, port):
            print(f"[health-check] Port {port} released.")
            return
        time.sleep(0.3)
    print(f"[health-check] WARNING: port {port} is still busy - startup may fail.")


def _set_aside(path: Path, reason: str) -> None:
    """Odkłada plik zapisu obok (nic nie kasujemy) — ``game.db`` → ``game.<reason>-<czas>.db``."""
    target = path.with_name(f"{path.stem}.{reason}-{time.strftime('%Y%m%d-%H%M%S')}{path.suffix}")
    path.rename(target)
    print(f"[save] Previous save moved to {target}")


def _open_store(path: Path, fresh: bool) -> EventStore:
    """Plik partii: wznowienie albo nowy; nieczytelny zapis jest odkładany, nie kasowany."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if fresh and path.exists():
        _set_aside(path, "old")
    store: EventStore | None = None
    try:
        store = EventStore(path)
        store.current()
    except Exception as exc:  # noqa: BLE001 — każdy błąd odczytu = nie wznawiamy tej partii
        if store is not None:
            store.close()
        print(f"[save] Cannot load {path}: {exc}")
        _set_aside(path, "broken")
        store = EventStore(path)
    return store


def _pause_clock_after_restart(server_app: FastAPI) -> None:
    """Zegar szachowy staje na chwili ostatniej akcji — przestój serwera nie zjada czasu graczy."""
    service = server_app.state.ctx.service
    state = service.current_state()
    if not state.clock.enabled or state.clock.paused:
        return
    feed = service.activity_feed()
    last = next((created for _, _, current, created, _ in feed if current and created), None)
    paused = game_clock.pause(state, last if last is not None else service.now())
    service.replace_state(paused, label="clock:pause-restart")
    print("[save] Chess clock paused after restart - resume it in the game.")


def main() -> None:
    """Startuje serwer deweloperski Uvicorn (po zwolnieniu portu); ``--network`` = gra sieciowa."""
    parser = argparse.ArgumentParser(prog="python -m src.api")
    parser.add_argument("--network", action="store_true", help="od razu otwórz lobby sieciowe")
    parser.add_argument(
        "--save", type=Path, default=None, help="konkretny plik partii (domyślnie ostatni w saves/)"
    )
    parser.add_argument("--fresh", action="store_true", help="zacznij w nowym pliku zapisu")
    parser.add_argument(
        "--no-bots", action="store_true", help="boty nie grają same (sterowanie ręczne/God-Mode)"
    )
    args = parser.parse_args()
    saves = SaveManager(SAVES_DIR)
    path = args.save or (None if args.fresh else saves.latest()) or saves.new_path()
    store = _open_store(path, fresh=bool(args.save and args.fresh))
    resumed = store.current() is not None
    server_app = create_app(
        store=store,
        network=args.network,
        host_token=os.environ.get("CUSTODIAN_HOST_TOKEN"),
        saves_dir=SAVES_DIR,
        bug_reports_dir=BUG_REPORTS_DIR,
        bots=not args.no_bots,
    )
    server_app.state.ctx.save_name = path.name
    print(f"[save] {'Resumed game from' if resumed else 'New save file'} {path}")
    if resumed:
        _pause_clock_after_restart(server_app)
    print("[network] Open http://localhost:5173 - host or join a network game from the menu.")
    _ensure_port_free(HOST, PORT)
    uvicorn.run(server_app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()

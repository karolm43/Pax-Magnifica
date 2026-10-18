"""Punkt wejścia serwera API: ``uv run python -m src.api``.

Uruchamia aplikację FastAPI na Uvicornie (domyślnie ``127.0.0.1:8000``).
Przeznaczone do ręcznego uruchamiania w terminalu podczas developmentu — nie
jest odpalane automatycznie przez agenta.

Przed startem zwalnia port (health-check): osierocony proces z poprzedniej sesji
często trzymał port 8000 (``Errno 10048``) i serwował STARY kod. Zabijamy go, by
nowy serwer na pewno wystartował ze świeżym kodem.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time

import uvicorn

from src.api.app import create_app

HOST = "127.0.0.1"
PORT = 8000

app = create_app()


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
    print(f"[health-check] Port {port} zajęty — zwalniam osierocony proces...")
    _free_port_windows(port)
    for _ in range(10):
        if not _port_in_use(host, port):
            print(f"[health-check] Port {port} zwolniony.")
            return
        time.sleep(0.3)
    print(f"[health-check] UWAGA: port {port} nadal zajęty — start może się nie udać.")


def main() -> None:
    """Startuje serwer deweloperski Uvicorn (po zwolnieniu portu)."""
    _ensure_port_free(HOST, PORT)
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()

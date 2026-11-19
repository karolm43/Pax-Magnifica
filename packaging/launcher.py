"""Launcher paczki Pax Magnifica (``PaxMagnifica.exe``): serwer + przeglądarka jednym kliknięciem.

Uruchamia JEDEN serwer (API + zbudowany frontend, ``src/api/bundle.py``) na porcie 8000 i otwiera
przeglądarkę. Okno konsoli = gra działa; zamknięcie okna kończy grę (partia jest zapisywana
na bieżąco w ``saves/`` obok ``.exe`` i wznawia się przy następnym starcie).

Działa też bez zamrażania (test paczki z repo): ``uv run python packaging/launcher.py``.
"""

from __future__ import annotations

import multiprocessing
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

DEFAULT_PORT = 8000
PORT_TRIES = 20


def _root() -> Path:
    """Katalog paczki: obok ``.exe`` (zamrożony) albo korzeń repo (uruchomienie ze źródeł)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


def _pick_port() -> int:
    """Pierwszy wolny port od 8000 — nie ubijamy cudzych procesów na komputerze gracza."""
    for port in range(DEFAULT_PORT, DEFAULT_PORT + PORT_TRIES):
        if _port_free(port):
            return port
    raise SystemExit(f"No free port in {DEFAULT_PORT}-{DEFAULT_PORT + PORT_TRIES - 1}.")


def _lan_addresses() -> list[str]:
    """Adresy IPv4 tego komputera (LAN/ZeroTier) — do podania znajomym w grze sieciowej."""
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return sorted({str(info[4][0]) for info in infos if not str(info[4][0]).startswith("127.")})


def _open_browser_when_ready(url: str, port: int) -> None:
    for _ in range(120):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.25)
    webbrowser.open(url)


def _banner(port: int) -> None:
    line = "=" * 64
    print(line)
    print("  PAX MAGNIFICA")
    print(f"  Game:  http://localhost:{port}/   (opens in your browser)")
    print("  Keep this window open while playing - closing it quits the game.")
    print("  Your game is saved automatically in the 'saves' folder.")
    addresses = _lan_addresses()
    if addresses:
        print("  Network game: copy invite links in the game (they use these addresses):")
        for address in addresses:
            print(f"     http://{address}:{port}/")
    print(line)


def main() -> None:
    root = _root()
    os.environ.setdefault("CUSTODIAN_ROOT", str(root))
    os.chdir(root)  # saves/ i bug_reports/ obok .exe

    # Import PO ustawieniu CUSTODIAN_ROOT — src.config czyta go przy imporcie.
    import uvicorn

    from src.api.__main__ import build_parser, build_server_app
    from src.api.bundle import BundleApp

    args = build_parser().parse_args()
    api = build_server_app(args)
    port = _pick_port()
    app = BundleApp(api, root / "frontend" / "dist")
    _banner(port)
    if os.environ.get("PAX_NO_BROWSER") != "1":
        url = f"http://localhost:{port}/"
        threading.Thread(target=_open_browser_when_ready, args=(url, port), daemon=True).start()
    # proxy_headers=False: o hoście decyduje wyłącznie adres połączenia (patrz src/api/bundle.py).
    uvicorn.run(
        app, host="0.0.0.0", port=port, access_log=False, log_level="warning", proxy_headers=False
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()  # procesy robocze bota (ProcessPoolExecutor) w .exe
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — w .exe okno zamknęłoby się bez śladu
        import traceback

        traceback.print_exc()
        print(f"\nPax Magnifica failed to start: {exc}")
        input("Press Enter to close...")

"""Router dźwięku (czysta prezentacja): lista plików audio i kontekst do kwestii frakcji.

- ``GET /audio/manifest`` — jakie pliki NAPRAWDĘ leżą w ``assets/``: głosy frakcji
  (``assets/voices/<frakcja>/*``), transmisje (``assets/voices/transmissions/*``), muzyka tła
  (``assets/music/[<nastrój>/]*``) i dźwięki interfejsu (``assets/extra/sfx/ui/*``). Front pyta
  RAZ, zamiast zgadywać nazwy (każdy brak byłby czerwonym 404 w konsoli). Pliki serwuje ``/static``.
- ``GET /audio/homes`` — pozycje systemów domowych graczy (kwestie „obrona/inwazja domu”).

Same odczyty, bez zmiany stanu — więc bez ``actor``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from src import config
from src.api.context import AppContext, get_ctx
from src.core.board_graph import home_positions_by_player

router = APIRouter(prefix="/audio", tags=["audio"])

# Formaty, które przeglądarka odtwarza natywnie.
AUDIO_EXTENSIONS = {".mp3", ".ogg", ".opus", ".wav", ".m4a", ".aac", ".flac", ".webm"}


def _audio_files(folder: Path) -> list[str]:
    """Nazwy plików audio bezpośrednio w katalogu (posortowane; pusty, gdy brak katalogu)."""
    if not folder.is_dir():
        return []
    return sorted(
        p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )


def build_manifest(assets_dir: Path) -> dict[str, object]:
    """Spis plików audio w ``assets_dir`` (osobna funkcja, żeby test mógł podać katalog)."""
    voices_dir = assets_dir / "voices"
    voices: dict[str, list[str]] = {}
    if voices_dir.is_dir():
        for sub in sorted(voices_dir.iterdir()):
            if sub.is_dir() and sub.name != "transmissions":
                files = _audio_files(sub)
                if files:
                    voices[sub.name] = files
    music_dir = assets_dir / "music"
    # Klucz "" = pliki leżące wprost w assets/music/ (bez podziału na nastroje).
    music: dict[str, list[str]] = {}
    root_tracks = _audio_files(music_dir)
    if root_tracks:
        music[""] = root_tracks
    if music_dir.is_dir():
        for sub in sorted(music_dir.iterdir()):
            if sub.is_dir():
                files = _audio_files(sub)
                if files:
                    music[sub.name] = files
    return {
        "voices": voices,
        "transmissions": _audio_files(voices_dir / "transmissions"),
        "music": music,
        "ui": _audio_files(assets_dir / "extra" / "sfx" / "ui"),
    }


@router.get("/manifest")
def get_audio_manifest() -> dict[str, object]:
    """Spis plików audio (głosy, transmisje, muzyka, UI) — ścieżki względne wobec ``/static``."""
    return build_manifest(config.ASSETS_DIR)


@router.get("/homes")
def get_audio_homes(ctx: AppContext = Depends(get_ctx)) -> dict[str, list[str]]:
    """Pozycje systemów domowych graczy: ``{player_id: [pozycje]}``."""
    return home_positions_by_player(ctx.service.current_state(), ctx.registry)

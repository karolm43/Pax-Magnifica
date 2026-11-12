"""Mierzy promień tarczy każdej planety na grafice jej kafelka.

Dane AsyncTI4 podają środek planety na kafelku (``planetLayout.centerPosition``), ale promień
(``planetRadius``) tylko dla kilku planet. Front (okno inwazji) potrzebuje promienia, żeby wyciąć
planetę z kafelka w całości i zachować różnice wielkości między planetami - mierzymy go więc
z samego obrazka: na promieniach od środka szukamy krawędzi tarczy (spadek średniej jasności
z pasa wewnątrz do pasa na zewnątrz okręgu), a kwantylem po kątach odcinamy etykiety, ikony,
pierścienie dekoracji i ciemną stronę planety.

Oficjalne grafiki rysują planety w praktyce w dwóch rozmiarach: zwykłe (~60 px, ``STANDARD``)
i duże (Mecatol, legendarne, Thunder's Edge: ~95-125 px). Pomiar zwykłych planet na zatłoczonych
kafelkach bywa zaszumiony, więc zapisujemy tylko planety wyraźnie duże (>= ``LARGE_FROM``);
pozostałe front traktuje jako ``STANDARD`` (``DEFAULT_PLANET_RADIUS`` w ``planetTileArt.ts``).
Tylko aktywne źródła (``assets/enabled_sources.json``).

Wynik: ``frontend/src/entities/data/planetArtRadius.json`` (``{id_planety: promień_px}``).
Uruchomienie: ``uv run --with pillow --with numpy python scripts/measure_planet_radius.py``.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ROOT / "frontend/src/entities/data/planetArtRadius.json"

R_MIN, R_MAX = 18, 140
ANGLES = np.deg2rad(np.arange(0, 360, 4))
# Szerokość pasów porównania jasności po obu stronach krawędzi (px).
BAND = 8
# Który kwantyl spadków po kątach liczy się jako siła krawędzi.
QUANTILE = 0.8
# Promień zwykłej planety na kafelku i próg, od którego planeta jest "duża" (px).
STANDARD = 60
LARGE_FROM = 85


def tile_images() -> dict[str, Path]:
    """Id kafelka -> plik grafiki."""
    out: dict[str, Path] = {}
    for f in (ASSETS / "systems").glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        path = ASSETS / "tiles" / str(data.get("imagePath") or "")
        if data.get("imagePath") and path.exists():
            out[str(data["id"])] = path
    return out


def edge_profile(lum: np.ndarray, alpha: np.ndarray, cx: float, cy: float) -> np.ndarray:
    """Dla każdego promienia: górny kwantyl (po kątach) spadku jasności przez okrąg o tym promieniu.

    Kwantyl, nie mediana: ciemna strona planety (terminator) nie odcina się od tła, więc brzeg
    jest wyraźny tylko na oświetlonej części obwodu - a łagodne ściemnienie wnętrza tarczy
    występuje wszędzie i przy medianie wygrywało z prawdziwym brzegiem.
    """
    h, w = lum.shape
    radii = np.arange(R_MIN, R_MAX + 1)

    def sample(r: np.ndarray) -> np.ndarray:
        xs = np.clip(np.rint(cx + r[:, None] * np.cos(ANGLES)), 0, w - 1).astype(int)
        ys = np.clip(np.rint(cy + r[:, None] * np.sin(ANGLES)), 0, h - 1).astype(int)
        v = lum[ys, xs]
        # Poza heksem (przezroczystość) nie ma ani planety, ani tła - nie liczymy.
        return np.where(alpha[ys, xs] > 200, v, np.nan)

    # Średnie z pasów po obu stronach okręgu (nie pojedyncze piksele): cienkie jasne łuki
    # dekoracji kafelka prawie nie ruszają średniej z pasa, pełna tarcza planety tak.
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        inner = np.nanmean([sample(radii - d) for d in range(2, BAND + 2)], axis=0)
        outer = np.nanmean([sample(radii + d) for d in range(2, BAND + 2)], axis=0)
    drop = inner - outer
    return np.nanquantile(drop, QUANTILE, axis=1)


def measure(path: Path, cx: float, cy: float) -> int | None:
    img = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32)
    rgb, alpha = img[..., :3], img[..., 3]
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    prof = edge_profile(lum, alpha, cx, cy)
    if np.all(np.isnan(prof)):
        return None
    best = int(np.nanargmax(prof))
    if prof[best] < 12:  # brak wyraźnej krawędzi (np. planeta-żeton, mgławica)
        return None
    return int(R_MIN + best)


def main() -> int:
    tiles = tile_images()
    enabled = set(json.loads((ASSETS / "enabled_sources.json").read_text(encoding="utf-8")))
    out: dict[str, int] = {}
    skipped: list[str] = []
    for f in sorted((ASSETS / "planets").glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        if p.get("source") not in enabled:
            continue
        layout = p.get("planetLayout") or {}
        center = layout.get("centerPosition") or p.get("positionInTile")
        tile = tiles.get(str(p.get("tileId") or ""))
        if not center or not tile:
            continue
        r = measure(tile, float(center["x"]), float(center["y"]))
        if r is None:
            skipped.append(p["id"])
            continue
        if r >= LARGE_FROM:
            out[p["id"]] = r
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"duże planety: {len(out)}; bez krawędzi: {' '.join(skipped) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

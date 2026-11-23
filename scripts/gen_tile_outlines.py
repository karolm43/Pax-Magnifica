"""Generuje obrysy niehexagonalnych kafli systemów (Creuss, Crimson, Mallice, Kwon, Ethan).

Kafle „spiralne” (shipPositionsType TYPE09/12/15) mają grafikę większą od heksa (ok. 416x386)
i kształt nieregularny. Frontend używa obrysu jako hit-targetu klikania i podświetleń, zamiast
heksa 345x299. Obrys = kontur kanału alfa (próg 128), uproszczony Douglas-Peuckerem (2 px).

Uruchomienie (zależności tylko na czas skryptu):
    uv run --with pillow --with numpy --with scikit-image python scripts/gen_tile_outlines.py
Wynik: frontend/src/entities/geometry/tileOutlines.generated.ts
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from skimage import measure

ROOT = Path(__file__).resolve().parent.parent
TILES = ROOT / "assets" / "tiles"
OUT = ROOT / "frontend" / "src" / "entities" / "geometry" / "tileOutlines.generated.ts"

# id systemu -> plik grafiki (jak imagePath w frontend/src/entities/data/systems.ts)
SPIRAL_TILES = {
    "51": "51_Creuss.png",
    "118": "118_Crimson.png",
    "82a": "82a_Mallice_locked.png",
    "82b": "82b_Mallice_unlocked.png",
    "c10": "C10_Kwon.png",
    "c11": "C11_Ethan.png",
}


def outline(path: Path) -> tuple[int, int, str]:
    alpha = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3]
    height, width = alpha.shape
    padded = np.pad(alpha, 1)
    contour = max(measure.find_contours(padded, 128), key=len)
    poly = measure.approximate_polygon(contour, tolerance=2.0)
    points = [(round(col - 1, 1), round(row - 1, 1)) for row, col in poly[:-1]]
    d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in points) + " Z"
    return width, height, d


def main() -> None:
    lines = [
        "// WYGENEROWANE przez scripts/gen_tile_outlines.py — nie edytuj ręcznie.",
        "// Obrysy kanału alfa grafik kafli spiralnych (współrzędne grafiki, px).",
        "",
        "export const SPIRAL_TILE_OUTLINES: Record<",
        "  string,",
        "  { width: number; height: number; path: string }",
        "> = {",
    ]
    for system_id, file_name in SPIRAL_TILES.items():
        width, height, d = outline(TILES / file_name)
        lines.append(f'  "{system_id}": {{ width: {width}, height: {height}, path: "{d}" }},')
    lines.append("};")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"zapisano {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

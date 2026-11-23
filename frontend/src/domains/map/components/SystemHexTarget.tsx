import { useRef } from "react";
import { tileOutline } from "@/entities/geometry/tileOutline";
import classes from "./SystemHexTarget.module.css";

type Props = {
  /** Lewy klik (bez przesunięcia mapy) — dostaje zdarzenie, by menu otworzyć pod kursorem. */
  onOpen: (event: React.MouseEvent) => void;
  /** Id systemu — dla niehexagonalnych kafelków hit-target i podświetlenie idą po ich kształcie. */
  systemId?: string;
};

/**
 * The system's own hit target: the click that opens the system dossier. The
 * path, not the bounding box, receives events, so the tile's corners stay
 * dead space; it sits just above the tile art and below every layer with its
 * own pointer semantics (planet circles, units, tokens), so nothing the map
 * already does changes. The hover wash lives in MapTile.module.css on the
 * container's :hover — no React state, no re-render under a moving cursor.
 *
 * Kształt = ``tileOutline``: heks albo kontur nieregularnej grafiki (Creuss, Crimson,
 * Mallice…) — klik i podświetlenie pokrywają się z tym, co widać.
 */
export function SystemHexTarget({ onOpen, systemId }: Props) {
  const pointerDown = useRef<{ x: number; y: number } | null>(null);
  const outline = tileOutline(systemId);

  return (
    <svg
      className={`system-hex-target ${classes.target}`}
      viewBox={`0 0 ${outline.width} ${outline.height}`}
      width={outline.width}
      height={outline.height}
      style={{ width: outline.width, height: outline.height }}
      aria-hidden="true"
    >
      <path
        d={outline.path}
        className={classes.hex}
        onPointerDown={(event) => {
          pointerDown.current = { x: event.clientX, y: event.clientY };
        }}
        onClick={(event) => {
          /* The pannable view drags to scroll; a pan that ends over a hex
             still fires click, so anything that traveled isn't a click. */
          const down = pointerDown.current;
          pointerDown.current = null;
          if (down) {
            const travel = Math.hypot(
              event.clientX - down.x,
              event.clientY - down.y
            );
            if (travel > 6) return;
          }
          onOpen(event);
        }}
      />
    </svg>
  );
}

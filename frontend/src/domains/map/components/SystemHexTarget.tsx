import { useRef } from "react";
import {
  HEX_PATH,
  TILE_HEIGHT,
  TILE_WIDTH,
} from "@/entities/geometry/tilePositioning";
import { getTileById } from "@/entities/lookup/systems";
import { assetUrl } from "@/shared/assets/resolveAsset";
import classes from "./SystemHexTarget.module.css";

type Props = {
  /** Lewy klik (bez przesunięcia mapy) — dostaje zdarzenie, by menu otworzyć pod kursorem. */
  onOpen: (event: React.MouseEvent) => void;
  /** Id systemu — dla niehexagonalnych kafelków podświetlenie idzie po ich kształcie. */
  systemId?: string;
};

/**
 * Systemy o kształcie innym niż heks (Creuss home, Crimson home, Mallice /
 * Wormhole Nexus). Podświetlenie hovera rysujemy z kanału alfa ich tekstury,
 * zamiast sześciokąta.
 */
const IRREGULAR_SYSTEM_IDS = new Set(["51", "118", "82a", "82b"]);

/**
 * The hex's own hit target: the click that opens the system dossier. The
 * path, not the bounding box, receives events, so the tile's corners stay
 * dead space; it sits just above the tile art and below every layer with its
 * own pointer semantics (planet circles, units, tokens), so nothing the map
 * already does changes. The hover wash lives in MapTile.module.css on the
 * container's :hover — no React state, no re-render under a moving cursor.
 */
export function SystemHexTarget({ onOpen, systemId }: Props) {
  const pointerDown = useRef<{ x: number; y: number } | null>(null);
  const irregular = systemId !== undefined && IRREGULAR_SYSTEM_IDS.has(systemId);
  const imagePath = irregular ? getTileById(systemId)?.imagePath : undefined;

  return (
    <>
      {imagePath && (
        <svg className={classes.filterDefs} aria-hidden="true">
          <filter
            id="system-shape-wash"
            x="-5%"
            y="-5%"
            width="110%"
            height="110%"
            colorInterpolationFilters="sRGB"
          >
            <feFlood className={classes.washFill} result="fill" />
            <feComposite in="fill" in2="SourceAlpha" operator="in" result="body" />
            <feMorphology
              in="SourceAlpha"
              operator="erode"
              radius="1.5"
              result="inner"
            />
            <feComposite
              in="SourceAlpha"
              in2="inner"
              operator="out"
              result="edge"
            />
            <feFlood className={classes.washStroke} result="line" />
            <feComposite in="line" in2="edge" operator="in" result="outline" />
            <feMerge>
              <feMergeNode in="body" />
              <feMergeNode in="outline" />
            </feMerge>
          </filter>
        </svg>
      )}
      {imagePath && (
        <img
          className={`system-hex-target ${classes.shapeWash}`}
          src={assetUrl(`/tiles/${imagePath}`)}
          alt=""
          aria-hidden="true"
          draggable={false}
        />
      )}
      <svg
        className={`system-hex-target ${classes.target}`}
        viewBox={`0 0 ${TILE_WIDTH} ${TILE_HEIGHT}`}
        width={TILE_WIDTH}
        height={TILE_HEIGHT}
        aria-hidden="true"
      >
        <path
          d={HEX_PATH}
          className={imagePath ? classes.hexHitOnly : classes.hex}
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
    </>
  );
}

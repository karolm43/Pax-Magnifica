// Mini-plansza miejsc przy stole (bez systemów): zarys galaktyki z pierścieni 0–3 i sześć
// narożników pierścienia 3, czyli sloty domowe. Każde miejsce jest wypełnione kolorem
// gracza, który tam siedzi; klik w miejsce przesuwa tam aktywnego gracza (zajęte miejsce =
// zamiana). Układ: płaski heks, miejsce 1 na górze, dalej zgodnie z ruchem wskazówek zegara
// (jak `HOME_SLOT_COLORS_6P` w backendzie).

import type { CSSProperties } from "react";
import { getTextColor } from "@/entities/lookup/colors";
import type { SetupSlot } from "../useSetupStore";
import { colorLabel, colorSwatchBackground } from "../playerColors";
import styles from "./SeatBoard.module.css";

/** Promień heksa (px). Reszta geometrii wynika z niego. */
const S = 20;
const SQRT3 = Math.sqrt(3);
/** Narożniki pierścienia 3 w kolejności miejsc 1..6 (góra, potem zgodnie z zegarem). */
const SEAT_CORNERS: ReadonlyArray<readonly [number, number]> = [
  [0, -3],
  [3, -3],
  [3, 0],
  [0, 3],
  [-3, 3],
  [-3, 0],
];

/** Środek heksa osiowego (q, r) względem środka planszy. */
function center(q: number, r: number): { x: number; y: number } {
  return { x: 1.5 * S * q, y: SQRT3 * S * (r + q / 2) };
}

/** Wszystkie komórki pierścieni 0..3 (zarys planszy). */
const RING_CELLS: Array<readonly [number, number]> = [];
for (let q = -3; q <= 3; q++) {
  for (let r = -3; r <= 3; r++) {
    if (Math.max(Math.abs(q), Math.abs(r), Math.abs(q + r)) <= 3) {
      RING_CELLS.push([q, r]);
    }
  }
}

const SEAT_SCALE = 1.9;
const WIDTH = 2 * (4.5 * S + SEAT_SCALE * S) + 8;
const HEIGHT = 2 * (3 * SQRT3 * S + SEAT_SCALE * SQRT3 * S * 0.5) + 8;

function hexBox(
  q: number,
  r: number,
  scale: number,
  shrink = 1,
): CSSProperties {
  const { x, y } = center(q, r);
  const w = 2 * S * scale * shrink;
  const h = SQRT3 * S * scale * shrink;
  return {
    width: w,
    height: h,
    left: WIDTH / 2 + x - w / 2,
    top: HEIGHT / 2 + y - h / 2,
  };
}

export function SeatBoard({
  slots,
  activeIndex,
  onPickSeat,
}: {
  slots: readonly SetupSlot[];
  activeIndex: number;
  onPickSeat: (seat: number) => void;
}) {
  return (
    <div
      className={styles.board}
      style={{ width: WIDTH, height: HEIGHT }}
      role="group"
      aria-label="Seats around the galaxy"
    >
      {RING_CELLS.map(([q, r]) => (
        <span key={`${q},${r}`} className={styles.cell} style={hexBox(q, r, 1, 0.9)} aria-hidden />
      ))}

      {SEAT_CORNERS.map(([q, r], seat) => {
        const occupantIndex = slots.findIndex((s) => s.seat === seat);
        const occupant = occupantIndex >= 0 ? slots[occupantIndex] : null;
        const mine = occupantIndex === activeIndex;
        const textColor = occupant ? getTextColor(occupant.color) : "white";
        const name = occupant
          ? occupant.name.trim() || `Player ${occupantIndex + 1}`
          : "empty";
        const title = occupant
          ? `Seat ${seat + 1}: ${name} (${colorLabel(occupant.color)})${
              mine ? "" : ", click to swap"
            }`
          : `Seat ${seat + 1}: empty, click to sit here`;
        return (
          <span key={seat}>
            {mine && (
              <span
                className={styles.activeRing}
                style={hexBox(q, r, SEAT_SCALE, 1.18)}
                aria-hidden
              />
            )}
            <button
              type="button"
              className={styles.seat}
              style={{
                ...hexBox(q, r, SEAT_SCALE),
                background: occupant ? colorSwatchBackground(occupant.color) : undefined,
                color: textColor,
              }}
              aria-label={title}
              aria-pressed={mine}
              title={title}
              onClick={() => onPickSeat(seat)}
            >
              <span className={styles.seatNumber}>{seat + 1}</span>
              <span className={styles.seatName}>
                {occupant ? `P${occupantIndex + 1}` : "free"}
              </span>
            </button>
          </span>
        );
      })}
    </div>
  );
}

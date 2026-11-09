import { useEffect, useRef, useState, type ReactNode } from "react";
import styles from "@/domains/battle/BattleOverlay.module.css";

/** Po tylu ms przytrzymania zaczyna się pula (krótsze kliknięcie = zwykły rzut). */
const HOLD_MS = 240;

export type HoldState = "start" | "fire" | "cancel";

/**
 * Przycisk rzutu kośćmi (wspólny dla wszystkich okien). Kliknięcie rzuca od razu;
 * PRZYTRZYMANIE zbiera kości w puli (widać, ile ich jest), a puszczenie przycisku nad nim
 * rzuca. Puszczenie poza przyciskiem anuluje pulę bez rzutu. ``onHold`` dostaje etapy
 * ("start" / "fire" / "cancel") - okno ustawia wtedy pulę w ``useDiceStage``.
 * Klawiatura (Enter/Spacja) działa jak zwykłe kliknięcie.
 */
export function HoldRollButton({
  disabled,
  onFire,
  onHold,
  className,
  title,
  hint = true,
  children,
}: {
  disabled: boolean;
  onFire: () => void;
  onHold: (state: HoldState) => void;
  /** Klasa wyglądu przycisku z modułu CSS okna wywołującego. */
  className?: string;
  title?: string;
  /** Podpowiedź „hold to shake" pod przyciskiem. */
  hint?: boolean;
  children: ReactNode;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const [holding, setHolding] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const active = useRef(false);
  const suppressClick = useRef(false);
  const stop = useRef<(() => void) | null>(null);

  // Odpięcie nasłuchu i pula przy odmontowaniu w trakcie przytrzymania.
  useEffect(
    () => () => {
      window.clearTimeout(timer.current);
      stop.current?.();
      if (active.current) onHold("cancel");
    },
    [],
  );

  const press = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (disabled || e.button !== 0) return;
    suppressClick.current = false;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      active.current = true;
      setHolding(true);
      onHold("start");
    }, HOLD_MS);
    const release = (ev: PointerEvent) => {
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
      stop.current = null;
      window.clearTimeout(timer.current);
      if (!active.current) return; // krótkie kliknięcie obsłuży onClick
      active.current = false;
      setHolding(false);
      const inside =
        ev.type === "pointerup" &&
        ref.current?.contains(ev.target as Node) === true;
      suppressClick.current = inside;
      onHold(inside ? "fire" : "cancel");
      if (inside) onFire();
    };
    stop.current = () => {
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
    };
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
  };

  return (
    <>
      <button
        ref={ref}
        type="button"
        className={`${className ?? ""} ${styles.holdBtn}`}
        data-holding={holding || undefined}
        disabled={disabled}
        title={title}
        onPointerDown={press}
        onClick={() => {
          if (suppressClick.current) {
            suppressClick.current = false;
            return;
          }
          onFire();
        }}
      >
        {children}
      </button>
      {hint && (
        <small className={styles.holdHint}>
          Tap to roll · hold to shake the dice, release to throw
        </small>
      )}
    </>
  );
}

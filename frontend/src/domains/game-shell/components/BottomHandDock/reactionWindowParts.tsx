import { Tooltip } from "@/ds";
import styles from "./HeldPlayBanner.module.css";

/** Ile sekund dodaje „More time” (RULES.md 54.11, `reaction_window.WAIT_EXTENSION_SECONDS`). */
export const MORE_TIME_SECONDS = 10;

/**
 * Tekst dla gracza, który nie decyduje w oknie (spasował sam albo silnik spasował za niego).
 * Nie zdradza, ilu graczy spasowało — pasy są prywatne (RULES.md 54.11).
 */
export function waitingText(eligible: boolean, extensions: number): string {
  const base = eligible
    ? "You're not reacting — the window closes on its own."
    : "Waiting for reactions…";
  return extensions > 0 ? `${base} Someone asked for more time.` : base;
}

/**
 * „More time”: +10 s raz na okno. Dostępne dla każdego uprawnionego (także tego, za kogo silnik
 * spasował), więc prośba nic nie mówi o ręce. Inni widzą tylko, że ktoś poprosił.
 */
export function MoreTimeButton({ asked, onAsk }: { asked: boolean; onAsk: () => void }) {
  return (
    <Tooltip
      label={
        asked
          ? "You already asked for more time in this window."
          : `Give everyone ${MORE_TIME_SECONDS} more seconds (once per window). Nobody sees who asked.`
      }
      multiline
      w={240}
    >
      <button
        type="button"
        className={styles.wait}
        disabled={asked}
        onClick={onAsk}
      >
        +{MORE_TIME_SECONDS}s
      </button>
    </Tooltip>
  );
}

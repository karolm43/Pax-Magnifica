import type { ReactNode } from "react";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import styles from "./Stepper.module.css";

/**
 * Jeden licznik −/+ w całej grze (oferty, płatność, handel, rozdział żetonów, usuwanie jednostek).
 * Etykiety dostępności: „Less <label>” / „More <label>” (lokatory testów po rolach ARIA).
 * `bare` = same przyciski i wartość (bez ramki i podpisu) — gdy wiersz ma już własną etykietę.
 */
export function Stepper({
  label,
  value,
  min = 0,
  max,
  onChange,
  disabled,
  icon,
  hint,
  showMax,
  bare,
  active,
}: {
  label: string;
  value: number;
  min?: number;
  max: number;
  onChange: (next: number) => void;
  disabled?: boolean;
  /** Ikona przed podpisem (monety, sprite jednostki…). */
  icon?: ReactNode;
  /** Mniejszy podpis pod nazwą. */
  hint?: string;
  /** Przycisk „max N” (domyślnie tylko przy zakresie > 1). */
  showMax?: boolean;
  bare?: boolean;
  /** Podświetla wartość > 0 (np. „do usunięcia”). */
  active?: boolean;
}) {
  const clamp = (n: number) => Math.max(min, Math.min(max, n));
  const control = (
    <span className={styles.ctl}>
      <button
        type="button"
        className={styles.btn}
        disabled={disabled || value <= min}
        aria-label={`Less ${label}`}
        onClick={() => onChange(clamp(value - 1))}
      >
        <IconMinus size={14} aria-hidden="true" />
      </button>
      <output className={styles.value} data-active={(active && value > 0) || undefined} aria-live="polite">
        {value}
      </output>
      <button
        type="button"
        className={styles.btn}
        disabled={disabled || value >= max}
        aria-label={`More ${label}`}
        onClick={() => onChange(clamp(value + 1))}
      >
        <IconPlus size={14} aria-hidden="true" />
      </button>
    </span>
  );
  if (bare) return control;
  const maxShown = showMax ?? max > min + 1;
  return (
    <div className={styles.stepper} role="group" aria-label={label}>
      <span className={styles.label}>
        {icon}
        <span className={styles.text}>
          {label}
          {hint && <small>{hint}</small>}
        </span>
      </span>
      {control}
      {maxShown && (
        <button
          type="button"
          className={styles.max}
          disabled={disabled || value === max}
          onClick={() => onChange(max)}
        >
          max {max}
        </button>
      )}
    </div>
  );
}

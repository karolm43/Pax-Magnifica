import type { MouseEvent } from "react";
import { Unit } from "@/shared/ui/Unit";
import styles from "./RouteUnitChip.module.css";

/**
 * Przycisk jednostki do wyboru w ruchu z trasą (box i rysunek trasy na mapie): klik dodaje
 * 1 sztukę (Shift = wszystkie), prawy przycisk odejmuje 1 (Shift = wszystkie). Pokazuje
 * ``wybrane/dostępne``. Pełna nazwa jednostki (nie skrót AsyncTI4) trafia do ``title`` i etykiety.
 */
export function RouteUnitChip({
  asyncId,
  colorAlias,
  faction,
  name,
  caption,
  picked,
  max,
  disabled,
  title,
  variant,
  onChange,
}: {
  asyncId: string;
  colorAlias: string;
  faction: string;
  name: string;
  /** Dopisek pod nazwą (strefa: orbita / nazwa planety). */
  caption?: string;
  picked: number;
  max: number;
  disabled?: boolean;
  title?: string;
  /** ``row`` = wiersz w boxie, ``badge`` = mały znacznik na trasie na mapie. */
  variant: "row" | "badge";
  /** ``delta`` > 0 dodaje, < 0 odejmuje; ``Infinity`` = wszystkie. */
  onChange: (delta: number) => void;
}) {
  const click = (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (disabled) return;
    onChange(event.shiftKey ? Number.POSITIVE_INFINITY : 1);
  };
  const rightClick = (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (disabled) return;
    onChange(event.shiftKey ? Number.NEGATIVE_INFINITY : -1);
  };
  return (
    <button
      type="button"
      className={styles.chip}
      data-variant={variant}
      data-picked={picked > 0 || undefined}
      disabled={disabled}
      title={title ?? `${name}: click +1, right-click −1, Shift = all`}
      aria-label={`${name}${caption ? ` (${caption})` : ""}: ${picked} of ${max} selected`}
      onClick={click}
      onContextMenu={rightClick}
    >
      <span className={styles.sprite}>
        <Unit unitType={asyncId} colorAlias={colorAlias} faction={faction} scaleSprite />
      </span>
      {variant === "row" && (
        <span className={styles.label}>
          <b>{name}</b>
          {caption && <small>{caption}</small>}
        </span>
      )}
      <span className={styles.count}>
        {picked}/{max}
      </span>
    </button>
  );
}

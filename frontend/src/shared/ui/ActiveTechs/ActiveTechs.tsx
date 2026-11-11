import { useGameData } from "@/state/useGameContext";
import { Tech } from "@/domains/player/components/Tech";
import type { TechEffectContext } from "@/entities/data/types";
import styles from "./ActiveTechs.module.css";

type Props = {
  /** Okno UI, w którym pokazujemy karty (produkcja, ruch, walka...). */
  context: TechEffectContext;
  /** Gracz po kolorze (jak w `PlayerData.color`) - jeden z dwóch identyfikatorów. */
  color?: string | null;
  /** Gracz po frakcji (`PlayerData.faction`). */
  faction?: string | null;
  /** Etykieta przed kartami, np. nazwa strony w walce. */
  label?: string;
  className?: string;
};

/**
 * Technologie gracza istotne w tym oknie - TE SAME kafelki co w panelu gracza (`Tech`):
 * kolor typu, oczka poziomu, przygaszenie gdy wyczerpana, a po kliknięciu pełna karta
 * technologii. Dane z `PlayerData.techEffects` (silnik: `core/tech_effects.py`).
 */
export function ActiveTechs({ context, color, faction, label, className }: Props) {
  const gameData = useGameData();
  const player = gameData?.playerData?.find(
    (p) => (color != null && p.color === color) || (faction != null && p.faction === faction),
  );
  const items = (player?.techEffects ?? []).filter((t) => t.contexts.includes(context));
  if (items.length === 0) return null;
  return (
    <div
      className={className ? `${styles.row} ${className}` : styles.row}
      role="list"
      aria-label={label ? `${label}: active technologies` : "Active technologies"}
    >
      {label ? <span className={styles.label}>{label}</span> : null}
      {items.map((t) => (
        <div key={t.alias} role="listitem" className={styles.item}>
          <Tech techId={t.alias} isExhausted={t.state === "exhausted"} />
        </div>
      ))}
    </div>
  );
}

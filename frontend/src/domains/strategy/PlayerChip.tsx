import type { CSSProperties, ReactNode } from "react";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import type { PromptPlayer } from "./strategyPrompt";
import styles from "./StrategyPrompt.module.css";

/** Kolor gracza (kolor przy stole) jako CSS ``rgb()``; neutralny szary, gdy nieznany. */
export function playerRgb(color: string | undefined | null): string {
  const rgb = color ? resolvePrimaryRgb(color) : undefined;
  return rgb ? `rgb(${rgb.red} ${rgb.green} ${rgb.blue})` : "rgb(148 163 184)";
}

/** Nazwa gracza do wyświetlenia (jak w pozostałych oknach). */
export function playerName(p: PromptPlayer): string {
  const clean = (v?: string | null) => {
    const t = v?.trim();
    return t && t.toLowerCase() !== "null" ? t : null;
  };
  return (
    clean(p.displayName) ??
    clean(p.userName) ??
    clean(p.flexibleDisplayName) ??
    clean(p.faction) ??
    p.color
  );
}

/**
 * Wybieralny „żeton gracza": ikona frakcji w obwódce koloru gracza + nazwa. Używany we
 * wszystkich oknach kart strategii, gdzie wybiera się graczy (Trade, Politics...).
 */
export function PlayerChip({
  player,
  selected,
  disabled,
  onClick,
  badge,
}: {
  player: PromptPlayer;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  badge?: ReactNode;
}) {
  return (
    <button
      type="button"
      className={styles.playerChip}
      style={{ "--pc": playerRgb(player.color) } as CSSProperties}
      data-on={selected || undefined}
      disabled={disabled}
      onClick={onClick}
    >
      <span className={styles.playerIcon}>
        {player.faction ? <CircularFactionIcon faction={player.faction} size={26} /> : null}
      </span>
      <span className={styles.playerText}>
        <b>{playerName(player)}</b>
        <small>{player.color}</small>
      </span>
      {badge ? <span className={styles.playerBadge}>{badge}</span> : null}
    </button>
  );
}

import type { CSSProperties } from "react";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import { useGameData } from "@/state/useGameContext";
import styles from "./PlayerTag.module.css";

/**
 * Nieklikalny znacznik gracza do tekstu i nagłówków (komunikaty, karty decyzji, wybory celu):
 * ikona frakcji w obwódce koloru gracza + nazwa w jego kolorze. Ten sam wygląd co wybieralny
 * ``PlayerChip`` z okien kart strategii, tylko w wersji „w linii” — żeby cel dało się rozpoznać
 * na pierwszy rzut oka (logo i kolor jak na planszy), a nie po samej nazwie.
 */
export function PlayerTag({
  playerId,
  size = 16,
  showName = true,
  fallback,
  known,
}: {
  playerId: string;
  /** Średnica ikony frakcji. */
  size?: number;
  /** ``false`` = sama ikona (nazwa w podpowiedzi). */
  showName?: boolean;
  /** Nazwa, gdy gracza nie ma w danych gry (np. surowe id z silnika). */
  fallback?: string;
  /** Dane gracza znane wołającemu (feed Activity ma własne nazwy/kolory) - mają pierwszeństwo. */
  known?: { name?: string | null; faction?: string | null; color?: string | null };
}) {
  const gameData = useGameData();
  const player = gameData?.playerData?.find((p) => p.discordId === playerId);
  const name = known?.name?.trim() || (player ? playerName(player) : (fallback ?? playerId));
  const faction = known?.faction ?? player?.faction;
  const color = known?.color ?? player?.color;
  return (
    <span
      className={styles.tag}
      style={{ "--pc": playerRgb(color) } as CSSProperties}
      title={color ? `${name} · ${color}` : name}
    >
      <span className={styles.icon} aria-hidden="true">
        {faction ? <CircularFactionIcon faction={faction} size={size} /> : null}
      </span>
      {showName ? <b className={styles.name}>{name}</b> : <span className={styles.sr}>{name}</span>}
    </span>
  );
}

import { useState, type CSSProperties } from "react";
import { IconSparkles } from "@tabler/icons-react";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import type { ActiveEffectData, PlayerData } from "@/entities/data/types";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { playerRgb } from "@/domains/strategy/PlayerChip";
import styles from "./BoardEffectsZone.module.css";

/** Szerokość strefy i odstęp od planszy (px ekranu, bez skali zoomu) - geometria planszy je rezerwuje. */
export const EFFECTS_ZONE_WIDTH = 300;
export const EFFECTS_ZONE_GAP = 32;

function EffectCard({ effect, player }: { effect: ActiveEffectData; player: PlayerData | undefined }) {
  const [open, setOpen] = useState(false);
  return (
    <li
      className={styles.card}
      style={{ "--pc": playerRgb(player?.color) } as CSSProperties}
      data-open={open || undefined}
    >
      <button
        type="button"
        className={styles.cardBtn}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        title={effect.text || effect.name}
      >
        <span className={styles.icon} aria-hidden="true">
          {player?.faction ? (
            <CircularFactionIcon faction={player.faction} size={26} />
          ) : (
            <IconSparkles size={16} />
          )}
        </span>
        <span className={styles.body}>
          {effect.kind && <small className={styles.kind}>{effect.kind}</small>}
          <b className={styles.name}>{effect.name}</b>
          {effect.detail && <span className={styles.detail}>{effect.detail}</span>}
        </span>
      </button>
      {effect.until && <span className={styles.until}>{effect.until}</span>}
      {open && effect.text && <p className={styles.text}>{effect.text}</p>}
    </li>
  );
}

/**
 * Efekty trwałe „położone obok planszy” (RULES.md 54): bohater Letnev do końca rundy, kość
 * agenta w tej rundzie walki, premie z kart itd. Fizyczne pole na stole przy prawej krawędzi
 * planszy - przesuwa się i przewija razem z mapą (nie nakładka na ekran). Pole leży zawsze,
 * także puste; klik w kartę efektu pokazuje jej tekst.
 */
export function BoardEffectsZone({ gameId, bleedRight }: { gameId: string; bleedRight: number }) {
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const effects = gameState?.activeEffects ?? [];
  const playerOf = (owner: string | null) =>
    owner ? gameData?.playerData.find((p) => p.faction === owner) : undefined;

  return (
    <section
      className={styles.zone}
      aria-label="Active effects"
      style={
        {
          "--zone-left": `${bleedRight + EFFECTS_ZONE_GAP}px`,
          "--zone-width": `${EFFECTS_ZONE_WIDTH}px`,
        } as CSSProperties
      }
    >
      <header className={styles.plate}>
        <IconSparkles size={14} aria-hidden="true" />
        <span>Active effects</span>
        {effects.length > 0 && <b className={styles.count}>{effects.length}</b>}
      </header>
      {effects.length === 0 ? (
        <p className={styles.empty}>No lasting effects in play</p>
      ) : (
        <ul className={styles.list}>
          {effects.map((effect) => (
            <EffectCard key={effect.id} effect={effect} player={playerOf(effect.owner)} />
          ))}
        </ul>
      )}
    </section>
  );
}

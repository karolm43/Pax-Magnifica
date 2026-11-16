import { useState, type CSSProperties } from "react";
import { IconSparkles } from "@tabler/icons-react";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import type { ActiveEffectData, PlayerData } from "@/entities/data/types";
import { TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { playerRgb } from "@/domains/strategy/PlayerChip";
import styles from "./BoardEffectsZone.module.css";

/** Najmniejszy rozmiar pudełka (px ekranu) - przy małym zoomie pole systemu byłoby nieczytelne. */
const MIN_WIDTH = 170;
const MIN_HEIGHT = 140;
/** Odstęp od krawędzi planszy w jednostkach planszy (skaluje się z zoomem). */
const GAP = 40;

function EffectIcon({ player, size }: { player: PlayerData | undefined; size: number }) {
  return player?.faction ? (
    <CircularFactionIcon faction={player.faction} size={size} />
  ) : (
    <IconSparkles size={size - 6} />
  );
}

/** Chip efektu na tacy; klik = karta z pełnym opisem (jak żetony mapy). */
function EffectChip({ effect, player }: { effect: ActiveEffectData; player: PlayerData | undefined }) {
  const [opened, setOpened] = useState(false);
  return (
    <li className={styles.item} style={{ "--pc": playerRgb(player?.color) } as CSSProperties}>
      <SmoothPopover opened={opened} onChange={setOpened} position="left">
        <SmoothPopover.Target>
          <button
            type="button"
            className={styles.chip}
            aria-expanded={opened}
            onClick={() => setOpened((o) => !o)}
          >
            <span className={styles.icon} aria-hidden="true">
              <EffectIcon player={player} size={18} />
            </span>
            <span className={styles.name}>{effect.name}</span>
          </button>
        </SmoothPopover.Target>
        <SmoothPopover.Dropdown p={0}>
          <DetailsCard width={320}>
            <DetailsCard.Title
              title={effect.name}
              type={effect.kind || "Effect"}
              icon={<DetailsCard.Icon shape="round" icon={<EffectIcon player={player} size={28} />} />}
            />
            {effect.detail && <DetailsCard.Section title="Applies to" content={effect.detail} />}
            {effect.until && <DetailsCard.Section title="Lasts until" content={effect.until} />}
            {effect.text && <DetailsCard.Section title="Effect" content={effect.text} />}
          </DetailsCard>
        </SmoothPopover.Dropdown>
      </SmoothPopover>
    </li>
  );
}

/**
 * Efekty trwałe „położone obok planszy” (RULES.md 54): bohater Letnev do końca rundy, kość
 * agenta w tej rundzie walki, premie z kart itd. Pudełko wielkości jednego systemu przy prawym
 * górnym rogu planszy - leży na stole i przesuwa się z mapą, nie zmienia układu planszy.
 * Leży zawsze, także puste; klik w efekt pokazuje jego kartę.
 */
export function BoardEffectsZone({
  gameId,
  zoom,
  bleedRight,
}: {
  gameId: string;
  zoom: number;
  bleedRight: number;
}) {
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const effects = gameState?.activeEffects ?? [];
  const playerOf = (owner: string | null) =>
    owner ? gameData?.playerData.find((p) => p.faction === owner) : undefined;

  return (
    <section
      className={styles.zone}
      aria-label="Active effects"
      style={{
        left: `calc(100% + ${bleedRight + GAP * zoom}px)`,
        width: Math.max(MIN_WIDTH, TILE_WIDTH * zoom),
        height: Math.max(MIN_HEIGHT, TILE_HEIGHT * zoom),
      }}
    >
      <header className={styles.plate}>
        <IconSparkles size={12} aria-hidden="true" />
        <span>Effects</span>
        {effects.length > 0 && <b className={styles.count}>{effects.length}</b>}
      </header>
      {effects.length === 0 ? (
        <p className={styles.empty}>None in play</p>
      ) : (
        <ul className={styles.list}>
          {effects.map((effect) => (
            <EffectChip key={effect.id} effect={effect} player={playerOf(effect.owner)} />
          ))}
        </ul>
      )}
    </section>
  );
}

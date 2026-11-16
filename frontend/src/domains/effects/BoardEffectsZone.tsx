import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { IconSparkles } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import type { ActiveEffectData, PlayerData } from "@/entities/data/types";
import type { GameData, Tile } from "@/entities/game/types";
import { TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { playerRgb } from "@/domains/strategy/PlayerChip";
import { effectsZoneAnchor } from "./effectsZoneAnchor";
import styles from "./BoardEffectsZone.module.css";

function EffectIcon({ player, size }: { player: PlayerData | undefined; size: number }) {
  return player?.faction ? (
    <CircularFactionIcon faction={player.faction} size={size} />
  ) : (
    <IconSparkles size={size - 8} />
  );
}

/** Żeton efektu na tacy; klik = karta z pełnym opisem (jak żetony mapy). */
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
              <EffectIcon player={player} size={44} />
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
 * agenta w tej rundzie walki, premie z kart itd. Taca leży W WARSTWIE PLANSZY (jej jednostki
 * i skala) po prawej stronie planszy, za jej krawędzią, na wysokości luki między polami graczy
 * 2 i 3 (`effectsZoneAnchor`). Ma wysokość
 * jednego systemu i rozszerza się w prawo o kolejne kolumny, gdy efektów przybywa.
 * Leży zawsze, także pusta; klik w efekt pokazuje jego kartę.
 */
export function BoardEffectsZone({ gameData, tiles }: { gameData: GameData; tiles: Tile[] }) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const anchor = effectsZoneAnchor(
    gameData.statTilePositions ?? {},
    gameData.ringCount,
    gameData.tilePositions,
    Math.max(0, ...tiles.map((t) => t.properties.x + TILE_WIDTH)),
  );
  if (!anchor) return null;
  const effects = gameState?.activeEffects ?? [];
  const playerOf = (owner: string | null) =>
    owner ? gameData.playerData.find((p) => p.faction === owner) : undefined;

  return (
    <section
      className={styles.zone}
      aria-label="Active effects"
      style={{ left: anchor.x, top: anchor.y, minWidth: TILE_WIDTH, height: TILE_HEIGHT }}
    >
      <header className={styles.plate}>
        <IconSparkles size={26} aria-hidden="true" />
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

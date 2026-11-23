import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { IconSparkles } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import type { ActiveEffectData, PlayerData } from "@/entities/data/types";
import type { GameData, Tile } from "@/entities/game/types";
import { HEX_PATH, TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { playerRgb } from "@/domains/strategy/PlayerChip";
import { EFFECTS_PER_HEX, effectsZoneAnchor, zoneCells } from "./effectsZoneAnchor";
import styles from "./BoardEffectsZone.module.css";

/** Środki żetonów na jednym heksie (współrzędne heksa 345x299): 2 rzędy po 3. */
const TOKEN_SLOTS = [
  { x: 100, y: 122 },
  { x: 172.5, y: 122 },
  { x: 245, y: 122 },
  { x: 100, y: 212 },
  { x: 172.5, y: 212 },
  { x: 245, y: 212 },
];

/** Wewnętrzny, grawerowany obrys heksa - ta sama ścieżka, zmniejszona wokół środka. */
const INNER_HEX = `translate(${TILE_WIDTH / 2} ${TILE_HEIGHT / 2}) scale(0.92) translate(${-TILE_WIDTH / 2} ${-TILE_HEIGHT / 2})`;

function EffectIcon({ player, size }: { player: PlayerData | undefined; size: number }) {
  return player?.faction ? (
    <CircularFactionIcon faction={player.faction} size={size} />
  ) : (
    <IconSparkles size={size - 8} />
  );
}

/** Żeton efektu na tacy (jak żetony mapy); klik = karta z pełnym opisem. */
function EffectToken({
  effect,
  player,
  at,
}: {
  effect: ActiveEffectData;
  player: PlayerData | undefined;
  at: { x: number; y: number };
}) {
  const [opened, setOpened] = useState(false);
  return (
    <li
      className={styles.item}
      style={{ "--pc": playerRgb(player?.color), left: at.x, top: at.y } as CSSProperties}
    >
      <SmoothPopover opened={opened} onChange={setOpened} position="left">
        <SmoothPopover.Target>
          <button
            type="button"
            className={styles.token}
            aria-label={effect.name}
            title={effect.name}
            aria-expanded={opened}
            onClick={() => setOpened((o) => !o)}
          >
            <span className={styles.disc} aria-hidden="true">
              <EffectIcon player={player} size={52} />
            </span>
            <span className={styles.label} aria-hidden="true">
              {effect.name}
            </span>
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
 * Efekty trwałe „położone na planszy” (RULES.md 54): bohater Letnev do końca rundy, kość
 * agenta w tej rundzie walki, premie z kart itd. Taca to HEKS na siatce planszy (jej jednostki
 * i skala), w wolnej komórce po prawej między polami graczy 2 i 3 (`effectsZoneAnchor`) -
 * wygląda jak pusty slot planszy: ciemne wgłębienie z grawerowanym, neutralnym obrysem
 * (inny niż kolorowe, przerywane pola graczy). Efekty to okrągłe żetony (2 rzędy po 3);
 * gdy jest ich więcej, taca dokłada heksy w prawo. Leży zawsze, także pusta.
 */
export function BoardEffectsZone({ gameData, tiles }: { gameData: GameData; tiles: Tile[] }) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const anchor = effectsZoneAnchor(
    gameData.statTilePositions ?? {},
    gameData.ringCount,
    gameData.tilePositions,
    tiles.map((t) => ({ x: t.properties.x, y: t.properties.y })),
  );
  if (!anchor) return null;
  const effects = gameState?.activeEffects ?? [];
  const playerOf = (owner: string | null) =>
    owner ? gameData.playerData.find((p) => p.faction === owner) : undefined;
  const cells = zoneCells(effects.length);
  const width = Math.max(...cells.map((c) => c.x)) + TILE_WIDTH;
  const height = Math.max(...cells.map((c) => c.y)) + TILE_HEIGHT;

  return (
    <section
      className={styles.zone}
      aria-label="Active effects"
      style={{ left: anchor.x, top: anchor.y, width, height }}
    >
      <svg className={styles.tray} width={width} height={height} aria-hidden="true">
        <defs>
          <radialGradient id="effects-tray-floor" cx="50%" cy="35%" r="75%">
            <stop offset="0%" stopColor="rgb(30 40 58)" />
            <stop offset="100%" stopColor="rgb(6 9 15)" />
          </radialGradient>
        </defs>
        {cells.map((cell) => (
          <g key={`${cell.x},${cell.y}`} transform={`translate(${cell.x} ${cell.y})`}>
            <path className={styles.floor} d={HEX_PATH} />
            <path className={styles.engrave} d={HEX_PATH} transform={INNER_HEX} />
          </g>
        ))}
      </svg>
      <header className={styles.plate}>
        <IconSparkles size={22} aria-hidden="true" />
        <span>Effects</span>
        {effects.length > 0 && <b className={styles.count}>{effects.length}</b>}
      </header>
      {effects.length === 0 ? (
        <p className={styles.empty}>None in play</p>
      ) : (
        <ul className={styles.list}>
          {effects.map((effect, i) => {
            const cell = cells[Math.floor(i / EFFECTS_PER_HEX)];
            const slot = TOKEN_SLOTS[i % EFFECTS_PER_HEX];
            return (
              <EffectToken
                key={effect.id}
                effect={effect}
                player={playerOf(effect.owner)}
                at={{ x: cell.x + slot.x, y: cell.y + slot.y }}
              />
            );
          })}
        </ul>
      )}
    </section>
  );
}

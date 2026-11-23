import { Fragment, useState, type CSSProperties, type ReactNode } from "react";
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
import { IconScale } from "@tabler/icons-react";
import { LawDetailsCard } from "@/domains/cards/components/LawDetailsCard";
import type { LawInPlay } from "@/entities/data/types";
import {
  EFFECTS_PER_HEX,
  effectsZoneAnchor,
  zoneCells,
  type ZoneSide,
} from "./effectsZoneAnchor";
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
  side,
}: {
  effect: ActiveEffectData;
  player: PlayerData | undefined;
  at: { x: number; y: number };
  side: ZoneSide;
}) {
  const [opened, setOpened] = useState(false);
  return (
    <li
      className={styles.item}
      style={{ "--pc": playerRgb(player?.color), left: at.x, top: at.y } as CSSProperties}
    >
      <SmoothPopover opened={opened} onChange={setOpened} position={side === "left" ? "right" : "left"}>
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

/** Żeton prawa na tacy; klik = ta sama karta prawa co na tablicy celów (`LawDetailsCard`). */
function LawToken({
  law,
  player,
  at,
  side,
}: {
  law: LawInPlay;
  player: PlayerData | undefined;
  at: { x: number; y: number };
  side: ZoneSide;
}) {
  const [opened, setOpened] = useState(false);
  return (
    <li
      className={styles.item}
      style={{ "--pc": playerRgb(player?.color), left: at.x, top: at.y } as CSSProperties}
    >
      <SmoothPopover opened={opened} onChange={setOpened} position={side === "left" ? "right" : "left"}>
        <SmoothPopover.Target>
          <button
            type="button"
            className={styles.token}
            aria-label={law.name}
            title={law.name}
            aria-expanded={opened}
            onClick={() => setOpened((o) => !o)}
          >
            <span className={styles.disc} aria-hidden="true">
              {player?.faction ? (
                <CircularFactionIcon faction={player.faction} size={52} />
              ) : (
                <IconScale size={34} stroke={1.6} />
              )}
            </span>
            <span className={styles.label} aria-hidden="true">
              {law.name}
            </span>
          </button>
        </SmoothPopover.Target>
        <SmoothPopover.Dropdown p={0}>
          <LawDetailsCard law={law} />
        </SmoothPopover.Dropdown>
      </SmoothPopover>
    </li>
  );
}

/** Napis tacy; klik/najechanie wyjaśnia, co ta taca pokazuje. */
function TrayPlate({ label, info, count }: { label: string; info: string; count: number }) {
  const [opened, setOpened] = useState(false);
  return (
    <header className={styles.plate}>
      <SmoothPopover opened={opened} onChange={setOpened} position="bottom">
        <SmoothPopover.Target>
          <button
            type="button"
            className={styles.plateButton}
            title={info}
            aria-expanded={opened}
            aria-label={`${label} - what is this?`}
            onClick={() => setOpened((o) => !o)}
          >
            <span>{label}</span>
            {count > 0 && <b className={styles.count}>{count}</b>}
          </button>
        </SmoothPopover.Target>
        <SmoothPopover.Dropdown p={0}>
          <DetailsCard width={300}>
            <DetailsCard.Title title={label} type="Board tray" />
            <DetailsCard.Section title="What it shows" content={info} />
          </DetailsCard>
        </SmoothPopover.Dropdown>
      </SmoothPopover>
    </header>
  );
}

const EFFECTS_INFO =
  "Lasting effects currently in play: hero abilities, card bonuses and other things that last until a set moment (end of round, end of combat…). Click a token to see what it affects and how long it lasts.";
const LAWS_INFO =
  "Laws that were passed in the Agenda phase and stay in force until repealed. Click a token to read the law and who was elected.";

type TrayItem = { key: string; node: (at: { x: number; y: number }) => ReactNode };

/** Wspólna taca: heks (lub kilka) na siatce planszy po wybranej stronie, żetony po 6 na heks. */
function BoardTray({
  gameData,
  tiles,
  side,
  label,
  ariaLabel,
  info,
  emptyText,
  items,
}: {
  gameData: GameData;
  tiles: Tile[];
  side: ZoneSide;
  label: string;
  ariaLabel: string;
  info: string;
  emptyText: string;
  items: TrayItem[];
}) {
  const anchor = effectsZoneAnchor(
    gameData.statTilePositions ?? {},
    gameData.ringCount,
    gameData.tilePositions,
    tiles.map((t) => ({ x: t.properties.x, y: t.properties.y })),
    side,
  );
  if (!anchor) return null;
  const raw = zoneCells(items.length, side);
  const minX = Math.min(...raw.map((c) => c.x));
  const cells = raw.map((c) => ({ x: c.x - minX, y: c.y }));
  const width = Math.max(...cells.map((c) => c.x)) + TILE_WIDTH;
  const height = Math.max(...cells.map((c) => c.y)) + TILE_HEIGHT;
  // Napis leży na pierwszym heksie (tym przy kotwicy; po lewej to ostatnia komórka listy).
  const anchorIndex = side === "left" ? cells.length - 1 : 0;
  const first = cells[anchorIndex];
  const gradient = `tray-floor-${side}`;

  return (
    <section
      className={styles.zone}
      aria-label={ariaLabel}
      style={{ left: anchor.x + minX, top: anchor.y, width, height }}
    >
      <svg className={styles.tray} width={width} height={height} aria-hidden="true">
        <defs>
          <radialGradient id={gradient} cx="50%" cy="35%" r="75%">
            <stop offset="0%" stopColor="rgb(30 40 58)" />
            <stop offset="100%" stopColor="rgb(6 9 15)" />
          </radialGradient>
        </defs>
        {cells.map((cell) => (
          <g key={`${cell.x},${cell.y}`} transform={`translate(${cell.x} ${cell.y})`}>
            <path className={styles.floor} d={HEX_PATH} style={{ fill: `url(#${gradient})` }} />
            <path className={styles.engrave} d={HEX_PATH} transform={INNER_HEX} />
          </g>
        ))}
      </svg>
      <div className={styles.plateWrap} style={{ left: first.x, top: first.y }}>
        <TrayPlate label={label} info={info} count={items.length} />
      </div>
      {items.length === 0 ? (
        <p className={styles.empty} style={{ left: first.x, top: first.y + 132 }}>
          {emptyText}
        </p>
      ) : (
        <ul className={styles.list}>
          {items.map((item, i) => {
            const k = Math.floor(i / EFFECTS_PER_HEX);
            const cell = cells[side === "left" ? cells.length - 1 - k : k];
            const slot = TOKEN_SLOTS[i % EFFECTS_PER_HEX];
            return <Fragment key={item.key}>{item.node({ x: cell.x + slot.x, y: cell.y + slot.y })}</Fragment>;
          })}
        </ul>
      )}
    </section>
  );
}

/**
 * Efekty trwałe „położone na planszy” (RULES.md 54): bohater Letnev do końca rundy, kość
 * agenta w tej rundzie walki, premie z kart itd. Taca to HEKS na siatce planszy, w wolnej
 * komórce po PRAWEJ między polami graczy (`effectsZoneAnchor`). Leży zawsze, także pusta.
 */
export function BoardEffectsZone({ gameData, tiles }: { gameData: GameData; tiles: Tile[] }) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const effects = gameState?.activeEffects ?? [];
  const playerOf = (owner: string | null) =>
    owner ? gameData.playerData.find((p) => p.faction === owner) : undefined;
  return (
    <BoardTray
      gameData={gameData}
      tiles={tiles}
      side="right"
      label="Effects"
      ariaLabel="Active effects"
      info={EFFECTS_INFO}
      emptyText="None in play"
      items={effects.map((effect) => ({
        key: effect.id,
        node: (at) => <EffectToken effect={effect} player={playerOf(effect.owner)} at={at} side="right" />,
      }))}
    />
  );
}

/** Prawa w grze: lustrzana taca po LEWEJ stronie planszy (decyzja użytkownika 2026-11-23). */
export function BoardLawsZone({ gameData, tiles }: { gameData: GameData; tiles: Tile[] }) {
  const laws = gameData.lawsInPlay ?? [];
  return (
    <BoardTray
      gameData={gameData}
      tiles={tiles}
      side="left"
      label="Laws"
      ariaLabel="Laws in play"
      info={LAWS_INFO}
      emptyText="No laws in play"
      items={laws.map((law, i) => ({
        key: `${law.id}-${i}`,
        node: (at) => (
          <LawToken
            law={law}
            player={
              law.electedFaction
                ? gameData.playerData.find((p) => p.faction === law.electedFaction)
                : undefined
            }
            at={at}
            side="left"
          />
        ),
      }))}
    />
  );
}

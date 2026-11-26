import type { CSSProperties, ReactNode } from "react";
import { IconAlertTriangle } from "@tabler/icons-react";
import { DebtTokens } from "@/domains/player/components/DebtTokens";
import { FragmentsPool } from "@/domains/player/components/FragmentsPool";
import { ReinforcementTokensGroup } from "@/domains/player/components/ReinforcementTokensGroup";
import { ResourceInfluenceCompact } from "@/domains/player/components/ResourceInfluenceTable";
import { usePlayerCardComputedData } from "@/domains/player/components/PlayerCardShared/usePlayerCardComputedData";
import { useSettingsStore } from "@/state/appStore";
import { PlanetTraitIcon } from "@/shared/ui/PlanetTraitIcon";
import type { PlanetTrait } from "@/entities/game/planetTraits";
import { CommandCounter } from "@/domains/map/components/CommandCounter";
import { useFactionTokenImage } from "@/hooks/useFactionTokenImage";
import { getColorAlias } from "@/entities/lookup/colors";
import type { PlayerData } from "@/entities/data/types";
import type { EmpireStats } from "../empireStats";
import styles from "./CommandWing.module.css";

/*
 * Right piece of the player zone: the command sheet as printed - a hexagon split by a frame
 * into TACTIC (top), FLEET (upper right), STRATEGY (lower right), TRADE GOODS (bottom left) and
 * the reinforcements (upper left), with the live tokens lying in each pool. Under the mat, the
 * supply tray: what the player can spend right now (planets), relic fragments, debts and other
 * tokens in reinforcements.
 */

const COMMAND_TOKEN_SUPPLY = 16;
/** Tokens drawn in one pool; more are shown as "+n". */
const PILE_MAX = 8;

type Pt = readonly [number, number];

const H = 50 * Math.sqrt(3);
const O: Pt = [0, 0];
/** Flat-top hexagon, radius 100, centred on the origin. */
const V = {
  r: [100, 0],
  tr: [50, -H],
  tl: [-50, -H],
  l: [-100, 0],
  bl: [-50, H],
  br: [50, H],
} as const satisfies Record<string, Pt>;
const HEX: Pt[] = [V.tl, V.tr, V.r, V.br, V.bl, V.l];
/** Frame spokes: none to the bottom-left corner - trade goods is one merged pool. */
const SPOKES: Pt[] = [V.tl, V.tr, V.r, V.br, V.l];
const VIEW = { x: -106, y: -H - 6, w: 212, h: 2 * H + 12 };

type SectorId = "tactic" | "fleet" | "strategy" | "tg" | "reinf";

const SECTORS: Record<SectorId, Pt[]> = {
  tactic: [O, V.tl, V.tr],
  fleet: [O, V.tr, V.r],
  strategy: [O, V.r, V.br],
  tg: [O, V.br, V.bl, V.l],
  reinf: [O, V.l, V.tl],
};

/** Where each pool's content sits (mat coordinates), clear of the hub. */
const ANCHOR: Record<SectorId, Pt> = {
  tactic: [0, -56],
  fleet: [54, -29],
  strategy: [54, 29],
  tg: [-22, 52],
  reinf: [-52, -30],
};

function centroid(pts: Pt[]): Pt {
  return [
    pts.reduce((s, p) => s + p[0], 0) / pts.length,
    pts.reduce((s, p) => s + p[1], 0) / pts.length,
  ];
}

function scaled(pts: Pt[], k: number): Pt[] {
  const [cx, cy] = centroid(pts);
  return pts.map(([x, y]) => [cx + (x - cx) * k, cy + (y - cy) * k] as Pt);
}

const points = (pts: Pt[]) => pts.map((p) => p.map((n) => n.toFixed(2)).join(",")).join(" ");

const HUB: Pt[] = HEX.map(([x, y]) => [x * 0.15, y * 0.15] as Pt);

function anchorStyle(id: SectorId): CSSProperties {
  const [x, y] = ANCHOR[id];
  return {
    left: `${((x - VIEW.x) / VIEW.w) * 100}%`,
    top: `${((y - VIEW.y) / VIEW.h) * 100}%`,
  };
}

/** The mat's printed shapes and the grey frame laid over it. */
function MatShapes({ warn }: { warn: boolean }) {
  return (
    <svg
      className={styles.svg}
      viewBox={`${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}`}
      aria-hidden="true"
    >
      {(Object.keys(SECTORS) as SectorId[]).map((id) => (
        <g key={id} className={styles.sector} data-sector={id} data-warn={(id === "fleet" && warn) || undefined}>
          <polygon className={styles.field} points={points(scaled(SECTORS[id], 0.94))} />
          <polygon className={styles.inner} points={points(scaled(SECTORS[id], id === "tg" ? 0.66 : 0.6))} />
        </g>
      ))}
      <g className={styles.frame}>
        <polygon points={points(HEX)} />
        {SPOKES.map(([x, y]) => (
          <line key={`${x},${y}`} x1={0} y1={0} x2={x} y2={y} />
        ))}
      </g>
      <polygon className={styles.hub} points={points(HUB)} />
    </svg>
  );
}

/**
 * Up to `PILE_MAX` tokens of one kind lying in the pool, in a neat overlapping row - the same
 * token the map draws (`CommandCounter`: colour triangle + faction emblem; fleet side up in the
 * fleet pool).
 */
function Pile({
  count,
  colorAlias,
  faction,
  type = "command",
  faded,
}: {
  count: number;
  colorAlias: string;
  faction?: string;
  type?: "command" | "fleet";
  faded?: boolean;
}) {
  const shown = Math.min(count, PILE_MAX);
  return (
    <span className={styles.pile} data-faded={faded || undefined} aria-hidden="true">
      {Array.from({ length: shown }, (_, i) => (
        <CommandCounter
          key={i}
          fluid
          className={styles.token}
          colorAlias={colorAlias}
          faction={faction}
          type={type}
          style={{ zIndex: i } as CSSProperties}
        />
      ))}
      {count > shown && <span className={styles.more}>+{count - shown}</span>}
    </span>
  );
}

/** A pile of trade goods (no faction mark). */
function TgPile({ count }: { count: number }) {
  const shown = Math.min(count, PILE_MAX);
  return (
    <span className={styles.pile} aria-hidden="true">
      {Array.from({ length: shown }, (_, i) => (
        <img key={i} className={styles.tgToken} src="/tg.png" alt="" />
      ))}
      {count > shown && <span className={styles.more}>+{count - shown}</span>}
    </span>
  );
}

function Pool({
  id,
  label,
  value,
  title,
  warn,
  children,
}: {
  id: SectorId;
  label: string;
  value: ReactNode;
  title: string;
  warn?: boolean;
  children?: ReactNode;
}) {
  return (
    <div
      className={styles.pool}
      data-kind={id}
      data-warn={warn || undefined}
      style={anchorStyle(id)}
      role="group"
      aria-label={title}
      title={title}
    >
      <span className={styles.label}>{label}</span>
      <b className={styles.value}>{value}</b>
      {children}
    </div>
  );
}

const TRAITS: PlanetTrait[] = ["cultural", "hazardous", "industrial"];

/** One labelled shelf of the supply tray. */
function Shelf({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.shelf} role="group" aria-label={label}>
      <span className={styles.shelfLabel}>{label}</span>
      {children}
    </div>
  );
}

export function CommandWing({ player, empire }: { player: PlayerData; empire?: EmpireStats }) {
  const settings = useSettingsStore((s) => s.settings);
  const { planetEconomics } = usePlayerCardComputedData(player);
  // Most non-fighter ships in one system; null while the board is unknown.
  const largestFleet = empire ? empire.largestFleet : null;
  const factionToken = useFactionTokenImage(player.faction);
  const colorAlias = getColorAlias(player.color);
  const faction = player.faction || undefined;
  const edict = player.mahactEdict?.length ?? 0;
  const fleet = player.fleetCC + edict;
  const fleetFull = largestFleet !== null && fleet > 0 && largestFleet >= fleet;
  const tg = player.tg ?? 0;
  const debts = player.debtTokens ?? {};
  const hasDebts = Object.values(debts).some((n) => n > 0);
  const reinf = player.ccReinf;

  return (
    <section className={styles.wing} aria-label="Command sheet">
      <div className={styles.mat}>
        <div className={styles.matBg} aria-hidden="true" />
        <MatShapes warn={fleetFull} />
        {player.faction && (
          <img className={styles.hubMark} src={factionToken} alt="" aria-hidden="true" />
        )}

        <Pool
          id="tactic"
          label="Tactic"
          value={player.tacticalCC}
          title={`Tactic pool: ${player.tacticalCC} command tokens`}
        >
          <Pile count={player.tacticalCC} colorAlias={colorAlias} faction={faction} />
        </Pool>

        <Pool
          id="fleet"
          label="Fleet"
          value={`${fleet}${edict > 0 ? "*" : ""}`}
          title={`Fleet pool: ${fleet} command tokens${edict > 0 ? ` (${edict} from Edict)` : ""}`}
          warn={fleetFull}
        >
          <Pile count={player.fleetCC} colorAlias={colorAlias} faction={faction} type="fleet" />
          {largestFleet !== null && (
            <span
              className={styles.fleetUse}
              title="Largest fleet (non-fighter ships in one system) vs. fleet pool tokens"
            >
              {fleetFull && <IconAlertTriangle size={11} aria-label="Fleet pool full" />}
              Largest {largestFleet}/{fleet}
            </span>
          )}
        </Pool>

        <Pool
          id="strategy"
          label="Strategy"
          value={player.strategicCC}
          title={`Strategy pool: ${player.strategicCC} command tokens`}
        >
          <Pile count={player.strategicCC} colorAlias={colorAlias} faction={faction} />
        </Pool>

        <Pool id="tg" label="Trade goods" value={tg} title={`Trade goods: ${tg}`}>
          <TgPile count={tg} />
        </Pool>

        {reinf !== undefined && (
          <Pool
            id="reinf"
            label="Reinforcements"
            value={reinf}
            title={`Reinforcements: ${reinf} of ${COMMAND_TOKEN_SUPPLY} command tokens`}
          >
            <Pile count={reinf} colorAlias={colorAlias} faction={faction} faded />
          </Pool>
        )}
      </div>

      <div className={styles.supply}>
        <Shelf label="Ready to spend">
          <ResourceInfluenceCompact
            planetEconomics={planetEconomics}
            showTotalSpend={settings.showPlayerAreaTotalSpend}
          />
        </Shelf>
        {empire && (
          <Shelf label="Planets">
            <span className={styles.traits}>
              {TRAITS.map((t) => (
                <span key={t} title={`${empire.traits[t]} ${t} planets`}>
                  <PlanetTraitIcon trait={t} size={20} />
                  <b data-zero={empire.traits[t] === 0 || undefined}>{empire.traits[t]}</b>
                </span>
              ))}
              {empire.planets.legendary > 0 && (
                <span title={`${empire.planets.legendary} legendary planets`}>
                  <b>★ {empire.planets.legendary}</b>
                </span>
              )}
              <span className={styles.traitNote}>
                {empire.planets.ready}/{empire.planets.total} ready
              </span>
            </span>
          </Shelf>
        )}
        <Shelf label="Relic fragments">
          <FragmentsPool fragments={player.fragments ?? []} reserveSpace />
        </Shelf>
        {hasDebts && (
          <Shelf label="Debts">
            <DebtTokens debts={debts} compact />
          </Shelf>
        )}
        {settings.showPlayerAreaReinforcements && (
          <ReinforcementTokensGroup
            breachTokensReinf={player.breachTokensReinf}
            sleeperTokensReinf={player.sleeperTokensReinf}
            ghostWormholesReinf={player.ghostWormholesReinf}
            galvanizeTokensReinf={player.galvanizeTokensReinf}
          />
        )}
      </div>

      <p className={styles.motto} lang="la">
        Pax Magnifica Bellum Gloriosum
      </p>
    </section>
  );
}

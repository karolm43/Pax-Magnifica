import type { CSSProperties } from "react";
import { IconShieldHalfFilled, IconSkull } from "@tabler/icons-react";
import { Unit } from "@/shared/ui/Unit";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { BattleSide } from "@/api/useBoardEditor";
import type { Mark, ShipEntity } from "./battleAssign";
import type { ShipView } from "./useBattleFx";
import styles from "./BattleOverlay.module.css";

/* Rozmiar okrętu na polu bitwy wg typu (asyncId): okręty liniowe wyraźnie większe od
   eskorty, myśliwce i piechota małe — skala oddaje „wagę" jednostki. */
const SHIP_SIZE: Record<string, number> = {
  ws: 112,
  fs: 108,
  dn: 94,
  cv: 84,
  ca: 72,
  dd: 62,
  ff: 36,
  mf: 66,
  gf: 42,
};

/* Szereg w szyku bitewnym (0 = pierwsza linia, najbliżej przeciwnika): myśliwce i
   niszczyciele z przodu, okręty liniowe z tyłu; w walce naziemnej piechota przed mechami. */
const RANK: Record<string, number> = {
  ff: 0,
  gf: 0,
  dd: 1,
  mf: 1,
  ca: 2,
  cv: 3,
  dn: 4,
  fs: 5,
  ws: 5,
};

function shipSize(asyncId: string): number {
  return SHIP_SIZE[asyncId] ?? 64;
}

/** „Życie" egzemplarza: 2 punkty (Sustain gotowy), 1 (uszkodzony/zwykły). */
function hpPips(ship: ShipEntity): { full: number; total: number } {
  if (ship.unit.sustain) return { full: ship.damaged ? 1 : 2, total: 2 };
  return { full: 1, total: 1 };
}

/** Grupuje egzemplarze w szeregi wg ``RANK`` (od pierwszej linii). */
function ranks(views: ShipView[]): ShipView[][] {
  const byRank = new Map<number, ShipView[]>();
  for (const view of views) {
    const rank = RANK[view.ship.asyncId] ?? 3;
    byRank.set(rank, [...(byRank.get(rank) ?? []), view]);
  }
  return [...byRank.entries()].sort((a, b) => a[0] - b[0]).map(([, list]) => list);
}

function ShipToken({
  view,
  rank,
  index,
  side,
  colorAlias,
  faction,
  mark,
  selectable,
  onToggle,
}: {
  view: ShipView;
  rank: number;
  index: number;
  side: "left" | "right";
  colorAlias: string;
  faction: string;
  mark: Mark | undefined;
  selectable: boolean;
  onToggle: (ship: ShipEntity) => void;
}) {
  const { ship, dying } = view;
  const size = shipSize(ship.asyncId);
  const pips = hpPips(ship);
  const label = `${ship.name}${ship.damaged ? " (damaged)" : ""}`;
  const style = {
    "--rank": rank,
    "--i": index,
    "--dir": side === "left" ? -1 : 1,
    "--slot": `${size}px`,
    "--ship-size": `${Math.round(size * 0.78)}px`,
  } as CSSProperties;
  const common = {
    className: styles.ship,
    style,
    "data-side": side,
    "data-base": ship.asyncId,
    "data-damaged": ship.damaged || undefined,
    "data-mark": mark,
    // Cel pocisków salwy — warstwa animacji mierzy położenia po tych atrybutach. Także
    // egzemplarze eksplodujące (np. myśliwce zestrzelone przez AFB w tej samej salwie):
    // pociski do nich dolatują, zanim wybuchną (wybuch jest opóźniony w CSS).
    "data-ship-side": side,
    "data-ship-base": ship.baseType,
  };
  const content = (
    <>
      <span className={styles.shipSprite}>
        <Unit unitType={ship.asyncId} colorAlias={colorAlias} faction={faction} scaleSprite />
      </span>
      <span className={styles.pips} aria-label={`${pips.full} of ${pips.total} hit points`}>
        {Array.from({ length: pips.total }, (_, i) => (
          <span key={i} className={styles.pip} data-full={i < pips.full || undefined} />
        ))}
      </span>
      {mark && (
        <span className={styles.markBadge} data-mark={mark}>
          {(mark === "sustain" || mark === "both") && <IconShieldHalfFilled size={12} />}
          {(mark === "destroy" || mark === "both") && <IconSkull size={12} />}
        </span>
      )}
      {dying && <span className={styles.explosion} aria-hidden="true" />}
    </>
  );

  if (selectable && !dying) {
    return (
      <button
        type="button"
        {...common}
        data-selectable
        onClick={() => onToggle(ship)}
        title={`${label} — click to ${ship.canSustain ? "use Sustain Damage / destroy" : "destroy"}`}
        aria-pressed={mark !== undefined}
      >
        {content}
      </button>
    );
  }
  return (
    <div {...common} data-dying={dying || undefined} title={label}>
      {content}
    </div>
  );
}

/**
 * Kolumna jednej strony: nagłówek (frakcja, rola, kości, oczekiwane trafienia, pasek
 * życia), szyk bitewny (szeregi od pierwszej linii — myśliwce z przodu, okręty liniowe z
 * tyłu; wejście armady z boku) i spis jednostek z wartościami bojowymi. W kroku
 * przypisania strat okręty strony stają się klikalne.
 */
export function BattleFleet({
  side,
  views,
  align,
  name,
  colorAlias,
  maxHp,
  isWinner,
  assigning,
  marks,
  onToggle,
}: {
  side: BattleSide;
  views: ShipView[];
  align: "left" | "right";
  name: string;
  colorAlias: string;
  maxHp: number;
  isWinner: boolean;
  assigning: boolean;
  marks: Record<string, Mark>;
  onToggle: (ship: ShipEntity) => void;
}) {
  const hpRatio = maxHp > 0 ? Math.max(0, side.hp / maxHp) : 0;
  return (
    <section
      className={styles.fleet}
      data-align={align}
      data-assigning={assigning || undefined}
      aria-label={`${side.role === "attacker" ? "Attacker" : "Defender"}: ${name}`}
    >
      <header className={styles.fleetHead}>
        <CircularFactionIcon faction={side.faction} size={38} />
        <div className={styles.fleetWho}>
          <span className={styles.role}>
            {side.role === "attacker" ? "Attacker" : "Defender"}
            {isWinner && <b className={styles.victor}>Victor</b>}
          </span>
          <b className={styles.fleetName}>{name}</b>
          <span className={styles.fleetStats}>
            {side.unitCount} unit{side.unitCount === 1 ? "" : "s"} · {side.totalDice} dice · ~
            {side.expectedHits} hits
          </span>
        </div>
      </header>

      <div className={styles.hpBar} role="meter" aria-valuenow={side.hp} aria-valuemax={maxHp}>
        <span className={styles.hpFill} style={{ width: `${hpRatio * 100}%` }} />
        <span className={styles.hpText}>
          {side.hp} / {maxHp} HP
        </span>
      </div>

      <div className={styles.formation}>
        {views.length === 0 && <span className={styles.wiped}>Fleet destroyed</span>}
        {ranks(views).map((rankViews, rank) => (
          <div key={rankViews[0].ship.asyncId} className={styles.rank}>
            {rankViews.map((view, i) => (
              <ShipToken
                key={view.ship.id}
                view={view}
                rank={rank}
                index={i}
                side={align}
                colorAlias={colorAlias}
                faction={side.faction}
                mark={marks[view.ship.id]}
                selectable={assigning}
                onToggle={onToggle}
              />
            ))}
          </div>
        ))}
      </div>

      <table className={styles.roster}>
        <thead>
          <tr>
            <th>Unit</th>
            <th title="Hits on X+ × dice per unit">Combat</th>
            <th title="Anti-Fighter Barrage">AFB</th>
            <th title="Sustain Damage">Sustain</th>
          </tr>
        </thead>
        <tbody>
          {side.units.map((u) => (
            <tr key={u.baseType}>
              <td>
                <b>{u.count}×</b> {u.name}
                {u.damaged > 0 && <span className={styles.dmgTag}>{u.damaged} dmg</span>}
              </td>
              <td>
                {u.hitsOn}+ ×{u.dicePerUnit}
                {u.modifier > 0 && <span className={styles.modTag}>+{u.modifier}</span>}
              </td>
              <td>{u.afbHitsOn !== null ? `${u.afbHitsOn}+ ×${u.afbDice}` : "—"}</td>
              <td>{u.sustain ? `${u.sustainable}/${u.count}` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

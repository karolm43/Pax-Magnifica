import type { CSSProperties } from "react";
import { IconShieldHalfFilled, IconSkull, IconSwords } from "@tabler/icons-react";
import { Unit } from "@/shared/ui/Unit";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { BattleSide } from "@/api/useBoardEditor";
import type { Mark, ShipEntity } from "./battleAssign";
import type { ShipView } from "./useBattleFx";
import styles from "./BattleOverlay.module.css";

/* Rozmiar okrętu na polu bitwy wg typu (asyncId) — duże okręty liniowe, małe myśliwce. */
const SHIP_SIZE: Record<string, number> = {
  ws: 92,
  fs: 92,
  dn: 78,
  cv: 70,
  ca: 64,
  dd: 58,
  mf: 62,
  ff: 42,
  gf: 44,
};

function shipSize(asyncId: string): number {
  return SHIP_SIZE[asyncId] ?? 60;
}

/** „Życie" egzemplarza: 2 punkty (Sustain gotowy), 1 (uszkodzony/zwykły). */
function hpPips(ship: ShipEntity): { full: number; total: number } {
  if (ship.unit.sustain) return { full: ship.damaged ? 1 : 2, total: 2 };
  return { full: 1, total: 1 };
}

function ShipToken({
  view,
  index,
  side,
  colorAlias,
  faction,
  mark,
  selectable,
  onToggle,
}: {
  view: ShipView;
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
  const content = (
    <>
      <span className={styles.shipSprite} style={{ width: size, height: size }}>
        <Unit unitType={ship.asyncId} colorAlias={colorAlias} faction={faction} scaleSprite />
      </span>
      <span className={styles.pips} aria-label={`${pips.full} of ${pips.total} hit points`}>
        {Array.from({ length: pips.total }, (_, i) => (
          <span key={i} className={styles.pip} data-full={i < pips.full || undefined} />
        ))}
      </span>
      {mark && (
        <span className={styles.markBadge} data-mark={mark}>
          {(mark === "sustain" || mark === "both") && <IconShieldHalfFilled size={13} />}
          {(mark === "destroy" || mark === "both") && <IconSkull size={13} />}
        </span>
      )}
      {dying && <span className={styles.explosion} aria-hidden="true" />}
    </>
  );

  const style = {
    "--i": index,
    "--dir": side === "left" ? -1 : 1,
  } as CSSProperties;

  if (selectable && !dying) {
    return (
      <button
        type="button"
        className={styles.ship}
        data-side={side}
        data-damaged={ship.damaged || undefined}
        data-mark={mark}
        data-selectable
        style={style}
        onClick={() => onToggle(ship)}
        title={`${label} — click to ${ship.canSustain ? "use Sustain Damage / destroy" : "destroy"}`}
        aria-pressed={mark !== undefined}
      >
        {content}
      </button>
    );
  }
  return (
    <div
      className={styles.ship}
      data-side={side}
      data-damaged={ship.damaged || undefined}
      data-dying={dying || undefined}
      style={style}
      title={label}
    >
      {content}
    </div>
  );
}

/**
 * Kolumna jednej strony: nagłówek (frakcja, rola, kości, oczekiwane trafienia, pasek
 * życia), okręty na polu bitwy (wlatują z boku, eksplodują po zniszczeniu) i spis jednostek
 * z wartościami bojowymi. W kroku przypisania strat okręty strony stają się klikalne.
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
        <CircularFactionIcon faction={side.faction} size={42} />
        <div className={styles.fleetWho}>
          <span className={styles.role}>
            <IconSwords size={11} aria-hidden="true" />
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
        {views.map((view, i) => (
          <ShipToken
            key={view.ship.id}
            view={view}
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

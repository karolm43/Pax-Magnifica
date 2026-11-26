import type { CSSProperties } from "react";
import { playerName } from "@/domains/strategy/PlayerChip";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { getColorAlias } from "@/entities/lookup/colors";
import { Unit } from "@/shared/ui/Unit";
import type { PlayerData } from "@/entities/data/types";
import type { CompareRow } from "./empireCompare";
import type { BuildOption, EmpireStats } from "./empireStats";
import styles from "./PlayerTab.module.css";

/*
 * Empire panel of the Player tab: the player against the table (value, place, who leads, what
 * is in play in total - `empireCompare`) and the Shipyard calculator: how much of each unit the
 * ready resources + trade goods buy at the best PRODUCTION. Icons are the map's (`Unit`, emblems).
 */


const LIMIT_COPY: Record<BuildOption["limitedBy"], string> = {
  resources: "resources",
  production: "dock limit",
  reinforcements: "reinforcements",
  fleetPool: "fleet pool",
};

/** Why a unit cannot be built at all - shown on the dimmed tile (resources/PRODUCTION = plain 0×). */
const BLOCKED_COPY: Partial<Record<BuildOption["limitedBy"], string>> = {
  reinforcements: "none left",
  fleetPool: "fleet pool full",
};

function ordinal(n: number): string {
  const tail = n % 100 >= 11 && n % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th";
  return `${n}${tail}`;
}

/** Each measure: value with its share of the total, place, leader(s) and the total. */
function VersusTable({ rows, shown }: { rows: CompareRow[]; shown: PlayerData }) {
  return (
    <table className={styles.versus} aria-label="Empire versus the table">
      <thead>
        <tr>
          <th scope="col">Measure</th>
          <th scope="col">{playerName(shown)}</th>
          <th scope="col">Place</th>
          <th scope="col">Leader</th>
          <th scope="col">In game</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          // Share of the total; for a best-of measure, of the leader's value.
          const base = row.total ?? row.best;
          const share = base > 0 ? Math.min(1, row.value / base) : 0;
          const leads = row.leaders.some((p) => p.color === shown.color);
          return (
            <tr key={row.id} title={row.hint} data-first={(row.rank === 1 && row.best > 0) || undefined}>
              <th scope="row">{row.label}</th>
              <td className={styles.versusValue}>
                <b>{row.value}</b>
                <span className={styles.share} aria-hidden="true">
                  <span style={{ width: `${share * 100}%` }} />
                </span>
              </td>
              <td>
                <span className={styles.place}>
                  {row.best === 0 ? "–" : ordinal(row.rank)}
                </span>
                <small> of {row.players}</small>
              </td>
              <td>
                {row.leaders.length === 0 ? (
                  <small>nobody yet</small>
                ) : (
                  <span className={styles.leader}>
                    {row.leaders.slice(0, 3).map((p) => (
                      <span key={p.color} title={playerName(p)}>
                        {p.faction ? <CircularFactionIcon faction={p.faction} size={20} /> : null}
                      </span>
                    ))}
                    <b>{row.best}</b>
                    <small>
                      {leads
                        ? row.leaders.length > 1
                          ? "you, tied"
                          : "you"
                        : row.leaders.length > 1
                          ? `${row.leaders.length} tied`
                          : playerName(row.leaders[0])}
                    </small>
                  </span>
                )}
              </td>
              <td>
                {row.total === null ? (
                  <small>–</small>
                ) : (
                  <>
                    <b>{row.total}</b> <small>{row.totalLabel}</small>
                  </>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function costLabel(cost: number): string {
  return cost < 1 ? `${cost * 2} for 2` : String(cost);
}

export function EmpirePanel({
  player,
  stats,
  compare = [],
}: {
  player: PlayerData;
  stats: EmpireStats;
  compare?: CompareRow[];
}) {
  const colorAlias = getColorAlias(player.color);
  return (
    <section className={styles.panel} aria-label="Empire">
      <h3 className={styles.panelTitle}>Empire</h3>
      {compare.length > 0 && <VersusTable rows={compare} shown={player} />}

      <h4 className={styles.subTitle}>Shipyard</h4>
      <p className={styles.hint}>
        With <b className={styles.budget}>{stats.budget}</b> to spend (ready resources + trade goods),{" "}
        <b className={styles.budget}>{stats.readyInfluence}</b> ready influence, and your best space dock
        system producing up to {stats.maxProduction} units
        {stats.fleetRoom !== null ? ` (room for ${stats.fleetRoom} more ships under your fleet pool)` : ""}, you
        could build:
      </p>
      <ul className={styles.build}>
        {stats.build.map((b) => {
          const blocked = b.max === 0 ? BLOCKED_COPY[b.limitedBy] : undefined;
          return (
          <li
            key={b.asyncId}
            className={styles.buildItem}
            data-zero={b.max === 0 || undefined}
            data-blocked={blocked ? "" : undefined}
            title={`${b.name}: cost ${costLabel(b.cost)} · up to ${b.max}, limited by ${LIMIT_COPY[b.limitedBy]}${
              b.reinforcements === null ? "" : ` · ${b.reinforcements} in reinforcements`
            }`}
          >
            <span className={styles.buildUnit} style={{ "--unit-fit": "28px" } as CSSProperties}>
              <Unit
                unitType={b.asyncId}
                colorAlias={colorAlias}
                faction={player.faction}
                scaleSprite
                showFactionTokens={false}
              />
            </span>
            <span className={styles.buildText}>
              <b>{b.max}×</b>
              <small>{b.name}</small>
              <small>
                {blocked ?? (
                  <>
                    cost {costLabel(b.cost)}
                    {b.max > 0 || b.limitedBy !== "resources" ? ` · ${LIMIT_COPY[b.limitedBy]}` : ""}
                  </>
                )}
              </small>
            </span>
          </li>
          );
        })}
      </ul>
    </section>
  );
}

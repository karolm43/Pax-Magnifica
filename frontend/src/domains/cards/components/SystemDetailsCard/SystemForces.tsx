import type { CSSProperties } from "react";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { FactionIcon } from "@/shared/ui/FactionIcon";
import { Unit } from "@/shared/ui/Unit";
import { useSystemOdds } from "@/api/boardQueries";
import { factionsInSystem } from "@/domains/map/components/SystemDossier/attacker";
import {
  formatStat,
  summarizeZone,
  type UnitRow,
} from "@/domains/map/components/SystemDossier/fleetMath";
import { useFactionHelpers } from "@/domains/map/components/SystemDossier/useFactionHelpers";
import type { Tile } from "@/entities/game/types";
import styles from "./SystemForces.module.css";

const pct = (share: number) => `${Math.round(share * 100)}%`;

type Force = { rows: UnitRow[]; hp: number; attack: number };

/** One force per faction for the whole system: ships in space + ground forces on planets. */
function forcesOf(tile: Tile, playerFor: ReturnType<typeof useFactionHelpers>["playerFor"]) {
  const forces = new Map<string, Force>();
  const add = (
    units: Tile["unitsByFaction"],
    fights: Parameters<typeof summarizeZone>[2],
  ) => {
    for (const { faction, rows, math } of summarizeZone(units, playerFor, fights)) {
      const force = forces.get(faction) ?? { rows: [], hp: 0, attack: 0 };
      force.rows.push(...rows);
      force.hp += math.hitPoints;
      force.attack += math.expectedHits;
      forces.set(faction, force);
    }
  };
  add(tile.unitsByFaction, (unit) => unit.isShip);
  for (const planet of Object.values(tile.planets)) {
    add(planet.unitsByFaction, (unit) => unit.isGroundForce);
  }
  return forces;
}

/**
 * Whole-system summary for the hover card: per faction its units (icon + count),
 * total hit points and expected hits per round; for a two-sided fight, a win-chance bar.
 */
export function SystemForces({ tile }: { tile: Tile }) {
  const helpers = useFactionHelpers();
  const contested = factionsInSystem(tile).length >= 2;
  const { data, isPending } = useSystemOdds(tile.position, contested);
  const forces = forcesOf(tile, helpers.playerFor);
  if (forces.size === 0) return null;

  // Space fight is the one that decides the system; otherwise the first ground fight.
  const odds = data?.zones.find((z) => z.zone === "space") ?? data?.zones[0];

  return (
    <DetailsCard.Section
      title="Forces"
      content={
        <div className={styles.zone}>
          {[...forces].map(([faction, force]) => (
            <div
              key={faction}
              className={styles.force}
              style={{ "--pc": helpers.rgb(faction) } as CSSProperties}
            >
              <FactionIcon faction={faction} w={16} h={16} />
              <span className={styles.units}>
                {force.rows.map((row) => (
                  <span key={`${row.asyncId}-${row.unit.id}`} className={styles.unit} title={row.unit.name}>
                    <span className={styles.icon}>
                      <Unit
                        unitType={row.asyncId}
                        colorAlias={helpers.colorAlias(faction)}
                        faction={faction}
                        scaleSprite
                      />
                    </span>
                    {row.count}
                  </span>
                ))}
              </span>
              <span className={styles.stats} title="Hit points · expected hits per round">
                {formatStat(force.hp)} HP · ⚔ {formatStat(force.attack)}
              </span>
            </div>
          ))}
          {contested && isPending && (
            <div className={styles.odds} aria-busy>
              <div className={styles.bar} data-loading />
            </div>
          )}
          {odds && (
            <div
              className={styles.odds}
              role="img"
              aria-label={`Win chance: ${helpers.displayName(odds.attacker)} ${pct(odds.attackerWin)}, ${helpers.displayName(odds.defender)} ${pct(odds.defenderWin)}`}
            >
              <div className={styles.bar}>
                <i style={{ width: pct(odds.attackerWin), background: `rgb(${helpers.rgb(odds.attacker)})` }} />
                <i style={{ width: pct(odds.draw), background: "var(--ds-h28)" }} />
                <i style={{ width: pct(odds.defenderWin), background: `rgb(${helpers.rgb(odds.defender)})` }} />
              </div>
              <div className={styles.legend}>
                <b>{pct(odds.attackerWin)}</b>
                <b>{pct(odds.defenderWin)}</b>
              </div>
            </div>
          )}
        </div>
      }
    />
  );
}

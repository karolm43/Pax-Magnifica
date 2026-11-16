import type { CSSProperties, ReactNode } from "react";
import { getColorAlias } from "@/entities/lookup/colors";
import { PlanetTraitIcon } from "@/shared/ui/PlanetTraitIcon";
import { TechSkipIcon, type TechType } from "@/shared/ui/TechSkipIcon";
import { Unit } from "@/shared/ui/Unit";
import type { PlayerData } from "@/entities/data/types";
import type { PlanetTrait } from "@/entities/game/planetTraits";
import type { BuildOption, EmpireStats } from "./empireStats";
import styles from "./PlayerTab.module.css";

/*
 * Panel „Empire” zakładki Player: przegląd terytorium i sił (systemy, planety wg cech,
 * specjalizacje, flota vs pula floty) oraz kalkulator „Shipyard” - ile czego da się zbudować
 * za gotowe zasoby + trade goods przy największym PRODUCTION. Ikony to te same assety co na
 * mapie i w strefie gracza (`PlanetTraitIcon`, `TechSkipIcon`, `Unit`).
 */

const TRAITS: PlanetTrait[] = ["cultural", "hazardous", "industrial"];
const SKIPS: TechType[] = ["biotic", "propulsion", "cybernetic", "warfare"];

const LIMIT_COPY: Record<BuildOption["limitedBy"], string> = {
  resources: "resources",
  production: "PRODUCTION",
  reinforcements: "reinforcements",
};

function Stat({ label, value, sub, title }: { label: string; value: ReactNode; sub?: ReactNode; title: string }) {
  return (
    <div className={styles.stat} title={title}>
      <small>{label}</small>
      <b>{value}</b>
      {sub !== undefined && <span>{sub}</span>}
    </div>
  );
}

function costLabel(cost: number): string {
  return cost < 1 ? `${cost * 2} for 2` : String(cost);
}

export function EmpirePanel({ player, stats }: { player: PlayerData; stats: EmpireStats }) {
  const colorAlias = getColorAlias(player.color);
  const fleetFull = stats.fleetPool > 0 && stats.largestFleet >= stats.fleetPool;
  return (
    <section className={styles.panel} aria-label="Empire">
      <h3 className={styles.panelTitle}>Empire</h3>
      <div className={styles.stats}>
        <Stat
          label="Systems"
          value={stats.systems.present}
          sub={`${stats.systems.controlled} alone`}
          title={`Units or planets in ${stats.systems.present} systems; in ${stats.systems.controlled} of them no other player is present`}
        />
        <Stat
          label="Planets"
          value={stats.planets.total}
          sub={`${stats.planets.ready} ready`}
          title={`${stats.planets.total} planets controlled, ${stats.planets.ready} ready`}
        />
        <Stat
          label="Ships"
          value={stats.forces.ships}
          sub={`+${stats.forces.fighters} fighters`}
          title="Non-fighter ships and fighters on the board"
        />
        <Stat
          label="Ground"
          value={stats.forces.ground}
          title="Infantry and mechs on the board"
        />
        <Stat
          label="Structures"
          value={stats.forces.docks + stats.forces.pds}
          sub={`${stats.forces.docks} dock · ${stats.forces.pds} PDS`}
          title="Space docks and PDS on the board"
        />
        <Stat
          label="Largest fleet"
          value={
            <span data-warn={fleetFull || undefined}>
              {stats.largestFleet}/{stats.fleetPool}
            </span>
          }
          sub="fleet pool"
          title="Most non-fighter ships you have in one system vs. tokens in your fleet pool"
        />
      </div>

      <div className={styles.iconRow}>
        <span className={styles.iconGroup} aria-label="Planet traits">
          {TRAITS.map((t) => (
            <span key={t} className={styles.iconCount} title={`${stats.traits[t]} ${t} planets`}>
              <PlanetTraitIcon trait={t} size={18} />
              <b data-zero={stats.traits[t] === 0 || undefined}>{stats.traits[t]}</b>
            </span>
          ))}
          {stats.planets.legendary > 0 && (
            <span className={styles.iconCount} title="Legendary planets">
              <b>★ {stats.planets.legendary}</b>
            </span>
          )}
        </span>
        <span className={styles.iconGroup} aria-label="Tech specialties on ready planets">
          <small>Skips</small>
          {SKIPS.map((c) => (
            <span key={c} className={styles.iconCount} title={`${stats.skips[c]} ready ${c} specialty planets`}>
              <TechSkipIcon techType={c} size={16} />
              <b data-zero={stats.skips[c] === 0 || undefined}>{stats.skips[c]}</b>
            </span>
          ))}
        </span>
      </div>

      <h4 className={styles.subTitle}>Shipyard</h4>
      <p className={styles.hint}>
        With {stats.budget} to spend (ready resources + trade goods) and PRODUCTION up to{" "}
        {stats.maxProduction} in one system, you could build:
      </p>
      <ul className={styles.build}>
        {stats.build.map((b) => (
          <li
            key={b.asyncId}
            className={styles.buildItem}
            data-zero={b.max === 0 || undefined}
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
                cost {costLabel(b.cost)}
                {b.max > 0 || b.limitedBy !== "resources" ? ` · ${LIMIT_COPY[b.limitedBy]}` : ""}
              </small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

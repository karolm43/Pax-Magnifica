/*
 * Pasek zasobów „jak w strategiach" — odczyt MOICH zasobów w pasku zakładek:
 * planety (suma i optymalnie, jak ledger w strefie gracza), trade goods, commodities, żetony
 * dowodzenia, statki na planszy według typu i fragmenty. Ikony to te same assety, co w strefie
 * gracza (`/pa_resources.png`, `InfluenceIcon`, `/tg.png`, `/comms.png`, `Unit`). Wszystkie
 * odczyty mają jeden wygląd (kolor niosą ikony). Gracz = biurko (`useDeskPlayer`).
 */
import type { CSSProperties, ReactNode } from "react";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { usePlanetEconomics } from "@/domains/player/hooks/usePlanetEconomics";
import { FragmentsPool } from "@/domains/player/components/FragmentsPool";
import { lookupUnit } from "@/entities/lookup/units";
import { getColorAlias } from "@/entities/lookup/colors";
import type { PlayerData } from "@/entities/data/types";
import InfluenceIcon from "@/shared/ui/InfluenceIcon";
import { Unit } from "@/shared/ui/Unit";
import styles from "./ResourceBar.module.css";

/** Statki w kolejności jak w strefie gracza (`PlayerCardUnitsArea`). */
const SHIP_ORDER = ["ws", "fs", "dn", "cv", "ca", "dd", "ff"];

const floor = (n: number | null | undefined) => Math.floor(n ?? 0);

function Value({ value, total }: { value: number; total?: number }) {
  return (
    <>
      <b data-zero={value === 0 || undefined}>{value}</b>
      {total !== undefined && <i>/{total}</i>}
    </>
  );
}

/** Grupa odczytów z małym podpisem (TOTAL / OPTIMAL / SHIPS). */
function Group({ label, title, children }: { label?: string; title: string; children: ReactNode }) {
  return (
    <span className={styles.group} title={title}>
      {label && <small>{label}</small>}
      {children}
    </span>
  );
}

function Pair({ icon, value, total }: { icon: ReactNode; value: number; total?: number }) {
  return (
    <span className={styles.pair}>
      <span className={styles.icon}>{icon}</span>
      <Value value={value} total={total} />
    </span>
  );
}

const RES = <img src="/pa_resources.png" alt="" />;
const INF = <InfluenceIcon size={18} />;

function Ships({ player }: { player: PlayerData }) {
  const colorAlias = getColorAlias(player.color);
  const ships = SHIP_ORDER.flatMap((asyncId) => {
    const count = player.unitCounts?.[asyncId]?.deployedCount ?? 0;
    const unit = lookupUnit(asyncId, player.faction, player);
    return count > 0 && unit ? [{ asyncId, count, name: unit.name }] : [];
  });
  if (ships.length === 0) return null;
  return (
    <Group
      label="Ships"
      title={`Ships on the board: ${ships.map((s) => `${s.count} ${s.name}`).join(", ")}`}
    >
      {ships.map((s) => (
        <span key={s.asyncId} className={styles.pair}>
          <span className={styles.ship} style={{ "--unit-fit": "22px" } as CSSProperties}>
            <Unit
              unitType={s.asyncId}
              colorAlias={colorAlias}
              faction={player.faction}
              scaleSprite
              showFactionTokens={false}
            />
          </span>
          <b>{s.count}</b>
        </span>
      ))}
    </Group>
  );
}

function ResourceBarFor({ desk }: { desk: PlayerData }) {
  const player = getPlayerCardLayoutFields(desk);
  const { total, optimal, flex, flexSpendOnly } = usePlanetEconomics(desk);
  const tg = player.tg ?? 0;
  const comms = player.commodities ?? 0;
  const commsMax = player.commoditiesTotal ?? 0;
  const fleet = player.fleetCC + (desk.mahactEdict?.length ?? 0);
  const showFlex = floor(flex.totalFlex) > 0;

  return (
    <div className={styles.bar} role="group" aria-label="Your stores">
      {!flexSpendOnly && (
        <Group
          label="Total"
          title={`Planets, ready of all - resources ${floor(total.currentResources)}/${floor(total.totalResources)}, influence ${floor(total.currentInfluence)}/${floor(total.totalInfluence)}`}
        >
          <Pair icon={RES} value={floor(total.currentResources)} total={floor(total.totalResources)} />
          <Pair icon={INF} value={floor(total.currentInfluence)} total={floor(total.totalInfluence)} />
        </Group>
      )}
      <Group
        label="Optimal"
        title="Optimal spend: each planet counted for its better value (ready of all)"
      >
        {!flexSpendOnly && (
          <>
            <Pair icon={RES} value={floor(optimal.currentResources)} total={floor(optimal.totalResources)} />
            <Pair icon={INF} value={floor(optimal.currentInfluence)} total={floor(optimal.totalInfluence)} />
          </>
        )}
        {(showFlex || flexSpendOnly) && (
          <span className={styles.pair}>
            <small className={styles.flex}>flex</small>
            <Value value={floor(flex.currentFlex)} total={floor(flex.totalFlex)} />
          </span>
        )}
      </Group>
      <Group title={`Trade goods: ${tg} · commodities: ${comms} of ${commsMax}`}>
        <Pair icon={<img src="/tg.png" alt="" />} value={tg} />
        <Pair icon={<img src="/comms.png" alt="" />} value={comms} total={commsMax} />
      </Group>
      <Group
        label="CC"
        title={`Command tokens: ${player.tacticalCC} tactic · ${fleet} fleet · ${player.strategicCC} strategy`}
      >
        <span className={styles.cc}>
          <b>{player.tacticalCC}</b>
          <em>T</em>
          <b>{fleet}</b>
          <em>F</em>
          <b>{player.strategicCC}</b>
          <em>S</em>
        </span>
      </Group>
      <Ships player={desk} />
      {player.fragments.length > 0 && <FragmentsPool fragments={player.fragments} />}
    </div>
  );
}

export function ResourceBar() {
  const desk = useDeskPlayer();
  return desk ? <ResourceBarFor desk={desk} /> : null;
}

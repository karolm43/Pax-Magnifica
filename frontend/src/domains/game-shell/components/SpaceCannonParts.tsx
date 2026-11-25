import { useState, type CSSProperties } from "react";
import { IconMinus, IconPlus, IconSkull, IconWand } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { lookupUnit } from "@/entities/lookup/units";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { Unit } from "@/shared/ui/Unit";
import type {
  SpaceCannonLogEntry,
  SpaceCannonPending,
  SpaceCannonRoll,
  SpaceCannonShip,
} from "@/api/useBoardEditor";
import styles from "./SpaceCannonStepPanel.module.css";

/** Nazwa wyświetlana i alias koloru gracza o danym kluczu tożsamości (web-data `faction`). */
export function usePlayerLookup() {
  const gameData = useGameData();
  return (key: string) => {
    const player = gameData?.playerData?.find((p) => p.faction === key);
    return {
      name: player ? getPlayerFactionDisplayName(player) : key,
      colorAlias: getColorAlias(player?.color),
    };
  };
}

/** Etykieta miejsca strzelca: statki w przestrzeni vs planeta (+ system, gdy sąsiedni). */
export function zoneLabel(roll: { zone: string; position: string }): string {
  return roll.zone === "space" ? `space ${roll.position}` : `${roll.zone} ${roll.position}`;
}

/**
 * Wyniki rzutów: dla każdej grupy strzelców rząd kości; trafienie (≥ próg) świeci na
 * czerwono i „wpada" z krótkim opóźnieniem (animacja), pudło jest wygaszone.
 */
export function DiceRolls({ rolls }: { rolls: SpaceCannonRoll[] }) {
  return (
    <div className={styles.rolls}>
      {rolls.map((roll, ri) => (
        <div key={`${roll.baseType}-${roll.zone}-${roll.position}-${ri}`} className={styles.rollRow}>
          <span className={styles.rollLabel}>
            {roll.name} · {roll.hitsOn}+
            <small> {zoneLabel(roll)}</small>
            {(roll.modifier ?? 0) !== 0 && (
              <b
                className={styles.rollTag}
                data-tone="debuff"
                title="Technology of the targeted player changes each die result"
              >
                {roll.modifier > 0 ? "+" : "\u2212"}
                {Math.abs(roll.modifier)} to each die (Antimass Deflectors)
              </b>
            )}
            {(roll.extraDice ?? 0) > 0 && (
              <b
                className={styles.rollTag}
                data-tone="buff"
                title="Plasma Scoring: this unit rolled additional dice"
              >
                +{roll.extraDice} die (Plasma Scoring)
              </b>
            )}
          </span>
          <span className={styles.diceRow}>
            {roll.dice.map((value, di) => {
              const modifier = roll.modifier ?? 0;
              const result = value + modifier;
              return (
                <span
                  key={di}
                  className={styles.die}
                  data-hit={result >= roll.hitsOn || undefined}
                  style={{ "--i": ri * 6 + di } as CSSProperties}
                  title={
                    modifier !== 0
                      ? `Rolled ${value}, ${modifier > 0 ? "+" : "\u2212"}${Math.abs(modifier)} = ${result}: ${result >= roll.hitsOn ? "Hit" : "Miss"}`
                      : value >= roll.hitsOn
                        ? "Hit"
                        : "Miss"
                  }
                >
                  {value}
                  {modifier !== 0 && <small className={styles.dieMod}>{"\u2192"}{result}</small>}
                </span>
              );
            })}
          </span>
        </div>
      ))}
    </div>
  );
}

export type SpaceCannonAssignPlan = {
  sustain: { baseType: string; count: number }[];
  destroy: { baseType: string; count: number }[];
  destroyDamaged: { baseType: string; count: number }[];
};

/**
 * Plan dla silnika z wyboru gracza: ``sustain`` użyć Sustain Damage i ``destroyed`` zniszczeń
 * na typ. Niszczymy najpierw statki uszkodzone (także te właśnie uszkodzone), potem całe.
 */
export function spaceCannonPlan(
  ships: SpaceCannonShip[],
  sustain: Record<string, number>,
  destroyed: Record<string, number>,
): SpaceCannonAssignPlan {
  const plan: SpaceCannonAssignPlan = {
    sustain: [],
    destroy: [],
    destroyDamaged: [],
  };
  for (const ship of ships) {
    const s = sustain[ship.baseType] ?? 0;
    const d = destroyed[ship.baseType] ?? 0;
    const dd = Math.min(d, (ship.damaged ?? 0) + s);
    if (s > 0) plan.sustain.push({ baseType: ship.baseType, count: s });
    if (dd > 0)
      plan.destroyDamaged.push({ baseType: ship.baseType, count: dd });
    if (d - dd > 0)
      plan.destroy.push({ baseType: ship.baseType, count: d - dd });
  }
  return plan;
}

/**
 * "Auto" hit assignment (RULES.md 38.4 ⚠️ ASSUMPTION): first every available Sustain Damage
 * (on the most expensive ships - each cancels ``cancels`` hits), then destroy the CHEAPEST
 * ships for the hits left. The player can still change it before confirming.
 */
export function autoAssignHits(
  ships: SpaceCannonShip[],
  required: number,
  cancels: number,
  costOf: (ship: SpaceCannonShip) => number,
): { sustain: Record<string, number>; destroyed: Record<string, number> } {
  const sustain: Record<string, number> = {};
  const destroyed: Record<string, number> = {};
  let left = required;
  const byCost = [...ships].sort((a, b) => costOf(b) - costOf(a));
  for (const ship of byCost) {
    const free = ship.sustain ? ship.count - (ship.damaged ?? 0) : 0;
    const use = Math.min(free, Math.ceil(Math.max(left, 0) / Math.max(cancels, 1)));
    if (use > 0) {
      sustain[ship.baseType] = use;
      left -= use * cancels;
    }
  }
  for (const ship of byCost.reverse()) {
    if (left <= 0) break;
    const kill = Math.min(ship.count, left);
    destroyed[ship.baseType] = kill;
    left -= kill;
  }
  return { sustain, destroyed };
}

/** Stepper −/+ jednej decyzji (Sustain Damage albo zniszczenie) dla typu statku. */
function StepPair({
  verb,
  name,
  value,
  canLess,
  canMore,
  danger,
  onChange,
}: {
  verb: string;
  name: string;
  value: number;
  canLess: boolean;
  canMore: boolean;
  danger?: boolean;
  onChange: (delta: number) => void;
}) {
  return (
    <span className={styles.shipBtns} role="group" aria-label={`${verb} ${name}`}>
      <button
        type="button"
        className={styles.step}
        disabled={!canLess}
        onClick={() => onChange(-1)}
        aria-label={`Less: ${verb} ${name}`}
      >
        <IconMinus size={12} />
      </button>
      <small className={styles.shipCount}>
        {verb} {value}
      </small>
      <button
        type="button"
        className={styles.step}
        data-danger={danger || undefined}
        disabled={!canMore}
        onClick={() => onChange(+1)}
        aria-label={`${verb} ${name}`}
      >
        <IconPlus size={12} />
      </button>
    </span>
  );
}

/**
 * Gracz-cel pokrywa trafienia Space Cannon: Sustain Damage (statek staje się uszkodzony,
 * R_sustain_damage) albo zniszczenie. Silnik waliduje plan (422 z powodem).
 */
export function AssignHits({
  pending,
  ships,
  targetName,
  colorAlias,
  faction,
  busy,
  onConfirm,
}: {
  pending: SpaceCannonPending;
  ships: SpaceCannonShip[];
  targetName: string;
  colorAlias: string;
  faction: string;
  busy: boolean;
  onConfirm: (plan: SpaceCannonAssignPlan) => void;
}) {
  const [sustain, setSustain] = useState<Record<string, number>>({});
  const [destroyed, setDestroyed] = useState<Record<string, number>>({});
  const sum = (r: Record<string, number>) =>
    Object.values(r).reduce((a, b) => a + b, 0);
  // Non-Euclidean Shielding: tarcza anuluje 2 trafienia; ostatnia może anulować mniej
  // (same tarcze, nadwyżka < cancels) — ta sama reguła co ``isCovered`` w oknie bitwy.
  const cancels = pending.cancels ?? 1;
  const raw = sum(sustain) * cancels + sum(destroyed);
  const lastShieldOver =
    cancels > 1 &&
    sum(destroyed) === 0 &&
    raw > pending.required &&
    raw < pending.required + cancels;
  const chosen = lastShieldOver ? pending.required : raw;
  const ready = chosen === pending.required;
  const full = chosen >= pending.required;
  const anySustain = ships.some((s) => s.sustain);
  const left = pending.required - chosen;
  const auto = () => {
    const plan = autoAssignHits(ships, pending.required, cancels, (ship) => {
      return lookupUnit(ship.asyncId, faction)?.cost ?? 0;
    });
    setSustain(plan.sustain);
    setDestroyed(plan.destroyed);
  };

  const bump = (
    set: typeof setSustain,
    baseType: string,
    max: number,
    delta: number,
  ) =>
    set((prev) => {
      const next = (prev[baseType] ?? 0) + delta;
      if (next < 0 || next > max) return prev;
      if (delta > 0 && full) return prev;
      return { ...prev, [baseType]: next };
    });

  return (
    <section className={styles.assign} aria-label="Assign hits">
      <header className={styles.assignHead}>
        <IconSkull size={14} aria-hidden="true" />
        <span>
          <b>{targetName}</b> must cover <b>{pending.required}</b> hit
          {pending.required === 1 ? "" : "s"}
          {anySustain && (
            <small>
              {" "}
              — Sustain Damage cancels{" "}
              {cancels === 1 ? "a hit" : `${cancels} hits`}
            </small>
          )}
        </span>
        <span className={styles.counter} data-ready={ready || undefined}>
          {chosen}/{pending.required}
        </span>
        <button
          type="button"
          className={styles.autoBtn}
          disabled={busy}
          onClick={auto}
          title="Sustain Damage first, then destroy the cheapest ships - you can still change it"
        >
          <IconWand size={13} aria-hidden="true" /> Auto
        </button>
      </header>
      <div className={styles.ships}>
        {ships.map((ship) => {
          const s = sustain[ship.baseType] ?? 0;
          const d = destroyed[ship.baseType] ?? 0;
          const damaged = ship.damaged ?? 0;
          const maxSustain = ship.sustain ? ship.count - damaged : 0;
          return (
            <div key={ship.baseType} className={styles.shipTile}>
              <div className={styles.icon}>
                <Unit
                  unitType={ship.asyncId}
                  colorAlias={colorAlias}
                  faction={faction}
                  scaleSprite
                />
              </div>
              <span className={styles.shipName}>
                {ship.name}
                <small>
                  {" "}
                  ×{ship.count}
                  {damaged > 0 && `, ${damaged} damaged`}
                </small>
              </span>
              {maxSustain > 0 && (
                <StepPair
                  verb="Sustain"
                  name={ship.name}
                  value={s}
                  canLess={!busy && s > 0}
                  canMore={!busy && s < maxSustain && !full}
                  onChange={(delta) =>
                    bump(setSustain, ship.baseType, maxSustain, delta)
                  }
                />
              )}
              <StepPair
                verb="Destroy"
                name={ship.name}
                value={d}
                danger
                canLess={!busy && d > 0}
                canMore={!busy && d < ship.count && !full}
                onChange={(delta) =>
                  bump(setDestroyed, ship.baseType, ship.count, delta)
                }
              />
            </div>
          );
        })}
      </div>
      <button
        type="button"
        className={styles.confirm}
        disabled={busy || !ready}
        onClick={() => onConfirm(spaceCannonPlan(ships, sustain, destroyed))}
      >
        {ready
          ? "Confirm losses"
          : `Assign ${left} more hit${left === 1 ? "" : "s"}`}
      </button>
    </section>
  );
}

/** Dziennik rozstrzygnięć okna: kto, w kogo, ile trafień i jakie straty. */
export function SpaceCannonLog({
  log,
  nameOf,
}: {
  log: SpaceCannonLogEntry[];
  nameOf: (key: string) => string;
}) {
  if (log.length === 0) return null;
  return (
    <ol className={styles.log} aria-label="Space Cannon results">
      {log.map((entry, i) => {
        const destroyed = Object.entries(entry.destroyed)
          .map(([baseType, count]) => `${count}× ${baseType}`)
          .join(", ");
        return (
          <li key={i} className={styles.logRow} data-hit={entry.hits > 0 || undefined}>
            <b>{nameOf(entry.roller)}</b>
            {entry.passed ? (
              <span className={styles.muted}> passed</span>
            ) : (
              <>
                <span className={styles.muted}> → </span>
                <b>{nameOf(entry.target)}</b>
                <span>
                  {" "}
                  · {entry.hits} hit{entry.hits === 1 ? "" : "s"}
                  {destroyed ? ` · lost ${destroyed}` : ""}
                </span>
                <DiceRolls rolls={entry.rolls} />
              </>
            )}
          </li>
        );
      })}
    </ol>
  );
}

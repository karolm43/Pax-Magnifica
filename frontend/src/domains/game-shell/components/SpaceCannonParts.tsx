import { useState, type CSSProperties } from "react";
import { IconMinus, IconPlus, IconSkull } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
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
          </span>
          <span className={styles.diceRow}>
            {roll.dice.map((value, di) => (
              <span
                key={di}
                className={styles.die}
                data-hit={value >= roll.hitsOn || undefined}
                style={{ "--i": ri * 6 + di } as CSSProperties}
                title={value >= roll.hitsOn ? "Hit" : "Miss"}
              >
                {value}
              </span>
            ))}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * Przypisanie strat: gracz-cel niszczy dokładnie ``required`` statków. Licznik ``x/N``,
 * +/− per typ (do liczby posiadanych), potwierdzenie dopiero przy komplecie. Stan
 * wyboru jest lokalny — rodzic montuje komponent z ``key`` nowego przypisania.
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
  onConfirm: (losses: { baseType: string; count: number }[]) => void;
}) {
  const [losses, setLosses] = useState<Record<string, number>>({});
  const chosen = Object.values(losses).reduce((a, b) => a + b, 0);
  const ready = chosen === pending.required;

  const change = (baseType: string, max: number, delta: number) =>
    setLosses((prev) => {
      const next = (prev[baseType] ?? 0) + delta;
      if (next < 0 || next > max) return prev;
      if (delta > 0 && chosen >= pending.required) return prev;
      return { ...prev, [baseType]: next };
    });

  return (
    <section className={styles.assign} aria-label="Assign hits">
      <header className={styles.assignHead}>
        <IconSkull size={14} aria-hidden="true" />
        <span>
          <b>{targetName}</b> must destroy <b>{pending.required}</b> ship
          {pending.required === 1 ? "" : "s"}
        </span>
        <span className={styles.counter} data-ready={ready || undefined}>
          {chosen}/{pending.required}
        </span>
      </header>
      <div className={styles.ships}>
        {ships.map((ship) => {
          const picked = losses[ship.baseType] ?? 0;
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
              <span className={styles.shipName}>{ship.name}</span>
              <span className={styles.shipCount}>
                {picked}/{ship.count}
              </span>
              <span className={styles.shipBtns}>
                <button
                  type="button"
                  className={styles.step}
                  disabled={busy || picked <= 0}
                  onClick={() => change(ship.baseType, ship.count, -1)}
                  aria-label={`Keep ${ship.name}`}
                >
                  <IconMinus size={12} />
                </button>
                <button
                  type="button"
                  className={styles.step}
                  data-danger
                  disabled={busy || picked >= ship.count || chosen >= pending.required}
                  onClick={() => change(ship.baseType, ship.count, +1)}
                  aria-label={`Destroy ${ship.name}`}
                >
                  <IconPlus size={12} />
                </button>
              </span>
            </div>
          );
        })}
      </div>
      <button
        type="button"
        className={styles.confirm}
        disabled={busy || !ready}
        onClick={() =>
          onConfirm(
            Object.entries(losses).map(([baseType, count]) => ({ baseType, count })),
          )
        }
      >
        {ready ? "Destroy selected ships" : `Select ${pending.required - chosen} more`}
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

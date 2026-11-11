import { type CSSProperties } from "react";
import { IconShieldHalfFilled, IconSkull } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias, resolvePrimaryRgb } from "@/entities/lookup/colors";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { Unit } from "@/shared/ui/Unit";
import type { BattleSide, BattleUnit } from "@/api/useBoardEditor";
import {
  expandShips,
  type Mark,
  type ShipEntity,
} from "@/domains/battle/battleAssign";
import type { InvasionRoll, InvasionUnit } from "./useInvasion";
import styles from "./InvasionOverlay.module.css";

/** Wygląd gracza po kluczu tożsamości: nazwa, alias koloru i składowe RGB (spacje!). */
export function usePlayerLook() {
  const gameData = useGameData();
  return (key: string) => {
    const player = gameData?.playerData?.find((p) => p.faction === key);
    const rgb = player?.color ? resolvePrimaryRgb(player.color) : undefined;
    return {
      name: player ? getPlayerFactionDisplayName(player) : key,
      colorAlias: getColorAlias(player?.color),
      // `rgb(var(--x) / a)` wymaga składowych oddzielonych SPACJAMI.
      rgb: rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184",
    };
  };
}

/** Jednostki planety → egzemplarze do klikania (te same znaczniki co w oknie bitwy). */
export function expandForces(
  faction: string,
  units: InvasionUnit[],
): ShipEntity[] {
  const battleUnits: BattleUnit[] = units.map((u) => ({
    baseType: u.baseType,
    asyncId: u.asyncId,
    name: u.name,
    count: u.count,
    damaged: u.damaged,
    hitsOn: u.baseHitsOn,
    baseHitsOn: u.baseHitsOn,
    modifier: 0,
    dicePerUnit: 1,
    totalDice: u.count,
    expectedHits: 0,
    sustain: u.sustain,
    sustainable: u.sustain ? u.count - u.damaged : 0,
    afbHitsOn: null,
    afbDice: 0,
  }));
  const side: BattleSide = {
    faction,
    playerId: faction,
    role: "defender",
    units: battleUnits,
    unitCount: units.reduce((n, u) => n + u.count, 0),
    totalDice: 0,
    expectedHits: 0,
    hp: 0,
  };
  return expandShips(side);
}

/** Pojedyncza jednostka naziemna: sprite + znacznik straty, opcjonalnie klikalna. */
export function GroundToken({
  ship,
  colorAlias,
  faction,
  mark,
  onClick,
}: {
  ship: ShipEntity;
  colorAlias: string;
  faction: string;
  mark?: Mark;
  onClick?: () => void;
}) {
  const body = (
    <>
      <span className={styles.tokenSprite}>
        <Unit
          unitType={ship.asyncId}
          colorAlias={colorAlias}
          faction={faction}
          scaleSprite
        />
      </span>
      {ship.unit.sustain && (
        <span
          className={styles.tokenHp}
          data-damaged={ship.damaged || undefined}
          aria-label={ship.damaged ? "damaged" : "ready"}
        />
      )}
      {mark && (
        <span className={styles.tokenMark} data-mark={mark}>
          {(mark === "sustain" || mark === "both") && (
            <IconShieldHalfFilled size={11} />
          )}
          {(mark === "destroy" || mark === "both") && <IconSkull size={11} />}
        </span>
      )}
    </>
  );
  const title = `${ship.name}${ship.damaged ? " (damaged)" : ""}`;
  if (onClick) {
    return (
      <button
        type="button"
        className={styles.token}
        data-selectable
        data-mark={mark}
        onClick={onClick}
        title={`${title} — click to ${ship.canSustain ? "use Sustain Damage / destroy" : "destroy"}`}
        aria-pressed={mark !== undefined}
      >
        {body}
      </button>
    );
  }
  return (
    <span
      className={styles.token}
      title={title}
    >
      {body}
    </span>
  );
}

/**
 * Kostki d10 z podświetleniem trafień (wynik ≥ próg). Modyfikator celu (Antimass Deflectors: -1)
 * pokazuje surowy rzut i wynik po modyfikatorze; kość z Plasma Scoring ma osobny znacznik.
 */
export function DiceRow({ roll }: { roll: InvasionRoll }) {
  const modifier = roll.modifier ?? 0;
  const sign = modifier > 0 ? "+" : "\u2212";
  return (
    <div className={styles.rollRow}>
      <span className={styles.rollLabel}>
        {roll.count > 0 ? `${roll.count}× ` : ""}
        {roll.name} <small>{roll.hitsOn}+</small>
        {modifier !== 0 && (
          <b className={styles.rollTag} data-tone="debuff">
            {sign}
            {Math.abs(modifier)} to each die (Antimass Deflectors)
          </b>
        )}
        {(roll.extraDice ?? 0) > 0 && (
          <b className={styles.rollTag} data-tone="buff">
            +{roll.extraDice} die (Plasma Scoring)
          </b>
        )}
      </span>
      <span className={styles.dice}>
        {roll.dice.map((d, i) => {
          const result = d + modifier;
          return (
            <i
              key={i}
              className={styles.die}
              data-hit={result >= roll.hitsOn || undefined}
              style={{ "--i": i } as CSSProperties}
              title={
                modifier !== 0
                  ? `Rolled ${d}, ${sign}${Math.abs(modifier)} = ${result}`
                  : undefined
              }
            >
              {d}
              {modifier !== 0 && <small className={styles.dieMod}>{"\u2192"}{result}</small>}
            </i>
          );
        })}
      </span>
      <b className={styles.rollHits} data-zero={roll.hits === 0 || undefined}>
        {roll.hits} hit{roll.hits === 1 ? "" : "s"}
      </b>
    </div>
  );
}
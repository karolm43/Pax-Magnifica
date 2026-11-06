import type { CSSProperties } from "react";
import {
  IconBolt,
  IconCheck,
  IconDice5,
  IconFlag,
  IconTargetArrow,
  IconTrophy,
  IconWand,
} from "@tabler/icons-react";
import type {
  BattleLogEntry,
  BattleRoll,
  BattleView,
} from "@/api/useBoardEditor";
import styles from "./BattleOverlay.module.css";

type Step = NonNullable<BattleView["step"]>;

function steps(view: BattleView): { key: Step; label: string }[] {
  const list: { key: Step; label: string }[] = [];
  if (view.kind === "space" && view.round === 1 && hasAfbHistoryOrStep(view)) {
    list.push({ key: "AFB", label: "Barrage" });
  }
  list.push(
    { key: "ROLL", label: "Roll" },
    { key: "ASSIGN", label: "Assign hits" },
  );
  return list;
}

function hasAfbHistoryOrStep(view: BattleView): boolean {
  return (
    view.step === "AFB" ||
    view.log.some((e) => e.phase === "AFB" && e.round === 1)
  );
}

function DiceGroup({ rolls }: { rolls: BattleRoll[] }) {
  if (rolls.length === 0) return <span className={styles.noDice}>No dice</span>;
  return (
    <div className={styles.diceGroup}>
      {rolls.map((roll, ri) => (
        <div key={`${roll.baseType}-${ri}`} className={styles.diceLine}>
          <span className={styles.diceUnit}>
            {roll.name}{" "}
            <small>
              {roll.hitsOn}+{roll.modifier > 0 ? ` (+${roll.modifier})` : ""}
            </small>
          </span>
          <span className={styles.diceRow}>
            {roll.dice.map((value, di) => {
              const hit = value + roll.modifier >= roll.hitsOn;
              return (
                <span
                  key={di}
                  className={styles.die}
                  data-hit={hit || undefined}
                  style={{ "--i": ri * 5 + di } as CSSProperties}
                  title={hit ? "Hit" : "Miss"}
                >
                  {value}
                </span>
              );
            })}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Taca z ostatnią salwą obu stron: kości, próg, trafienia. */
function LastVolley({
  entry,
  attacker,
  defender,
  nameOf,
}: {
  entry: BattleLogEntry;
  attacker: string;
  defender: string;
  nameOf: (key: string) => string;
}) {
  return (
    <section className={styles.volley} aria-label="Last volley">
      <header className={styles.volleyHead}>
        <IconDice5 size={14} aria-hidden="true" />
        {entry.phase === "AFB"
          ? "Anti-Fighter Barrage"
          : `Round ${entry.round} — combat rolls`}
      </header>
      {[attacker, defender].map((key) => (
        <div key={key} className={styles.volleySide}>
          <div className={styles.volleyWho}>
            <b>{nameOf(key)}</b>
            <span
              className={styles.hitPill}
              data-hits={(entry.hits[key] ?? 0) > 0 || undefined}
            >
              {entry.hits[key] ?? 0} hit
              {(entry.hits[key] ?? 0) === 1 ? "" : "s"}
            </span>
          </div>
          <DiceGroup rolls={entry.rolls[key] ?? []} />
        </div>
      ))}
    </section>
  );
}

/**
 * Środek pola bitwy: tor kroków, główna akcja bieżącego kroku, przypisanie strat
 * (licznik + Auto/Clear/Confirm), ostatnia salwa oraz ekran wyniku.
 */
export function BattleCenter({
  view,
  nameOf,
  busy,
  absorbed,
  onAfb,
  onRoll,
  onAuto,
  onClearMarks,
  onConfirmAssign,
  onClose,
}: {
  view: BattleView;
  nameOf: (key: string) => string;
  busy: boolean;
  absorbed: number;
  onAfb: () => void;
  onRoll: () => void;
  onAuto: () => void;
  onClearMarks: () => void;
  onConfirmAssign: () => void;
  onClose: () => void;
}) {
  const attacker = view.attacker?.faction ?? "";
  const defender = view.defender?.faction ?? "";
  const step = view.step;
  const last = view.log.length > 0 ? view.log[view.log.length - 1] : null;
  const assigning = view.assigning;
  const required = assigning ? (view.required[assigning] ?? 0) : 0;
  const ready = assigning !== null && absorbed === required;

  return (
    <div className={styles.center}>
      <div className={styles.roundBadge}>
        <small>
          {view.kind === "ground" ? "Ground combat" : "Space combat"}
        </small>
        <b>Round {view.round}</b>
      </div>

      {step !== "DONE" && (
        <ol className={styles.track} aria-label="Combat steps">
          {steps(view).map((s) => (
            <li key={s.key} data-now={s.key === step || undefined}>
              {s.label}
            </li>
          ))}
        </ol>
      )}

      {view.nebula && (
        <p className={styles.notice}>
          Nebula: the defender adds +1 to each combat roll.
        </p>
      )}

      {step === "AFB" && (
        <div className={styles.actionCard}>
          <p>
            Before the first round, units with <b>Anti-Fighter Barrage</b> fire
            at enemy fighters. Both sides roll at once; Sustain Damage cannot
            cancel these hits.
          </p>
          <button
            type="button"
            className={styles.primary}
            disabled={busy}
            onClick={onAfb}
          >
            <IconTargetArrow size={17} aria-hidden="true" /> Fire barrage
          </button>
        </div>
      )}

      {step === "ROLL" && (
        <div className={styles.actionCard}>
          <p>
            {nameOf(attacker)} rolls first, then {nameOf(defender)}. Each die at
            or above the unit's combat value is a hit.
          </p>
          <button
            type="button"
            className={styles.primary}
            disabled={busy}
            onClick={onRoll}
          >
            <IconBolt size={17} aria-hidden="true" /> Roll combat dice
          </button>
        </div>
      )}

      {step === "ASSIGN" && assigning && (
        <div className={styles.actionCard} data-assign>
          <p>
            <b>{nameOf(assigning)}</b> covers <b>{required}</b> hit
            {required === 1 ? "" : "s"}. Click your ships:{" "}
            <span className={styles.legendShield}>shield</span> = Sustain Damage
            (cancels a hit), <span className={styles.legendSkull}>skull</span> =
            destroyed.
          </p>
          <div className={styles.assignMeter} data-ready={ready || undefined}>
            <span
              style={{
                width: `${required ? (absorbed / required) * 100 : 0}%`,
              }}
            />
            <b>
              {absorbed} / {required}
            </b>
          </div>
          <div className={styles.assignBtns}>
            <button
              type="button"
              className={styles.ghost}
              disabled={busy}
              onClick={onAuto}
            >
              <IconWand size={15} aria-hidden="true" /> Auto
            </button>
            <button
              type="button"
              className={styles.ghost}
              disabled={busy || absorbed === 0}
              onClick={onClearMarks}
            >
              Clear
            </button>
            <button
              type="button"
              className={styles.primary}
              disabled={busy || !ready}
              onClick={onConfirmAssign}
            >
              <IconCheck size={16} aria-hidden="true" /> Confirm losses
            </button>
          </div>
        </div>
      )}

      {step === "DONE" && (
        <div className={styles.result} data-outcome={view.outcome ?? undefined}>
          {view.outcome === "winner" && view.winner ? (
            <>
              <IconTrophy size={34} aria-hidden="true" />
              <small>Victory</small>
              <b>{nameOf(view.winner)}</b>
              <span>
                wins the {view.kind === "ground" ? "ground" : "space"} combat
              </span>
            </>
          ) : (
            <>
              <IconFlag size={34} aria-hidden="true" />
              <b>Draw</b>
              <span>No units remain on either side</span>
            </>
          )}
          <button
            type="button"
            className={styles.primary}
            disabled={busy}
            onClick={onClose}
          >
            Close battle
          </button>
        </div>
      )}

      {last && (
        <LastVolley
          entry={last}
          attacker={attacker}
          defender={defender}
          nameOf={nameOf}
        />
      )}
    </div>
  );
}

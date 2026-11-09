import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  IconBolt,
  IconCheck,
  IconDice5,
  IconArrowBackUp,
  IconFlag,
  IconRun,
  IconShield,
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
  // Walka kosmiczna: Announce Retreats przed rzutami i Retreat po stratach (RULES.md 39.5).
  if (view.kind === "space") list.push({ key: "ANNOUNCE", label: "Retreat?" });
  list.push(
    { key: "ROLL", label: "Roll" },
    { key: "ASSIGN", label: "Assign hits" },
  );
  if (
    view.kind === "space" &&
    (view.retreating.length > 0 || view.step === "RETREAT")
  ) {
    list.push({ key: "RETREAT", label: "Retreat" });
  }
  return list;
}

function hasAfbHistoryOrStep(view: BattleView): boolean {
  return (
    view.step === "AFB" ||
    view.log.some((e) => e.phase === "AFB" && e.round === 1)
  );
}

/** Po tylu ms przytrzymania „Roll" zaczyna się pula (krótsze kliknięcie = zwykły rzut). */
const HOLD_MS = 240;

export type HoldState = "start" | "fire" | "cancel";

/**
 * Przycisk rzutu kośćmi. Kliknięcie rzuca od razu; PRZYTRZYMANIE zbiera kości obu stron w
 * puli (widać, ile ich jest) i dopiero puszczenie przycisku nad nim rzuca. Puszczenie poza
 * przyciskiem anuluje pulę bez rzutu.
 */
function HoldRollButton({
  disabled,
  onFire,
  onHold,
  children,
}: {
  disabled: boolean;
  onFire: () => void;
  onHold: (state: HoldState) => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const [holding, setHolding] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const active = useRef(false);
  const suppressClick = useRef(false);
  const stop = useRef<(() => void) | null>(null);

  // Odpięcie nasłuchu i pula przy odmontowaniu / zablokowaniu przycisku w trakcie przytrzymania.
  useEffect(
    () => () => {
      window.clearTimeout(timer.current);
      stop.current?.();
      if (active.current) onHold("cancel");
    },
    [],
  );

  const press = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (disabled || e.button !== 0) return;
    suppressClick.current = false;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      active.current = true;
      setHolding(true);
      onHold("start");
    }, HOLD_MS);
    const release = (ev: PointerEvent) => {
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
      stop.current = null;
      window.clearTimeout(timer.current);
      if (!active.current) return; // krótkie kliknięcie obsłuży onClick
      active.current = false;
      setHolding(false);
      const inside =
        ev.type === "pointerup" &&
        ref.current?.contains(ev.target as Node) === true;
      suppressClick.current = inside;
      onHold(inside ? "fire" : "cancel");
      if (inside) onFire();
    };
    stop.current = () => {
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
    };
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
  };

  return (
    <>
      <button
        ref={ref}
        type="button"
        className={`${styles.primary} ${styles.holdBtn}`}
        data-holding={holding || undefined}
        disabled={disabled}
        onPointerDown={press}
        onClick={() => {
          if (suppressClick.current) {
            suppressClick.current = false;
            return;
          }
          onFire();
        }}
      >
        {children}
      </button>
      <small className={styles.holdHint}>
        Tap to roll · hold to shake the dice, release to throw
      </small>
    </>
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
  rolling,
}: {
  entry: BattleLogEntry;
  attacker: string;
  defender: string;
  nameOf: (key: string) => string;
  /** Kości jeszcze toczą się po stole — wynik w panelu czeka na odsłonięcie. */
  rolling: boolean;
}) {
  return (
    <section
      className={styles.volley}
      aria-label="Last volley"
      data-rolling={rolling || undefined}
    >
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
  onAnnounce,
  onRetreat,
  systemLabel,
  rolling,
  onHold,
}: {
  onHold: (state: HoldState) => void;
  view: BattleView;
  nameOf: (key: string) => string;
  busy: boolean;
  /** Trwa rzut kośćmi na stole (panel strat czeka, wynik w tacy ukryty). */
  rolling: boolean;
  absorbed: number;
  onAfb: () => void;
  onRoll: () => void;
  onAuto: () => void;
  onClearMarks: () => void;
  onConfirmAssign: () => void;
  onClose: () => void;
  onAnnounce: (announce: boolean) => void;
  onRetreat: (destination: string) => void;
  systemLabel: (position: string) => string;
}) {
  const attacker = view.attacker?.faction ?? "";
  const defender = view.defender?.faction ?? "";
  const step = view.step;
  // Taca kości: ostatnia SALWA (wpis odwrotu nie ma rzutów).
  const last =
    [...view.log].reverse().find((e) => e.phase !== "RETREAT") ?? null;
  const announcing = view.announcing;
  const announceOptions = announcing
    ? (view.retreatOptions[announcing] ?? [])
    : [];
  const retreater = view.retreating[0] ?? null;
  const retreatOptions = retreater
    ? (view.retreatOptions[retreater] ?? [])
    : [];
  const retreatedEntries = Object.entries(view.retreated);
  const assigning = view.assigning;
  const required = assigning ? (view.required[assigning] ?? 0) : 0;
  const ready = assigning !== null && absorbed === required;

  return (
    <div className={styles.center} data-rolling={rolling || undefined}>
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
          <HoldRollButton disabled={busy} onFire={onAfb} onHold={onHold}>
            <IconTargetArrow size={17} aria-hidden="true" /> Fire barrage
          </HoldRollButton>
        </div>
      )}

      {step === "ANNOUNCE" && announcing && (
        <div className={styles.actionCard} data-retreat>
          <p>
            <b>{nameOf(announcing)}</b> may announce a retreat. Ships still
            fight this round and withdraw after losses are assigned.
            {announcing === defender &&
              " If the defender retreats, the attacker cannot retreat this round."}
          </p>
          <p className={styles.retreatTargets}>
            Can withdraw to:{" "}
            {announceOptions.map((o) => systemLabel(o.position)).join(", ")}
          </p>
          <div className={styles.retreatBtns}>
            <button
              type="button"
              className={styles.ghost}
              disabled={busy}
              onClick={() => onAnnounce(false)}
            >
              <IconShield size={16} aria-hidden="true" /> Stand and fight
            </button>
            <button
              type="button"
              className={styles.retreatBtn}
              disabled={busy}
              onClick={() => onAnnounce(true)}
            >
              <IconRun size={16} aria-hidden="true" /> Announce retreat
            </button>
          </div>
        </div>
      )}

      {step === "RETREAT" && retreater && (
        <div className={styles.actionCard} data-retreat>
          <p>
            <b>{nameOf(retreater)}</b> retreats. All ships with movement
            withdraw to one adjacent system and place a command token there.
            Fighters and ground forces in space that cannot be carried are lost.
          </p>
          <div className={styles.retreatDest}>
            {retreatOptions.map((o) => (
              <button
                key={o.position}
                type="button"
                className={styles.retreatBtn}
                disabled={busy}
                onClick={() => onRetreat(o.position)}
              >
                <IconArrowBackUp size={16} aria-hidden="true" />{" "}
                {systemLabel(o.position)}
              </button>
            ))}
          </div>
        </div>
      )}

      {step === "ROLL" && view.retreating.length > 0 && (
        <p className={styles.retreatNote}>
          <IconRun size={14} aria-hidden="true" /> {nameOf(view.retreating[0])}{" "}
          will retreat after this round.
        </p>
      )}

      {step === "ROLL" && (
        <div className={styles.actionCard}>
          <p>
            {nameOf(attacker)} rolls first, then {nameOf(defender)}. Each die at
            or above the unit's combat value is a hit.
          </p>
          <HoldRollButton disabled={busy} onFire={onRoll} onHold={onHold}>
            <IconBolt size={17} aria-hidden="true" /> Roll combat dice
          </HoldRollButton>
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
                {retreatedEntries.length > 0
                  ? "holds the system"
                  : `wins the ${view.kind === "ground" ? "ground" : "space"} combat`}
              </span>
              {retreatedEntries.map(([key, pos]) => (
                <span key={key} className={styles.retreatResult}>
                  <IconArrowBackUp size={14} aria-hidden="true" /> {nameOf(key)}{" "}
                  withdrew to {systemLabel(pos)}
                </span>
              ))}
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
          rolling={rolling}
        />
      )}
    </div>
  );
}

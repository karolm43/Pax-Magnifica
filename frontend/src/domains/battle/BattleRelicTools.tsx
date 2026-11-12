import { useState } from "react";
import { IconDiamond, IconDice5, IconMinus, IconPlus } from "@tabler/icons-react";
import { useBoardEditor, type BattleAbilityTool, type BattleRoll, type BattleView } from "@/api/useBoardEditor";
import styles from "./BattleRelicTools.module.css";

/** Klucz kości: "<indeks wpisu rzutu>:<indeks kości>" (ten sam format co w silniku). */
type DieKey = string;

/** Rząd kości jednego rzutu: klik zaznacza/odznacza kość do przerzutu. */
function DiceRow({
  entries,
  picked,
  disabled,
  onToggle,
}: {
  entries: BattleRoll[];
  picked: Set<DieKey>;
  disabled: boolean;
  onToggle: (key: DieKey) => void;
}) {
  return (
    <div className={styles.rows}>
      {entries.map((entry, entryIndex) => (
        <div key={`${entry.baseType}-${entryIndex}`} className={styles.row}>
          <span className={styles.unit}>
            {entry.name}
            <small>hits on {entry.hitsOn}</small>
          </span>
          <span className={styles.dice}>
            {entry.dice.map((value, dieIndex) => {
              const key = `${entryIndex}:${dieIndex}`;
              const hit = value >= entry.hitsOn;
              return (
                <button
                  key={key}
                  type="button"
                  className={styles.die}
                  data-hit={hit || undefined}
                  aria-pressed={picked.has(key)}
                  aria-label={`${entry.name}: ${value} (${hit ? "hit" : "miss"})`}
                  disabled={disabled}
                  onClick={() => onToggle(key)}
                >
                  {value}
                </button>
              );
            })}
          </span>
        </div>
      ))}
    </div>
  );
}

function useDicePicker() {
  const [picked, setPicked] = useState<Set<DieKey>>(new Set());
  const toggle = (key: DieKey) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  return { picked, toggle, clear: () => setPicked(new Set()), set: setPicked };
}

/** Zdolność frakcji (np. Munitions Reserves): zaznacz kości i przerzuć w jednym kliknięciu. */
function AbilityReroll({
  tool,
  view,
  nameOf,
  busy,
}: {
  tool: BattleAbilityTool;
  view: BattleView;
  nameOf: (key: string) => string;
  busy: boolean;
}) {
  const { playFactionComponent } = useBoardEditor();
  const { picked, toggle, clear, set } = useDicePicker();
  const [working, setWorking] = useState(false);
  const entries = view.rolls[tool.faction] ?? [];
  const misses = entries.flatMap((entry, e) =>
    entry.dice.flatMap((value, d) => (value < entry.hitsOn ? [`${e}:${d}`] : [])),
  );
  const disabled = busy || working;
  const count = picked.size;
  const valid = count >= Math.max(1, tool.min) && count <= tool.max;

  const reroll = async () => {
    setWorking(true);
    try {
      await playFactionComponent(tool.playerId, tool.kind, tool.componentId, { dice: [...picked] });
      clear();
    } catch {
      // Powód (422) pokazał komunikat; wybór zostaje do poprawki.
    } finally {
      setWorking(false);
    }
  };

  return (
    <section className={styles.tool} aria-label={`${tool.name}: reroll dice`}>
      <header className={styles.toolHead}>
        <IconDice5 size={15} aria-hidden="true" />
        <b>{tool.name}</b>
        <span className={styles.owner}>{nameOf(tool.faction)}</span>
      </header>
      <p className={styles.text}>{tool.text}</p>
      <DiceRow entries={entries} picked={picked} disabled={disabled} onToggle={toggle} />
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.ghost}
          disabled={disabled || misses.length === 0}
          onClick={() => set(new Set(misses.slice(0, tool.max)))}
        >
          Select misses ({misses.length})
        </button>
        <button
          type="button"
          className={styles.primary}
          disabled={disabled || !valid}
          onClick={() => void reroll()}
        >
          Reroll {count} {count === 1 ? "die" : "dice"}
        </button>
      </div>
    </section>
  );
}

/**
 * Narzędzia nad rzutami rundy, widoczne po rzucie, zanim ktokolwiek przypisze straty:
 * - zdolności frakcji z oknem użycia (np. **Munitions Reserves**: po opłaceniu 2 TG na starcie
 *   rundy gracz zaznacza kości i przerzuca je tutaj, bez szukania zdolności w menu akcji);
 * - **The Crown of Thalnos** (RULES.md 59): przerzut z +1; jednostka bez trafienia po przerzucie
 *   ginie;
 * - **Heart of Ixth**: wyczerp kartę i zmień wynik jednej kości (własnej lub przeciwnika) o ±1.
 * Silnik liczy trafienia od nowa i odbudowuje kolejkę przypisania strat.
 */
export function BattleRelicTools({
  view,
  nameOf,
  busy,
}: {
  view: BattleView;
  nameOf: (key: string) => string;
  busy: boolean;
}) {
  const { battleRelicReroll, battleRelicAdjust } = useBoardEditor();
  const thalnos = useDicePicker();
  const [working, setWorking] = useState(false);
  const tools = view.relicTools ?? [];
  const abilities = view.abilityTools ?? [];
  if (view.step !== "ASSIGN" || (tools.length === 0 && abilities.length === 0)) return null;

  const rerollers = tools.filter((t) => t.tool === "reroll").map((t) => t.faction);
  const adjusters = tools.filter((t) => t.tool === "adjust").map((t) => t.faction);
  const disabled = busy || working;

  const run = async (action: () => Promise<void>) => {
    setWorking(true);
    try {
      await action();
      thalnos.clear();
    } finally {
      setWorking(false);
    }
  };

  const reroll = (faction: string) => {
    const byEntry = new Map<number, number[]>();
    for (const key of thalnos.picked) {
      const [entry, die] = key.split(":").map(Number);
      byEntry.set(entry, [...(byEntry.get(entry) ?? []), die]);
    }
    const picks = [...byEntry].map(([entry, dice]) => ({ entry, dice }));
    void run(() => battleRelicReroll(faction, picks));
  };

  return (
    <div className={styles.wrap} aria-label="Dice tools">
      <p className={styles.lead}>Before hits are assigned you may change the dice:</p>

      {abilities.map((tool) => (
        <AbilityReroll
          key={`${tool.faction}-${tool.kind}-${tool.componentId}`}
          tool={tool}
          view={view}
          nameOf={nameOf}
          busy={busy}
        />
      ))}

      {rerollers.map((faction) => (
        <section key={`reroll-${faction}`} className={styles.tool} data-tone="relic">
          <header className={styles.toolHead}>
            <IconDiamond size={15} aria-hidden="true" />
            <b>The Crown of Thalnos</b>
            <span className={styles.owner}>{nameOf(faction)}</span>
          </header>
          <p className={styles.text}>
            Reroll any dice with +1 to the result; a unit that rerolls and has no hit is destroyed.
          </p>
          <DiceRow
            entries={view.rolls[faction] ?? []}
            picked={thalnos.picked}
            disabled={disabled}
            onToggle={thalnos.toggle}
          />
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.primary}
              disabled={disabled || thalnos.picked.size === 0}
              onClick={() => reroll(faction)}
            >
              Reroll {thalnos.picked.size} {thalnos.picked.size === 1 ? "die" : "dice"}
            </button>
          </div>
        </section>
      ))}

      {adjusters.map((faction) => (
        <section key={`adjust-${faction}`} className={styles.tool} data-tone="relic">
          <header className={styles.toolHead}>
            <IconDiamond size={15} aria-hidden="true" />
            <b>Heart of Ixth</b>
            <span className={styles.owner}>{nameOf(faction)}</span>
          </header>
          <p className={styles.text}>Exhaust to change one die (yours or your opponent&apos;s) by 1.</p>
          <div className={styles.rows}>
            {Object.entries(view.rolls).flatMap(([target, entries]) =>
              entries.map((entry, entryIndex) => (
                <div key={`${target}-${entryIndex}`} className={styles.row}>
                  <span className={styles.unit}>
                    {entry.name}
                    <small>{nameOf(target)}</small>
                  </span>
                  <span className={styles.dice}>
                    {entry.dice.map((value, dieIndex) => (
                      <span key={dieIndex} className={styles.adjust}>
                        <button
                          type="button"
                          disabled={disabled || value <= 1}
                          aria-label={`Lower die ${value} by 1`}
                          onClick={() =>
                            void run(() =>
                              battleRelicAdjust({ faction, target, entry: entryIndex, die: dieIndex, delta: -1 }),
                            )
                          }
                        >
                          <IconMinus size={11} />
                        </button>
                        <b className={styles.die} data-hit={value >= entry.hitsOn || undefined}>
                          {value}
                        </b>
                        <button
                          type="button"
                          disabled={disabled || value >= 10}
                          aria-label={`Raise die ${value} by 1`}
                          onClick={() =>
                            void run(() =>
                              battleRelicAdjust({ faction, target, entry: entryIndex, die: dieIndex, delta: 1 }),
                            )
                          }
                        >
                          <IconPlus size={11} />
                        </button>
                      </span>
                    ))}
                  </span>
                </div>
              )),
            )}
          </div>
        </section>
      ))}
    </div>
  );
}

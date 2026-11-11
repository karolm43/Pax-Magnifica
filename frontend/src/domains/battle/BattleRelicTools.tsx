import { useState } from "react";
import { IconDiamond } from "@tabler/icons-react";
import { useBoardEditor, type BattleView } from "@/api/useBoardEditor";

/**
 * Relikty nad rzutami rundy (RULES.md 59), widoczne po rzucie, zanim ktokolwiek przypisze straty:
 * - **The Crown of Thalnos**: wybierz kości swojego rzutu i przerzuć je z +1 do wyniku; jednostka,
 *   która przerzucała kości i nie ma po nich trafienia, ginie;
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
  // Zaznaczone kości do przerzutu: "<entry>:<die>".
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [working, setWorking] = useState(false);
  const tools = view.relicTools ?? [];
  if (tools.length === 0 || view.step !== "ASSIGN") return null;

  const rerollers = tools.filter((t) => t.tool === "reroll").map((t) => t.faction);
  const adjusters = tools.filter((t) => t.tool === "adjust").map((t) => t.faction);
  const disabled = busy || working;

  const run = async (action: () => Promise<void>) => {
    setWorking(true);
    try {
      await action();
      setPicked(new Set());
    } finally {
      setWorking(false);
    }
  };

  const toggle = (key: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const reroll = (faction: string) => {
    const byEntry = new Map<number, number[]>();
    for (const key of picked) {
      const [entry, die] = key.split(":").map(Number);
      byEntry.set(entry, [...(byEntry.get(entry) ?? []), die]);
    }
    const picks = [...byEntry].map(([entry, dice]) => ({ entry, dice }));
    void run(() => battleRelicReroll(faction, picks));
  };

  return (
    <div
      style={{
        border: "1px solid rgba(234, 179, 8, 0.45)",
        background: "rgba(234, 179, 8, 0.08)",
        borderRadius: 10,
        padding: "8px 10px",
        display: "grid",
        gap: 8,
        fontSize: 12,
      }}
      aria-label="Relic dice tools"
    >
      <b style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <IconDiamond size={14} aria-hidden="true" /> Relics: change the dice before hits are assigned
      </b>

      {rerollers.map((faction) => (
        <div key={`reroll-${faction}`} style={{ display: "grid", gap: 4 }}>
          <span>
            <b>{nameOf(faction)}</b> - The Crown of Thalnos: pick dice to reroll (+1 to the
            result; a unit that rerolls and has no hit is destroyed).
          </span>
          {(view.rolls[faction] ?? []).map((entry, entryIndex) => (
            <div key={`${entry.baseType}-${entryIndex}`} style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              <span>{entry.name}:</span>
              {entry.dice.map((value, dieIndex) => {
                const key = `${entryIndex}:${dieIndex}`;
                return (
                  <button
                    key={key}
                    type="button"
                    disabled={disabled}
                    aria-pressed={picked.has(key)}
                    onClick={() => toggle(key)}
                    style={{
                      minWidth: 26,
                      fontWeight: picked.has(key) ? 700 : 400,
                      outline: picked.has(key) ? "2px solid #eab308" : "1px solid #888",
                    }}
                  >
                    {value}
                  </button>
                );
              })}
            </div>
          ))}
          <button type="button" disabled={disabled || picked.size === 0} onClick={() => reroll(faction)}>
            Reroll {picked.size} {picked.size === 1 ? "die" : "dice"}
          </button>
        </div>
      ))}

      {adjusters.map((faction) => (
        <div key={`adjust-${faction}`} style={{ display: "grid", gap: 4 }}>
          <span>
            <b>{nameOf(faction)}</b> - Heart of Ixth: exhaust to change one die by 1.
          </span>
          {Object.entries(view.rolls).flatMap(([target, entries]) =>
            entries.map((entry, entryIndex) => (
              <div key={`${target}-${entryIndex}`} style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <span>
                  {nameOf(target)} - {entry.name}:
                </span>
                {entry.dice.map((value, dieIndex) => (
                  <span key={dieIndex} style={{ display: "inline-flex", gap: 2 }}>
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
                      -
                    </button>
                    <b>{value}</b>
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
                      +
                    </button>
                  </span>
                ))}
              </div>
            )),
          )}
        </div>
      ))}
    </div>
  );
}

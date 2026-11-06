import { useState } from "react";
import { IconBolt, IconEye, IconEyeOff, IconHandStop } from "@tabler/icons-react";
import {
  useBoardEditor,
  useSpaceCannon,
  type SpaceCannonSide,
} from "@/api/useBoardEditor";
import { useSettingsStore } from "@/state/appStore";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { Unit } from "@/shared/ui/Unit";
import {
  AssignHits,
  DiceRolls,
  SpaceCannonLog,
  usePlayerLookup,
} from "./SpaceCannonParts";
import styles from "./SpaceCannonStepPanel.module.css";

type Lookup = ReturnType<typeof usePlayerLookup>;

/**
 * Karta tury bieżącego strzelca: jego jednostki z Space Cannon (próg, kości, zasięg),
 * wybór celu (aktywny gracz wybiera; nieaktywny celuje w aktywnego) oraz Fire / Pass.
 * Stan wyboru celu jest lokalny — rodzic montuje kartę z ``key`` bieżącego gracza.
 */
function TurnCard({
  side,
  lookup,
  busy,
  onFire,
  onPass,
}: {
  side: SpaceCannonSide;
  lookup: Lookup;
  busy: boolean;
  onFire: (target: string) => void;
  onPass: () => void;
}) {
  const me = lookup(side.faction);
  const [target, setTarget] = useState<string | null>(
    side.targets.length === 1 ? side.targets[0] : null,
  );

  return (
    <section className={styles.turn} aria-label={`${me.name} may fire`}>
      <header className={styles.turnHead}>
        <CircularFactionIcon faction={side.faction} size={22} />
        <span className={styles.turnWho}>
          <small>Now firing</small>
          <b>{me.name}</b>
        </span>
        <span className={styles.expected} title="Dice · expected hits">
          {side.totalDice} dice · ~{side.expectedHits} hits
        </span>
      </header>

      <div className={styles.shooters}>
        {side.shooters.map((s) => (
          <div key={`${s.baseType}-${s.position}-${s.zone}`} className={styles.shooterRow}>
            <div className={styles.icon}>
              <Unit
                unitType={s.asyncId}
                colorAlias={me.colorAlias}
                faction={side.faction}
                scaleSprite
              />
            </div>
            <span className={styles.shooterName}>
              <b>{s.count}×</b> {s.name}
            </span>
            <span className={styles.shooterStat} title="Hits on X+ · dice per unit">
              {s.hitsOn}+ ×{s.dicePerUnit}
            </span>
            {s.remote && (
              <span className={styles.badge} title="Deep Space Cannon — fires from an adjacent system">
                from {s.position}
              </span>
            )}
          </div>
        ))}
      </div>

      {side.targets.length > 1 && (
        <div className={styles.targets} role="radiogroup" aria-label="Choose target">
          <small>Target</small>
          {side.targets.map((key) => (
            <button
              key={key}
              type="button"
              role="radio"
              aria-checked={target === key}
              className={styles.target}
              data-active={target === key || undefined}
              onClick={() => setTarget(key)}
            >
              <CircularFactionIcon faction={key} size={16} />
              {lookup(key).name}
            </button>
          ))}
        </div>
      )}
      {side.targets.length === 1 && (
        <p className={styles.note}>
          Target: <b>{lookup(side.targets[0]).name}</b>
          {" "}(the active player)
        </p>
      )}

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.fire}
          disabled={busy || target === null}
          onClick={() => target !== null && onFire(target)}
          title={target === null ? "Pick a target first" : "Roll Space Cannon dice"}
        >
          <IconBolt size={15} aria-hidden="true" /> Fire
        </button>
        <button type="button" className={styles.pass} disabled={busy} onClick={onPass}>
          <IconHandStop size={15} aria-hidden="true" /> Don't fire
        </button>
      </div>
    </section>
  );
}

/**
 * Krok SPACE CANNON akcji taktycznej — panel Offense (RULES.md 38). Prowadzi okno
 * czasowe: kolejka graczy (od aktywnego, zgodnie z zegarem), karta bieżącego strzelca,
 * wynik rzutu z kośćmi, przypisanie strat przez gracza-cel i dziennik. Strzelać może
 * KAŻDY gracz z Space Cannon w zasięgu, nie tylko aktywny; zasięg (Deep Space Cannon,
 * PDS II) wynika z danych i jest widoczny w soczewce mapy „Space Cannon range".
 */
export function SpaceCannonStepPanel() {
  const { data: panel } = useSpaceCannon(true);
  const { spaceCannonFire, spaceCannonPass, spaceCannonAssign } = useBoardEditor();
  const lookup = usePlayerLookup();
  const showRange = useSettingsStore((s) => s.settings.showPDSLayer);
  const toggleRange = useSettingsStore((s) => s.handlers.togglePdsMode);
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód odrzucenia (422) pokazał już panel komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  if (!panel) return <span className={styles.note}>Loading Space Cannon…</span>;

  const nameOf = (key: string) => lookup(key).name;
  const current = panel.sides.find((s) => s.faction === panel.current);
  const pending = panel.pending;
  const pendingKey = pending
    ? `${pending.roller}>${pending.target}:${pending.hits}:${panel.log.length}`
    : "";
  // Trwający rzut jest już w dzienniku (dopisany przy strzale) — nie pokazuj go dwa razy.
  const history = pending ? panel.log.slice(0, -1) : panel.log;

  return (
    <div className={styles.root}>
      <div className={styles.topBar}>
        <span className={styles.title}>Space Cannon Offense</span>
        <button
          type="button"
          className={styles.lens}
          aria-pressed={showRange}
          onClick={toggleRange}
          title="Highlight systems under Space Cannon fire (key P)"
        >
          {showRange ? <IconEyeOff size={13} /> : <IconEye size={13} />}
          Range
        </button>
      </div>

      {!panel.isOpen && !panel.resolved && (
        <p className={styles.note}>
          Nothing can fire here: no Space Cannon units in range, or no one to hit.
          Space Cannon needs units in this system, or PDS II (Deep Space Cannon)
          in an adjacent one.
        </p>
      )}
      {!panel.isOpen && panel.resolved && (
        <p className={styles.done}>Space Cannon resolved — continue with Next step.</p>
      )}

      {panel.isOpen && (
        <ol className={styles.queue} aria-label="Firing order">
          {panel.queue.map((key) => {
            const state = panel.responded.includes(key)
              ? "done"
              : key === panel.current
                ? "now"
                : "wait";
            return (
              <li key={key} className={styles.queueItem} data-state={state}>
                <CircularFactionIcon faction={key} size={18} />
                <span>{nameOf(key)}</span>
              </li>
            );
          })}
        </ol>
      )}

      {pending ? (
        <>
          <header className={styles.shotHead}>
            <span>
              <b>{nameOf(pending.roller)}</b> fires on <b>{nameOf(pending.target)}</b>
            </span>
            <span className={styles.hitCount} data-hits={pending.hits > 0 || undefined}>
              {pending.hits} hit{pending.hits === 1 ? "" : "s"}
            </span>
          </header>
          <span className={styles.beam} data-hits={pending.hits > 0 || undefined} />
          <DiceRolls rolls={pending.rolls} />
          <AssignHits
            key={pendingKey}
            pending={pending}
            ships={panel.targetShips}
            targetName={nameOf(pending.target)}
            colorAlias={lookup(pending.target).colorAlias}
            faction={pending.target}
            busy={busy}
            onConfirm={(losses) =>
              void run(() => spaceCannonAssign(pending.target, losses))
            }
          />
        </>
      ) : (
        current && (
          <TurnCard
            key={current.faction}
            side={current}
            lookup={lookup}
            busy={busy}
            onFire={(target) => void run(() => spaceCannonFire(current.faction, target))}
            onPass={() => void run(() => spaceCannonPass(current.faction))}
          />
        )
      )}

      <SpaceCannonLog log={history} nameOf={nameOf} />
    </div>
  );
}

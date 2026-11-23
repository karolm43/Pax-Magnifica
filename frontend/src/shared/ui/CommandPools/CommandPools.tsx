import { AutoButton } from "@/shared/ui/AutoButton/AutoButton";
import { Stepper } from "@/shared/ui/Stepper/Stepper";
import styles from "./CommandPools.module.css";

/** Rozdział żetonów dowodzenia: pula taktyczna, floty i strategii. */
export type PoolAlloc = { t: number; f: number; s: number };

const POOLS: { key: keyof PoolAlloc; label: string }[] = [
  { key: "t", label: "Tactic" },
  { key: "f", label: "Fleet" },
  { key: "s", label: "Strategy" },
];

/** Ile żetonów zostało do rozłożenia (ujemne = za dużo). */
export function poolsLeft(alloc: PoolAlloc, total: number): number {
  return total - (alloc.t + alloc.f + alloc.s);
}

/**
 * Trzy pule żetonów dowodzenia z licznikami − / + (wspólny `Stepper`, bez wpisywania liczb) —
 * ten sam widżet w fazie statusu (RULES.md 41), Predictive Intelligence, Leadership i Warfare.
 * „+” jest aktywny tylko, gdy zostały żetony do rozłożenia (suma zawsze ≤ ``total``).
 * ``onAuto`` dodaje „Auto” (podpowiedziany rozdział) nad pulami.
 */
export function CommandPools({
  alloc,
  total,
  disabled = false,
  onChange,
  onAuto,
  autoTitle,
  current,
}: {
  alloc: PoolAlloc;
  total: number;
  disabled?: boolean;
  onChange: (next: PoolAlloc) => void;
  onAuto?: () => void;
  autoTitle?: string;
  /** Obecny stan puli gracza (podpis „now N”). */
  current?: Partial<PoolAlloc>;
}) {
  const left = poolsLeft(alloc, total);
  return (
    <div className={styles.wrap}>
      {onAuto && <AutoButton disabled={disabled} onClick={onAuto} title={autoTitle} />}
      <div className={styles.pools} role="group" aria-label="Command token pools">
        {POOLS.map(({ key, label }) => (
          <div key={key} className={styles.pool}>
            <span>{label}</span>
            <Stepper
              bare
              label={`${label} tokens`}
              value={alloc[key]}
              max={alloc[key] + Math.max(0, left)}
              disabled={disabled}
              onChange={(next) => onChange({ ...alloc, [key]: next })}
            />
            {current?.[key] != null && <small>now {current[key]}</small>}
          </div>
        ))}
      </div>
    </div>
  );
}

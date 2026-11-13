import { IconMinus, IconPlus } from "@tabler/icons-react";
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
 * Trzy pule żetonów dowodzenia z przyciskami − / + (bez wpisywania liczb). Wspólne dla
 * fazy statusu (krok 5, RULES.md 41) i Predictive Intelligence — ten sam widżet wszędzie.
 * „+” jest aktywny tylko, gdy zostały żetony do rozłożenia (suma zawsze = ``total``).
 */
export function CommandPools({
  alloc,
  total,
  disabled = false,
  onChange,
}: {
  alloc: PoolAlloc;
  total: number;
  disabled?: boolean;
  onChange: (next: PoolAlloc) => void;
}) {
  const left = poolsLeft(alloc, total);
  return (
    <div className={styles.pools} role="group" aria-label="Command token pools">
      {POOLS.map(({ key, label }) => (
        <div key={key} className={styles.pool}>
          <span>{label}</span>
          <div>
            <button
              type="button"
              aria-label={`Fewer ${label} tokens`}
              disabled={disabled || alloc[key] <= 0}
              onClick={() => onChange({ ...alloc, [key]: alloc[key] - 1 })}
            >
              <IconMinus size={13} aria-hidden="true" />
            </button>
            <b aria-label={`${label}: ${alloc[key]}`}>{alloc[key]}</b>
            <button
              type="button"
              aria-label={`More ${label} tokens`}
              disabled={disabled || left <= 0}
              onClick={() => onChange({ ...alloc, [key]: alloc[key] + 1 })}
            >
              <IconPlus size={13} aria-hidden="true" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

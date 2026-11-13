import { IconShieldHalfFilled, IconSkull, IconTargetArrow } from "@tabler/icons-react";
import type { BattleLogEntry, BattleView } from "@/api/useBoardEditor";
import { lookupUnit } from "@/entities/lookup/units";
import { BASE_TYPE_BY_ASYNC } from "@/domains/map/components/UnitStack/cargo";
import { Unit } from "@/shared/ui/Unit";
import styles from "./BattleOverlay.module.css";

/* baseType → asyncId (odwrotność wspólnej mapy ruchu; jedno źródło tłumaczenia). */
const ASYNC_BY_BASE: Record<string, string> = Object.fromEntries(
  Object.entries(BASE_TYPE_BY_ASYNC).map(([asyncId, base]) => [base, asyncId]),
);

export type SideTotals = {
  hits: number;
  sustained: number;
  losses: Record<string, number>;
};

/** Sumy całej walki dla strony: trafienia zadane, użyte Sustain Damage, straty per typ. */
export function battleTotals(log: BattleLogEntry[], key: string): SideTotals {
  const totals: SideTotals = { hits: 0, sustained: 0, losses: {} };
  for (const entry of log) {
    totals.hits += entry.hits[key] ?? 0;
    for (const n of Object.values(entry.sustained[key] ?? {})) totals.sustained += n;
    for (const [base, n] of Object.entries(entry.losses[key] ?? {})) {
      if (n > 0) totals.losses[base] = (totals.losses[base] ?? 0) + n;
    }
  }
  return totals;
}

/**
 * Proste podsumowanie zakończonej walki (ekran wyniku): liczba rund i dla każdej strony
 * zadane trafienia, Sustain Damage oraz zniszczone jednostki (ikony jak na polu bitwy).
 */
export function BattleSummary({
  view,
  nameOf,
  colorOf,
}: {
  view: BattleView;
  nameOf: (key: string) => string;
  colorOf: (key: string) => string;
}) {
  const sides = [view.attacker?.faction, view.defender?.faction].filter(
    (k): k is string => !!k,
  );
  const rounds = view.round;
  return (
    <section className={styles.summary} aria-label="Battle summary">
      <header className={styles.summaryHead}>
        Battle summary · {rounds} round{rounds === 1 ? "" : "s"}
      </header>
      {sides.map((key) => {
        const t = battleTotals(view.log, key);
        const lost = Object.entries(t.losses);
        return (
          <div key={key} className={styles.summarySide}>
            <div className={styles.summaryWho}>
              <b>{nameOf(key)}</b>
              <span title="Hits scored">
                <IconTargetArrow size={12} aria-hidden="true" /> {t.hits}
              </span>
              {t.sustained > 0 && (
                <span title="Sustain Damage used">
                  <IconShieldHalfFilled size={12} aria-hidden="true" /> {t.sustained}
                </span>
              )}
            </div>
            {lost.length === 0 ? (
              <span className={styles.summaryNone}>No losses</span>
            ) : (
              <ul className={styles.summaryLosses} aria-label={`${nameOf(key)} losses`}>
                {lost.map(([base, n]) => {
                  const asyncId = ASYNC_BY_BASE[base] ?? base;
                  const unitName = lookupUnit(asyncId, key)?.name ?? base;
                  return (
                    <li key={base} title={`${unitName} destroyed`}>
                      <span className={styles.summaryIcon}>
                        <Unit unitType={asyncId} colorAlias={colorOf(key)} faction={key} scaleSprite />
                      </span>
                      <IconSkull size={11} aria-hidden="true" />×{n}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </section>
  );
}

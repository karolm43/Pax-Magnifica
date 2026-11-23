import { IconShieldHalfFilled, IconSkull, IconTargetArrow } from "@tabler/icons-react";
import type { BattleLogEntry, BattleView } from "@/api/useBoardEditor";
import { getGenericUnitDataByAsyncId, lookupUnit } from "@/entities/lookup/units";
import { BASE_TYPE_BY_ASYNC } from "@/domains/map/components/UnitStack/cargo";
import { Unit } from "@/shared/ui/Unit";
import { battleSeed, describeBattle } from "@/entities/lore/battleLore";
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

const sumLosses = (losses: Record<string, number>) =>
  Object.values(losses).reduce((a, b) => a + b, 0);

/** Pełna nazwa jednostki z typu bazowego (nigdy id AsyncTI4). */
const unitFullName = (base: string) => getGenericUnitDataByAsyncId(ASYNC_BY_BASE[base] ?? base)?.name ?? base;

/**
 * Proste podsumowanie zakończonej walki (ekran wyniku): liczba rund i dla każdej strony
 * zadane trafienia, Sustain Damage oraz zniszczone jednostki (ikony jak na polu bitwy).
 */
export function BattleSummary({
  view,
  nameOf,
  colorOf,
  where,
}: {
  view: BattleView;
  nameOf: (key: string) => string;
  colorOf: (key: string) => string;
  /** Nazwa miejsca walki (system albo planeta) do opisu fabularnego. */
  where?: string;
}) {
  const sides = [view.attacker?.faction, view.defender?.faction].filter(
    (k): k is string => !!k,
  );
  const rounds = view.round;
  const attackerKey = view.attacker?.faction;
  const defenderKey = view.defender?.faction;
  let story: ReturnType<typeof describeBattle> | null = null;
  if (attackerKey && defenderKey && where) {
    const att = battleTotals(view.log, attackerKey);
    const def = battleTotals(view.log, defenderKey);
    const attackerLost = sumLosses(att.losses);
    const defenderLost = sumLosses(def.losses);
    story = describeBattle({
      kind: view.kind ?? "space",
      where,
      attacker: nameOf(attackerKey),
      defender: nameOf(defenderKey),
      winner:
        view.outcome === "winner" && view.winner
          ? view.winner === attackerKey
            ? "attacker"
            : "defender"
          : null,
      rounds,
      attackerLost,
      defenderLost,
      attackerTypes: att.losses,
      defenderTypes: def.losses,
      typeName: unitFullName,
      seed: battleSeed(view.position, view.planet, rounds, attackerLost, defenderLost),
    });
  }
  return (
    <section className={styles.summary} aria-label="Battle summary">
      <header className={styles.summaryHead}>
        Battle summary · {rounds} round{rounds === 1 ? "" : "s"}
      </header>
      {story && (
        <p className={styles.summaryStory}>
          <b>{story.headline}.</b> {story.text}
        </p>
      )}
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

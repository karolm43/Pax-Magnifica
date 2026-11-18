import type { ReactNode } from "react";
import { IconWand } from "@tabler/icons-react";
import styles from "./ExtraDicePicker.module.css";

/** Źródło dodatkowych kości (Plasma Scoring, commander Argent, Strike Wing Ambuscade). */
export type ExtraDie = { key: string; name: string; dice: number };
/** Rzucająca grupa jednostek, której można dać kość. */
export type ExtraDiceGroup = { key: string; label: string; hitsOn: number; sub?: string };
/** Wybór per źródło: klucz grupy, ``auto`` (najcelniejsza) albo ``none`` (bez kości). */
export type ExtraDicePicks = Record<string, string>;

export const AUTO = "auto";
export const NONE = "none";

/** Domyślnie każde źródło na „Auto”. */
export function defaultPicks(sources: ExtraDie[]): ExtraDicePicks {
  return Object.fromEntries(sources.map((s) => [s.key, AUTO]));
}

/** Ile dodatkowych kości dostaje każda grupa (lustro ``core/extra_dice.assign``). */
export function extraByGroup(
  sources: ExtraDie[],
  groups: ExtraDiceGroup[],
  picks: ExtraDicePicks,
): Record<string, number> {
  const best = [...groups].sort((a, b) => a.hitsOn - b.hitsOn || a.key.localeCompare(b.key))[0];
  const out: Record<string, number> = {};
  for (const source of sources) {
    const pick = picks[source.key] ?? NONE;
    const target = pick === AUTO ? best?.key : pick === NONE ? undefined : pick;
    if (target && groups.some((g) => g.key === target)) {
      out[target] = (out[target] ?? 0) + source.dice;
    }
  }
  return out;
}

const dieWord = (n: number) => (n === 1 ? "die" : "dice");

/**
 * Dodatkowe kości przy rzucie zdolności jednostek: KAŻDE źródło gracz przypisuje osobno
 * (decyzja użytkownika 2026-11-18) — „Auto” (najcelniejsza grupa), konkretna grupa albo bez kości.
 * Ten sam komponent w Space Cannon, Bombardment, Space Cannon Defense i AFB.
 */
export function ExtraDicePicker({
  sources,
  groups,
  value,
  onChange,
  disabled,
}: {
  sources: ExtraDie[];
  groups: ExtraDiceGroup[];
  value: ExtraDicePicks;
  onChange: (next: ExtraDicePicks) => void;
  disabled?: boolean;
}) {
  if (sources.length === 0 || groups.length === 0) return null;
  const set = (source: string, pick: string) => onChange({ ...value, [source]: pick });
  return (
    <div className={styles.picker}>
      {sources.map((source) => {
        const pick = value[source.key] ?? NONE;
        const option = (key: string, content: ReactNode) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={pick === key}
            className={styles.option}
            data-active={pick === key || undefined}
            disabled={disabled}
            onClick={() => set(source.key, key)}
          >
            {content}
          </button>
        );
        return (
          <div
            key={source.key}
            className={styles.source}
            role="radiogroup"
            aria-label={`${source.name}: extra ${dieWord(source.dice)}`}
          >
            <small>
              <b>{source.name}</b>: 1 unit may roll {source.dice} additional {dieWord(source.dice)}.
            </small>
            <div className={styles.options}>
              {option(
                AUTO,
                <>
                  <IconWand size={13} aria-hidden="true" /> Auto
                </>,
              )}
              {groups.map((g) =>
                option(
                  g.key,
                  <>
                    {g.label} <small>({g.hitsOn}+{g.sub ? ` · ${g.sub}` : ""})</small>
                  </>,
                ),
              )}
              {option(NONE, "No extra die")}
            </div>
          </div>
        );
      })}
    </div>
  );
}

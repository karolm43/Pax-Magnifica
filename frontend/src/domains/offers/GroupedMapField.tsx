import { useMemo, useState } from "react";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { getPlanetData } from "@/entities/lookup/planets";
import { useMapPick } from "@/domains/strategy/mapPick";
import { useGameData } from "@/state/useGameContext";
import { stackRange, stacksOf, withStackCount, type Classified } from "./optionKinds";
import { FieldHead, Tile, UnitStackStepper } from "./DecisionTiles";
import styles from "./DecisionFields.module.css";

type Group = { target: string; name: string; options: ActionCardOption[] };

/** Nazwa celu: planeta z danych, system jako pozycja + jego planety. */
function useTargetName(kind: Classified["kind"]) {
  const tiles = useGameData()?.tiles;
  return (target: string) => {
    if (kind === "planet") return getPlanetData(target)?.name ?? target;
    const planets = Object.keys(tiles?.[target]?.planets ?? {})
      .map((id) => getPlanetData(id)?.name)
      .filter(Boolean);
    return planets.length > 0 ? `${planets.join(", ")} (${target})` : `System ${target}`;
  };
}

/**
 * Wybór „gdzie i co” (RULES.md 56, decyzja użytkownika: nigdy długa lista „X on Y”): cele
 * (planety / systemy) świecą na mapie, klik w cel - na mapie albo na jego chipie - pokazuje, co
 * można zrobić TAM: jednakowe jednostki to jeden licznik −/+, pozostałe opcje to kafelki. Opcje
 * bez celu („Do not place”, „Decline”) zostają kafelkami pod spodem. Wartość pola jest ta sama
 * co w zwykłym formularzu (id opcji), więc silnik waliduje wybór jak dotąd.
 */
export function GroupedMapField({
  input,
  classified,
  value,
  disabled,
  mapActive,
  onChange,
}: {
  input: Extract<ActionCardInput, { kind: "choice" | "multi" }>;
  classified: Classified;
  value: FormValue | undefined;
  disabled: boolean;
  mapActive: boolean;
  onChange: (value: FormValue) => void;
}) {
  const nameOf = useTargetName(classified.kind);
  const { groups, loose } = useMemo(() => {
    const byTarget = new Map<string, ActionCardOption[]>();
    const rest: ActionCardOption[] = [];
    for (const option of input.options) {
      const target = classified.targets.get(option.id);
      if (!target) {
        rest.push(option);
        continue;
      }
      byTarget.set(target, [...(byTarget.get(target) ?? []), option]);
    }
    return { groups: [...byTarget.entries()], loose: rest };
  }, [input.options, classified]);
  const named: Group[] = groups.map(([target, options]) => ({ target, name: nameOf(target), options }));

  const multi = input.kind === "multi";
  const picked = multi ? (Array.isArray(value) ? value : []) : typeof value === "string" ? [value] : [];
  const pickedIn = (group: Group) => group.options.filter((o) => picked.includes(o.id)).length;
  const firstPicked = named.find((g) => pickedIn(g) > 0)?.target ?? null;
  const [focus, setFocus] = useState<string | null>(null);
  const current = named.find((g) => g.target === (focus ?? firstPicked)) ?? null;

  const toggle = (id: string) => {
    if (!multi) {
      onChange(id);
      return;
    }
    if (picked.includes(id)) onChange(picked.filter((p) => p !== id));
    else if (input.max === 1) onChange([id]);
    else if (picked.length < input.max) onChange([...picked, id]);
  };
  const open = (target: string) => {
    if (disabled) return;
    setFocus(target);
    // Jedna rzecz do zrobienia w tym miejscu: klik w cel od razu ją wybiera.
    const group = named.find((g) => g.target === target);
    if (group?.options.length === 1 && group.options[0]) toggle(group.options[0].id);
  };

  useMapPick(classified.kind === "planet" ? "planet" : "system", named.map((g) => g.target), open, {
    enabled: mapActive && !disabled,
    selected: current?.target ?? null,
  });

  const place = classified.kind === "planet" ? "planet" : "system";
  const range = multi ? (input.min === input.max ? `${input.min}` : `${input.min}–${input.max}`) : "";
  const note = [
    multi ? `${picked.length} selected · pick ${range}` : null,
    `click a glowing ${place} on the map`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className={styles.field}>
      <FieldHead label={input.label} hint={input.hint} note={note} />
      <div className={styles.placeChips} role="group" aria-label={`${input.label}: ${place}s`}>
        {named.map((group) => {
          const n = pickedIn(group);
          return (
            <button
              key={group.target}
              type="button"
              className={styles.placeChip}
              aria-pressed={current?.target === group.target}
              data-picked={n > 0 || undefined}
              disabled={disabled}
              onClick={() => open(group.target)}
            >
              {group.name}
              {n > 0 && <i className={styles.placeCount}>{n}</i>}
            </button>
          );
        })}
      </div>
      {current ? (
        <section className={styles.placePanel} aria-label={current.name}>
          <h5 className={styles.placeTitle}>{current.name}</h5>
          <div className={styles.tiles}>
            {stacksOf(current.options).map(({ key, options: stack }) => {
              const option = stack[0];
              if (!option) return null;
              if (multi && stack.length > 1) {
                const r = stackRange(picked, stack, input.max);
                return (
                  <UnitStackStepper
                    key={key}
                    options={stack}
                    value={r.value}
                    max={r.max}
                    disabled={disabled}
                    onChange={(count) => onChange(withStackCount(picked, stack, count, input.max))}
                  />
                );
              }
              return stack.map((one) => {
                const selected = picked.includes(one.id);
                return (
                  <Tile
                    key={one.id}
                    option={one}
                    multi={multi}
                    selected={selected}
                    disabled={
                      disabled || (multi && !selected && input.max > 1 && picked.length >= input.max)
                    }
                    onClick={() => toggle(one.id)}
                  />
                );
              });
            })}
          </div>
        </section>
      ) : (
        <p className={styles.hint}>Click a glowing {place} on the map (or its name above) to choose what happens there.</p>
      )}
      {loose.length > 0 && (
        <div className={styles.tiles}>
          {loose.map((option) => (
            <Tile
              key={option.id}
              option={option}
              multi={multi}
              selected={picked.includes(option.id)}
              disabled={disabled}
              onClick={() => toggle(option.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

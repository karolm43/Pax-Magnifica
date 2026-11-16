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
 * KAŻDY wybór planety / systemu (RULES.md 56, decyzja użytkownika: NIGDY lista planet ani
 * checkboxy - zawsze klik na mapie). Cele świecą na mapie; okno pokazuje tylko to, co już
 * wybrano (chip z ×), a nie listę wszystkich celów. Gdy w jednym miejscu jest kilka rzeczy do
 * zrobienia („PDS / mech na X”), klik w cel pokazuje, co można zrobić TAM: jednakowe jednostki
 * to jeden licznik −/+, pozostałe opcje to kafelki. Opcje bez celu („Do not place”, „Decline”)
 * zostają kafelkami pod spodem. Wartość pola to id opcji, więc silnik waliduje wybór jak dotąd.
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
    mapActive ? `click a glowing ${place} on the map` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  // Na liście tylko wybrane miejsca (i to, które właśnie oglądamy) - resztę wskazuje mapa.
  const shown = named.filter((g) => pickedIn(g) > 0 || g.target === current?.target);
  const unpick = (group: Group) => {
    const ids = new Set(group.options.map((o) => o.id));
    if (multi) onChange(picked.filter((id) => !ids.has(id)));
    else onChange(null);
    if (focus === group.target) setFocus(null);
  };
  // Panel „co tutaj” tylko wtedy, gdy w miejscu jest więcej niż jedna rzecz do wyboru.
  const panel = current && current.options.length > 1 ? current : null;

  return (
    <div className={styles.field}>
      <FieldHead label={input.label} hint={input.hint} note={note} />
      {shown.length > 0 ? (
        <div className={styles.placeChips} role="group" aria-label={`${input.label}: chosen ${place}s`}>
          {shown.map((group) => {
            const n = pickedIn(group);
            return (
              <span key={group.target} className={styles.placeChipWrap}>
                <button
                  type="button"
                  className={styles.placeChip}
                  aria-pressed={current?.target === group.target}
                  data-picked={n > 0 || undefined}
                  disabled={disabled}
                  onClick={() => setFocus(group.target)}
                >
                  {group.name}
                  {n > 1 && <i className={styles.placeCount}>{n}</i>}
                </button>
                {n > 0 && (
                  <button
                    type="button"
                    className={styles.placeRemove}
                    aria-label={`Remove ${group.name}`}
                    disabled={disabled}
                    onClick={() => unpick(group)}
                  >
                    ×
                  </button>
                )}
              </span>
            );
          })}
        </div>
      ) : (
        <p className={styles.mapCall}>
          {named.length > 0
            ? `Click a glowing ${place} on the map.`
            : `No legal ${place} right now.`}
        </p>
      )}
      {panel && (
        <section className={styles.placePanel} aria-label={panel.name}>
          <h5 className={styles.placeTitle}>{panel.name}</h5>
          <div className={styles.tiles}>
            {stacksOf(panel.options).map(({ key, options: stack }) => {
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

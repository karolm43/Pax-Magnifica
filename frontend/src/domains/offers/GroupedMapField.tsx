import { useMemo, useState } from "react";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { getPlanetData } from "@/entities/lookup/planets";
import type { MapTargetKind } from "@/state/appStore";
import { useMapTargets } from "@/domains/strategy/mapPick";
import { useGameData } from "@/state/useGameContext";
import {
  planetOf,
  stackRange,
  stacksOf,
  systemOf,
  withStackCount,
  type Classified,
  type OptionLookups,
} from "./optionKinds";
import { useOptionLookups } from "./DecisionPickers";
import { FieldHead, Tile, UnitStackStepper } from "./DecisionTiles";
import { MapPickStatus, type MapTarget } from "./MapPickStatus";
import styles from "./DecisionFields.module.css";

type Group = MapTarget & { key: string; name: string; options: ActionCardOption[] };

export const keyOf = (kind: MapTargetKind, id: string) => `${kind}:${id}`;

/**
 * Cel opcji na mapie. Wybór „na planecie ALBO w przestrzeni” (Yin Spinner: „any planet you
 * control or any space area with your ships”) ma oba rodzaje naraz: opcja z planetą = klik w
 * planetę, opcja z samym systemem = klik w heks (jego przestrzeń). W zwykłym wyborze systemu
 * (bez opcji „przestrzeń”) cel zostaje systemem, nawet gdy opcja wspomina planetę.
 */
export function targetsOf(
  options: ActionCardOption[],
  classified: Classified,
  look: OptionLookups,
): Map<string, MapTarget> {
  const space = options.some((o) => !planetOf(o, look) && systemOf(o, look));
  const split = classified.kind === "planet" || space;
  const out = new Map<string, MapTarget>();
  for (const option of options) {
    if (!split) {
      const system = classified.targets.get(option.id);
      if (system) out.set(option.id, { kind: "system", id: system });
      continue;
    }
    const planet = planetOf(option, look);
    const system = planet ? null : systemOf(option, look);
    if (planet) out.set(option.id, { kind: "planet", id: planet });
    else if (system) out.set(option.id, { kind: "system", id: system });
  }
  return out;
}

/** Nazwa celu: planeta z danych; system jako jego planety + pozycja („przestrzeń” w mieszanym). */
export function useTargetName() {
  const tiles = useGameData()?.tiles;
  return (target: MapTarget, mixed: boolean) => {
    if (target.kind === "planet") return getPlanetData(target.id)?.name ?? target.id;
    const planets = Object.keys(tiles?.[target.id]?.planets ?? {})
      .map((id) => getPlanetData(id)?.name)
      .filter(Boolean);
    const system = planets.length > 0 ? `${planets.join(", ")} (${target.id})` : `System ${target.id}`;
    return mixed ? `Space · ${system}` : system;
  };
}

/**
 * KAŻDY wybór planety / systemu (RULES.md 56, decyzja użytkownika: NIGDY lista planet ani
 * checkboxy - zawsze klik na mapie). Cele świecą na mapie; okno pokazuje jedną linię stanu
 * (``MapPickStatus``) i to, co już wybrano (chip z ×), a nie listę celów. Gdy w jednym miejscu
 * jest kilka rzeczy do zrobienia („PDS / mech na X”), klik w cel pokazuje, co można zrobić TAM:
 * jednakowe jednostki to jeden licznik −/+, pozostałe opcje to kafelki. Opcje bez celu
 * („Do not place”, „Decline”) zostają kafelkami. Wartość pola to id opcji - silnik waliduje.
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
  const lookups = useOptionLookups();
  const nameOf = useTargetName();
  const { groups, loose, mixed } = useMemo(() => {
    const targets = targetsOf(input.options, classified, lookups);
    const byKey = new Map<string, { target: MapTarget; options: ActionCardOption[] }>();
    const rest: ActionCardOption[] = [];
    for (const option of input.options) {
      const target = targets.get(option.id);
      if (!target) {
        rest.push(option);
        continue;
      }
      const key = keyOf(target.kind, target.id);
      const group = byKey.get(key) ?? { target, options: [] };
      group.options.push(option);
      byKey.set(key, group);
    }
    const kinds = new Set([...byKey.values()].map((g) => g.target.kind));
    return { groups: [...byKey.entries()], loose: rest, mixed: kinds.size > 1 };
  }, [input.options, classified, lookups]);
  // Jedna opcja w miejscu: chip nosi etykietę silnika („Space area of system 301”, „Darien”).
  const named: Group[] = groups.map(([key, g]) => ({
    key,
    ...g.target,
    name: g.options.length === 1 && g.options[0] ? g.options[0].label : nameOf(g.target, mixed),
    options: g.options,
  }));

  const multi = input.kind === "multi";
  const picked = multi ? (Array.isArray(value) ? value : []) : typeof value === "string" ? [value] : [];
  const pickedIn = (group: Group) => group.options.filter((o) => picked.includes(o.id)).length;
  const firstPicked = named.find((g) => pickedIn(g) > 0)?.key ?? null;
  // ``null`` = pokaż pierwsze wybrane miejsce, ``""`` = nic (gracz je zamknął), inaczej klucz.
  const [focus, setFocus] = useState<string | null>(null);
  const current = named.find((g) => g.key === (focus ?? firstPicked)) ?? null;

  const toggle = (id: string) => {
    if (!multi) {
      // Ponowny klik w wybrane (kafelek albo cel na mapie) odznacza - jak zdjęcie żetonu.
      onChange(picked.includes(id) ? null : id);
      return;
    }
    if (picked.includes(id)) onChange(picked.filter((p) => p !== id));
    else if (input.max === 1) onChange([id]);
    else if (picked.length < input.max) onChange([...picked, id]);
  };
  const open = (key: string) => {
    if (disabled) return;
    const group = named.find((g) => g.key === key);
    // Jedna rzecz do zrobienia w tym miejscu: klik w cel od razu ją wybiera, a ponowny klik
    // odznacza CAŁKIEM - fokus też znika, żeby miejsce nie zostało „wybrane” w oknie i na mapie.
    if (group?.options.length === 1 && group.options[0]) {
      const id = group.options[0].id;
      const unpicking = picked.includes(id);
      toggle(id);
      setFocus(unpicking ? "" : key);
      return;
    }
    // Kilka rzeczy w miejscu: klik otwiera panel „co tutaj”, ponowny klik go zamyka.
    setFocus((prev) => ((prev ?? firstPicked) === key ? "" : key));
  };

  const handle = useMapTargets(
    {
      systems: named.filter((g) => g.kind === "system").map((g) => g.id),
      planets: named.filter((g) => g.kind === "planet").map((g) => g.id),
    },
    (target, kind) => open(keyOf(kind, target)),
    { enabled: mapActive && !disabled, selected: current?.id ?? null },
  );

  const range = multi ? (input.min === input.max ? `${input.min}` : `${input.min}–${input.max}`) : "";
  // Na liście tylko wybrane miejsca (i to, które właśnie oglądamy) - resztę wskazuje mapa.
  const shown = named.filter((g) => pickedIn(g) > 0 || g.key === current?.key);
  const unpick = (group: Group) => {
    const ids = new Set(group.options.map((o) => o.id));
    if (multi) onChange(picked.filter((id) => !ids.has(id)));
    else onChange(null);
    if ((focus ?? firstPicked) === group.key) setFocus("");
  };
  // Panel „co tutaj” tylko wtedy, gdy w miejscu jest więcej niż jedna rzecz do wyboru.
  const panel = current && current.options.length > 1 ? current : null;

  return (
    // Klik w pole przejmuje mapę dla tego okna (gdy obok czeka inne okno z wyborem na mapie).
    <div className={styles.field} onPointerDownCapture={mapActive ? handle.claim : undefined}>
      <FieldHead
        label={input.label}
        hint={input.hint}
        note={multi ? `${picked.length} selected · pick ${range}` : undefined}
      />
      {mapActive && (
        <MapPickStatus targets={named} handle={handle} disabled={disabled} />
      )}
      {shown.length > 0 && (
        <div className={styles.placeChips} role="group" aria-label={`${input.label}: chosen`}>
          {shown.map((group) => {
            const n = pickedIn(group);
            return (
              <span key={group.key} className={styles.placeChipWrap}>
                <button
                  type="button"
                  className={styles.placeChip}
                  aria-pressed={current?.key === group.key}
                  data-picked={n > 0 || undefined}
                  disabled={disabled}
                  onClick={() => setFocus(group.key)}
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

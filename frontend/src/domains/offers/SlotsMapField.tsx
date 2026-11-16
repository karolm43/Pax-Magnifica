import { useMemo, useState } from "react";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { useMapTargets } from "@/domains/strategy/mapPick";
import type { Classified } from "./optionKinds";
import { useOptionLookups } from "./DecisionPickers";
import { FieldHead, Tile } from "./DecisionTiles";
import { keyOf, targetsOf, useTargetName } from "./GroupedMapField";
import { MapPickStatus, type MapTarget } from "./MapPickStatus";
import styles from "./DecisionFields.module.css";

type ChoiceInput = Extract<ActionCardInput, { kind: "choice" }>;
type Place = MapTarget & { key: string; name: string; options: ActionCardOption[] };

/** Etykieta pola bez numeru slotu („Infantry 1 commits to” → „Infantry commits to”). */
function baseLabel(label: string): string {
  return label.replace(/\s+#?\d+\b/, "").trim();
}

/**
 * JEDNAKOWE SLOTY jako jedno pole (``slotGroups``): silnik pyta N razy o to samo („Infantry
 * 1/2/3 commits to”, każde z „No infantry”), a gracz planszówki myśli „kładę do 3 piechot”.
 * Każdy klik w świecący cel na mapie dokłada 1 sztukę (ten sam cel kilka razy = ×2, ×3), chip
 * celu ma − (zdejmij jedną) i × (zdejmij wszystkie). Opcja bez celu („No infantry”) nie jest
 * kafelkiem - wolne sloty dostają ją same. Wartości pól to nadal id opcji, silnik waliduje.
 */
export function SlotsMapField({
  inputs,
  classified,
  values,
  disabled,
  mapActive,
  onChange,
}: {
  inputs: ChoiceInput[];
  classified: Classified;
  values: Record<string, FormValue>;
  disabled: boolean;
  mapActive: boolean;
  onChange: (key: string, value: FormValue) => void;
}) {
  const first = inputs[0];
  const lookups = useOptionLookups();
  const nameOf = useTargetName();
  const { places, none, rest } = useMemo(() => {
    const targets = targetsOf(first.options, classified, lookups);
    const byKey = new Map<string, Place>();
    const loose: ActionCardOption[] = [];
    for (const option of first.options) {
      const target = targets.get(option.id);
      if (!target) {
        loose.push(option);
        continue;
      }
      const key = keyOf(target.kind, target.id);
      const place = byKey.get(key) ?? { ...target, key, name: "", options: [] };
      place.options.push(option);
      byKey.set(key, place);
    }
    const kinds = new Set([...byKey.values()].map((p) => p.kind));
    for (const place of byKey.values()) {
      place.name =
        place.options.length === 1 && place.options[0]
          ? place.options[0].label
          : nameOf(place, kinds.size > 1);
    }
    // Jedna opcja bez celu = „pusty slot” (No infantry / None); więcej zostaje kafelkami.
    return {
      places: [...byKey.values()],
      none: loose.length === 1 ? loose[0] : null,
      rest: loose.length === 1 ? [] : loose,
    };
    // ``nameOf`` czyta dane planszy - nazwy liczymy razem z celami.
  }, [first.options, classified, lookups]);

  const keys = inputs.map((i) => i.key);
  // Zajęte sloty: id opcji z celem albo z ``rest`` (w kolejności pól).
  const filled = keys
    .map((k) => values[k])
    .filter((v): v is string => typeof v === "string" && v !== "" && v !== none?.id);
  const free = keys.length - filled.length;
  const [focus, setFocus] = useState<string | null>(null);

  /** Zapisuje listę wyborów w slotach po kolei; resztę slotów wypełnia „pusty slot”. */
  const write = (next: string[]) => {
    keys.forEach((key, i) => onChange(key, next[i] ?? none?.id ?? null));
  };
  const add = (optionId: string) => {
    if (free <= 0) return;
    write([...filled, optionId]);
  };
  const removeOne = (optionIds: string[]) => {
    const at = filled.map((id) => optionIds.includes(id)).lastIndexOf(true);
    if (at < 0) return;
    write(filled.filter((_, i) => i !== at));
  };
  const removeAll = (optionIds: string[]) => write(filled.filter((id) => !optionIds.includes(id)));
  const countIn = (place: Place) =>
    filled.filter((id) => place.options.some((o) => o.id === id)).length;

  const open = (key: string) => {
    if (disabled) return;
    const place = places.find((p) => p.key === key);
    if (!place) return;
    if (place.options.length === 1 && place.options[0]) add(place.options[0].id);
    else setFocus(key);
  };
  const handle = useMapTargets(
    {
      systems: places.filter((p) => p.kind === "system").map((p) => p.id),
      planets: places.filter((p) => p.kind === "planet").map((p) => p.id),
    },
    (target, kind) => open(keyOf(kind, target)),
    { enabled: mapActive && !disabled && free > 0, selected: focus?.split(":")[1] ?? null },
  );
  const shown = places.filter((p) => countIn(p) > 0);
  const panel = places.find((p) => p.key === focus && p.options.length > 1) ?? null;

  return (
    <div className={styles.field} onPointerDownCapture={mapActive ? handle.claim : undefined}>
      <FieldHead
        label={baseLabel(first.label)}
        hint={first.hint}
        note={`${filled.length} / ${keys.length} placed`}
      />
      {mapActive && free > 0 && (
        <MapPickStatus targets={places} handle={handle} disabled={disabled} />
      )}
      {free === 0 && (
        <p className={styles.mapCall}>All {keys.length} placed - remove one to choose again.</p>
      )}
      {shown.length > 0 && (
        <div className={styles.placeChips} role="group" aria-label={`${baseLabel(first.label)}: chosen`}>
          {shown.map((place) => {
            const n = countIn(place);
            const ids = place.options.map((o) => o.id);
            return (
              <span key={place.key} className={styles.placeChipWrap}>
                <button
                  type="button"
                  className={styles.placeChip}
                  data-picked
                  disabled={disabled || free <= 0}
                  onClick={() => open(place.key)}
                  title="Add one more here"
                >
                  {place.name}
                  {n > 1 && <i className={styles.placeCount}>×{n}</i>}
                </button>
                <button
                  type="button"
                  className={styles.placeMinus}
                  aria-label={`One less on ${place.name}`}
                  disabled={disabled}
                  onClick={() => removeOne(ids)}
                >
                  −
                </button>
                <button
                  type="button"
                  className={styles.placeRemove}
                  aria-label={`Remove ${place.name}`}
                  disabled={disabled}
                  onClick={() => removeAll(ids)}
                >
                  ×
                </button>
              </span>
            );
          })}
        </div>
      )}
      {panel && (
        <section className={styles.placePanel} aria-label={panel.name}>
          <h5 className={styles.placeTitle}>{panel.name}</h5>
          <div className={styles.tiles}>
            {panel.options.map((option) => (
              <Tile
                key={option.id}
                option={option}
                multi
                selected={filled.includes(option.id)}
                disabled={disabled || free <= 0}
                onClick={() => add(option.id)}
              />
            ))}
          </div>
        </section>
      )}
      {rest.length > 0 && (
        <div className={styles.tiles}>
          {rest.map((option) => (
            <Tile
              key={option.id}
              option={option}
              multi
              selected={filled.includes(option.id)}
              disabled={disabled || (free <= 0 && !filled.includes(option.id))}
              onClick={() => (filled.includes(option.id) ? removeOne([option.id]) : add(option.id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

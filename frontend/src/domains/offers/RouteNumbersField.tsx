import { useMemo, useState } from "react";
import { IconArrowRight } from "@tabler/icons-react";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { getPlanetData } from "@/entities/lookup/planets";
import { useMapPick } from "@/domains/strategy/mapPick";
import { FieldHead, Stepper } from "./DecisionTiles";
import styles from "./DecisionFields.module.css";

type NumberInput = Extract<ActionCardInput, { kind: "number" }>;
export type Route = { input: NumberInput; from: string; to: string };

/** Wejścia liczbowe-przeniesienia (``meta = {from, to}`` z ``offer_inputs.route_meta``). */
export function routeOf(input: ActionCardInput): Route | null {
  if (input.kind !== "number") return null;
  const from = input.meta?.from;
  const to = input.meta?.to;
  return typeof from === "string" && typeof to === "string" ? { input, from, to } : null;
}

const nameOf = (planet: string) => getPlanetData(planet)?.name ?? planet;

/**
 * Przeniesienia jednostek planeta -> planeta (Bioplasmosis) jako wybór NA MAPIE zamiast listy
 * stepperów dla każdej pary: klik w planetę źródłową (świecą te, z których można), potem w cel
 * (świecą osiągalne) = +1 jednostka. Poniżej tylko wybrane przeniesienia z licznikiem −/+.
 * Suma z jednej planety nie przekracza jej jednostek (``max`` wejścia = ile ich tam jest).
 */
export function RouteNumbersField({
  routes,
  values,
  disabled,
  mapActive,
  onChange,
}: {
  routes: Route[];
  values: Record<string, FormValue>;
  disabled: boolean;
  mapActive: boolean;
  onChange: (key: string, value: FormValue) => void;
}) {
  const [source, setSource] = useState<string | null>(null);
  const countOf = (route: Route) => (typeof values[route.input.key] === "number" ? (values[route.input.key] as number) : 0);
  const sources = useMemo(() => [...new Set(routes.map((r) => r.from))], [routes]);
  // Ile jednostek stoi na źródle (każde wejście z tego źródła ma ``max`` = ta liczba).
  const capacity = (from: string) => Math.max(0, ...routes.filter((r) => r.from === from).map((r) => r.input.max));
  const sent = (from: string) => routes.filter((r) => r.from === from).reduce((sum, r) => sum + countOf(r), 0);
  const destinations = source ? routes.filter((r) => r.from === source).map((r) => r.to) : [];

  const pick = (planet: string) => {
    if (disabled) return;
    if (!source || planet === source || !destinations.includes(planet)) {
      setSource(sources.includes(planet) ? planet : null);
      return;
    }
    const route = routes.find((r) => r.from === source && r.to === planet);
    if (route && sent(source) < capacity(source)) onChange(route.input.key, countOf(route) + 1);
  };

  // Najpierw świecą źródła; po wybraniu źródła - jego cele (i ono samo, by je odznaczyć).
  useMapPick("planet", source ? [source, ...destinations] : sources, pick, {
    enabled: mapActive && !disabled,
    selected: source,
  });

  const chosen = routes.filter((r) => countOf(r) > 0);
  const unit = routes[0]?.input.meta?.unit;
  const label = `Move ${unit === "infantry" ? "infantry" : "units"} between your planets`;

  return (
    <div className={styles.field}>
      <FieldHead
        label={label}
        hint={routes[0]?.input.hint}
        note={source ? `from ${nameOf(source)}: click a glowing planet to move 1 there` : "click a glowing planet to move from"}
      />
      <div className={styles.placeChips} role="group" aria-label="Move from">
        {sources.map((from) => (
          <button
            key={from}
            type="button"
            className={styles.placeChip}
            aria-pressed={source === from}
            data-picked={sent(from) > 0 || undefined}
            disabled={disabled}
            onClick={() => setSource(source === from ? null : from)}
          >
            {nameOf(from)}
            <i className={styles.placeCount}>
              {capacity(from) - sent(from)}
            </i>
          </button>
        ))}
      </div>
      {source && (
        <div className={styles.placeChips} role="group" aria-label={`Move from ${nameOf(source)} to`}>
          {routes
            .filter((r) => r.from === source)
            .map((r) => (
              <button
                key={r.input.key}
                type="button"
                className={styles.placeChip}
                disabled={disabled || sent(source) >= capacity(source)}
                onClick={() => pick(r.to)}
              >
                <IconArrowRight size={12} aria-hidden="true" />
                {nameOf(r.to)}
              </button>
            ))}
        </div>
      )}
      {chosen.map((r) => (
        <Stepper
          key={r.input.key}
          label={`${nameOf(r.from)} → ${nameOf(r.to)}`}
          value={countOf(r)}
          min={0}
          max={countOf(r) + capacity(r.from) - sent(r.from)}
          disabled={disabled}
          onChange={(next) => onChange(r.input.key, next)}
        />
      ))}
    </div>
  );
}

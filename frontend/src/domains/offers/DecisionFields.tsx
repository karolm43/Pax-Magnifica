import { useMemo } from "react";
import { MultiSelect, Select } from "@/ds";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { useGameData } from "@/state/useGameContext";
import { classifyOptions, stackRange, stacksOf, withStackCount } from "./optionKinds";
import { describeOption, useOptionLookups } from "./DecisionPickers";
import { FieldHead, metaOf, Stepper, Tile, UnitStackStepper } from "./DecisionTiles";
import { GroupedMapField } from "./GroupedMapField";
import { TechPickField } from "./TechPickField";
import { routeOf, RouteNumbersField, type Route } from "./RouteNumbersField";
import styles from "./DecisionFields.module.css";

/*
 * Wspólne pola decyzji gracza (oferty „may”, zdolności, technologie, karty, relikty). Backend
 * opisuje wejścia (choice / multi / number) i legalne opcje; tu zamieniamy je na kafelki do
 * kliknięcia zamiast list rozwijanych, a liczby na stepper. Opcje z ``meta`` dostają grafikę:
 * jednostka (sprite w kolorze gracza), planeta (wartość do zapłaty), kość (wynik i trafienie).
 * Płatność (planety + trade goods) to jeden widżet z paskiem „zapłacono X / Y”.
 */

/** Powyżej tylu opcji kafelki byłyby ścianą przycisków — wracamy do listy z wyszukiwaniem. */
const MAX_TILES = 18;

type Payment = { cost: number; valueKind: string; tradeGoods: string };

function paymentOf(input: ActionCardInput): Payment | null {
  return input.kind === "multi" && input.payment ? input.payment : null;
}

export { Stepper };

/** Jedno pole decyzji (bez parowania płatności — patrz ``DecisionFields``). */
export function DecisionField({
  input,
  value,
  disabled,
  onChange,
  mapActive = true,
}: {
  input: ActionCardInput;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
  /** Czy to pole trzyma wybór na mapie (jedno pole naraz - patrz ``DecisionFields``). */
  mapActive?: boolean;
}) {
  if (input.kind === "number") {
    return (
      <div className={styles.field}>
        {input.hint && <p className={styles.hint}>{input.hint}</p>}
        <Stepper
          label={input.label}
          value={typeof value === "number" ? value : input.min}
          min={input.min}
          max={input.max}
          disabled={disabled}
          coins={/trade.?goods|\btg\b/i.test(`${input.key} ${input.label}`)}
          onChange={onChange}
        />
      </div>
    );
  }

  // Informacja (np. „technologię wybierzesz po zagraniu”) - bez pola do wyboru.
  if (input.kind === "info") {
    return (
      <div className={styles.field}>
        <p className={styles.hint}>
          {input.label}
          {input.hint ? ` ${input.hint}` : ""}
        </p>
      </div>
    );
  }
  // Badanie ma własne pełne okno (``ResearchOfferOverlay``), nie pole formularza.
  if (input.kind === "research") return null;
  return (
    <ChoiceField
      input={input}
      value={value}
      disabled={disabled}
      onChange={onChange}
      mapActive={mapActive}
    />
  );
}

/**
 * Wybór z opcji (choice / multi). Rodzaj opcji rozpoznaje ``classifyOptions``: gracze dostają
 * ikony frakcji, technologie - drzewo technologii, planety i systemy - TYLKO klik na mapie.
 */
function ChoiceField({
  input,
  value,
  disabled,
  onChange,
  mapActive,
}: {
  input: Extract<ActionCardInput, { kind: "choice" | "multi" }>;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
  mapActive: boolean;
}) {
  const options = input.options;
  const lookups = useOptionLookups();
  const idMap = useGameData()?.strategyCardIdMap;
  const classified = useMemo(() => classifyOptions(options, lookups), [options, lookups]);
  const kindOf = (option: ActionCardOption) => {
    const target = classified?.targets.get(option.id);
    return classified && target ? { kind: classified.kind, target } : undefined;
  };
  const picked = Array.isArray(value) ? value : [];
  // Planety i systemy: ZAWSZE wybór na mapie (``GroupedMapField``), nigdy lista - decyzja
  // użytkownika. Technologie: drzewo technologii (``TechPickField``), nigdy lista.
  const grouped = classified?.kind === "planet" || classified?.kind === "system";
  // Technologie i gracze zawsze jako kafelki (bez listy rozwijanej).
  const alwaysTiles = classified?.kind === "technology" || classified?.kind === "player";
  // Kafelki z opisem (technologia, cel, karta) są szersze - tekst zasady ma się zmieścić.
  const rich =
    classified?.kind === "technology" ||
    (!classified && options.some((o) => describeOption(o, idMap)));
  const data = options.map((o) => ({ value: o.id, label: o.label }));
  const stacks = useMemo(() => stacksOf(options), [options]);

  if (classified?.kind === "technology") {
    return (
      <TechPickField
        input={input}
        classified={classified}
        value={value}
        disabled={disabled}
        onChange={onChange}
      />
    );
  }

  if (grouped && classified) {
    return (
      <GroupedMapField
        input={input}
        classified={classified}
        value={value}
        disabled={disabled}
        mapActive={mapActive}
        onChange={onChange}
      />
    );
  }

  if (input.kind === "multi") {
    const range = input.min === input.max ? `${input.min}` : `${input.min}–${input.max}`;
    if (stacks.length > MAX_TILES && !alwaysTiles && !rich) {
      return (
        <MultiSelect
          label={input.label}
          description={[input.hint, `Pick ${range}.`].filter(Boolean).join(" ")}
          data={data}
          value={picked}
          searchable
          disabled={disabled}
          placeholder={data.length ? "Choose…" : "Nothing to choose"}
          onChange={(next) => onChange(next.slice(0, input.max))}
        />
      );
    }
    const toggle = (id: string) => {
      if (picked.includes(id)) onChange(picked.filter((p) => p !== id));
      else if (input.max === 1) onChange([id]);
      else if (picked.length < input.max) onChange([...picked, id]);
    };
    return (
      <div className={styles.field}>
        <FieldHead
          label={input.label}
          hint={input.hint}
          note={`${picked.length} selected · pick ${range}`}
        />
        <div className={styles.tiles} data-rich={rich || undefined}>
          {stacks.map(({ key, options: stack }) => {
            const [option] = stack;
            if (stack.length > 1) {
              const range = stackRange(picked, stack, input.max);
              return (
                <UnitStackStepper
                  key={key}
                  options={stack}
                  value={range.value}
                  max={range.max}
                  disabled={disabled}
                  onChange={(count) => onChange(withStackCount(picked, stack, count, input.max))}
                />
              );
            }
            const selected = picked.includes(option.id);
            return (
              <Tile
                key={option.id}
                option={option}
                kind={kindOf(option)}
                multi
                selected={selected}
                disabled={disabled || (!selected && input.max > 1 && picked.length >= input.max)}
                onClick={() => toggle(option.id)}
              />
            );
          })}
        </div>
        {input.max > 1 && options.length > 1 && (
          <div className={styles.quick}>
            <button
              type="button"
              disabled={disabled || picked.length === Math.min(input.max, options.length)}
              onClick={() => onChange(options.slice(0, input.max).map((o) => o.id))}
            >
              {input.max >= options.length ? "All" : `First ${input.max}`}
            </button>
            <button type="button" disabled={disabled || picked.length === 0} onClick={() => onChange([])}>
              None
            </button>
          </div>
        )}
      </div>
    );
  }

  if (options.length > MAX_TILES && !alwaysTiles && !rich) {
    return (
      <Select
        label={input.label}
        description={input.hint || undefined}
        data={data}
        value={typeof value === "string" ? value : null}
        searchable
        disabled={disabled}
        placeholder={data.length ? "Choose…" : "Nothing to choose"}
        onChange={onChange}
      />
    );
  }
  return (
    <div className={styles.field}>
      <FieldHead label={input.label} hint={input.hint} />
      <div
        className={styles.tiles}
        data-rich={rich || undefined}
        role="radiogroup"
        aria-label={input.label}
      >
        {options.map((option) => (
          <Tile
            key={option.id}
            option={option}
            kind={kindOf(option)}
            multi={false}
            selected={value === option.id}
            disabled={disabled}
            onClick={() => onChange(option.id)}
          />
        ))}
      </div>
    </div>
  );
}

/** Płatność: kafelki planet z wartościami + licznik trade goods + pasek postępu. */
function PaymentField({
  input,
  payment,
  tgInput,
  values,
  disabled,
  onChange,
}: {
  input: Extract<ActionCardInput, { kind: "multi" }>;
  payment: Payment;
  tgInput: Extract<ActionCardInput, { kind: "number" }> | undefined;
  values: Record<string, FormValue>;
  disabled: boolean;
  onChange: (key: string, value: FormValue) => void;
}) {
  const picked = Array.isArray(values[input.key]) ? (values[input.key] as string[]) : [];
  const tg = typeof values[payment.tradeGoods] === "number" ? (values[payment.tradeGoods] as number) : 0;
  const fromPlanets = input.options
    .filter((o) => picked.includes(o.id))
    .reduce((sum, o) => sum + (typeof metaOf(o).value === "number" ? (metaOf(o).value as number) : 0), 0);
  const paid = fromPlanets + tg;
  const enough = paid >= payment.cost;
  const toggle = (id: string) =>
    onChange(input.key, picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id]);

  return (
    <div className={styles.field}>
      <FieldHead label={`Pay ${payment.cost} ${payment.valueKind}`} hint={input.hint} />
      <div className={styles.payBar} data-ok={enough || undefined} aria-live="polite">
        <span>
          Paid <b>{paid}</b> / {payment.cost}
          {paid > payment.cost ? " · overpaying" : ""}
        </span>
        <i aria-hidden="true">
          <em style={{ width: `${Math.min(100, (paid / Math.max(1, payment.cost)) * 100)}%` }} />
        </i>
      </div>
      {input.options.length > 0 ? (
        <div className={styles.tiles}>
          {input.options.map((option) => (
            <Tile
              key={option.id}
              option={option}
              multi
              selected={picked.includes(option.id)}
              disabled={disabled}
              onClick={() => toggle(option.id)}
            />
          ))}
        </div>
      ) : (
        <p className={styles.hint}>No ready planets — pay with trade goods.</p>
      )}
      {tgInput && tgInput.max > 0 && (
        <Stepper
          label="Trade goods"
          value={tg}
          min={tgInput.min}
          max={tgInput.max}
          disabled={disabled}
          coins
          onChange={(next) => onChange(payment.tradeGoods, next)}
        />
      )}
    </div>
  );
}

/**
 * Cały formularz decyzji: pola po kolei, a para „planety + trade goods” oznaczona przez backend
 * jako ``payment`` renderuje się jako jeden widżet płatności.
 */
export function DecisionFields({
  inputs,
  values,
  disabled,
  onChange,
}: {
  inputs: ActionCardInput[];
  values: Record<string, FormValue>;
  disabled: boolean;
  onChange: (key: string, value: FormValue) => void;
}) {
  const paidBy = new Set<string>();
  for (const input of inputs) {
    const payment = paymentOf(input);
    if (payment) paidBy.add(payment.tradeGoods);
  }
  // Mapa ma jeden tryb wyboru: trzyma go pierwsze pole z planetami/systemami bez odpowiedzi
  // (a gdy wszystkie mają odpowiedź - pierwsze takie pole, żeby można było zmienić zdanie).
  const lookups = useOptionLookups();
  const mapKey = useMemo(() => {
    const onMap = inputs.filter((input) => {
      if (input.kind !== "choice" && input.kind !== "multi") return false;
      if (paymentOf(input)) return false;
      const kind = classifyOptions(input.options, lookups)?.kind;
      return kind === "planet" || kind === "system";
    });
    const open = onMap.find((input) => {
      const v = values[input.key];
      return v === undefined || v === null || (Array.isArray(v) && v.length === 0);
    });
    return (open ?? onMap[0])?.key ?? null;
  }, [inputs, lookups, values]);
  // Przeniesienia planeta -> planeta (Bioplasmosis): jeden wybór na mapie w miejscu pierwszego.
  const routes = useMemo(
    () => inputs.map(routeOf).filter((r): r is Route => r !== null),
    [inputs],
  );
  const firstRoute = routes[0]?.input.key;
  return (
    <div className={styles.form}>
      {inputs.map((input) => {
        if (routeOf(input)) {
          if (input.key !== firstRoute) return null;
          return (
            <RouteNumbersField
              key={input.key}
              routes={routes}
              values={values}
              disabled={disabled}
              mapActive={mapKey === null}
              onChange={onChange}
            />
          );
        }
        const payment = input.kind === "multi" ? paymentOf(input) : null;
        if (payment && input.kind === "multi") {
          const tgInput = inputs.find(
            (i): i is Extract<ActionCardInput, { kind: "number" }> =>
              i.key === payment.tradeGoods && i.kind === "number",
          );
          return (
            <PaymentField
              key={input.key}
              input={input}
              payment={payment}
              tgInput={tgInput}
              values={values}
              disabled={disabled}
              onChange={onChange}
            />
          );
        }
        if (input.kind === "number" && paidBy.has(input.key)) return null;
        return (
          <DecisionField
            key={input.key}
            input={input}
            value={values[input.key]}
            mapActive={input.key === mapKey}
            disabled={disabled}
            onChange={(next) => onChange(input.key, next)}
          />
        );
      })}
    </div>
  );
}

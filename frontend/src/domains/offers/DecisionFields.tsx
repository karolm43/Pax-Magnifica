import { IconCheck, IconCoins, IconMinus, IconPlus } from "@tabler/icons-react";
import { MultiSelect, Select } from "@/ds";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { getColorAlias } from "@/entities/lookup/colors";
import { Unit } from "@/shared/ui/Unit";
import { asyncOfBase } from "@/domains/movement/routeTypes";
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

type Meta = Record<string, unknown>;

type Payment = { cost: number; valueKind: string; tradeGoods: string };

function metaOf(option: ActionCardOption): Meta {
  return option.meta ?? {};
}

function paymentOf(input: ActionCardInput): Payment | null {
  const raw = (input as { payment?: Payment }).payment;
  return raw && typeof raw.cost === "number" ? raw : null;
}

/** „Nazwa - dopisek” z backendu → tytuł kafelka i mniejszy podpis. */
function splitLabel(label: string): { title: string; caption: string } {
  const at = label.indexOf(" - ");
  if (at < 0) return { title: label, caption: "" };
  return { title: label.slice(0, at), caption: label.slice(at + 3) };
}

function OptionBody({ option }: { option: ActionCardOption }) {
  const meta = metaOf(option);
  if (typeof meta.die === "number") {
    const hitsOn = typeof meta.hitsOn === "number" ? meta.hitsOn : 11;
    const hit = meta.die >= hitsOn;
    return (
      <>
        <span className={styles.die} data-hit={hit || undefined} aria-hidden="true">
          {meta.die}
        </span>
        <span className={styles.optText}>
          <b>{splitLabel(option.label.split(":")[0] ?? option.label).title}</b>
          <small>{hit ? "hit" : `miss (hits on ${hitsOn})`}</small>
        </span>
      </>
    );
  }
  const { title, caption } = splitLabel(option.label);
  if (typeof meta.unit === "string") {
    const count = typeof meta.count === "number" ? meta.count : 0;
    return (
      <>
        <span className={styles.sprite} aria-hidden="true">
          <Unit
            unitType={asyncOfBase(meta.unit)}
            colorAlias={getColorAlias(typeof meta.color === "string" ? meta.color : undefined)}
            faction={typeof meta.faction === "string" ? meta.faction : undefined}
            scaleSprite
          />
          {count > 1 && <i className={styles.count}>×{count}</i>}
        </span>
        <span className={styles.optText}>
          <b>{title}</b>
          {caption && <small>{caption}</small>}
        </span>
      </>
    );
  }
  if (typeof meta.planet === "string") {
    const value = typeof meta.value === "number" ? meta.value : 0;
    return (
      <>
        <span
          className={styles.value}
          data-kind={meta.valueKind === "influence" ? "influence" : "resources"}
          aria-hidden="true"
        >
          {value}
        </span>
        <span className={styles.optText}>
          <b>{title.replace(/\s*\(\d+\)$/, "")}</b>
          <small>{caption || (meta.valueKind === "influence" ? "influence" : "resources")}</small>
        </span>
      </>
    );
  }
  return (
    <span className={styles.optText}>
      <b>{title}</b>
      {caption && <small>{caption}</small>}
    </span>
  );
}

function Tile({
  option,
  selected,
  disabled,
  multi,
  onClick,
}: {
  option: ActionCardOption;
  selected: boolean;
  disabled: boolean;
  multi: boolean;
  onClick: () => void;
}) {
  const meta = metaOf(option);
  const shape = typeof meta.die === "number" ? "die" : undefined;
  return (
    <button
      type="button"
      className={styles.tile}
      data-shape={shape}
      aria-pressed={selected}
      disabled={disabled}
      title={option.label}
      onClick={onClick}
    >
      <OptionBody option={option} />
      {multi && (
        <span className={styles.check} aria-hidden="true">
          {selected && <IconCheck size={11} />}
        </span>
      )}
    </button>
  );
}

function FieldHead({ label, hint, note }: { label: string; hint?: string; note?: string }) {
  return (
    <div className={styles.head}>
      <span className={styles.label}>{label}</span>
      {note && <span className={styles.note}>{note}</span>}
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}

/** Stepper liczby: − wartość + (bez suwaka i bez wpisywania z klawiatury). */
export function Stepper({
  label,
  value,
  min,
  max,
  disabled,
  coins,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled: boolean;
  coins?: boolean;
  onChange: (value: number) => void;
}) {
  const clamp = (n: number) => Math.max(min, Math.min(max, n));
  return (
    <div className={styles.stepper} role="group" aria-label={label}>
      {coins && <IconCoins size={16} className={styles.coins} aria-hidden="true" />}
      <span className={styles.stepLabel}>{label}</span>
      <button
        type="button"
        className={styles.stepBtn}
        disabled={disabled || value <= min}
        aria-label={`${label}: less`}
        onClick={() => onChange(clamp(value - 1))}
      >
        <IconMinus size={14} />
      </button>
      <output className={styles.stepValue} aria-live="polite">
        {value}
      </output>
      <button
        type="button"
        className={styles.stepBtn}
        disabled={disabled || value >= max}
        aria-label={`${label}: more`}
        onClick={() => onChange(clamp(value + 1))}
      >
        <IconPlus size={14} />
      </button>
      {max > min + 1 && (
        <button
          type="button"
          className={styles.stepMax}
          disabled={disabled || value === max}
          onClick={() => onChange(max)}
        >
          max {max}
        </button>
      )}
    </div>
  );
}

/** Jedno pole decyzji (bez parowania płatności — patrz ``DecisionFields``). */
export function DecisionField({
  input,
  value,
  disabled,
  onChange,
}: {
  input: ActionCardInput;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
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

  const options = input.options;
  const data = options.map((o) => ({ value: o.id, label: o.label }));

  if (input.kind === "multi") {
    const picked = Array.isArray(value) ? value : [];
    const range = input.min === input.max ? `${input.min}` : `${input.min}–${input.max}`;
    if (options.length > MAX_TILES) {
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
        <div className={styles.tiles}>
          {options.map((option) => {
            const selected = picked.includes(option.id);
            return (
              <Tile
                key={option.id}
                option={option}
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

  if (options.length > MAX_TILES) {
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
      <div className={styles.tiles} role="radiogroup" aria-label={input.label}>
        {options.map((option) => (
          <Tile
            key={option.id}
            option={option}
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
  return (
    <div className={styles.form}>
      {inputs.map((input) => {
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
            disabled={disabled}
            onChange={(next) => onChange(input.key, next)}
          />
        );
      })}
    </div>
  );
}

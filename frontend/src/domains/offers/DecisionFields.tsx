import { useMemo, useState } from "react";
import { IconCoins } from "@tabler/icons-react";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { useGameData } from "@/state/useGameContext";
import {
  classifyOptions,
  slotGroups,
  splitDeclines,
  stackRange,
  stacksOf,
  withStackCount,
  type Classified,
} from "./optionKinds";
import { SlotsMapField } from "./SlotsMapField";
import { describeOption, useOptionLookups } from "./DecisionPickers";
import { AutoButton } from "@/shared/ui/AutoButton/AutoButton";
import { Stepper } from "@/shared/ui/Stepper/Stepper";
import { DeclineRow, FieldHead, metaOf, pickNote, Tile, UnitStackStepper } from "./DecisionTiles";
import { PaymentTiles } from "./PaymentTiles";
import { GroupedMapField } from "./GroupedMapField";
import { TechPickField } from "./TechPickField";
import { routeOf, RouteNumbersField, type Route } from "./RouteNumbersField";
import { autoPay } from "@/domains/technology/techModel";
import { movesOf, UnitMovesField } from "./UnitMovesField";
import styles from "./DecisionFields.module.css";

/*
 * Wspólne pola decyzji gracza (oferty „may”, zdolności, technologie, karty, relikty). Backend
 * opisuje wejścia (choice / multi / number) i legalne opcje; tu zamieniamy je na kafelki do
 * kliknięcia zamiast list rozwijanych, a liczby na stepper. Opcje z ``meta`` dostają grafikę:
 * jednostka (sprite w kolorze gracza), planeta (wartość do zapłaty), kość (wynik i trafienie).
 * Płatność (planety + trade goods) to jeden widżet z paskiem „zapłacono X / Y”.
 */

/**
 * Powyżej tylu opcji kafelki dostają pomocniczy filtr i przewijaną siatkę - nadal kafelki, nigdy
 * lista rozwijana (U6, decyzja użytkownika P2: klik/drag zamiast list).
 */
const MAX_TILES = 18;

/** Option labels longer than this get one full-width row each (``data-wide``). */
const WIDE_LABEL = 26;

/** Filtr pomocniczy dużej siatki kafelków: dopasowanie po etykiecie (bez rozróżniania wielkości). */
function useTileFilter(options: ActionCardOption[]) {
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const visible = needle
    ? options.filter((o) => o.label.toLowerCase().includes(needle))
    : options;
  return { query, setQuery, visible, many: options.length > MAX_TILES };
}

function TileFilter({
  label,
  query,
  onChange,
  shown,
  total,
}: {
  label: string;
  query: string;
  onChange: (query: string) => void;
  shown: number;
  total: number;
}) {
  return (
    <input
      type="search"
      className={styles.filter}
      aria-label={`Filter ${label}`}
      placeholder={`Filter ${total} options…${query ? ` (${shown} shown)` : ""}`}
      value={query}
      onChange={(e) => onChange(e.currentTarget.value)}
    />
  );
}

type Payment = { cost: number; valueKind: string; tradeGoods: string };
type ChoiceInput = Extract<ActionCardInput, { kind: "choice" }>;

function paymentOf(input: ActionCardInput): Payment | null {
  return input.kind === "multi" && input.payment ? input.payment : null;
}

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
    // „Auto” tylko dla wydawania i walki (decyzja użytkownika 2026-11-27) - wartość podpowiedziana
    // przez silnik; gracz może ją zmienić stepperem. Bez „Auto” stepper startuje od ``min``.
    const auto = input.auto;
    return (
      <div className={styles.field}>
        {input.hint && <p className={styles.hint}>{input.hint}</p>}
        {auto !== undefined && (
          <AutoButton disabled={disabled} onClick={() => onChange(auto)} />
        )}
        <Stepper
          label={input.label}
          value={typeof value === "number" ? value : (auto ?? input.min)}
          min={input.min}
          max={input.max}
          disabled={disabled}
          icon={
            /trade.?goods|\btg\b/i.test(`${input.key} ${input.label}`) ? (
              <IconCoins size={16} aria-hidden="true" />
            ) : undefined
          }
          onChange={onChange}
        />
      </div>
    );
  }

  // Informacja (np. „technologię wybierzesz po zagraniu”) - bez pola do wyboru.
  if (input.kind === "info") {
    if (input.show && input.options.length > 0) return <ShownCards input={input} />;
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
  // „Auto” wyboru z listy: tylko walka i wydawanie (decyzja użytkownika 2026-11-27).
  const autoId =
    input.kind === "choice" && input.auto !== undefined
      ? input.options.find((o) => o.value === input.auto)?.id
      : undefined;
  const field = (
    <ChoiceField
      input={input}
      value={value}
      disabled={disabled}
      onChange={onChange}
      mapActive={mapActive}
    />
  );
  if (autoId === undefined) return field;
  return (
    <div className={styles.field}>
      <AutoButton disabled={disabled} pressed={value === autoId} onClick={() => onChange(autoId)} />
      {field}
    </div>
  );
}

/**
 * Cards the player only LOOKS at (So Ata, Kyver - RULES.md 62.22): the same chips as a choice,
 * read-only (nothing to pick), the full card behind ⓘ.
 */
function ShownCards({ input }: { input: Extract<ActionCardInput, { kind: "info" }> }) {
  return (
    <div className={styles.field}>
      <FieldHead label={input.label} hint={input.hint} />
      <div className={styles.tiles} data-rich role="list" aria-label={input.label}>
        {input.options.map((option) => (
          <span key={option.id} role="listitem">
            <Tile option={option} multi={false} selected={false} disabled onClick={() => {}} />
          </span>
        ))}
      </div>
    </div>
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
  // Kafelki z opisem (technologia, cel, karta) są szersze - tekst zasady ma się zmieścić.
  const rich =
    classified?.kind === "technology" ||
    (!classified && options.some((o) => describeOption(o, idMap)));
  // Sentence-long labels ("Purge 1 relic fragment: gain 1 command token (fleet pool)") get a
  // full-width row each: clamped to a narrow tile, the options would look identical.
  const wide = !rich && options.some((o) => o.label.length > WIDE_LABEL);
  // Odmowy („Do not …”, „Decline”) osobno, za „or” - nie jako kolejny kafelek opcji (pkt 6 planu).
  const { regular, declines } = useMemo(() => splitDeclines(options), [options]);
  const filter = useTileFilter(regular);
  const stacks = useMemo(() => stacksOf(filter.visible), [filter.visible]);

  // Technologie do ODDANIA (Divert Funding) to zwykła lista kafelków z opisem, nie okno badania.
  const plainList = input.kind === "choice" && input.display === "list";
  if (classified?.kind === "technology" && !plainList) {
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
    const head = pickNote(picked.length, input.min, input.max);
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
          note={head.note}
          done={head.done}
        />
        {filter.many && (
          <TileFilter
            label={input.label}
            query={filter.query}
            onChange={filter.setQuery}
            shown={filter.visible.length}
            total={regular.length}
          />
        )}
        <div
          className={filter.many ? `${styles.tiles} ${styles.tilesScroll}` : styles.tiles}
          data-rich={rich || undefined}
        data-wide={wide || undefined}
        >
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
        <DeclineRow
          options={declines}
          isSelected={(id) => picked.includes(id)}
          disabled={disabled}
          onPick={toggle}
        />
        {input.max > 1 && regular.length > 1 && (
          <div className={styles.quick}>
            <button
              type="button"
              disabled={disabled || picked.length === Math.min(input.max, regular.length)}
              onClick={() => onChange(regular.slice(0, input.max).map((o) => o.id))}
            >
              {input.max >= regular.length ? "All" : `First ${input.max}`}
            </button>
            <button type="button" disabled={disabled || picked.length === 0} onClick={() => onChange([])}>
              None
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={styles.field}>
      <FieldHead
        label={input.label}
        hint={input.hint}
        {...pickNote(typeof value === "string" ? 1 : 0, 1, 1)}
      />
      {filter.many && (
        <TileFilter
          label={input.label}
          query={filter.query}
          onChange={filter.setQuery}
          shown={filter.visible.length}
          total={regular.length}
        />
      )}
      <div
        className={filter.many ? `${styles.tiles} ${styles.tilesScroll}` : styles.tiles}
        data-rich={rich || undefined}
        data-wide={wide || undefined}
        role="radiogroup"
        aria-label={input.label}
      >
        {filter.visible.map((option) => (
          <Tile
            key={option.id}
            option={option}
            kind={kindOf(option)}
            multi={false}
            selected={value === option.id}
            disabled={disabled}
            // Ponowny klik w wybrany kafelek odznacza (wybór nie jest „na zawsze”).
            onClick={() => onChange(value === option.id ? null : option.id)}
          />
        ))}
      </div>
      <DeclineRow
        options={declines}
        isSelected={(id) => value === id}
        disabled={disabled}
        onPick={(id) => onChange(value === id ? null : id)}
      />
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
  const toggle = (id: string) =>
    onChange(input.key, picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id]);
  // „Auto”: najtańsza płatność - planety od największych bez zbędnych, potem trade goods.
  const auto = () => {
    const worth = Object.fromEntries(
      input.options.map((o) => [o.id, typeof metaOf(o).value === "number" ? (metaOf(o).value as number) : 0]),
    );
    const pay = autoPay(worth, [], tgInput?.max ?? 0, payment.cost);
    onChange(input.key, pay.planets);
    if (tgInput) onChange(payment.tradeGoods, Math.max(tgInput.min, pay.tradeGoods));
  };

  return (
    <div className={styles.field}>
      <PaymentTiles
        title={`Pay ${payment.cost} ${payment.valueKind}`}
        hint={input.hint}
        cost={payment.cost}
        unit={payment.valueKind}
        planets={input.options}
        picked={picked}
        onTogglePlanet={toggle}
        tradeGoods={tg}
        tradeGoodsMin={tgInput?.min ?? 0}
        tradeGoodsMax={tgInput?.max ?? 0}
        onTradeGoods={(next) => onChange(payment.tradeGoods, next)}
        onAuto={auto}
        paid={paid}
        disabled={disabled}
      />
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
  // Jednakowe sloty z celami na mapie (bohater Yin) = jedno pole ``SlotsMapField``.
  const slots = useMemo(() => {
    const found = new Map<string, { inputs: ChoiceInput[]; classified: Classified }>();
    for (const [firstKey, keys] of slotGroups(inputs)) {
      const group = keys
        .map((k) => inputs.find((i) => i.key === k))
        .filter((i): i is ChoiceInput => i?.kind === "choice");
      const classified = group[0] ? classifyOptions(group[0].options, lookups) : null;
      if (classified && (classified.kind === "planet" || classified.kind === "system")) {
        found.set(firstKey, { inputs: group, classified });
      }
    }
    return found;
  }, [inputs, lookups]);
  const slotMember = new Set(
    [...slots.values()].flatMap((g) => g.inputs.slice(1).map((i) => i.key)),
  );
  const mapKey = useMemo(() => {
    const onMap = inputs.filter((input) => {
      if (input.kind !== "choice" && input.kind !== "multi") return false;
      if (paymentOf(input) || slotMember.has(input.key) || movesOf(input)) return false;
      const kind = classifyOptions(input.options, lookups)?.kind;
      return kind === "planet" || kind === "system";
    });
    const open = onMap.find((input) => {
      const v = values[input.key];
      return v === undefined || v === null || (Array.isArray(v) && v.length === 0);
    });
    return (open ?? onMap[0])?.key ?? null;
    // ``slotMember`` wynika z ``inputs`` i ``lookups``.
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
        if (slotMember.has(input.key)) return null;
        // Ruch z efektu = przeciąganie jednostek na mapie z linią (jak ruch taktyczny).
        const moves = movesOf(input);
        if (moves && input.kind === "multi") {
          return (
            <UnitMovesField
              key={input.key}
              input={input}
              moves={moves}
              value={values[input.key]}
              disabled={disabled}
              onChange={(next) => onChange(input.key, next)}
            />
          );
        }
        const slotGroup = slots.get(input.key);
        if (slotGroup) {
          return (
            <SlotsMapField
              key={input.key}
              inputs={slotGroup.inputs}
              classified={slotGroup.classified}
              values={values}
              disabled={disabled}
              mapActive={input.key === mapKey}
              onChange={onChange}
            />
          );
        }
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

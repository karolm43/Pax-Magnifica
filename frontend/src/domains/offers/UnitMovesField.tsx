import { useEffect, useMemo, useRef, useState } from "react";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { useMapTargets } from "@/domains/strategy/mapPick";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { lookupUnit } from "@/entities/lookup/units";
import { RouteUnitChip } from "@/domains/movement/RouteUnitChip";
import { asyncOfBase } from "@/domains/movement/routeTypes";
import { FieldHead } from "./DecisionTiles";
import { MapPickStatus } from "./MapPickStatus";
import styles from "./DecisionFields.module.css";
import boxStyles from "@/domains/movement/MoveRouteBox.module.css";

type MultiInput = Extract<ActionCardInput, { kind: "multi" }>;
type MoveOption = { id: string; unit: string; from: string; to: string; baseType: string };
type Stack = { key: string; from: string; baseType: string; units: string[]; dests: string[] };

/** Opcje ruchu z ``offer_inputs.unit_moves`` (``meta.move``) albo null dla zwykłego pola. */
export function movesOf(input: ActionCardInput): MoveOption[] | null {
  if (input.kind !== "multi" || input.options.length === 0) return null;
  const found: MoveOption[] = [];
  for (const option of input.options) {
    const move = option.meta?.move as { unit?: unknown; from?: unknown; to?: unknown } | undefined;
    const baseType = option.meta?.unit;
    if (
      typeof move?.unit !== "string" ||
      typeof move.from !== "string" ||
      typeof move.to !== "string" ||
      typeof baseType !== "string"
    ) {
      return null;
    }
    found.push({ id: option.id, unit: move.unit, from: move.from, to: move.to, baseType });
  }
  return found;
}

const SPACE = "space";

/**
 * Ruch jednostek z EFEKTU (bohater, przełom, karta) - TEN SAM schemat co zwykły ruch:
 *
 * 1. klik w świecący system ze swoimi statkami (albo Ctrl+klik jednostek na mapie),
 * 2. wybór jednostek: wiersze jak w ``MoveRouteBox`` (klik +1, prawy −1, Shift = wszystkie);
 *    wybór = zaznaczenie Ctrl na mapie (``multiSelect`` - licznik na stosie, plakietka przy
 *    kursorze), więc okno i mapa nigdy się nie rozjeżdżają,
 * 3. klik w świecący cel na mapie wysyła tam wybrane jednostki (albo przeciągnięcie stosu /
 *    zaznaczonej grupy na cel - ``useUnitDrag`` -> ``effectMove.onDrop``).
 *
 * Zaplanowane ruchy rysuje mapa (``EffectMoveLayer``), a okno trzyma listę „skąd -> dokąd” z
 * −/+. Ponowny klik w wybrany system go odznacza. Wartość pola = id opcji
 * ``"<jednostka>><cel>"``; legalność sprawdza silnik.
 */
export function UnitMovesField({
  input,
  moves,
  value,
  disabled,
  onChange,
}: {
  input: MultiInput;
  moves: MoveOption[];
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (next: string[]) => void;
}) {
  const gameData = useGameData();
  const setEffectMove = useAppStore((s) => s.setEffectMove);
  const setMoveRangeSources = useAppStore((s) => s.setMoveRangeSources);
  const dragKey = useAppStore((s) => s.effectMoveDrag);
  const selection = useAppStore((s) => s.multiSelect);
  const ctrlPickUnit = useAppStore((s) => s.ctrlPickUnit);
  const ctrlUnpickUnit = useAppStore((s) => s.ctrlUnpickUnit);
  const clearMultiSelect = useAppStore((s) => s.clearMultiSelect);
  const [picked, setPicked] = useState<string | null>(null);
  const [tip, setTip] = useState<string | null>(null);
  const chosen = useMemo(() => (Array.isArray(value) ? value : []), [value]);
  const meta = input.options[0]?.meta ?? {};
  const faction = typeof meta.faction === "string" ? meta.faction : "";
  const player = gameData?.playerData?.find((p) => p.faction === faction);
  const colorAlias = getColorAlias(player?.color);

  const byId = useMemo(() => new Map(moves.map((m) => [m.id, m])), [moves]);
  const stacks = useMemo(() => {
    const found = new Map<string, Stack>();
    for (const m of moves) {
      const key = `${m.from}|${m.baseType}`;
      const stack = found.get(key) ?? { key, from: m.from, baseType: m.baseType, units: [], dests: [] };
      if (!stack.units.includes(m.unit)) stack.units.push(m.unit);
      if (!stack.dests.includes(m.to)) stack.dests.push(m.to);
      found.set(key, stack);
    }
    return found;
  }, [moves]);
  const sources = useMemo(() => [...new Set([...stacks.values()].map((s) => s.from))], [stacks]);
  const assigned = new Map(
    chosen.map((id) => byId.get(id)).filter((m): m is MoveOption => m !== undefined).map((m) => [m.unit, m.to]),
  );
  const canGo = (unit: string, to: string) => byId.has(`${unit}>${to}`);
  const freeIn = (key: string) => stacks.get(key)?.units.filter((u) => !assigned.has(u)).length ?? 0;

  // Wybrany system: zaznaczenie Ctrl z mapy (gdy dotyczy tego ruchu) albo klik w system.
  const selectionHere =
    selection !== null && selection.faction === faction && sources.includes(selection.fromPosition)
      ? selection
      : null;
  const source = selectionHere?.fromPosition ?? picked;
  const sourceStacks = [...stacks.values()].filter((s) => s.from === source);
  const selectedOf = (baseType: string) =>
    selectionHere ? (selectionHere.items[`${asyncOfBase(baseType)}|${SPACE}`]?.count ?? 0) : 0;
  const selectedTotal = sourceStacks.reduce((n, s) => n + selectedOf(s.baseType), 0);
  const destinations = [...new Set(sourceStacks.flatMap((s) => s.dests))];

  /** Przenosi stosy (``key`` -> ``count`` sztuk) do ``to``: najpierw wolne, potem z innych celów. */
  const send = (items: { key: string; count: number }[], to: string) => {
    if (disabled) return;
    const taken: string[] = [];
    for (const { key, count } of items) {
      const stack = stacks.get(key);
      if (!stack) continue;
      const candidates = stack.units.filter((u) => canGo(u, to) && assigned.get(u) !== to);
      const free = candidates.filter((u) => !assigned.has(u));
      const elsewhere = candidates.filter((u) => assigned.has(u));
      taken.push(...[...free, ...elsewhere].slice(0, Math.max(0, count)));
    }
    if (taken.length === 0) return;
    const keep = chosen.filter((id) => !taken.includes(byId.get(id)?.unit ?? ""));
    onChange([...keep, ...taken.map((u) => `${u}>${to}`)]);
  };
  const bump = (key: string, to: string, delta: number) => {
    if (delta > 0) {
      const free = stacks.get(key)?.units.filter((u) => !assigned.has(u) && canGo(u, to)).length ?? 0;
      send([{ key, count: Math.min(delta, free) }], to);
      return;
    }
    const mine = chosen.filter((id) => {
      const m = byId.get(id);
      return m !== undefined && `${m.from}|${m.baseType}` === key && m.to === to;
    });
    const drop = new Set(mine.slice(Math.max(0, mine.length + delta)));
    onChange(chosen.filter((id) => !drop.has(id)));
  };

  /** Wybór jednostek stosu w systemie źródłowym = zaznaczenie Ctrl (+/−, Shift = wszystkie). */
  const select = (stack: Stack, delta: number) => {
    if (disabled) return;
    const asyncId = asyncOfBase(stack.baseType);
    const unit = { fromPosition: stack.from, faction, asyncId, fromZone: SPACE };
    const have = selectedOf(stack.baseType);
    const max = freeIn(stack.key);
    const target = Math.max(0, Math.min(max, have + delta));
    for (let i = have; i < target; i += 1) ctrlPickUnit({ ...unit, max });
    for (let i = have; i > target; i -= 1) ctrlUnpickUnit(unit);
    setTip(null);
  };
  const selectAll = () => {
    for (const stack of sourceStacks) select(stack, Number.POSITIVE_INFINITY);
  };

  /** Wysyła zaznaczone jednostki źródła do ``to`` (klik w cel albo upuszczenie grupy). */
  const commit = (to: string) => {
    const items = sourceStacks
      .map((s) => ({ key: s.key, count: selectedOf(s.baseType) }))
      .filter((i) => i.count > 0);
    send(items, to);
    clearMultiSelect();
  };

  const onPick = (position: string) => {
    if (disabled) return;
    setTip(null);
    if (position === source) {
      // Ponowny klik w wybrany system odznacza go (razem z zaznaczeniem).
      setPicked(null);
      clearMultiSelect();
      return;
    }
    if (source && destinations.includes(position)) {
      if (selectedTotal > 0) {
        commit(position);
        return;
      }
      if (!sources.includes(position)) {
        setTip("Choose the units first: click + on the list or Ctrl+click them on the map.");
        return;
      }
    }
    if (sources.includes(position)) {
      clearMultiSelect();
      setPicked(position);
    }
  };

  // Cele na mapie (jak każdy wybór w oknie decyzji): systemy ze statkami, a po wybraniu
  // systemu także jego cele. Okno trzyma mapę, dopóki jest otwarte.
  const pickTargets = source ? [...new Set([...sources, ...destinations])] : sources;
  const handle = useMapTargets({ systems: pickTargets }, (target) => onPick(target), {
    enabled: !disabled,
    selected: source,
  });

  // Ruchy pogrupowane „skąd -> dokąd” (kolejność pierwszego wyboru), w środku po typie.
  const groups = useMemo(() => {
    const found = new Map<string, { from: string; to: string; byType: Map<string, number> }>();
    for (const id of chosen) {
      const m = byId.get(id);
      if (!m) continue;
      const gk = `${m.from}>${m.to}`;
      const group = found.get(gk) ?? { from: m.from, to: m.to, byType: new Map<string, number>() };
      group.byType.set(m.baseType, (group.byType.get(m.baseType) ?? 0) + 1);
      found.set(gk, group);
    }
    return [...found.values()];
  }, [chosen, byId]);

  // Mapa: stosy tego ruchu da się przeciągać (pojedynczo albo grupą Ctrl), linie rysuje warstwa.
  const sendRef = useRef(send);
  sendRef.current = send;
  useEffect(() => {
    if (disabled || !faction) {
      setEffectMove(null);
      return;
    }
    setEffectMove({
      faction,
      dests: Object.fromEntries([...stacks.values()].map((s) => [s.key, s.dests])),
      onDrop: (items, to) => sendRef.current(items, to),
      lines: groups.map((g) => ({
        from: g.from,
        to: g.to,
        count: [...g.byType.values()].reduce((a, b) => a + b, 0),
      })),
    });
  }, [disabled, faction, stacks, groups, setEffectMove]);
  useEffect(
    () => () => {
      setEffectMove(null);
      useAppStore.getState().clearMultiSelect();
    },
    [setEffectMove],
  );

  // W trakcie przeciągania świecą cele przeciąganego stosu (poza tym - cele okna, jak wyżej).
  const glowKey = disabled || !dragKey ? "" : (stacks.get(dragKey)?.dests ?? []).join("|");
  useEffect(() => {
    setMoveRangeSources(new Set(glowKey === "" ? [] : glowKey.split("|")));
  }, [glowKey, setMoveRangeSources]);
  useEffect(() => () => setMoveRangeSources(new Set()), [setMoveRangeSources]);

  const tiles = gameData?.tiles ?? {};
  const systemName = (position: string): string => {
    const tile = tiles[position];
    const name = tile ? getTileById(tile.systemId)?.name : undefined;
    return name ? `${name} (${position})` : `System ${position}`;
  };
  const unitName = (baseType: string) =>
    lookupUnit(asyncOfBase(baseType), faction, player)?.name ?? baseType;
  const moving = chosen.length;

  return (
    <div className={styles.field} onPointerDownCapture={handle.claim}>
      <FieldHead
        label={input.label}
        hint={input.hint}
        note={moving > 0 ? `${moving} unit${moving === 1 ? "" : "s"} moving` : undefined}
      />

      {!source && (
        <>
          <MapPickStatus
            targets={sources.map((id) => ({ kind: "system", id }))}
            handle={handle}
            disabled={disabled}
          />
          <p className={styles.mapCall}>
            Click a glowing system with your ships, or Ctrl+click units on the map. You can also
            drag a stack straight onto its destination.
          </p>
        </>
      )}

      {source && (
        <section className={boxStyles.node} aria-label={`Units in ${systemName(source)}`}>
          <div className={boxStyles.nodeHead}>
            From {systemName(source)}
            {sourceStacks.some((s) => freeIn(s.key) > 0) && (
              <button type="button" className={boxStyles.link} disabled={disabled} onClick={selectAll}>
                Select all
              </button>
            )}
          </div>
          <div className={boxStyles.list}>
            {sourceStacks.map((stack) => (
              <RouteUnitChip
                key={stack.key}
                variant="row"
                asyncId={asyncOfBase(stack.baseType)}
                colorAlias={colorAlias}
                faction={faction}
                name={unitName(stack.baseType)}
                caption={freeIn(stack.key) === 0 ? "all already moving" : undefined}
                picked={selectedOf(stack.baseType)}
                max={freeIn(stack.key)}
                disabled={disabled || freeIn(stack.key) === 0}
                onChange={(delta) => select(stack, delta)}
              />
            ))}
          </div>
          {selectedTotal > 0 ? (
            <MapPickStatus
              targets={destinations.map((id) => ({ kind: "system", id }))}
              handle={handle}
              disabled={disabled}
            />
          ) : (
            <p className={styles.mapCall}>
              Choose units (click +1, right-click −1, Shift = all), then click a glowing
              destination on the map. Click this system again to deselect it.
            </p>
          )}
        </section>
      )}
      {tip && (
        <p className={styles.mapStatus} data-state="empty" role="status">
          {tip}
        </p>
      )}

      {groups.length > 0 && (
        <div className={boxStyles.sectionHead}>
          <span>Planned moves</span>
          <button type="button" className={boxStyles.link} disabled={disabled} onClick={() => onChange([])}>
            Clear all
          </button>
        </div>
      )}
      {groups.map((group) => (
        <div key={`${group.from}>${group.to}`} className={boxStyles.node}>
          <div className={boxStyles.nodeHead}>
            {systemName(group.from)} → {systemName(group.to)}
          </div>
          <div className={boxStyles.list}>
            {[...group.byType.entries()].map(([baseType, count]) => {
              const key = `${group.from}|${baseType}`;
              const free =
                stacks.get(key)?.units.filter((u) => !assigned.has(u) && canGo(u, group.to)).length ?? 0;
              return (
                <RouteUnitChip
                  key={baseType}
                  variant="row"
                  asyncId={asyncOfBase(baseType)}
                  colorAlias={colorAlias}
                  faction={faction}
                  name={unitName(baseType)}
                  picked={count}
                  max={count + free}
                  disabled={disabled}
                  onChange={(delta) => bump(key, group.to, delta)}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

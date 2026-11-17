import { useEffect, useRef, useState } from "react";
import type {
  BattleLogEntry,
  BattleRoll,
  BattleView,
} from "@/api/useBoardEditor";
import type { ShipEntity } from "./battleAssign";
import { countDice, diceLandMs, volleyStartMs } from "./diceRoll";

/**
 * Efekty wizualne pola bitwy (czysta prezentacja — wynik zawsze pochodzi z silnika).
 *
 * - ``useDyingShips``: egzemplarze, które zniknęły ze stanu, są jeszcze chwilę rysowane
 *   jako „eksplodujące", zanim znikną z pola.
 * - ``useVolley``: gdy w dzienniku pojawia się nowa salwa (AFB/rzuty), przygotowuje listę
 *   pocisków do animacji (strona, tor, trafienie, opóźnienie).
 */

const DYING_MS = 3800;
/**
 * Zgony jednej salwy NIE w tej samej chwili: kolejne egzemplarze giną co tyle ms (wybuchy
 * i dźwięki nie nakładają się w jeden huk), najwyżej `DIE_STAGGER_MAX` kroków.
 */
export const DIE_STAGGER_MS = 280;
const DIE_STAGGER_MAX = 6;
const VOLLEY_MS = 5200;
const MAX_BOLTS_PER_SIDE = 22;

const SUSTAIN_MS = 1400;
/** Czas życia odlatujących okrętów (zawrót + odlot ~4,4 s + opóźnienia szeregów). */
const LEAVING_MS = 6200;

export type ShipView = {
  ship: ShipEntity;
  dying: boolean;
  /** Opóźnienie śmierci tego egzemplarza (ms) — rozłożenie zgonów jednej salwy w czasie. */
  dieDelay: number;
  /** Okręt właśnie WYCOFUJE się z walki (odwrót) — odlatuje zamiast wybuchać. */
  leaving: boolean;
  justSustained: boolean;
};

/**
 * ``leaving`` = jednostki strony przeniesione w OSTATNIM odwrocie (baseType → liczba, z wpisu
 * RETREAT dziennika). Znikające egzemplarze tych typów odlatują; pozostałe (np. myśliwce bez
 * transportu, usunięte przy odwrocie) eksplodują jak zwykle.
 */
export function useDyingShips(
  ships: ShipEntity[],
  leaving: Record<string, number> | null = null,
): ShipView[] {
  const previous = useRef<ShipEntity[]>(ships);
  const latest = useRef<ShipEntity[]>(ships);
  latest.current = ships;
  const leavingRef = useRef(leaving);
  leavingRef.current = leaving;
  const [dying, setDying] = useState<ShipEntity[]>([]);
  const [delays, setDelays] = useState<Map<string, number>>(new Map());
  const placement = useRef<string[]>(ships.map((s) => s.id));
  const [departing, setDeparting] = useState<Set<string>>(new Set());
  // Egzemplarze, które WŁAŚNIE przyjęły Sustain Damage (były całe, teraz uszkodzone) —
  // błyskają tarczą przez chwilę, potem wracają do zwykłego wyglądu uszkodzonego.
  const [sustained, setSustained] = useState<Set<string>>(new Set());
  // Stabilna sygnatura składu floty: efekt reaguje tylko na realną zmianę egzemplarzy
  // (tablica ``ships`` jest nowa przy każdym renderze — zależność od niej kasowałaby timer).
  const signature = ships.map((s) => `${s.id}:${s.damaged ? 1 : 0}`).join(",");

  useEffect(() => {
    const ships = latest.current;
    const prev = previous.current;
    const current = new Set(ships.map((s) => s.id));
    const gone = prev.filter((s) => !current.has(s.id));
    const wasWhole = new Set(prev.filter((s) => !s.damaged).map((s) => s.id));
    const freshSustain = ships
      .filter((s) => s.damaged && wasWhole.has(s.id))
      .map((s) => s.id);
    previous.current = ships;
    if (freshSustain.length > 0) {
      setSustained((set) => new Set([...set, ...freshSustain]));
      window.setTimeout(() => {
        setSustained((set) => {
          const next = new Set(set);
          for (const id of freshSustain) next.delete(id);
          return next;
        });
      }, SUSTAIN_MS);
    }
    if (gone.length === 0) return;
    // Podział znikających: odlatujące (budżet z odwrotu wg typu) vs zniszczone.
    const budget = { ...(leavingRef.current ?? {}) };
    const leavingIds: string[] = [];
    for (const ship of gone) {
      if ((budget[ship.baseType] ?? 0) > 0) {
        budget[ship.baseType] -= 1;
        leavingIds.push(ship.id);
      }
    }
    if (leavingIds.length > 0) {
      setDeparting((set) => new Set([...set, ...leavingIds]));
    }
    // Kolejność zgonów: od pierwszej linii (indeks w szyku), co DIE_STAGGER_MS.
    const dyingNow = gone.filter((s) => !leavingIds.includes(s.id));
    const stagger = new Map(
      dyingNow.map((s, k) => [s.id, Math.min(k, DIE_STAGGER_MAX) * DIE_STAGGER_MS]),
    );
    setDelays((map) => new Map([...map, ...stagger]));
    const longest = Math.max(0, ...stagger.values());
    setDying((list) => [...list.filter((s) => !current.has(s.id)), ...gone]);
    window.setTimeout(() => {
      setDying((list) => list.filter((s) => !gone.some((g) => g.id === s.id)));
      setDeparting((set) => {
        const next = new Set(set);
        for (const id of leavingIds) next.delete(id);
        return next;
      });
      setDelays((map) => {
        const next = new Map(map);
        for (const g of gone) next.delete(g.id);
        return next;
      });
    }, leavingIds.length > 0 ? LEAVING_MS : DYING_MS + longest);
  }, [signature]);

  const alive = new Set(ships.map((s) => s.id));
  const views = new Map<string, ShipView>();
  for (const ship of ships) {
    views.set(ship.id, {
      ship,
      dying: false,
      dieDelay: 0,
      leaving: false,
      justSustained: sustained.has(ship.id),
    });
  }
  for (const ship of dying) {
    if (alive.has(ship.id)) continue;
    const leaves = departing.has(ship.id);
    views.set(ship.id, {
      ship,
      dying: !leaves,
      dieDelay: delays.get(ship.id) ?? 0,
      leaving: leaves,
      justSustained: false,
    });
  }
  // Konający okręt zostaje na SWOIM miejscu w szyku (nie przeskakuje na koniec szeregu):
  // kolejność z poprzedniego renderu, nowe egzemplarze na końcu. Przestawienie elementu
  // w DOM restartowałoby też jego animacje CSS (np. wlot floty).
  const order = [
    ...placement.current.filter((id) => views.has(id)),
    ...[...views.keys()].filter((id) => !placement.current.includes(id)),
  ];
  placement.current = order;
  return order.map((id) => views.get(id)!);
}

export type Bolt = {
  id: string;
  /** Strona strzelająca: lewa (atakujący) albo prawa (obrońca). */
  from: "left" | "right";
  hit: boolean;
  /** Typ jednostki, która oddała strzał (pocisk startuje z okrętu tego typu). */
  baseType: string;
  /** Indeks pocisku w obrębie typu — rozdziela strzały między egzemplarze. */
  shot: number;
  delayMs: number;
};

export type Volley = {
  id: number;
  phase: BattleLogEntry["phase"];
  bolts: Bolt[];
  /** Rzuty obu stron (do fizycznej animacji kostek na stole). */
  rolls: { left: BattleRoll[]; right: BattleRoll[] };
  /** Kiedy kości leżą już na stole (ms od początku salwy) — wtedy dopiero ruszają strzały. */
  diceMs: number;
};

function boltsFor(
  entry: BattleLogEntry,
  player: string,
  from: "left" | "right",
  volleyId: number,
  startMs: number,
): Bolt[] {
  const rolls = entry.rolls[player] ?? [];
  const dice = rolls.flatMap((roll) =>
    roll.dice.map((value, shot) => ({
      baseType: roll.baseType,
      shot,
      hit: value + roll.modifier >= roll.hitsOn,
    })),
  );
  // Trafienia najpierw, żeby przy limicie pocisków zawsze były widoczne.
  const ordered = [
    ...dice.filter((d) => d.hit),
    ...dice.filter((d) => !d.hit),
  ].slice(0, MAX_BOLTS_PER_SIDE);
  return ordered.map((die, i) => ({
    id: `${volleyId}-${from}-${i}`,
    from,
    hit: die.hit,
    baseType: die.baseType,
    shot: die.shot,
    // Atakujący strzela pierwszy, obrońca odpowiada (RULES.md 39 W5).
    // Strzały ruszają dopiero, gdy kości leżą na stole.
    delayMs:
      startMs + (from === "left" ? 0 : 1500) + i * 190 + Math.random() * 120,
  }));
}

/** Nowa salwa po każdym nowym wpisie dziennika (bez odtwarzania historii przy otwarciu). */
export function useVolley(view: BattleView | undefined): Volley | null {
  const seen = useRef<number | null>(null);
  const latest = useRef(view);
  latest.current = view;
  const [volley, setVolley] = useState<Volley | null>(null);
  const length = view?.log.length ?? 0;

  // Zależność tylko od długości dziennika (nowa salwa), nie od obiektu widoku — inaczej
  // każdy odczyt stanu kasowałby timer animacji.
  useEffect(() => {
    const view = latest.current;
    if (!view?.attacker || !view.defender) return;
    if (seen.current === null) {
      seen.current = length; // pierwszy odczyt: nie animuj tego, co już było
      return;
    }
    if (length <= seen.current) {
      seen.current = length;
      return;
    }
    seen.current = length;
    const entry = view.log[length - 1];
    const id = Date.now();
    const left = entry.rolls[view.attacker.faction] ?? [];
    const right = entry.rolls[view.defender.faction] ?? [];
    const diceMs = diceLandMs(countDice(left), countDice(right));
    const startMs = volleyStartMs(countDice(left), countDice(right));
    setVolley({
      id,
      phase: entry.phase,
      rolls: { left, right },
      diceMs,
      bolts: [
        ...boltsFor(entry, view.attacker.faction, "left", id, startMs),
        ...boltsFor(entry, view.defender.faction, "right", id, startMs),
      ],
    });
    window.setTimeout(
      () => setVolley((v) => (v?.id === id ? null : v)),
      VOLLEY_MS + startMs,
    );
  }, [length]);

  return volley;
}

/** Najwyższe widziane „życie" strony (pasek HP = bieżące / startowe). */
export function useMaxHp(key: string, hp: number): number {
  const best = useRef<{ key: string; hp: number }>({ key, hp });
  if (best.current.key !== key) best.current = { key, hp };
  if (hp > best.current.hp) best.current.hp = hp;
  return best.current.hp;
}

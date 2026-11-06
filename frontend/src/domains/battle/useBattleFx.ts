import { useEffect, useRef, useState } from "react";
import type { BattleLogEntry, BattleView } from "@/api/useBoardEditor";
import type { ShipEntity } from "./battleAssign";

/**
 * Efekty wizualne pola bitwy (czysta prezentacja — wynik zawsze pochodzi z silnika).
 *
 * - ``useDyingShips``: egzemplarze, które zniknęły ze stanu, są jeszcze chwilę rysowane
 *   jako „eksplodujące", zanim znikną z pola.
 * - ``useVolley``: gdy w dzienniku pojawia się nowa salwa (AFB/rzuty), przygotowuje listę
 *   pocisków do animacji (strona, tor, trafienie, opóźnienie).
 */

const DYING_MS = 3800;
const VOLLEY_MS = 5200;
const MAX_BOLTS_PER_SIDE = 22;

export type ShipView = { ship: ShipEntity; dying: boolean };

export function useDyingShips(ships: ShipEntity[]): ShipView[] {
  const previous = useRef<ShipEntity[]>(ships);
  const latest = useRef<ShipEntity[]>(ships);
  latest.current = ships;
  const [dying, setDying] = useState<ShipEntity[]>([]);
  // Stabilna sygnatura składu floty: efekt reaguje tylko na realną zmianę egzemplarzy
  // (tablica ``ships`` jest nowa przy każdym renderze — zależność od niej kasowałaby timer).
  const signature = ships.map((s) => `${s.id}:${s.damaged ? 1 : 0}`).join(",");

  useEffect(() => {
    const ships = latest.current;
    const current = new Set(ships.map((s) => s.id));
    const gone = previous.current.filter((s) => !current.has(s.id));
    previous.current = ships;
    if (gone.length === 0) return;
    setDying((list) => [...list.filter((s) => !current.has(s.id)), ...gone]);
    window.setTimeout(() => {
      setDying((list) => list.filter((s) => !gone.some((g) => g.id === s.id)));
    }, DYING_MS);
  }, [signature]);

  const alive = new Set(ships.map((s) => s.id));
  return [
    ...ships.map((ship) => ({ ship, dying: false })),
    ...dying
      .filter((s) => !alive.has(s.id))
      .map((ship) => ({ ship, dying: true })),
  ];
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
};

function boltsFor(
  entry: BattleLogEntry,
  player: string,
  from: "left" | "right",
  volleyId: number,
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
    delayMs: (from === "left" ? 0 : 1500) + i * 190 + Math.random() * 120,
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
    setVolley({
      id,
      phase: entry.phase,
      bolts: [
        ...boltsFor(entry, view.attacker.faction, "left", id),
        ...boltsFor(entry, view.defender.faction, "right", id),
      ],
    });
    window.setTimeout(
      () => setVolley((v) => (v?.id === id ? null : v)),
      VOLLEY_MS,
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

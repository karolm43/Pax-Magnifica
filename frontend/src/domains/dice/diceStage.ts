import { create } from "zustand";
import type { HoldState } from "./HoldRollButton";
import {
  countDice,
  diceLandMs,
  volleyStartMs,
  type DiceGroup,
} from "@/domains/battle/diceRoll";

/**
 * WSPÓLNA SCENA KOŚCI: jedno miejsce, w którym każde okno gry (Space Cannon, bombardowanie,
 * Fracture, karty akcji…) pokazuje fizyczny rzut kośćmi d10. Wynik rzutu ZAWSZE pochodzi z
 * silnika (``core/dice.py``); scena tylko go odtwarza. Pole bitwy ma własny, wbudowany stół
 * (``BattleOverlay``) i tej sceny nie używa.
 *
 * Użycie w oknie:
 *  - rzut gotowy z silnika → ``throwDice({ left: [grupy], leftRgb })``; zwrócone ``pauseMs`` to
 *    czas do wylądowania kości (do tego momentu nie zdradzaj wyniku w UI),
 *  - przycisk rzutu → ``<HoldRollButton onHold={…}>`` + ``holdDice`` (pula po przytrzymaniu).
 * Montuje ``DiceStageHost`` (raz, w ``GameMapPage``).
 */

export type DiceThrowInput = {
  /** Kości lewej strony (rzucającego) — przy ``solo`` jedyne. */
  left: DiceGroup[];
  right?: DiceGroup[];
  /** Składowe RGB oddzielone spacjami (np. "56 189 248"). */
  leftRgb: string;
  rightRgb?: string;
  /** Rzuca jedna strona: kostki lądują pośrodku. Domyślnie true, gdy brak ``right``. */
  solo?: boolean;
};

export type StageRoll = {
  id: number;
  rolls: { left: DiceGroup[]; right: DiceGroup[] };
  diceMs: number;
  solo: boolean;
  leftRgb: string;
  rightRgb: string;
  fromPool: boolean;
  pool: { left: number; right: number };
};

type PoolState = {
  phase: "off" | "hold" | "await";
  at: number;
  left: number;
  right: number;
  solo: boolean;
  leftRgb: string;
  rightRgb: string;
};

type Stage = {
  roll: StageRoll | null;
  pool: PoolState;
  holdStart: (pool: Omit<PoolState, "phase" | "at">) => void;
  holdFire: () => void;
  holdCancel: () => void;
  throwDice: (input: DiceThrowInput) => { id: number; pauseMs: number };
};

const IDLE_POOL: PoolState = {
  phase: "off",
  at: 0,
  left: 0,
  right: 0,
  solo: true,
  leftRgb: "148 163 184",
  rightRgb: "148 163 184",
};

/**
 * Handler ``onHold`` dla przycisku rzutu jednej strony: ``count`` kości w puli w kolorze ``rgb``.
 * Dla okien innych niż pole bitwy (Space Cannon, bombardowanie…).
 */
export function soloHold(
  count: number,
  rgb: string,
): (state: HoldState) => void {
  return (state) => {
    const stage = useDiceStage.getState();
    if (state === "start") {
      stage.holdStart({
        left: count,
        right: 0,
        solo: true,
        leftRgb: rgb,
        rightRgb: rgb,
      });
    } else if (state === "fire") stage.holdFire();
    else stage.holdCancel();
  };
}

/** Po tylu ms od puszczenia „Roll" pula znika, jeśli rzut nie nadszedł (np. błąd 422). */
const AWAIT_MS = 3000;

let lastId = 0;
const nextId = () => {
  lastId = Math.max(Date.now(), lastId + 1);
  return lastId;
};

export const useDiceStage = create<Stage>((set, get) => ({
  roll: null,
  pool: IDLE_POOL,
  holdStart: (pool) => set({ pool: { ...pool, phase: "hold", at: 0 } }),
  holdFire: () => {
    const at = Date.now();
    set((s) => ({ pool: { ...s.pool, phase: "await", at } }));
    window.setTimeout(() => {
      const { pool } = get();
      if (pool.phase === "await" && pool.at === at) {
        set({ pool: { ...pool, phase: "off" } });
      }
    }, AWAIT_MS);
  },
  holdCancel: () => set((s) => ({ pool: { ...s.pool, phase: "off" } })),
  throwDice: (input) => {
    const id = nextId();
    const right = input.right ?? [];
    const solo = input.solo ?? right.length === 0;
    const { pool } = get();
    const fromPool =
      pool.phase === "await" && pool.at > 0 && id - pool.at < 4000;
    const left = countDice(input.left);
    const rightN = countDice(right);
    set({
      pool: { ...IDLE_POOL },
      roll: {
        id,
        rolls: { left: input.left, right },
        diceMs: diceLandMs(left, rightN),
        solo,
        leftRgb: input.leftRgb,
        rightRgb: input.rightRgb ?? input.leftRgb,
        fromPool,
        pool: { left: pool.left, right: pool.right },
      },
    });
    return { id, pauseMs: volleyStartMs(left, rightN) };
  },
}));

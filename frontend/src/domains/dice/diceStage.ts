import { create } from "zustand";
import type { HoldState } from "./HoldRollButton";
import {
  countDice,
  diceLandMs,
  READ_MS,
  volleyStartMs,
  type DiceGroup,
} from "@/domains/battle/diceRoll";
import { useDiceGate } from "./diceGate";

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
  /**
   * ``Date.now()`` of the moment the caller's own reveal timers (CSS ``--wait``, ``setTimeout``)
   * started. The dice are anchored to it, so a late render / throttled tab makes them skip ahead
   * instead of landing AFTER the result was already revealed.
   */
  startedAt?: number;
};

export type StageRoll = {
  id: number;
  /** Wall-clock start the dice animation is anchored to (see ``DiceThrowInput.startedAt``). */
  startedAt: number;
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
  /** Czyści scenę (rzut i pulę) - przy odmontowaniu strony gry, żeby nowa gra nie odtworzyła starego rzutu. */
  reset: () => void;
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
    const startedAt = Math.min(input.startedAt ?? id, id);
    set({
      pool: { ...IDLE_POOL },
      roll: {
        id,
        startedAt,
        rolls: { left: input.left, right },
        diceMs: diceLandMs(left, rightN),
        solo,
        leftRgb: input.leftRgb,
        rightRgb: input.rightRgb ?? input.leftRgb,
        fromPool,
        pool: { left: pool.left, right: pool.right },
      },
    });
    // Rzut żyje tylko do zniknięcia stołu: potem czyścimy go ze sceny, inaczej każde ponowne
    // zamontowanie DiceStageHost (np. menu -> nowa gra) odtwarzałoby ostatni rzut od nowa.
    const lifeMs = diceLandMs(left, rightN) + READ_MS + 1500 + 600;
    window.setTimeout(() => {
      if (get().roll?.id === id) set({ roll: null });
    }, lifeMs);
    // Time left until the dice have landed, counted from the caller's own start.
    const pauseMs = Math.max(
      0,
      startedAt + volleyStartMs(left, rightN) - Date.now(),
    );
    // Reszta UI (oferty, limity, powiadomienia) czeka, aż kości wylądują (``diceGate``).
    useDiceGate.getState().hold(pauseMs);
    return { id, pauseMs };
  },
  reset: () => set({ roll: null, pool: IDLE_POOL }),
}));

// Store konfiguracji kreatora setupu (Setup_Wizard) — Zustand.
//
// Trzyma PEŁNY, autorytatywny model slotu gracza (per gracz) oraz stan nawigacji po
// krokach wg `SETUP_STEPS`. To ten store jest „jednym źródłem prawdy" konfiguracji nowej
// gry na froncie: kroki (zadania 12.x) czytają i zapisują te same pola, a kontener
// (`SetupWizard.tsx`) mapuje stan na `NewGameRequest` i wysyła do `/game/new`.
//
// Zgodnie z komentarzem w `setupSteps.ts`, tymczasowy `SlotConfig` z tamtego modułu jest
// MINIMALNY (tylko `startingTechAmount` pod predykat `isApplicable`). Pełny model slotu
// żyje TUTAJ (`SetupSlot`), a `setupSteps.ts` otrzymuje widok zawężony do `SlotConfig`
// przez pomocniczą projekcję `toSlotConfig`.

import { create } from "zustand";
import { SETUP_STEPS, type SetupStepDef, type SlotConfig } from "./setupSteps";
import { hasDeferredStartingTech } from "./deferredTech";
import type { FactionInfo, NewGamePlayer } from "@/api/useNewGame";

/** Typ sterowania graczem — odwzorowuje `ControlType` z backendu (R10.1). */
export type ControlType = "HUMAN" | "BOT";

/** Specjalna wartość oznaczająca „losowa frakcja" (gdy gracz nie wybrał jawnie). */
export const RANDOM_FACTION = "__random__";

/**
 * Zbiór dostępnych kolorów graczy. Kolejność i wartości zgodne z backendem
 * (`HOME_SLOT_COLORS_6P` w `src/core/home_slots.py`); liczność (6) >= maksymalnej liczby
 * graczy, co spełnia R7.7. To JEDYNE źródło kolorów na froncie — kroki czytają stąd.
 */
export const AVAILABLE_COLORS = [
  "red",
  "green",
  "white",
  "blue",
  "purple",
  "yellow",
] as const;

export type PlayerColor = (typeof AVAILABLE_COLORS)[number];

/** Zakres liczby graczy wspierany przez układ 6-osobowy (R11.3). */
export const MIN_PLAYERS = 2;
export const MAX_PLAYERS = 6;
export const DEFAULT_PLAYERS = 6;

/** Maksymalna długość nazwy wyświetlanej po strip (R7.2/R1.4). */
export const MAX_NAME_LENGTH = 50;

/**
 * Pełna konfiguracja jednego slotu gracza w setupie.
 *
 * - `name` — nazwa wyświetlana (pusta → backend nada automatyczną, R7.3).
 * - `color` — kolor ze zbioru `AVAILABLE_COLORS`.
 * - `factionId` — `RANDOM_FACTION` oznacza „losowa"; inaczej id grywalnej frakcji.
 * - `startingTech` — wybrane technologie startowe (tylko dla frakcji z wyborem).
 * - `controlType` — HUMAN/BOT (R10.1).
 * - `difficulty` — poziom trudności bota; `null` = losowa (BOT) lub brak (HUMAN, R10.4).
 * - `personality` — osobowość bota; `null` = losowa (BOT) lub brak (HUMAN).
 */
export interface SetupSlot {
  name: string;
  color: PlayerColor;
  factionId: string;
  startingTech: string[];
  controlType: ControlType;
  difficulty: string | null;
  personality: string | null;
}

/** Projekcja pełnego slotu do minimalnego `SlotConfig` wymaganego przez `setupSteps.ts`. */
export function toSlotConfig(
  slot: SetupSlot,
  factionById: Map<string, FactionInfo>,
): SlotConfig {
  const faction =
    slot.factionId !== RANDOM_FACTION ? factionById.get(slot.factionId) : undefined;
  return { startingTechAmount: faction?.starting_tech_amount ?? 0 };
}

/** Domyślny slot dla gracza o indeksie `index` (kolor przydzielany po kolejności). */
function makeDefaultSlot(index: number): SetupSlot {
  return {
    name: "",
    color: AVAILABLE_COLORS[index % AVAILABLE_COLORS.length],
    factionId: RANDOM_FACTION,
    startingTech: [],
    controlType: "HUMAN",
    difficulty: null,
    personality: null,
  };
}

/** Buduje listę `count` domyślnych slotów, zachowując istniejące wpisy przy zmianie liczby. */
function resizeSlots(prev: SetupSlot[], count: number): SetupSlot[] {
  const next: SetupSlot[] = [];
  for (let i = 0; i < count; i++) {
    next.push(prev[i] ?? makeDefaultSlot(i));
  }
  return next;
}

export interface SetupStore {
  /** Liczba graczy (slotów); zmiana przeskalowuje `slots`, zachowując dane. */
  playerCount: number;
  /** Konfiguracje slotów (indeks = numer gracza, 0-bazowy). */
  slots: SetupSlot[];
  /** Opcjonalny map string (puste → mapa testowa po stronie backendu). */
  mapString: string;
  /** Indeks bieżącego kroku w `SETUP_STEPS` (0-bazowy). */
  currentStepIndex: number;

  setPlayerCount: (count: number) => void;
  /** Aktualizuje wybrane pola jednego slotu (reszta bez zmian). */
  updateSlot: (index: number, patch: Partial<SetupSlot>) => void;
  /**
   * Ustawia frakcję slotu i CZYŚCI jego technologie startowe (R9.4 — zmiana frakcji
   * kasuje poprzedni wybór). Wspólna akcja, bo ta inwariantna reguła dotyczy każdego
   * miejsca, w którym zmienia się frakcja.
   */
  setFaction: (index: number, factionId: string) => void;
  /**
   * Ustawia typ sterowania; przełączenie na HUMAN czyści `difficulty` (R10.4), a na BOT
   * zostawia je puste do czasu jawnego wyboru (walidacja kroku wymusi wartość — R10.2).
   */
  setControlType: (index: number, controlType: ControlType) => void;
  setMapString: (value: string) => void;
  goToStep: (index: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  /** Przywraca store do stanu początkowego (np. przy ponownym wejściu w setup). */
  reset: () => void;
}

function initialSlots(): SetupSlot[] {
  return resizeSlots([], DEFAULT_PLAYERS);
}

export const useSetupStore = create<SetupStore>((set) => ({
  playerCount: DEFAULT_PLAYERS,
  slots: initialSlots(),
  mapString: "",
  currentStepIndex: 0,

  setPlayerCount: (count) =>
    set((state) => {
      const clamped = Math.min(MAX_PLAYERS, Math.max(MIN_PLAYERS, count));
      return { playerCount: clamped, slots: resizeSlots(state.slots, clamped) };
    }),

  updateSlot: (index, patch) =>
    set((state) => ({
      slots: state.slots.map((slot, i) => (i === index ? { ...slot, ...patch } : slot)),
    })),

  setFaction: (index, factionId) =>
    set((state) => ({
      slots: state.slots.map((slot, i) =>
        i === index ? { ...slot, factionId, startingTech: [] } : slot,
      ),
    })),

  setControlType: (index, controlType) =>
    set((state) => ({
      slots: state.slots.map((slot, i) =>
        i === index
          ? {
              ...slot,
              controlType,
              // HUMAN nie ma trudności ani osobowości; BOT zaczyna z pustym
              // wyborem (= losowo).
              difficulty: controlType === "HUMAN" ? null : slot.difficulty,
              personality: controlType === "HUMAN" ? null : slot.personality,
            }
          : slot,
      ),
    })),

  setMapString: (value) => set({ mapString: value }),

  goToStep: (index) =>
    set(() => ({
      currentStepIndex: Math.max(0, Math.min(index, SETUP_STEPS.length - 1)),
    })),

  nextStep: () =>
    set((state) => ({
      currentStepIndex: Math.min(state.currentStepIndex + 1, SETUP_STEPS.length - 1),
    })),

  prevStep: () =>
    set((state) => ({
      currentStepIndex: Math.max(state.currentStepIndex - 1, 0),
    })),

  reset: () =>
    set({
      playerCount: DEFAULT_PLAYERS,
      slots: initialSlots(),
      mapString: "",
      currentStepIndex: 0,
    }),
}));

// ── Czysta logika walidacji i mapowania (testowalna bez Reacta) ───────────────────

/** Czy nazwa po strip mieści się w 0..MAX (pusta jest OK → backend nada auto). */
function isNameLengthValid(name: string): boolean {
  return name.trim().length <= MAX_NAME_LENGTH;
}

// Walidacje per reguła — każda zwraca komunikat (po polsku, wskazujący slot) albo
// `null`. Rozbite na osobne funkcje, by walidacja „Dalej" mogła sprawdzać TYLKO
// reguły bieżącego kroku (patrz `validateStep`), a nie wymagać np. technologii,
// zanim gracz w ogóle dojdzie do kroku technologii (to blokowało przejście dalej).

/** Nazwy: długość + brak duplikatów niepustych (case-insensitive, po strip) — R7.4/R7.5. */
function validateNames(slots: SetupSlot[]): string | null {
  const seenNames = new Set<string>();
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i];
    if (!isNameLengthValid(slot.name)) {
      return `Player ${i + 1}: the name may have at most ${MAX_NAME_LENGTH} characters.`;
    }
    const normalized = slot.name.trim().toLowerCase();
    if (normalized.length > 0) {
      if (seenNames.has(normalized)) {
        return `Player ${i + 1}: the name "${slot.name.trim()}" is duplicated.`;
      }
      seenNames.add(normalized);
    }
  }
  return null;
}

/** Kolory: ze zbioru i bez duplikatów — R7.6/R7.8. */
function validateColors(slots: SetupSlot[]): string | null {
  const seenColors = new Set<string>();
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i];
    if (!AVAILABLE_COLORS.includes(slot.color)) {
      return `Player ${i + 1}: the color "${slot.color}" is not in the allowed set.`;
    }
    if (seenColors.has(slot.color)) {
      return `Player ${i + 1}: the color "${slot.color}" is duplicated.`;
    }
    seenColors.add(slot.color);
  }
  return null;
}

/** Frakcje: duplikaty jawnych wyborów — R8.8 (losowe pomijamy, dobiera backend). */
function validateFactions(slots: SetupSlot[]): string | null {
  const seenFactions = new Set<string>();
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i];
    if (slot.factionId === RANDOM_FACTION) continue;
    if (seenFactions.has(slot.factionId)) {
      return `Player ${i + 1}: the faction is duplicated.`;
    }
    seenFactions.add(slot.factionId);
  }
  return null;
}

/** Technologie startowe: liczba zaznaczeń == wymagana przez frakcję — R9.2/R9.5. */
function validateStartingTech(
  slots: SetupSlot[],
  factionById: Map<string, FactionInfo>,
): string | null {
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i];
    if (slot.factionId === RANDOM_FACTION) continue;
    // Frakcje z ODROCZONYM wyborem (Keleres, Deepwrought) wybierają technologie w grze,
    // nie w setupie — nie wymagamy od nich zaznaczenia (i tak nie mają panelu wyboru).
    if (hasDeferredStartingTech(slot.factionId)) continue;
    const faction = factionById.get(slot.factionId);
    const amount = faction?.starting_tech_amount ?? 0;
    if (amount > 0 && slot.startingTech.length !== amount) {
      return `Player ${i + 1}: choose exactly ${amount} starting technologies.`;
    }
  }
  return null;
}

/** Sterowanie: trudność i osobowość bota są opcjonalne (brak = losowo), więc bez błędów. */
function validateControl(_slots: SetupSlot[]): string | null {
  return null;
}

/**
 * Waliduje reguły TYLKO danego kroku kreatora. Używane do blokady „Dalej": nie można
 * wymagać technologii startowych, zanim gracz dojdzie do kroku technologii, więc każdy
 * krok sprawdza wyłącznie SWOJE reguły. Zwraca komunikat błędu albo `null`.
 */
export function validateStep(
  stepId: SetupStepDef["id"],
  slots: SetupSlot[],
  factionById: Map<string, FactionInfo>,
): string | null {
  switch (stepId) {
    case "name-color":
      // Krok „Gracze": nazwa, kolor ORAZ sterowanie (człowiek/bot + trudność bota).
      return (
        validateNames(slots) ?? validateColors(slots) ?? validateControl(slots)
      );
    case "faction":
      // Wybór technologii startowych jest teraz wbudowany w krok frakcji (panel
      // podglądu), więc tu walidujemy i frakcje, i komplet technologii startowych.
      return (
        validateFactions(slots) ?? validateStartingTech(slots, factionById)
      );
    default:
      return null;
  }
}

/**
 * Pełna walidacja konfiguracji — wszystkie reguły naraz (R7.4–R7.6, R9.2/R9.5, R10.2).
 * Używana przy „Generuj" (ostatni krok): dopiero wtedy wymagamy kompletu. Zwraca
 * komunikat błędu (po polsku, wskazujący slot) albo `null`, gdy konfiguracja jest
 * kompletna i spójna.
 *
 * Uwaga: ostateczną, autorytatywną walidację robi backend (`resolve_players`); tu
 * blokujemy „Generuj", by nie wysyłać ewidentnie błędnej konfiguracji.
 */
export function validateSetup(
  slots: SetupSlot[],
  factionById: Map<string, FactionInfo>,
): string | null {
  return (
    validateNames(slots) ??
    validateColors(slots) ??
    validateFactions(slots) ??
    validateStartingTech(slots, factionById) ??
    validateControl(slots)
  );
}

/**
 * Mapuje konfigurację setupu na `NewGameRequest` wysyłany do `/game/new`.
 *
 * - Puste nazwy → `undefined` (backend nada automatyczną, R7.3).
 * - `RANDOM_FACTION` → `faction_id: undefined` (backend losuje bez powtórzeń, R8.5).
 * - Technologie startowe dołączamy tylko gdy frakcja wymaga wyboru i gracz coś zaznaczył.
 * - HUMAN nie wysyła `difficulty` (R10.4).
 */
export function toNewGameRequest(
  slots: SetupSlot[],
  mapString: string,
  factionById: Map<string, FactionInfo>,
): { players: NewGamePlayer[]; map_string?: string } {
  const players: NewGamePlayer[] = slots.map((slot) => {
    const name = slot.name.trim();
    const isRandom = slot.factionId === RANDOM_FACTION;
    const faction = isRandom ? undefined : factionById.get(slot.factionId);
    // Frakcje z odroczonym wyborem (Keleres, Deepwrought) NIE wysyłają technologii —
    // backend startuje je bez technologii, a wybór następuje w grze.
    const deferred = !isRandom && hasDeferredStartingTech(slot.factionId);
    const needsTechChoice = !deferred && (faction?.starting_tech_amount ?? 0) > 0;

    const player: NewGamePlayer = {
      faction_id: isRandom ? undefined : slot.factionId,
      name: name.length > 0 ? name : undefined,
      color: slot.color,
      control_type: slot.controlType,
      difficulty: slot.controlType === "BOT" ? slot.difficulty ?? undefined : undefined,
      personality: slot.controlType === "BOT" ? slot.personality ?? undefined : undefined,
    };
    if (needsTechChoice && slot.startingTech.length > 0) {
      player.starting_tech = slot.startingTech;
    }
    return player;
  });

  return {
    players,
    map_string: mapString.trim() || undefined,
  };
}

/** Bieżący krok wg `currentStepIndex` (bezpieczny względem zakresu). */
export function currentStep(index: number): SetupStepDef {
  return SETUP_STEPS[Math.max(0, Math.min(index, SETUP_STEPS.length - 1))];
}

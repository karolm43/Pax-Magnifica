import type { ComponentType } from "react";
import { ConstructionPrimary, ConstructionSecondary } from "./Construction";
import { DiplomacyPrimary, DiplomacySecondary } from "./Diplomacy";
import { ImperialPrimary, ImperialSecondary } from "./Imperial";
import { LeadershipPrimary, LeadershipSecondary } from "./Leadership";
import { PoliticsPrimary } from "./Politics";
import { TechnologyPrimary, TechnologySecondary } from "./Technology";
import { TradePrimary } from "./Trade";
import { WarfarePrimary } from "./Warfare";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/** Widoki kroków PRIMARY po numerze inicjatywy karty (RULES.md 30.5). */
export const PRIMARY_VIEWS: Record<number, ComponentType<PrimaryViewProps>> = {
  1: LeadershipPrimary,
  2: DiplomacyPrimary,
  3: PoliticsPrimary,
  4: ConstructionPrimary,
  5: TradePrimary,
  6: WarfarePrimary,
  7: TechnologyPrimary,
  8: ImperialPrimary,
};

/**
 * Widoki wyborów przy „follow" (SECONDARY) - tylko karty, które wymagają danych
 * (backend sygnalizuje to polem ``needs_input`` w opcjach).
 */
export const SECONDARY_VIEWS: Record<number, ComponentType<SecondaryViewProps>> = {
  1: LeadershipSecondary,
  2: DiplomacySecondary,
  4: ConstructionSecondary,
  7: TechnologySecondary,
  8: ImperialSecondary,
};

/**
 * Jak pokazać krok: okno modalne (domyślnie), nieblokujący dok u góry, wcale (inne okno
 * przejmuje ekran) albo pełnoekranowe okno, które widok rysuje sam (``overlay``).
 */
export type StepMode = "modal" | "dock" | "hidden" | "overlay";

/**
 * Wyjątki od domyślnego okna modalnego: kroki, w których gracz klika mapę / pracuje w innym
 * oknie (produkcja, akcja taktyczna, drzewo technologii), więc modal by przeszkadzał.
 */
export const PRIMARY_STEP_MODE: Record<number, Record<string, StepMode>> = {
  2: { choose_system: "dock" },
  4: { production: "hidden", place_structure: "dock", place_structure_2: "dock" },
  6: { activate_system: "dock", tactical_action: "dock" },
  7: { research: "overlay", research_paid: "overlay" },
};

/** Tryb pokazania wyborów przy „follow" (dok dla mapy, overlay dla drzewa technologii). */
export const SECONDARY_MODE: Record<number, StepMode> = {
  4: "dock",
  7: "overlay",
};

/**
 * Szerokość okna modalnego primary (domyślnie 560 px). Trade mieści stół transakcji
 * (TradingTable), więc dostaje tyle miejsca co okno Transaction.
 */
export const PRIMARY_MODAL_SIZE: Record<number, number> = {
  5: 1080,
};

import type { ComponentType } from "react";
import { ConstructionPrimary, ConstructionSecondary } from "./Construction";
import { DiplomacyPrimary, DiplomacySecondary } from "./Diplomacy";
import { ImperialPrimary, ImperialSecondary } from "./Imperial";
import { LeadershipPrimary, LeadershipSecondary } from "./Leadership";
import { PoliticsPrimary } from "./Politics";
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
  8: ImperialSecondary,
};

/** Jak pokazać krok primary: okno modalne (domyślnie), nieblokujący dok albo wcale. */
export type StepMode = "modal" | "dock" | "hidden";

/**
 * Wyjątki od domyślnego okna modalnego: kroki, w których gracz klika mapę / pracuje w innym
 * oknie (produkcja, akcja taktyczna), więc modal zasłaniałby to, czego potrzebuje.
 */
export const PRIMARY_STEP_MODE: Record<number, Record<string, StepMode>> = {
  4: { production: "hidden" },
  6: { activate_system: "dock", tactical_action: "dock" },
};

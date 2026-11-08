import type { ComponentType } from "react";
import { DiplomacyPrimary, DiplomacySecondary } from "./Diplomacy";
import { ImperialPrimary, ImperialSecondary } from "./Imperial";
import { LeadershipPrimary, LeadershipSecondary } from "./Leadership";
import { PoliticsPrimary } from "./Politics";
import { TradePrimary } from "./Trade";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/** Widoki kroków PRIMARY po numerze inicjatywy karty (RULES.md 30.5). */
export const PRIMARY_VIEWS: Record<number, ComponentType<PrimaryViewProps>> = {
  1: LeadershipPrimary,
  2: DiplomacyPrimary,
  3: PoliticsPrimary,
  5: TradePrimary,
  8: ImperialPrimary,
};

/**
 * Widoki wyborów przy „follow" (SECONDARY) - tylko karty, które wymagają danych
 * (backend sygnalizuje to polem ``needs_input`` w opcjach).
 */
export const SECONDARY_VIEWS: Record<number, ComponentType<SecondaryViewProps>> = {
  1: LeadershipSecondary,
  2: DiplomacySecondary,
  8: ImperialSecondary,
};

import type { ComponentType } from "react";
import { LeadershipPrimary, LeadershipSecondary } from "./Leadership";
import { TradePrimary } from "./Trade";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/** Widoki kroków PRIMARY po numerze inicjatywy karty (RULES.md 30.5). */
export const PRIMARY_VIEWS: Record<number, ComponentType<PrimaryViewProps>> = {
  1: LeadershipPrimary,
  5: TradePrimary,
};

/**
 * Widoki wyborów przy „follow" (SECONDARY) - tylko karty, które wymagają danych
 * (backend sygnalizuje to polem ``needs_input`` w opcjach).
 */
export const SECONDARY_VIEWS: Record<number, ComponentType<SecondaryViewProps>> = {
  1: LeadershipSecondary,
};

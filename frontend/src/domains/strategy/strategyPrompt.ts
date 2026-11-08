import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";

/*
 * Monit karty strategii (RULES.md 30.5): co TERAZ musi rozstrzygnąć dany gracz — krok
 * primary (właściciel karty) albo secondary (bieżący respondent okna). Dozwolone wybory
 * (planety do wydania, cele, gracze...) liczy backend (`GET /strategy/options`), więc UI
 * nie powiela reguł, a dane prywatne dostaje wyłącznie adresat monitu.
 */

export type StrategyPrompt = {
  kind: "primary" | "secondary";
  initiative: number;
  /** Bieżący krok primary; null dla secondary. */
  step: string | null;
  draft: Record<string, unknown>;
  /** Opcje z modułu karty — kształt zależy od karty i kroku. */
  options: Record<string, unknown>;
};

/** Pola gracza używane przez widoki kart (podzbiór `playerData`). */
export type PromptPlayer = {
  discordId: string;
  color: string;
  faction?: string | null;
  displayName?: string | null;
  userName?: string | null;
  flexibleDisplayName?: string | null;
  tacticalCC?: number;
  fleetCC?: number;
  strategicCC?: number;
  ccReinf?: number;
  tg?: number;
};

export type PoolSplit = { tactical: number; fleet: number; strategic: number };

export const EMPTY_SPLIT: PoolSplit = { tactical: 0, fleet: 0, strategic: 0 };

export function splitTotal(split: PoolSplit): number {
  return split.tactical + split.fleet + split.strategic;
}

/** Zapytanie o monit; `version` zmienia się z każdym krokiem/respondentem (świeże dane). */
export function useStrategyPrompt(playerId: string | null, version: string) {
  return useQuery<StrategyPrompt | null>({
    queryKey: ["strategy", "prompt", playerId, version],
    enabled: playerId != null,
    staleTime: 0,
    queryFn: async () =>
      fetchJson<StrategyPrompt | null>(
        `/bot/strategy/options?player_id=${encodeURIComponent(playerId ?? "")}`,
        "strategy options",
      ),
  });
}

/** Odczyt liczby z luźnego słownika opcji (0, gdy brak/nie liczba). */
export function num(value: unknown): number {
  return typeof value === "number" ? value : 0;
}

/** Odczyt słownika `{id: wartość}` z luźnych opcji. */
export function numberMap(value: unknown): Record<string, number> {
  if (value == null || typeof value !== "object") return {};
  const out: Record<string, number> = {};
  for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
    if (typeof val === "number") out[key] = val;
  }
  return out;
}

/** Odczyt listy napisów z luźnych opcji. */
export function strList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

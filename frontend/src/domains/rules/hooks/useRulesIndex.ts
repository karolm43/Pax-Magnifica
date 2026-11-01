import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import type { RulesIndex } from "@/domains/rules/types";

/*
 * Router reguł żyje w KORZENIU backendu pod prefiksem /rules. Proxy Vite mapuje
 * "/bot/<x>" -> "/<x>" na backendzie, więc bazą jest samo "/bot" (jak dla
 * pozostałych endpointów Custodian Engine, por. useNewGame.ts).
 */
const BOT_ROOT = "/bot";

/**
 * Pobiera pełny indeks tematów Zasad (GET /bot/rules -> /rules).
 *
 * Indeks jest statyczny (pliki Markdown na dysku), więc `staleTime: Infinity`
 * — nie ma potrzeby ponownego pobierania po pierwszym wczytaniu.
 */
export function useRulesIndex() {
  return useQuery<RulesIndex>({
    queryKey: ["rules", "index"],
    queryFn: () => fetchJson<RulesIndex>(`${BOT_ROOT}/rules`, "rules index"),
    staleTime: Infinity,
  });
}

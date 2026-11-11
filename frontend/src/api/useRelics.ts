import { useQuery } from "@tanstack/react-query";
import type { ActionCardInput } from "@/api/useActionCard";

/*
 * Relikty gracza (RULES.md 59). Zakładka „Relics" na ręce pokazuje WSZYSTKIE relikty gracza;
 * te z „ACTION:" można przeciągnąć na strefę zagrania (silnik mówi, które są legalne teraz),
 * pasywne działają same. Front nie zna reliktów - renderuje opis z backendu.
 */

/** Korzeń proxy do backendu silnika (jak w ``useActionCard``; NIE ``/bot/api``). */
const BOT_ROOT = "/bot";

/** Czy relikt jest zagrywalny (ACTION) czy pasywny + decyzja silnika o zagrywalności TERAZ. */
export type RelicPlayability = {
  relic_id: string;
  kind: "action" | "passive";
  playable: boolean;
  /** Powód, gdy nie - pokazywany w podpowiedzi karty. */
  reason: string | null;
  /** Dla pasywnych: czy silnik egzekwuje efekt; dla ACTION: czy ma zakodowany efekt. */
  implemented: boolean;
  exhausted: boolean;
};

/** Opis reliktu i formularza jego ACTION. */
export type RelicForm = {
  relic_id: string;
  name: string;
  text: string;
  kind: "action" | "passive";
  implemented: boolean;
  exhausted: boolean;
  summary?: string | null;
  inputs: ActionCardInput[];
};

/**
 * Relikty gracza z zagrywalnością (po ``relic_id``). Odświeżane co kilka sekund, bo zależy od
 * tury, fazy, okien i celów na planszy.
 */
export function useRelicPlayability(playerId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["relicPlayable", playerId],
    enabled: Boolean(playerId) && enabled,
    staleTime: 0,
    refetchInterval: 3000,
    retry: false,
    queryFn: async (): Promise<Record<string, RelicPlayability>> => {
      const url = `${BOT_ROOT}/relic/playable?player_id=${encodeURIComponent(playerId ?? "")}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Error ${response.status}`);
      const data = (await response.json()) as { relics: RelicPlayability[] };
      return Object.fromEntries(data.relics.map((relic) => [relic.relic_id, relic]));
    },
  });
}

/** Formularz ACTION reliktu dla gracza (relikt musi leżeć przed nim, inaczej 422). */
export function useRelicForm(relicId: string | null, playerId: string | null) {
  return useQuery({
    queryKey: ["relicForm", relicId, playerId],
    enabled: Boolean(relicId && playerId),
    // Opcje zależą od bieżącego stanu gry - nie cache'ujemy między otwarciami.
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async (): Promise<RelicForm> => {
      const id = encodeURIComponent(relicId ?? "");
      const player = encodeURIComponent(playerId ?? "");
      const response = await fetch(`${BOT_ROOT}/relic/${id}/inputs?player_id=${player}`);
      if (!response.ok) {
        const raw = await response.text().catch(() => "");
        let detail = `Error ${response.status}`;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed.detail === "string") detail = parsed.detail;
        } catch {
          // nie-JSON - zostaje kod statusu
        }
        throw new Error(detail);
      }
      return (await response.json()) as RelicForm;
    },
  });
}

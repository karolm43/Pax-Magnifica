import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";
import type { ActionCardInput } from "@/api/useActionCard";

/*
 * Użycie technologii (RULES.md 57): formularz wyborów dla „ACTION:" technologii oraz zdolności
 * używane poza akcją (np. Psychoarchaeology). Legalne opcje liczy silnik; gracz zawsze decyduje.
 */
const BOT_ROOT = "/bot";

export type TechnologyForm = {
  tech_id: string;
  name: string;
  text: string;
  /** `action` = „ACTION:" (akcja komponentu), `free` = zdolność poza akcją. */
  kind: "action" | "free";
  /** False = silnik nie automatyzuje efektu (akcja tylko zapisana, skutek ręcznie). */
  implemented: boolean;
  exhausted: boolean;
  inputs: ActionCardInput[];
};

export type TechnologyAbility = TechnologyForm & { usable: boolean; reason: string };

/** Formularz użycia technologii dla gracza (technologia musi być jego). */
export function useTechnologyForm(techId: string | null, playerId: string | null) {
  return useQuery({
    queryKey: ["technologyForm", techId, playerId],
    enabled: Boolean(techId && playerId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async () =>
      fetchJson<TechnologyForm>(
        `${BOT_ROOT}/technology/${encodeURIComponent(techId ?? "")}/form?player_id=${encodeURIComponent(playerId ?? "")}`,
        "technologyForm",
      ),
  });
}

/** Zdolności technologii gracza używane poza akcją (lista z informacją, czy da się użyć teraz). */
export function useTechnologyAbilities(playerId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["technologyAbilities", playerId],
    enabled: Boolean(playerId) && enabled,
    staleTime: 0,
    queryFn: async () => {
      const data = await fetchJson<{ abilities: TechnologyAbility[] }>(
        `${BOT_ROOT}/technology/abilities?player_id=${encodeURIComponent(playerId ?? "")}`,
        "technologyAbilities",
      );
      return data.abilities;
    },
  });
}

/** Użycie zdolności poza akcją; 422 z powodem trafia do panelu komunikatów. */
export function useTechnologyAbilityUse() {
  const queryClient = useQueryClient();
  return useCallback(
    async (actorId: string, techId: string, params: Record<string, unknown>) => {
      const response = await fetch(`${BOT_ROOT}/technology/ability`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_id: actorId, tech_id: techId, params }),
      });
      if (!response.ok) {
        const raw = await response.text().catch(() => "");
        let message = raw || `Error ${response.status}`;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed.detail === "string") message = parsed.detail;
        } catch {
          // nie-JSON - zostaje surowy tekst
        }
        useAppStore.getState().setNotice(message, "error");
        throw new Error(message);
      }
      for (const key of ["technologyAbilities", "playerData", "history", "offers"]) {
        void queryClient.invalidateQueries({ queryKey: [key] });
      }
    },
    [queryClient],
  );
}

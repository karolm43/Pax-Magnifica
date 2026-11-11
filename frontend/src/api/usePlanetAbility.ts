import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import type { ActionCardInput } from "@/api/useActionCard";

/*
 * Karty zdolności legendarnych planet (RULES.md 60): formularz wyborów dla „ACTION:" (np. The
 * Nucleus). Legalne opcje liczy silnik; gracz zawsze decyduje. Zagranie idzie jak każda akcja
 * komponentu (`playComponentAction` z id `planet:<id>`).
 */
const BOT_ROOT = "/bot";

export type PlanetAbilityForm = {
  planet_id: string;
  name: string;
  planet_name: string;
  text: string;
  /** `action` = „ACTION:" (akcja komponentu), `passive` = działa przez oferty. */
  kind: "action" | "passive";
  /** False = silnik nie automatyzuje efektu (akcja tylko zapisana, skutek ręcznie). */
  implemented: boolean;
  exhausted: boolean;
  inputs: ActionCardInput[];
};

/** Id komponentu akcji dla karty zdolności legendarnej planety. */
export const planetComponentId = (planetId: string) => `planet:${planetId}`;

/** Formularz użycia karty zdolności legendarnej (planeta musi być kontrolowana przez gracza). */
export function usePlanetAbilityForm(planetId: string | null, playerId: string | null) {
  return useQuery({
    queryKey: ["planetAbilityForm", planetId, playerId],
    enabled: Boolean(planetId && playerId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async () =>
      fetchJson<PlanetAbilityForm>(
        `${BOT_ROOT}/planet-ability/${encodeURIComponent(planetId ?? "")}/form?player_id=${encodeURIComponent(playerId ?? "")}`,
        "planetAbilityForm",
      ),
  });
}

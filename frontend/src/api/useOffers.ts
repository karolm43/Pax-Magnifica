import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";
import type { ActionCardInput } from "@/api/useActionCard";

/*
 * Decyzje graczy (RULES.md 56): technologie i zdolności z „may" oraz wybory celu. Silnik NIGDY
 * nie wybiera za gracza - opisuje oferty (legalne opcje liczy sam), a UI zbiera odpowiedź tym
 * samym formularzem co karty akcji. Odpowiedź waliduje silnik (422 z powodem → komunikat).
 */
const BOT_ROOT = "/bot";

export type OfferView = {
  id: string;
  /** Gracz podejmujący decyzję (silnikowe `player_id`). */
  player_id: string;
  /** Właściciel źródła (inny niż decydent np. przy Assault Cannon - decyduje ofiara). */
  owner_id: string;
  /** Nazwa technologii/zdolności (z assetów). */
  name: string;
  label: string;
  text: string;
  /** Decyzji obowiązkowej nie można odrzucić. */
  mandatory: boolean;
  inputs: ActionCardInput[];
};

/** Oferty czekające na decyzję (`enabled` = w stanie gry są jakieś `pendingOffers`). */
export function useOffers(enabled: boolean) {
  return useQuery({
    queryKey: ["offers"],
    enabled,
    staleTime: 0,
    queryFn: async () => {
      const data = await fetchJson<{ offers: OfferView[] }>("/bot/offers", "offers");
      return data.offers;
    },
  });
}

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
}

/** Odpowiedzi gracza na oferty; po sukcesie odświeżają stan, walkę i inwazję. */
export function useOfferActions() {
  const queryClient = useQueryClient();
  const refresh = useCallback(() => {
    for (const key of ["offers", "battle", "invasion", "playerData", "history", "exploration"]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }, [queryClient]);

  const accept = useCallback(
    async (actorId: string, offerId: string, params: Record<string, unknown>) => {
      await post("/offers/accept", { actor_id: actorId, offer_id: offerId, params });
      refresh();
    },
    [refresh],
  );

  const decline = useCallback(
    async (actorId: string, offerId: string) => {
      await post("/offers/decline", { actor_id: actorId, offer_id: offerId });
      refresh();
    },
    [refresh],
  );

  return { accept, decline };
}

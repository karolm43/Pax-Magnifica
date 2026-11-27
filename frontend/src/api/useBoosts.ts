import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { fetchJson } from "@/api/fetchJson";
import { useGameState } from "@/api/useGameState";

/*
 * Cooperative effects ("boosts") and binding deals (RULES.md 54.15). A pull agent used on
 * another player's event is not pushed to its owner: the beneficiary sees it here and asks for it
 * (optionally paying), the owner answers through the normal offer card. The owner's terms are
 * private, so they come from this endpoint, not from the web data.
 */
const BOT_ROOT = "/bot";

export type BoostMode = "ask" | "standing" | "self";

export type BoostRow = {
  id: string;
  owner: string;
  /** Component key, e.g. ``leaders:saaragent``. */
  source: string;
  name: string;
  text: string;
  kind: string;
  mode: BoostMode;
  /** Standing offer price (TG + commodities); null for ``ask``. */
  price: number | null;
  /** Free for this player (an ally on the owner's standing offer). */
  free: boolean;
  /** A payment is possible now (a legal transaction between the two). */
  payable: boolean;
  /** Offer id of this player's open request, if any. */
  pending: string | null;
};

export type OutgoingDeal = {
  offerId: string;
  name: string;
  requester: string;
  owner: string;
  tradeGoods: number;
  commodities: number;
  accepted: boolean;
  at: number;
};

export type OwnedBoost = {
  source: string;
  name: string;
  text: string;
  kind: string;
  mode: BoostMode;
  price: number;
  freeFor: string[];
};

export type BoostsData = {
  available: BoostRow[];
  outgoing: OutgoingDeal[];
  owned: OwnedBoost[];
  /** "Watch / Hold" in force: ``combat`` / ``turn``; null = not watching. */
  watch: "combat" | "turn" | null;
};

/** Boosts of ``playerId`` - refetched with every game state update. */
export function useBoosts(playerId: string | null) {
  const params = useParams<{ mapid: string }>();
  const { dataUpdatedAt } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  return useQuery<BoostsData>({
    queryKey: ["boosts", playerId, dataUpdatedAt],
    enabled: playerId != null,
    staleTime: 0,
    placeholderData: (previous) => previous,
    queryFn: async () =>
      fetchJson<BoostsData>(
        `${BOT_ROOT}/boosts?player_id=${encodeURIComponent(playerId ?? "")}`,
        "boosts",
      ),
  });
}

async function post(path: string, actorId: string, body: Record<string, unknown>): Promise<void> {
  const response = await fetch(`${BOT_ROOT}/boosts/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Actor-Id": actorId },
    body: JSON.stringify({ player_id: actorId, ...body }),
  });
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      // body without JSON - keep the status
    }
    throw new Error(detail);
  }
}

/** Boost actions; every one refreshes the boosts and offers queries. */
export function useBoostActions() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["boosts"] });
    void queryClient.invalidateQueries({ queryKey: ["offers"] });
  };
  const run = async (path: string, actorId: string, body: Record<string, unknown>) => {
    try {
      await post(path, actorId, body);
    } finally {
      refresh();
    }
  };
  return {
    request: (actorId: string, boostId: string, tradeGoods: number, commodities: number) =>
      run("request", actorId, {
        boost_id: boostId,
        trade_goods: tradeGoods,
        commodities,
      }),
    withdraw: (actorId: string, offerId: string) => run("withdraw", actorId, { offer_id: offerId }),
    configure: (
      actorId: string,
      source: string,
      mode: BoostMode,
      price: number,
      freeFor: string[],
    ) => run("settings", actorId, { source, mode, price, free_for: freeFor }),
    watch: (actorId: string, until: "combat" | "turn" | null) => run("watch", actorId, { until }),
  };
}

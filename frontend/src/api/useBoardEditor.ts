import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

/*
 * God-Mode: edycja planszy bez sprawdzania zasad. Operator (gracz) może dodawać,
 * usuwać i przesuwać jednostki dowolnie. Endpointy w korzeniu backendu (proxy /bot).
 */
const BOT_ROOT = "/bot";

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`God-Mode edit failed (${response.status}). ${detail}`.trim());
  }
}

export type EditUnitArgs = {
  position: string;
  zone: string; // "space" albo ID planety
  faction: string;
  asyncId: string;
  delta: number;
};

export type MoveUnitArgs = {
  fromPosition: string;
  fromZone: string;
  toPosition: string;
  toZone: string;
  faction: string;
  asyncId: string;
  count?: number;
};

/**
 * Hook z akcjami edycji planszy (God-Mode). Każda akcja po sukcesie inwaliduje
 * dokument web-data, więc plansza i panele odświeżają się natychmiast.
 */
export function useBoardEditor() {
  const queryClient = useQueryClient();

  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ["playerData"] }),
    [queryClient],
  );

  const editUnit = useCallback(
    async ({ position, zone, faction, asyncId, delta }: EditUnitArgs) => {
      await post(`/system/${position}/edit-units`, {
        zone,
        faction,
        asyncId,
        delta,
      });
      await refresh();
    },
    [refresh],
  );

  const moveUnit = useCallback(
    async (args: MoveUnitArgs) => {
      await post("/units/move", {
        fromPosition: args.fromPosition,
        fromZone: args.fromZone,
        toPosition: args.toPosition,
        toZone: args.toZone,
        faction: args.faction,
        asyncId: args.asyncId,
        count: args.count ?? 1,
      });
      await refresh();
    },
    [refresh],
  );

  return { editUnit, moveUnit };
}

// Akcje zegara szachowego (RULES.md 58): pauza/wznowienie, start w trwającej grze, wyłączenie.
// Po każdej akcji odświeżamy web-data (`playerData`), z którego czyta pasek zegara.

import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/state/appStore";

async function post(path: string, body?: unknown): Promise<boolean> {
  const response = await fetch(`/bot/clock/${path}`, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.ok) return true;
  const raw = await response.text().catch(() => "");
  let message = raw || `Error ${response.status}`;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    if (typeof parsed.detail === "string") message = parsed.detail;
  } catch {
    // nie-JSON - zostaje surowy tekst
  }
  useAppStore.getState().setNotice(message, "error");
  return false;
}

export function useClockActions(gameId: string) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);

  const run = useCallback(
    async (path: string, body?: unknown) => {
      setBusy(true);
      try {
        await post(path, body);
        await queryClient.invalidateQueries({ queryKey: ["playerData", gameId] });
      } finally {
        setBusy(false);
      }
    },
    [gameId, queryClient],
  );

  return {
    busy,
    pause: () => run("pause"),
    resume: () => run("resume"),
    start: (totalMinutes: number, incrementSeconds: number) =>
      run("configure", { total_minutes: totalMinutes, increment_seconds: incrementSeconds }),
    disable: () => run("disable"),
  };
}

import { useState } from "react";
import { Button } from "@/ds";
import { useGameState } from "@/api/useGameState";
import { postReactionWindowSeconds } from "@/api/useActionCard";

/**
 * Długość okien reakcji W TRWAJĄCEJ grze (Ustawienia → Reaction windows, RULES.md 54.11): pokazuje
 * bieżącą wartość gry i ustawia nową (tylko host; inny gracz dostaje błąd z serwera).
 */
export function CurrentGameReactionWindow({
  gameId,
  seconds,
}: {
  gameId: string;
  seconds: number;
}) {
  const { data: gameState } = useGameState(gameId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = gameState?.reactionWindowSeconds;

  const apply = () => {
    setBusy(true);
    setError(null);
    postReactionWindowSeconds(seconds)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <span style={{ fontSize: "var(--text-meta)", color: "var(--ds-ink-lo)" }}>
        {current !== undefined ? `This game: ${current} s` : "No game loaded"}
      </span>
      <Button
        size="xs"
        loading={busy}
        disabled={current === undefined || current === seconds}
        onClick={apply}
      >
        Apply {seconds} s
      </Button>
      {error && (
        <span role="alert" style={{ fontSize: "var(--text-meta)", color: "rgb(var(--gd-red))" }}>
          {error}
        </span>
      )}
    </span>
  );
}

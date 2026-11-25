import { useState } from "react";
import { Button, Switch } from "@/ds";
import { useGameState } from "@/api/useGameState";
import {
  postQuickReactionWindows,
  postReactionJitter,
  postReactionWindowSeconds,
} from "@/api/useActionCard";

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

/** „Quick windows” W TRWAJĄCEJ grze (RULES.md 54.12): tylko host; inny gracz dostaje błąd. */
export function CurrentGameQuickWindows({ gameId }: { gameId: string }) {
  const { data: gameState } = useGameState(gameId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = gameState?.quickReactionWindows;

  const change = (enabled: boolean) => {
    setBusy(true);
    setError(null);
    postQuickReactionWindows(enabled)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <Switch
        checked={current === true}
        disabled={busy || current === undefined}
        onChange={(event) => change(event.currentTarget.checked)}
        aria-label="Quick windows"
        size="sm"
      />
      {error && (
        <span role="alert" style={{ fontSize: "var(--text-meta)", color: "rgb(var(--gd-red))" }}>
          {error}
        </span>
      )}
    </span>
  );
}

/** „Bluff jitter” W TRWAJĄCEJ grze (RULES.md 54.12): tylko host; działa z „Quick windows”. */
export function CurrentGameQuickJitter({ gameId }: { gameId: string }) {
  const { data: gameState } = useGameState(gameId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = gameState?.reactionJitterSeconds;

  const change = (seconds: number) => {
    setBusy(true);
    setError(null);
    postReactionJitter(seconds)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {[0, 1, 2].map((seconds) => (
        <Button
          key={seconds}
          size="xs"
          loading={busy && current !== seconds}
          disabled={current === undefined || current === seconds}
          onClick={() => change(seconds)}
        >
          {seconds === 0 ? "Off" : `${seconds} s`}
        </Button>
      ))}
      {error && (
        <span role="alert" style={{ fontSize: "var(--text-meta)", color: "rgb(var(--gd-red))" }}>
          {error}
        </span>
      )}
    </span>
  );
}

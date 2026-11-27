import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { IconClockPlay, IconX } from "@tabler/icons-react";
import { Button, Tooltip } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { fetchJson } from "@/api/fetchJson";
import { useGameState } from "@/api/useGameState";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import holdStyles from "./HoldControls.module.css";
import styles from "./BoostsButton.module.css";
import { ToolHint } from "./ToolHint";

/*
 * Queue a strategy card secondary decision ahead of your turn (RULES.md 30.13): while the primary
 * resolves or players before you answer, decide now; the game applies it in clockwise order when
 * your turn in the window comes (and asks you normally if it no longer fits). Only decisions
 * without extra choices are queued here - the rest you answer in the usual window.
 */

type QueueOptions = {
  initiative: number;
  options: Record<string, unknown>;
  queued: { execute: boolean } | null;
  ahead: string[];
  cost: number;
} | null;

async function post(path: string, playerId: string, execute: boolean): Promise<void> {
  const response = await fetch(`/bot/strategy/secondary/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Actor-Id": playerId },
    body: JSON.stringify({ player_id: playerId, execute, payload: {} }),
  });
  if (!response.ok) throw new Error(`Error ${response.status}`);
}

export function SecondaryQueueChip({ playerId }: { playerId: string }) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState, dataUpdatedAt } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const relevant =
    gameState?.pendingStrategy != null ||
    gameState?.pendingWindow?.windowType === "STRATEGY_SECONDARY";
  const queryClient = useQueryClient();
  const { data } = useQuery<QueueOptions>({
    queryKey: ["strategy", "queue", playerId, dataUpdatedAt],
    enabled: relevant,
    staleTime: 0,
    queryFn: async () =>
      fetchJson<QueueOptions>(
        `/bot/strategy/queue-options?player_id=${encodeURIComponent(playerId)}`,
        "strategy queue options",
      ),
  });
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  if (!relevant || !data) return null;

  const card = SC_NAMES[data.initiative] ?? `Strategy Card ${data.initiative}`;
  const needsInput = data.options?.needs_input === true;
  const run = (path: string, execute: boolean) => {
    setBusy(true);
    post(path, playerId, execute)
      .catch(() => undefined)
      .finally(() => {
        setBusy(false);
        void queryClient.invalidateQueries({ queryKey: ["strategy", "queue"] });
      });
  };
  const queued = data.queued;

  return (
    <>
      <Tooltip
        position="top"
        multiline
        maw={300}
        disabled={open}
        label={
          <ToolHint title="Queue secondary" status={queued ? "Your answer is queued." : "Not queued yet."}>
            Decide on the {card} secondary now; the game applies it when your turn in the window
            comes.
          </ToolHint>
        }
      >
        <button
          type="button"
          className={holdStyles.toolBtn}
          data-open={open || undefined}
          aria-expanded={open}
          aria-label={`Queue ${card} secondary`}
          onClick={() => setOpen((v) => !v)}
        >
          <IconClockPlay size={15} aria-hidden="true" />
          <span className={holdStyles.toolLabel}>
            {queued ? (queued.execute ? "Follow queued" : "Pass queued") : `${card}: queue`}
          </span>
        </button>
      </Tooltip>
      {open && (
        <aside className={holdStyles.panel} aria-label={`Queue the ${card} secondary`}>
          <header className={holdStyles.head}>
            <b>{card} - secondary</b>
            <button type="button" className={holdStyles.close} aria-label="Close" onClick={() => setOpen(false)}>
              <IconX size={14} aria-hidden="true" />
            </button>
          </header>
          {data.ahead.length > 0 && (
            <p className={holdStyles.note}>
              Answering before you:{" "}
              {data.ahead.map((pid) => (
                <PlayerTag key={pid} playerId={pid} size={14} />
              ))}
            </p>
          )}
          <p className={holdStyles.note}>
            {data.cost > 0 ? "Following costs 1 command token from your strategy pool. " : ""}
            Others see only that you are ready, not what you chose.
          </p>
          <div className={styles.pay}>
            <Button size="xs" variant={queued && !queued.execute ? "filled" : "default"} disabled={busy} onClick={() => run("queue", false)}>
              Don&apos;t follow
            </Button>
            {!needsInput && (
              <Button size="xs" variant={queued?.execute ? "filled" : "default"} disabled={busy} onClick={() => run("queue", true)}>
                Follow
              </Button>
            )}
            {queued && (
              <Button size="xs" variant="subtle" disabled={busy} onClick={() => run("unqueue", false)}>
                Withdraw
              </Button>
            )}
          </div>
          {needsInput && (
            <p className={styles.note}>Following needs choices - you make them when your turn comes.</p>
          )}
        </aside>
      )}
    </>
  );
}

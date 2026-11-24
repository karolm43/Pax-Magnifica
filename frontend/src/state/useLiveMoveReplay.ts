import { useCallback, useEffect, useRef, useState } from "react";
import { useActivityFeed } from "@/api/boardQueries";
import type { GameData } from "@/entities/game/types";
import type { LiveMove } from "@/entities/replay/types";
import {
  liveMoveFromEntry,
  replayBaseline,
  type PendingLiveMove,
} from "./liveMoveReplay";

/** A move whose map data has not refreshed by then is not replayed. */
const PAIRING_TIMEOUT_MS = 4000;
/** Live replay keys stay clear of history-preview keys. */
const LIVE_KEY_BASE = 1_000_000;

export type LiveMoveReplay = {
  key: number;
  previous: GameData;
  move: LiveMove;
  active: boolean;
};

/**
 * Physical flight of a confirmed fleet move or invasion landing on EVERY client: a new
 * Activity entry (`move_route` / `landed` facts) is paired with the live map before/after
 * it and replayed.
 * Entries present when the page opens are history, not news. `enabled` = false (history
 * preview open, mobile, admin fast mode) drops new moves without replaying them.
 */
export function useLiveMoveReplay(live: GameData | undefined, enabled: boolean) {
  const { data: feed } = useActivityFeed();
  const seen = useRef<number | null>(null);
  const currentLive = useRef<GameData | undefined>(undefined);
  const previousLive = useRef<GameData | undefined>(undefined);
  const nextKey = useRef(LIVE_KEY_BASE);
  const [pending, setPending] = useState<PendingLiveMove>();
  const [replay, setReplay] = useState<LiveMoveReplay>();

  useEffect(() => {
    if (live === currentLive.current) return;
    previousLive.current = currentLive.current;
    currentLive.current = live;
  }, [live]);

  useEffect(() => {
    if (!feed) return;
    const latest = feed.entries.at(-1)?.seq ?? 0;
    if (seen.current === null || latest < seen.current) {
      seen.current = latest;
      return;
    }
    const since = seen.current;
    seen.current = Math.max(since, latest);
    if (!enabled) return;
    const fresh = feed.entries.filter(
      (entry) =>
        entry.seq > since &&
        (feed.current_seq === null || entry.seq <= feed.current_seq),
    );
    // Several moves in one refresh: only the newest can be paired with the map.
    const move = fresh
      .map((entry) => liveMoveFromEntry(entry, feed.players))
      .filter((found): found is LiveMove => found !== undefined)
      .at(-1);
    if (!move) return;
    setPending({
      move,
      liveAtArrival: currentLive.current,
      previousAtArrival: previousLive.current,
    });
  }, [feed, enabled]);

  useEffect(() => {
    if (!pending) return;
    if (!enabled) {
      setPending(undefined);
      return;
    }
    const baseline = replayBaseline(pending, live);
    if (baseline) {
      nextKey.current += 1;
      setReplay({ key: nextKey.current, previous: baseline, move: pending.move, active: true });
      setPending(undefined);
      return;
    }
    const timeout = window.setTimeout(() => setPending(undefined), PAIRING_TIMEOUT_MS);
    return () => window.clearTimeout(timeout);
  }, [pending, live, enabled]);

  const stop = useCallback(
    () => setReplay((current) => (current?.active ? { ...current, active: false } : current)),
    [],
  );

  return { replay: enabled ? replay : undefined, stop };
}

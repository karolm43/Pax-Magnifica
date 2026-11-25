import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { postHeld } from "@/api/useActionCard";
import { useGameData } from "@/state/useGameContext";
import { ReactionQuickPass } from "./ReactionQuickPass";
import { MoreTimeButton, waitingText } from "./reactionWindowParts";
import { useWindowCountdown } from "./useWindowCountdown";
import styles from "./HeldPlayBanner.module.css";

/**
 * Okno Sabotage (RULES.md 53.6, 54.11): zagrana karta akcji czeka STAŁY czas ustawiony przez
 * hosta. Silnik sam pasuje za graczy bez Sabotage, więc „Drag Sabotage… or pass” widzi tylko ten,
 * kto może kartę anulować. Pasy są prywatne; po czasie klient prosi serwer o zwolnienie (serwer i
 * tak sprawdza własny zegar, a dowolny kolejny POST też zwalnia okno).
 */
export function HeldPlayBanner({
  viewerId,
  onNeedHand,
  playing = false,
}: {
  /** Gracz, którego rękę widzi ten pulpit (może spasować / zagrać Sabotage). */
  viewerId: string | null;
  /** Prośba o rozwinięcie ręki, gdy okno czeka na decyzję tego gracza. */
  onNeedHand: () => void;
  /** Gracz właśnie przeciąga kartę albo wypełnia formularz zagrania - zegar okna stoi. */
  playing?: boolean;
}) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const held = gameState?.heldPlay ?? null;
  const key = held ? `${held.cardId}:${held.openedAt}` : null;
  const owner = held?.playerId ?? "";
  const frozen = Boolean(held?.frozen);
  const left = useWindowCountdown(
    key,
    held?.holdSeconds ?? 0,
    () => {
      if (owner) void postHeld("release", owner);
    },
    frozen || playing,
  );

  const eligible = Boolean(held && viewerId && held.eligible.includes(viewerId));
  const passed = Boolean(held && viewerId && held.passed.includes(viewerId));
  const deciding = eligible && !passed;
  const me = useGameData()?.playerData?.find((p) => p.discordId === viewerId);

  // Przeciąganie / formularz Sabotage zatrzymuje zegar także na serwerze (i u pozostałych).
  const freezing = Boolean(key && deciding && playing && viewerId);
  useEffect(() => {
    if (!freezing || !viewerId) return;
    void postHeld("freeze", viewerId);
    return () => void postHeld("unfreeze", viewerId);
  }, [freezing, key, viewerId]);

  useEffect(() => {
    if (key && deciding) onNeedHand();
  }, [key, deciding]);

  if (!held) return null;
  const mine = viewerId === held.playerId;
  // Sabotage na tę kartę czeka na Instinct Training (RULES.md 62.9): teraz anuluje się Sabotage.
  const counter = held.counter ?? null;

  return (
    <aside className={styles.banner} data-reaction-banner="" role="status" aria-live="polite" aria-label="Sabotage window">
      <div className={styles.text}>
        <b>{mine ? "You play" : "Played"}: {held.cardName}</b>
        <span>{held.text}</span>
        {counter && (
          <span>
            {viewerId === counter.playerId ? "You play" : "Played"}: {counter.cardName} - it
            cancels the card above unless it is cancelled first.
          </span>
        )}
        <small>
          {deciding
            ? counter
              ? "Use Instinct Training to cancel the Sabotage, or pass."
              : "Drag Sabotage from your hand to cancel it, or pass."
            : waitingText(eligible, held.extensions ?? 0)}
        </small>
      </div>
      <div className={styles.side}>
        <span className={styles.count} aria-label="Seconds left">
          {left ?? held.holdSeconds}s{frozen || playing ? " ⏸" : ""}
        </span>
        {deciding && viewerId && (
          <button
            type="button"
            className={styles.pass}
            onClick={() => void postHeld("pass", viewerId)}
          >
            Pass
          </button>
        )}
        {eligible && viewerId && (
          <MoreTimeButton
            asked={(held.askedForTime ?? []).includes(viewerId)}
            onAsk={() => void postHeld("wait", viewerId)}
          />
        )}
        {deciding && viewerId && me && (
          <ReactionQuickPass
            me={me}
            category="sabotage"
            inCombat={Boolean(gameState?.activeCombat)}
            onPassed={() => void postHeld("pass", viewerId)}
          />
        )}
      </div>
    </aside>
  );
}

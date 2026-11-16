import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { postHeld } from "@/api/useActionCard";
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
}: {
  /** Gracz, którego rękę widzi ten pulpit (może spasować / zagrać Sabotage). */
  viewerId: string | null;
  /** Prośba o rozwinięcie ręki, gdy okno czeka na decyzję tego gracza. */
  onNeedHand: () => void;
}) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const held = gameState?.heldPlay ?? null;
  const key = held ? `${held.cardId}:${held.openedAt}` : null;
  const owner = held?.playerId ?? "";
  const left = useWindowCountdown(key, held?.holdSeconds ?? 0, () => {
    if (owner) void postHeld("release", owner);
  });

  const eligible = Boolean(held && viewerId && held.eligible.includes(viewerId));
  const passed = Boolean(held && viewerId && held.passed.includes(viewerId));
  const deciding = eligible && !passed;

  useEffect(() => {
    if (key && deciding) onNeedHand();
  }, [key, deciding]);

  if (!held) return null;
  const mine = viewerId === held.playerId;

  return (
    <aside className={styles.banner} role="status" aria-live="polite" aria-label="Sabotage window">
      <div className={styles.text}>
        <b>{mine ? "You play" : "Played"}: {held.cardName}</b>
        <span>{held.text}</span>
        <small>
          {deciding
            ? "Drag Sabotage from your hand to cancel it, or pass."
            : waitingText(eligible, held.extensions ?? 0)}
        </small>
      </div>
      <div className={styles.side}>
        <span className={styles.count} aria-label="Seconds left">
          {left ?? held.holdSeconds}s
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
      </div>
    </aside>
  );
}

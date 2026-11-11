import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { postHeld } from "@/api/useActionCard";
import styles from "./HeldPlayBanner.module.css";

/**
 * Okno Sabotage (RULES.md 53.6): zagrana karta akcji czeka ~10 s na reakcje. Inni gracze mogą
 * przeciągnąć Sabotage z ręki albo kliknąć "Pass". Odliczanie liczymy lokalnie od chwili, gdy
 * okno pojawiło się u nas (bez zgadywania różnicy zegarów); po czasie klient prosi serwer o
 * zwolnienie (serwer i tak sprawdza własny zegar, więc nadmiarowe wywołania są niegroźne).
 */
export function HeldPlayBanner({
  viewerId,
  onNeedHand,
}: {
  /** Gracz, którego rękę widzi ten pulpit (może spasować / zagrać Sabotage). */
  viewerId: string | null;
  /** Prośba o rozwinięcie ręki, gdy okno dotyczy tego gracza. */
  onNeedHand: () => void;
}) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const held = gameState?.heldPlay ?? null;
  const key = held ? `${held.cardId}:${held.openedAt}` : null;
  const [left, setLeft] = useState<number | null>(null);

  const eligible = Boolean(held && viewerId && held.eligible.includes(viewerId));
  const passed = Boolean(held && viewerId && held.passed.includes(viewerId));

  useEffect(() => {
    if (!held || !key) {
      setLeft(null);
      return;
    }
    const started = Date.now();
    const total = held.holdSeconds;
    let released = false;
    setLeft(total);
    const timer = window.setInterval(() => {
      const remaining = Math.max(0, total - Math.floor((Date.now() - started) / 1000));
      setLeft(remaining);
      if (remaining === 0 && !released) {
        released = true;
        void postHeld("release", held.playerId);
      }
    }, 250);
    return () => window.clearInterval(timer);
    // Odświeżamy tylko przy nowym oknie (klucz karty + czasu otwarcia).
  }, [key]);

  useEffect(() => {
    if (key && eligible && !passed) onNeedHand();
  }, [key, eligible, passed]);

  if (!held) return null;
  const mine = viewerId === held.playerId;

  return (
    <aside className={styles.banner} role="status" aria-live="polite">
      <div className={styles.text}>
        <b>{mine ? "You play" : "Played"}: {held.cardName}</b>
        <span>{held.text}</span>
        <small>
          {eligible && !passed
            ? "Drag Sabotage from your hand to cancel it, or pass."
            : "Waiting for answers (Sabotage)…"}
        </small>
      </div>
      <div className={styles.side}>
        <span className={styles.count} aria-label="Seconds left">
          {left ?? held.holdSeconds}s
        </span>
        {eligible && !passed && viewerId && (
          <button
            type="button"
            className={styles.pass}
            onClick={() => void postHeld("pass", viewerId)}
          >
            Pass
          </button>
        )}
      </div>
    </aside>
  );
}

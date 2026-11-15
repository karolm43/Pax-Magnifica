import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { postReactionPause } from "@/api/useActionCard";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import styles from "./HeldPlayBanner.module.css";

/**
 * Pauza ochronna (RULES.md 54.10): w kluczowym oknie (ogłoszona akcja strategiczna, ujawniona
 * agenda, wygrana walka, Sustain Damage) gra czeka do 10 s, żeby gracze zdążyli zagrać kartę z
 * ręki (Coup d'Etat, Veto, ridery, Salvage, Direct Hit…). Ten sam wygląd i odliczanie co okno
 * Sabotage (`HeldPlayBanner`): czas liczony lokalnie od pojawienia się pauzy, po nim klient prosi
 * serwer o zwolnienie (serwer i tak sprawdza własny zegar). Pytani są wszyscy z kartami akcji,
 * którzy mogą być stroną okna — baner nie zdradza, kto ma pasującą kartę.
 */
export function ReactionPauseBanner({
  viewerId,
  onNeedHand,
}: {
  /** Gracz, którego rękę widzi ten pulpit (może zagrać kartę albo spasować). */
  viewerId: string | null;
  /** Prośba o rozwinięcie ręki, gdy pauza dotyczy tego gracza. */
  onNeedHand: () => void;
}) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const pause = gameState?.reactionPause ?? null;
  const key = pause?.key ?? null;
  const [left, setLeft] = useState<number | null>(null);

  const eligible = Boolean(pause && viewerId && pause.eligible.includes(viewerId));
  const passed = Boolean(pause && viewerId && pause.passed.includes(viewerId));

  useEffect(() => {
    if (!pause || !key) {
      setLeft(null);
      return;
    }
    const started = Date.now();
    const total = pause.pauseSeconds;
    const asker = viewerId ?? pause.eligible[0] ?? "";
    let released = false;
    setLeft(total);
    const timer = window.setInterval(() => {
      const remaining = Math.max(0, total - Math.floor((Date.now() - started) / 1000));
      setLeft(remaining);
      if (remaining === 0 && !released && asker) {
        released = true;
        void postReactionPause("release", asker);
      }
    }, 250);
    return () => window.clearInterval(timer);
    // Odliczanie startuje od nowa tylko przy nowej pauzie (klucz okna).
  }, [key]);

  useEffect(() => {
    if (key && eligible && !passed) onNeedHand();
  }, [key, eligible, passed]);

  if (!pause) return null;

  return (
    <aside className={styles.banner} role="status" aria-live="polite" aria-label="Reaction window">
      <div className={styles.text}>
        <b>
          Reaction window: {pause.label}
          {pause.subject && (
            <>
              {" · "}
              <PlayerTag playerId={pause.subject} size={14} />
            </>
          )}
        </b>
        <small>
          {eligible && !passed
            ? "Play a card from your hand now, or pass."
            : `Waiting for other players (${pause.passed.length}/${pause.eligible.length} passed)…`}
        </small>
      </div>
      <div className={styles.side}>
        <span className={styles.count} aria-label="Seconds left">
          {left ?? pause.pauseSeconds}s
        </span>
        {eligible && !passed && viewerId && (
          <button
            type="button"
            className={styles.pass}
            onClick={() => void postReactionPause("pass", viewerId)}
          >
            Pass
          </button>
        )}
      </div>
    </aside>
  );
}

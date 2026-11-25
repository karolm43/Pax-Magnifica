import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { postReactionPause } from "@/api/useActionCard";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { MoreTimeButton, waitingText } from "./reactionWindowParts";
import { ReactionQuickPass } from "./ReactionQuickPass";
import { useWindowCountdown } from "./useWindowCountdown";
import styles from "./HeldPlayBanner.module.css";

/**
 * Pauza ochronna (RULES.md 54.10–54.11): w kluczowym oknie (ogłoszona akcja strategiczna,
 * ujawniona agenda, wygrana walka, Sustain Damage) gra czeka STAŁY czas ustawiony przez hosta, żeby
 * gracze zdążyli zagrać kartę z ręki (Coup d'Etat, Veto, ridery, Salvage, Direct Hit…). Silnik sam
 * pasuje za graczy bez pasującej karty, więc o decyzję jest proszony tylko ten, kto ma co zagrać.
 * Pasy są prywatne — baner nie pokazuje, ilu graczy spasowało (to zdradzałoby, kto ma kartę).
 */
export function ReactionPauseBanner({
  viewerId,
  onNeedHand,
}: {
  /** Gracz, którego rękę widzi ten pulpit (może zagrać kartę albo spasować). */
  viewerId: string | null;
  /** Prośba o rozwinięcie ręki, gdy pauza czeka na decyzję tego gracza. */
  onNeedHand: () => void;
}) {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const pause = gameState?.reactionPause ?? null;
  const key = pause?.key ?? null;
  const asker = viewerId ?? pause?.eligible[0] ?? "";
  const left = useWindowCountdown(key, pause?.pauseSeconds ?? 0, () => {
    if (asker) void postReactionPause("release", asker);
  });

  const eligible = Boolean(pause && viewerId && pause.eligible.includes(viewerId));
  const passed = Boolean(pause && viewerId && pause.passed.includes(viewerId));
  const deciding = eligible && !passed;
  const me = useGameData()?.playerData?.find((p) => p.discordId === viewerId);

  useEffect(() => {
    if (key && deciding) onNeedHand();
  }, [key, deciding]);

  if (!pause) return null;

  return (
    <aside className={styles.banner} data-reaction-banner="" role="status" aria-live="polite" aria-label="Reaction window">
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
          {deciding
            ? "You can react: play a card from your hand now, or pass."
            : waitingText(eligible, pause.extensions ?? 0)}
        </small>
      </div>
      <div className={styles.side}>
        <span className={styles.count} aria-label="Seconds left">
          {left ?? pause.pauseSeconds}s
        </span>
        {deciding && viewerId && (
          <button
            type="button"
            className={styles.pass}
            onClick={() => void postReactionPause("pass", viewerId)}
          >
            Pass
          </button>
        )}
        {eligible && viewerId && (
          <MoreTimeButton
            asked={(pause.askedForTime ?? []).includes(viewerId)}
            onAsk={() => void postReactionPause("wait", viewerId)}
          />
        )}
        {deciding && viewerId && me && (
          <ReactionQuickPass
            me={me}
            category={pause.category}
            inCombat={Boolean(gameState?.activeCombat)}
            onPassed={() => void postReactionPause("pass", viewerId)}
          />
        )}
      </div>
    </aside>
  );
}

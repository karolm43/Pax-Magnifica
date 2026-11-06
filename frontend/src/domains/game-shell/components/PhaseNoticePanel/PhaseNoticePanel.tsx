import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { IconX, IconInfoCircle, IconAlertTriangle } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { buildPhaseNotice, type PhaseNotice } from "./phaseNoticeMessage";
import styles from "./PhaseNoticePanel.module.css";

/* Ton fazy → trójka RGB akcentu (spójne z sygnałami design systemu). */
const TONE_RGB: Record<PhaseNotice["tone"], string> = {
  strategy: "var(--ds-sig-break)",
  action: "var(--ds-sig-bio)",
  status: "var(--ds-sig-warn)",
  agenda: "var(--ds-sig-law)",
  neutral: "var(--ds-hair-rgb)",
};

/**
 * PANEL KOMUNIKATÓW (standaryzowany „głos stołu") — osobny box PRZYPIĘTY u GÓRY
 * ekranu, nad mapą. Dwa tryby treści, jeden spójny styl:
 *
 *  1. Komunikat ODRZUCONEJ AKCJI (``notice`` z appStore, np. 422 „nie można…") —
 *     ma pierwszeństwo, pokazuje się z krzyżykiem do zamknięcia, auto-znika.
 *  2. KONTEKSTOWE prowadzenie fazy (``buildPhaseNotice``) — spokojny komunikat
 *     „czyja kolej / co odblokowuje przejście fazy", wynikający ze stanu gry.
 *
 * Pasek NIE przechwytuje panningu mapy (pointer-events tylko na wnętrzu). Gdy nie ma
 * ani notice, ani sensownego komunikatu fazy — nie renderuje się wcale.
 */
export function PhaseNoticePanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const players = gameData?.playerData ?? [];

  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);

  // Notice odrzuconej akcji sam znika po chwili (nie zostaje na stałe na pasku).
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => clearNotice(), 6000);
    return () => window.clearTimeout(timer);
  }, [notice, clearNotice]);

  // 1) Notice (błąd/info) ma pierwszeństwo — operator musi zobaczyć powód odmowy.
  if (notice) {
    const isError = notice.kind === "error";
    return (
      <div
        className={styles.wrap}
        role="status"
        aria-live="polite"
        style={{ "--accent": isError ? "var(--ds-sig-danger)" : "var(--ds-sig-prop)" } as React.CSSProperties}
      >
        <div className={styles.panel} data-notice data-kind={notice.kind}>
          <span className={styles.icon} aria-hidden="true">
            {isError ? (
              <IconAlertTriangle size={18} />
            ) : (
              <IconInfoCircle size={18} />
            )}
          </span>
          <span className={styles.text}>
            <b className={styles.title}>
              {isError ? "Action not allowed" : "Notice"}
            </b>
            <span className={styles.body}>{notice.text}</span>
          </span>
          <button
            type="button"
            className={styles.close}
            onClick={clearNotice}
            aria-label="Dismiss message"
          >
            <IconX size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    );
  }

  // 2) Kontekstowe prowadzenie fazy.
  const phaseNotice = buildPhaseNotice(gameState, players);
  if (!phaseNotice) return null;

  return (
    <div
      className={styles.wrap}
      role="status"
      aria-live="polite"
      style={{ "--accent": TONE_RGB[phaseNotice.tone] } as React.CSSProperties}
    >
      <div className={styles.panel} data-tone={phaseNotice.tone}>
        <span className={styles.dot} aria-hidden="true" />
        <span className={styles.text}>
          <b className={styles.title}>{phaseNotice.title}</b>
          <span className={styles.body}>{phaseNotice.body}</span>
        </span>
      </div>
    </div>
  );
}

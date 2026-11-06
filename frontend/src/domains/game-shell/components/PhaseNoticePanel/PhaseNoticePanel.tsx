import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { IconX, IconInfoCircle, IconAlertTriangle } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import type { GameState } from "@/entities/data/types";
import { announcementFor, type PhaseNotice } from "./phaseNoticeMessage";
import styles from "./PhaseNoticePanel.module.css";

/* Ton → trójka RGB akcentu (sygnały design systemu). */
const TONE_RGB: Record<PhaseNotice["tone"], string> = {
  strategy: "var(--ds-sig-break)",
  action: "var(--ds-sig-bio)",
  status: "var(--ds-sig-warn)",
  agenda: "var(--ds-sig-law)",
  neutral: "var(--ds-hair-rgb)",
};

/** Ile widoczny jest komunikat zanim sam zniknie (ms). */
const AUTO_DISMISS_MS = 7000;

type Shown =
  | { source: "notice"; kind: "error" | "info"; title: string; body: string }
  | { source: "phase"; notice: PhaseNotice };

/**
 * PANEL KOMUNIKATÓW — osobny box PRZYPIĘTY u GÓRY ekranu. REAKTYWNY, nie stały:
 * pojawia się tylko gdy „coś jest nie tak albo coś się zmienia" (uwaga użytkownika,
 * DECYZJA 2026-11), po czym sam znika po czasie i można go zamknąć krzyżykiem.
 *
 * Dwa źródła, jedno miejsce:
 *  1. ODRZUCONA AKCJA (``notice`` z appStore, np. 422) — pokazywana natychmiast.
 *  2. ZDARZENIE STANU (``announcementFor``): zmiana fazy albo „mówca może zakończyć
 *     fazę". Liczone z RÓŻNICY prev→next stanu — nie przypomina w kółko.
 *
 * Nie przechwytuje panningu mapy (pointer-events tylko na wnętrzu).
 */
export function PhaseNoticePanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const players = gameData?.playerData ?? [];

  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);

  const [shown, setShown] = useState<Shown | null>(null);
  const prevStateRef = useRef<GameState | null>(null);
  const lastKeyRef = useRef<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const dismiss = () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = null;
    setShown(null);
  };

  const armAutoDismiss = () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => setShown(null), AUTO_DISMISS_MS);
  };

  // Źródło 1: odrzucona akcja / info — ma pierwszeństwo, pokazujemy natychmiast.
  useEffect(() => {
    if (!notice) return;
    setShown({
      source: "notice",
      kind: notice.kind,
      title: notice.kind === "error" ? "Action not allowed" : "Notice",
      body: notice.text,
    });
    armAutoDismiss();
    // Czyścimy w store, by ten sam komunikat nie „przykleił się" do kolejnych zmian.
    const clearTimer = window.setTimeout(() => clearNotice(), 100);
    return () => window.clearTimeout(clearTimer);
  }, [notice, clearNotice]);

  // Źródło 2: zdarzenie stanu (zmiana fazy / brama „można zakończyć fazę").
  useEffect(() => {
    const prev = prevStateRef.current;
    const announcement = announcementFor(prev, gameState, players);
    prevStateRef.current = gameState ?? null;
    if (!announcement) return;
    // Nie powtarzaj tego samego zdarzenia (klucz) ani nie nadpisuj świeżego notice.
    if (announcement.key === lastKeyRef.current) return;
    lastKeyRef.current = announcement.key;
    setShown((cur) =>
      cur?.source === "notice" ? cur : { source: "phase", notice: announcement },
    );
    armAutoDismiss();
  }, [gameState, players]);

  useEffect(() => () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
  }, []);

  if (!shown) return null;

  const isNoticeError = shown.source === "notice" && shown.kind === "error";
  const accent =
    shown.source === "notice"
      ? isNoticeError
        ? "var(--ds-sig-danger)"
        : "var(--ds-sig-prop)"
      : TONE_RGB[shown.notice.tone];
  const title = shown.source === "notice" ? shown.title : shown.notice.title;
  const body = shown.source === "notice" ? shown.body : shown.notice.body;

  return (
    <div
      className={styles.wrap}
      role="status"
      aria-live="polite"
      style={{ "--accent": accent } as React.CSSProperties}
    >
      <div
        className={styles.panel}
        data-source={shown.source}
        data-kind={shown.source === "notice" ? shown.kind : undefined}
      >
        {shown.source === "notice" ? (
          <span className={styles.icon} aria-hidden="true">
            {isNoticeError ? (
              <IconAlertTriangle size={20} />
            ) : (
              <IconInfoCircle size={20} />
            )}
          </span>
        ) : (
          <span className={styles.dot} aria-hidden="true" />
        )}
        <span className={styles.text}>
          <b className={styles.title}>{title}</b>
          <span className={styles.body}>{body}</span>
        </span>
        <button
          type="button"
          className={styles.close}
          onClick={dismiss}
          aria-label="Dismiss message"
          title="Dismiss"
        >
          <IconX size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

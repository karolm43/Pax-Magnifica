import { useEffect, useRef, useState } from "react";
import { IconX, IconInfoCircle, IconAlertTriangle } from "@tabler/icons-react";
import { useAppStore } from "@/state/appStore";
import styles from "./PhaseNoticePanel.module.css";

/** Jak długo komunikat jest widoczny, zanim ruszy fade-out (ms). */
const AUTO_DISMISS_MS = 6000;
/** Czas trwania animacji fade-out przed odmontowaniem (ms) — zgodny z CSS. */
const FADE_OUT_MS = 320;

type Shown = { kind: "error" | "info"; title: string; body: string };

/**
 * PANEL KOMUNIKATÓW — osobny box PRZYPIĘTY u GÓRY ekranu. Pokazuje WYŁĄCZNIE komunikaty
 * o NIEDOZWOLONYCH / odrzuconych akcjach (``notice`` z appStore, ustawiane przy 422 w
 * ``useBoardEditor.post``) — np. „Next phase" w strategii zanim wszyscy wybiorą kartę,
 * „Pass" zanim zagrasz kartę strategii (DECYZJA 2026-11, uwaga użytkownika).
 *
 * Reaktywny: pojawia się na zdarzenie, po czym ZNIKA Z FADE-OUT (auto po czasie lub po
 * kliknięciu krzyżyka). Nie jest stałym przypomnieniem. Nie przechwytuje panningu mapy
 * (pointer-events tylko na wnętrzu).
 */
export function PhaseNoticePanel() {
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);

  const [shown, setShown] = useState<Shown | null>(null);
  // ``closing`` wyzwala animację fade-out PRZED odmontowaniem (CSS data-closing).
  const [closing, setClosing] = useState(false);
  const autoTimer = useRef<number | null>(null);
  const fadeTimer = useRef<number | null>(null);

  const clearTimers = () => {
    if (autoTimer.current) window.clearTimeout(autoTimer.current);
    if (fadeTimer.current) window.clearTimeout(fadeTimer.current);
    autoTimer.current = null;
    fadeTimer.current = null;
  };

  // Rozpoczyna znikanie: najpierw fade-out (CSS), po FADE_OUT_MS odmontowanie.
  const beginClose = () => {
    if (fadeTimer.current) return; // już się zamyka
    setClosing(true);
    fadeTimer.current = window.setTimeout(() => {
      setShown(null);
      setClosing(false);
      fadeTimer.current = null;
    }, FADE_OUT_MS);
  };

  // Nowy komunikat 422/info: pokaż natychmiast, uzbrój auto-fade po czasie.
  useEffect(() => {
    if (!notice) return;
    clearTimers();
    setClosing(false);
    setShown({
      kind: notice.kind,
      title: notice.kind === "error" ? "Action not allowed" : "Notice",
      body: notice.text,
    });
    autoTimer.current = window.setTimeout(beginClose, AUTO_DISMISS_MS);
    // Czyścimy w store, by ten sam tekst mógł pojawić się ponownie przy kolejnej
    // odrzuconej akcji (inaczej identyczny notice nie wyzwoliłby efektu).
    const storeClear = window.setTimeout(() => clearNotice(), 80);
    return () => window.clearTimeout(storeClear);
  }, [notice, clearNotice]);

  useEffect(() => clearTimers, []);

  if (!shown) return null;

  const isError = shown.kind === "error";
  const accent = isError ? "var(--ds-sig-danger)" : "var(--ds-sig-prop)";

  return (
    <div
      className={styles.wrap}
      role="status"
      aria-live="polite"
      data-closing={closing || undefined}
      style={{ "--accent": accent } as React.CSSProperties}
    >
      <div className={styles.panel} data-kind={shown.kind}>
        <span className={styles.icon} aria-hidden="true">
          {isError ? (
            <IconAlertTriangle size={20} />
          ) : (
            <IconInfoCircle size={20} />
          )}
        </span>
        <span className={styles.text}>
          <b className={styles.title}>{shown.title}</b>
          <span className={styles.body}>{shown.body}</span>
        </span>
        <button
          type="button"
          className={styles.close}
          onClick={beginClose}
          aria-label="Dismiss message"
          title="Dismiss"
        >
          <IconX size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

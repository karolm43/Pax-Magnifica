import { createPortal } from "react-dom";
import { PhaseNoticePanel } from "@/domains/game-shell/components/PhaseNoticePanel";
import { ActivityToasts } from "@/domains/game-shell/components/ActivityPanel";
import classes from "./NotificationArea.module.css";

/**
 * JEDNO miejsce na wszystkie wyskakujące komunikaty gry: odrzucone akcje (422/403,
 * ``PhaseNoticePanel``) nad powiadomieniami „kto co zrobił" (``ActivityToasts``).
 *
 * Kolumna u góry, na środku mapy — pod nagłówkiem i paskiem zakładek, między panelem stanu
 * gry (lewa) a paskiem narzędzi mapy i zdarzeniami (prawa), więc niczego z nich nie zasłania.
 * Przy oknie pełnoekranowym (walka, inwazja, agenda…) kolumna wjeżdża na środek jego nagłówka
 * i leży NAD oknem — okna nie mają już własnych pasków komunikatów (migały: komunikat żyje
 * w store tylko chwilę, panel trzyma go sam). Montowana raz na stronie gry.
 */
export function NotificationArea() {
  return createPortal(
    <div className={classes.area} aria-label="Notifications">
      <PhaseNoticePanel />
      <ActivityToasts />
    </div>,
    document.body,
  );
}

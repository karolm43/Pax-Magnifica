import { useEffect, useRef, useState, type ReactNode } from "react";
import { IconChevronDown, IconChevronUp } from "@tabler/icons-react";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import {
  ComponentInfoButton,
  type ComponentRef,
} from "@/domains/cards/components/ComponentInfo";
import styles from "./DecisionFrame.module.css";
import { DECISION_ZONE } from "@/hooks/useDecisionZone";

/**
 * Standard widths of every decision box (DecisionCenter cards, decision modals, prompt dock).
 * Mirrors ``--decision-w`` / ``--decision-w-wide`` in ``styles/themeSharedTokens.css``.
 */
export const DECISION_WIDTH = { standard: 460, wide: 560 } as const;

/** Opisy krótsze niż tyle znaków pokazujemy w całości (bez „more”). */
export const LONG_TEXT = 420;

/** Czy zdarzenie klawiatury trafia w pole, które samo obsługuje Enter/Esc (formularz, przycisk). */
export function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(target.tagName)
  );
}

export type DecisionFrameProps = {
  ariaLabel: string;
  /** Plakietka rodzaju: Primary / Secondary / Action card / Technology... (może zawierać `PlayerTag`). */
  kind?: ReactNode;
  /** Ikona przed nagłówkiem (np. błyskawica „Available now”, klepsydra okna reakcji). */
  icon?: ReactNode;
  /** Ton ramy: `window` = okno reakcji mija (bursztyn, puls), `closed` = okno minęło (przygaszona). */
  tone?: "window" | "closed";
  /** Wyróżniona linia pod nagłówkiem, przed tekstem (np. fraza okna „At the start of combat”). */
  subtitle?: ReactNode;
  /** Tooltip całej ramy. */
  hint?: string;
  /** Cudzy komponent (decyduje ofiara): czyj, z logo i kolorem. */
  ownerId?: string;
  /** Tytuł: nazwa albo gotowy chip komponentu (np. `Tech`). Nie powtarzaj go nad ramą. */
  title: ReactNode;
  /** ⓘ obok tytułu: pełna karta komponentu po kliknięciu (jak chip w panelu gracza). */
  infoRef?: ComponentRef;
  infoName?: string;
  required?: boolean;
  /** Ile kolejnych decyzji czeka w kolejce („+N more”). */
  queued?: number;
  /** Pełny tekst komponentu (normalny kolor, zwijany powyżej `LONG_TEXT`). */
  text?: string;
  /** Pola decyzji. */
  children?: ReactNode;
  /** Komunikaty pod polami: neutralne (`notes`) i ostrzeżenia (`warnings`). */
  notes?: string[];
  warnings?: string[];
  /** Akcja główna (Enter). Bez `onUse` stopka ma tylko Cancel/Close. */
  onUse?: () => void;
  useLabel?: string;
  canUse?: boolean;
  /** Pominięcie/anulowanie (Esc). Brak = decyzja wymagana. */
  onSkip?: () => void;
  skipLabel?: string;
  /** „Never ask”: odmowa + wyciszenie komponentu. */
  onNeverAsk?: () => void;
  /** Tooltip „Never ask” (domyślnie o zdolności; karty z ręki mówią o karcie). */
  neverAskHint?: string;
  /** Dodatkowy przycisk w stopce (np. Unlock), przed akcją główną. */
  secondary?: { label: string; onClick: () => void };
  busy?: boolean;
  /** Rama wewnątrz okna (AppModal): bez własnego obramowania; Esc obsługuje okno. */
  embedded?: boolean;
  /**
   * Skróty Enter/Esc. W kolumnie kilku ram (DecisionCenter) skróty ma tylko bieżąca decyzja
   * (oferta) - pozostałe karty podają `false`, żeby jeden Enter nie odpalił kilku akcji.
   */
  shortcuts?: boolean;
};

/**
 * Jedna rama okna decyzji gracza (`docs/PLAN_OKNA_DECYZJI.md`, U1): nagłówek (plakietka rodzaju,
 * tytuł z ⓘ, Required, „+N more”), pełny tekst, pola, komunikaty i stopka
 * [Never ask] [Skip Esc] [akcja Enter]. Używają jej: oferty (`OfferDock`), użycie karty/technologii/
 * lidera/legendarnej (`ComponentUseModal`).
 */
export function DecisionFrame({
  ariaLabel,
  kind,
  icon,
  tone,
  subtitle,
  hint,
  ownerId,
  title,
  infoRef,
  infoName,
  required,
  queued = 0,
  text,
  children,
  notes = [],
  warnings = [],
  onUse,
  useLabel = "Use",
  canUse = true,
  onSkip,
  skipLabel = "Skip",
  onNeverAsk,
  neverAskHint = "Skip and stop offering this ability. Undo in Reactions on the action panel.",
  secondary,
  busy = false,
  embedded = false,
  shortcuts = true,
}: DecisionFrameProps) {
  const [showText, setShowText] = useState(false);
  // Skróty czytają najnowszy stan bez ponownego podpinania nasłuchu.
  const latest = useRef({ onUse, canUse, onSkip, busy });
  latest.current = { onUse, canUse, onSkip, busy };
  useEffect(() => {
    if (!shortcuts) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      if (isInteractiveTarget(event.target)) return;
      const cur = latest.current;
      if (event.key === "Enter" && cur.onUse && cur.canUse && !cur.busy) {
        event.preventDefault();
        cur.onUse();
      } else if (event.key === "Escape" && !embedded && cur.onSkip && !cur.busy) {
        event.preventDefault();
        cur.onSkip();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [embedded, shortcuts]);

  const long = (text?.length ?? 0) > LONG_TEXT;
  const keys = shortcuts && !embedded;
  const hasActions = Boolean(onNeverAsk || onSkip || secondary || onUse);
  return (
    <section
      className={styles.frame}
      data-embedded={embedded || undefined}
      data-tone={tone}
      title={hint}
      // Strefa decyzji (U3): dymki mapy, dok ręki i baner reakcji jej nie zasłaniają.
      {...DECISION_ZONE}
      role="group"
      aria-label={ariaLabel}
    >
      <header className={styles.head}>
        {icon && <span className={styles.icon}>{icon}</span>}
        <span className={styles.titleBox}>
          {(kind || ownerId) && (
            <small className={styles.kind}>
              {kind}
              {ownerId && (
                <>
                  {kind ? " · " : ""}
                  <PlayerTag playerId={ownerId} size={13} />
                </>
              )}
            </small>
          )}
          <span className={styles.titleRow} data-no-drag>
            {typeof title === "string" ? <b className={styles.title}>{title}</b> : title}
            {infoRef && (
              <ComponentInfoButton componentRef={infoRef} name={infoName ?? (typeof title === "string" ? title : (typeof kind === "string" ? kind : "component"))} />
            )}
          </span>
        </span>
        {required && <span className={styles.tag} data-tone="required">Required</span>}
        {queued > 0 && <span className={styles.tag}>+{queued} more</span>}
      </header>

      {subtitle && <p className={styles.subtitle}>{subtitle}</p>}

      {text && (
        <div className={styles.textBlock}>
          <p className={styles.text} data-open={showText || !long || undefined}>
            {text}
          </p>
          {long && (
            <button
              type="button"
              className={styles.more}
              onClick={() => setShowText((open) => !open)}
            >
              {showText ? "less" : "more"}
              {showText ? (
                <IconChevronUp size={12} aria-hidden="true" />
              ) : (
                <IconChevronDown size={12} aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      )}

      {children}
      {notes.map((note) => (
        <p key={note} className={styles.note}>
          {note}
        </p>
      ))}
      {warnings.map((warning) => (
        <p key={warning} className={styles.warn}>
          {warning}
        </p>
      ))}

      {hasActions && (
        <footer className={styles.actions}>
          {onNeverAsk && (
            <button
              type="button"
              className={styles.never}
              disabled={busy}
              onClick={onNeverAsk}
              title={neverAskHint}
            >
              Never ask
            </button>
          )}
          {onSkip && (
            <button type="button" className={styles.skip} disabled={busy} onClick={onSkip}>
              {skipLabel} {keys && <kbd>Esc</kbd>}
            </button>
          )}
          {secondary && (
            <button type="button" className={styles.skip} disabled={busy} onClick={secondary.onClick}>
              {secondary.label}
            </button>
          )}
          {onUse && (
            <button type="button" className={styles.use} disabled={!canUse || busy} onClick={onUse}>
              <span className={styles.useLabel}>{useLabel}</span> {shortcuts && <kbd>Enter</kbd>}
            </button>
          )}
        </footer>
      )}
    </section>
  );
}

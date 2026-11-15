import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { IconChevronDown, IconChevronUp, IconHourglassHigh, IconHourglassOff } from "@tabler/icons-react";
import type { OpenTimingWindow } from "@/api/useOpenWindows";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { goneSince, mergeGone, type Gone } from "./timingWindows";
import styles from "./AbilityPrompts.module.css";

/*
 * Okna czasowe (RULES.md 54.9): JEDEN cichy chip w centrum decyzji (wygląd znacznika „Ready”),
 * widoczny dla wszystkich - bez informacji o rękach. Silnik podaje tylko okna, na które coś w grze
 * może jeszcze zareagować. Okno, które właśnie minęło, liczy się chwilę jako „closed”; lista
 * (co je zamyka) po kliknięciu. Właściciel karty dostaje osobno wyraźną kartę „Window open now”.
 */

const windowKey = (w: OpenTimingWindow) => w.key;

/**
 * Elementy, które zniknęły z `items`, trzymane przez `CLOSED_NOTICE_MS`. `items` musi mieć stałą
 * referencję między renderami (useMemo), a `key` być funkcją modułu.
 */
export function useRecentlyGone<T>(items: T[], key: (item: T) => string): T[] {
  const prev = useRef<T[]>(items);
  const [gone, setGone] = useState<Gone<T>[]>([]);
  useEffect(() => {
    const just = goneSince(prev.current, items, key);
    prev.current = items;
    setGone((cur) => mergeGone(cur, just, items, key, Date.now()));
  }, [items, key]);
  // Jeden zegar do najbliższego wygaśnięcia (nie ginie przy kolejnej zmianie listy).
  useEffect(() => {
    if (gone.length === 0) return;
    const next = Math.min(...gone.map((g) => g.until));
    const timer = window.setTimeout(
      () => setGone((cur) => mergeGone(cur, [], [], key, Date.now())),
      Math.max(0, next - Date.now()) + 20,
    );
    return () => window.clearTimeout(timer);
  }, [gone, key]);
  return useMemo(() => gone.map((g) => g.item), [gone]);
}

export function TimingWindowChips({
  windows,
  onDragStart,
  onDragReset,
}: {
  windows: OpenTimingWindow[];
  onDragStart: (event: ReactPointerEvent) => void;
  onDragReset: () => void;
}) {
  const closed = useRecentlyGone(windows, windowKey);
  const [open, setOpen] = useState(false);
  if (windows.length === 0 && closed.length === 0) return null;
  const Icon = windows.length > 0 ? IconHourglassHigh : IconHourglassOff;
  const summary = [
    windows.length > 0 ? `${windows.length} open` : null,
    closed.length > 0 ? `${closed.length} closed` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <section
      className={styles.chip}
      data-standing
      data-tone={windows.length > 0 ? "timing" : "closed"}
      aria-label={`Timing windows: ${summary}`}
    >
      <div
        className={styles.chipRow}
        onPointerDown={onDragStart}
        onDoubleClick={onDragReset}
        title="Drag to move · double-click resets position"
      >
        <Icon size={14} aria-hidden="true" className={styles.icon} />
        <button
          type="button"
          data-no-drag
          className={styles.chipName}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          title={open ? "Hide timing windows" : "Show timing windows"}
        >
          <small className={styles.kind}>Windows</small>
          <b>{summary}</b>
          {open ? (
            <IconChevronUp size={12} aria-hidden="true" />
          ) : (
            <IconChevronDown size={12} aria-hidden="true" />
          )}
        </button>
      </div>
      {open && (
        <ul className={styles.text} data-windows>
          {windows.map((w) => (
            <WindowRow key={w.key} window={w} />
          ))}
          {closed.map((w) => (
            <WindowRow key={`closed:${w.key}`} window={w} closed />
          ))}
        </ul>
      )}
    </section>
  );
}

/** Jedno okno na liście: kto, kiedy i co je zamyka (zamknięte - przekreślone). */
function WindowRow({ window: w, closed = false }: { window: OpenTimingWindow; closed?: boolean }) {
  return (
    <li data-closed={closed || undefined} data-subject={w.subject ? true : undefined}>
      {w.subject && <PlayerTag playerId={w.subject} size={12} />}
      <b>{w.label}</b>
      <small>{closed ? "Closed - the game moved on" : w.closes}</small>
    </li>
  );
}

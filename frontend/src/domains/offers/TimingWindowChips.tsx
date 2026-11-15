import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { IconChevronDown, IconChevronUp, IconHourglassHigh, IconHourglassOff } from "@tabler/icons-react";
import type { OpenTimingWindow } from "@/api/useOpenWindows";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { goneSince, mergeGone, type Gone } from "./timingWindows";
import styles from "./AbilityPrompts.module.css";

/*
 * Pasek okien czasowych (RULES.md 54.9): każde okno otwarte TERAZ jako cichy chip w centrum decyzji
 * (ten sam wygląd co znacznik „Ready”), widoczny dla wszystkich graczy - bez informacji o rękach.
 * Okno, które właśnie minęło, zostaje chwilę jako „Closed”: gracze widzą, że gra z niego wyszła.
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
  return (
    <>
      {windows.map((w) => (
        <WindowChip key={w.key} window={w} onDragStart={onDragStart} onDragReset={onDragReset} />
      ))}
      {closed.map((w) => (
        <WindowChip
          key={`closed:${w.key}`}
          window={w}
          closed
          onDragStart={onDragStart}
          onDragReset={onDragReset}
        />
      ))}
    </>
  );
}

function WindowChip({
  window: w,
  closed = false,
  onDragStart,
  onDragReset,
}: {
  window: OpenTimingWindow;
  closed?: boolean;
  onDragStart: (event: ReactPointerEvent) => void;
  onDragReset: () => void;
}) {
  const [open, setOpen] = useState(false);
  const Icon = closed ? IconHourglassOff : IconHourglassHigh;
  return (
    <section
      className={styles.chip}
      data-standing
      data-tone={closed ? "closed" : "timing"}
      aria-label={`${closed ? "Timing window closed" : "Timing window open"}: ${w.label}`}
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
          title={closed ? "This window has closed" : w.closes}
        >
          <small className={styles.kind}>{closed ? "Closed" : "Window"}</small>
          {w.subject && <PlayerTag playerId={w.subject} size={13} />}
          <b>{w.label}</b>
          {open ? (
            <IconChevronUp size={12} aria-hidden="true" />
          ) : (
            <IconChevronDown size={12} aria-hidden="true" />
          )}
        </button>
      </div>
      {open && (
        <p className={styles.text}>
          {closed
            ? "The game moved on - cards and abilities for this moment can no longer be used."
            : `${w.closes}. Cards and abilities for this moment can be used now.`}
        </p>
      )}
    </section>
  );
}

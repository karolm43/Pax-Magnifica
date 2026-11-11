import type { ReactNode } from "react";
import { AppModal } from "@/shared/ui/AppModal";
import classes from "./KeyboardShortcutsModal.module.css";

type KeyboardShortcutsModalProps = {
  opened: boolean;
  onClose: () => void;
};

type Shortcut = {
  description: string;
  /** Each entry is one key; alternatives for the same action share an entry as "+ =". */
  keys: string[];
  /** A contiguous run, drawn with an ellipsis between its ends. */
  range?: boolean;
};

/* Jedyny opis skrótów dla gracza — trzymaj w zgodzie z `hooks/useKeyboardShortcuts.ts`. */
const PLAYERS: Shortcut[] = [
  { description: "Player area by seat", keys: ["1", "2", "3", "8"], range: true },
  { description: "Same key again: back to board", keys: ["1–8"] },
  { description: "Player on the board", keys: ["Shift 1–8"] },
  { description: "Previous / next player", keys: ["[", "]"] },
  { description: "Objectives & points", keys: ["g"] },
  { description: "Back to the board", keys: ["b", "Home"] },
];

const MAP: Shortcut[] = [
  { description: "Zoom in / out", keys: ["+", "-"] },
  { description: "Zoom at cursor", keys: ["Ctrl Wheel"] },
  { description: "Fit board to window", keys: ["0"] },
  { description: "Planet traits", keys: ["y"] },
  { description: "Tech skips", keys: ["t"] },
  { description: "Attachments", keys: ["a"] },
  { description: "Space Cannon range", keys: ["p"] },
  { description: "Control overlays", keys: ["o"] },
];

const TOOLS: Shortcut[] = [
  { description: "Search the board", keys: ["/", "Ctrl F"] },
  { description: "Next / previous match", keys: ["Enter", "Shift Enter"] },
  { description: "Close panel / selection", keys: ["Esc"] },
  { description: "This list", keys: ["?"] },
];

function Keycap({ children }: { children: ReactNode }) {
  return <kbd className={classes.kbd}>{children}</kbd>;
}

function KeySequence({ keys, range }: Pick<Shortcut, "keys" | "range">) {
  if (!range) {
    return (
      <span className={classes.kseq}>
        {keys.map((key) => (
          <Keycap key={key}>{key}</Keycap>
        ))}
      </span>
    );
  }
  const head = keys.slice(0, -1);
  const last = keys[keys.length - 1];
  return (
    <span className={classes.kseq}>
      {head.map((key) => (
        <Keycap key={key}>{key}</Keycap>
      ))}
      <span className={classes.ellipsis} aria-label="through">
        …
      </span>
      <Keycap>{last}</Keycap>
    </span>
  );
}

function ShortcutColumn({ label, shortcuts }: { label: string; shortcuts: Shortcut[] }) {
  return (
    <section className={classes.column}>
      <div className={`overlay-modal-label ${classes.columnLabel}`}>{label}</div>
      {shortcuts.map((shortcut) => (
        <div key={shortcut.description} className={classes.krow}>
          <span>{shortcut.description}</span>
          <KeySequence keys={shortcut.keys} range={shortcut.range} />
        </div>
      ))}
    </section>
  );
}

export function KeyboardShortcutsModal({
  opened,
  onClose,
}: KeyboardShortcutsModalProps) {
  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title="Keyboard shortcuts"
      size={680}
      padding={0}
    >
      <div className="overlay-modal-content">
        <div className={classes.keys}>
          <ShortcutColumn label="Players & areas" shortcuts={PLAYERS} />
          <ShortcutColumn label="Map & lenses" shortcuts={MAP} />
          <ShortcutColumn label="Tools" shortcuts={TOOLS} />
        </div>
      </div>
      <footer className="overlay-modal-footer" data-align="start">
        <p className="overlay-modal-note">
          Shortcuts pause while you type or while a window is open.
        </p>
      </footer>
    </AppModal>
  );
}

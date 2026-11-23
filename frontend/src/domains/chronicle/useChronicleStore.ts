import { create } from "zustand";

const SEEN_KEY = "chronicle.seenSeq";

function readSeen(): number | null {
  try {
    const raw = sessionStorage.getItem(SEEN_KEY);
    return raw === null ? null : Number(raw);
  } catch {
    return null;
  }
}

/**
 * Stan Kroniki wspólny dla przycisku i księgi: czy okno jest otwarte oraz do którego wpisu
 * (`seq`) wszystko uznano za przeczytane — dzięki temu miganie przycisku gaśnie dokładnie
 * wtedy, gdy ktoś otworzy księgę.
 */
type ChronicleStore = {
  open: boolean;
  seenSeq: number | null;
  setOpen: (open: boolean) => void;
  markSeen: (seq: number) => void;
};

export const useChronicleStore = create<ChronicleStore>((set) => ({
  open: false,
  seenSeq: readSeen(),
  setOpen: (open) => set({ open }),
  markSeen: (seq) => {
    try {
      sessionStorage.setItem(SEEN_KEY, String(seq));
    } catch {
      /* brak storage — licznik żyje tylko w pamięci */
    }
    set({ seenSeq: seq });
  },
}));

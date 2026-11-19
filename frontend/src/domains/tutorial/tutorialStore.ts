import { create } from "zustand";
import type { ChapterId } from "./tutorialContent";

const COACH_KEY = "tutorial:coach";

function readCoachOpen(): boolean {
  try {
    return localStorage.getItem(COACH_KEY) !== "closed";
  } catch {
    return true; // brak dostępu do localStorage — domyślnie panel otwarty
  }
}

function writeCoachOpen(open: boolean): void {
  try {
    localStorage.setItem(COACH_KEY, open ? "open" : "closed");
  } catch {
    /* nie zapamiętamy wyboru — panel i tak działa */
  }
}

type TutorialState = {
  /** Otwarty rozdział okna How to play; null = okno zamknięte. */
  chapter: ChapterId | null;
  /** Panel „What now?” rozwinięty (true) czy zwinięty do ikony. */
  coachOpen: boolean;
  openGuide: (chapter?: ChapterId) => void;
  closeGuide: () => void;
  setCoachOpen: (open: boolean) => void;
};

/** Samouczek: okno How to play i panel podpowiedzi „What now?” (widoczność zapamiętana). */
export const useTutorialStore = create<TutorialState>((set) => ({
  chapter: null,
  coachOpen: readCoachOpen(),
  openGuide: (chapter = "goal") => set({ chapter }),
  closeGuide: () => set({ chapter: null }),
  setCoachOpen: (coachOpen) => {
    writeCoachOpen(coachOpen);
    set({ coachOpen });
  },
}));

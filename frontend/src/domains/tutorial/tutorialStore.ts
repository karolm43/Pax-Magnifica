import { create } from "zustand";
import type { ChapterId } from "./tutorialContent";
import type { TutorialTargetId } from "./targets";

const COACH_KEY = "tutorial:coach";
/** Game ids whose Guided UI Tour was offered (finished, dismissed or skipped). */
const TOUR_SEEN_KEY = "tutorial:tour-seen";
/** "Skip all": no tour offer and no first-time milestone tips. */
const TIPS_OFF_KEY = "tutorial:tips-off";
/** Milestone tip ids already shown and dismissed. */
const TIPS_SEEN_KEY = "tutorial:tips-seen";

/** First-time milestone tips (Layer 3). */
export type MilestoneId = "strategy-pick" | "tactical-activation" | "secondary" | "combat" | "production";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // no localStorage access: fall back to defaults
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* choice not remembered — the tutorial still works for this session */
  }
}

function readList(key: string): string[] {
  try {
    const parsed: unknown = JSON.parse(read(key) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function writeList(key: string, list: string[]): void {
  write(key, JSON.stringify(list));
}

type TutorialState = {
  /** Open chapter of the How to play window; null = closed. */
  chapter: ChapterId | null;
  /** "What now?" section expanded (true) or collapsed. */
  coachOpen: boolean;

  /** Guided UI Tour: index of the current step; null = tour not running. */
  tourStep: number | null;
  /** The first-visit "Take the tour?" offer is showing. */
  tourOffered: boolean;
  /** Game ids whose tour was already offered/taken (persisted). */
  tourSeenGames: string[];
  /** "Skip all" was chosen: no offers, no milestone tips (persisted). */
  tipsDisabled: boolean;
  /** Milestone tips already dismissed (persisted). */
  seenTips: string[];
  /** Target currently pulsing ("Show me" / milestone tip); null = none. */
  pulseTarget: TutorialTargetId | null;

  openGuide: (chapter?: ChapterId) => void;
  closeGuide: () => void;
  setCoachOpen: (open: boolean) => void;

  /** On entering a game: show the tour offer once per game, unless tips are disabled. */
  offerTourIfFirstVisit: (gameId: string) => void;
  startTour: () => void;
  setTourStep: (step: number) => void;
  /** Finish or dismiss the tour (and the offer); remembers the game as seen. */
  endTour: (gameId?: string) => void;
  /** Dismiss the tour, the offer and every milestone tip, permanently. */
  skipAll: (gameId?: string) => void;
  /** Replay: re-enable tips, forget seen tips, start the tour at step 0. */
  restartTour: () => void;
  markTipSeen: (id: MilestoneId) => void;
  pulse: (target: TutorialTargetId) => void;
  clearPulse: () => void;
};

/** Tutorial: How to play window, "What now?" coach, Guided UI Tour and milestone tips. */
export const useTutorialStore = create<TutorialState>((set, get) => ({
  chapter: null,
  coachOpen: read(COACH_KEY) !== "closed",
  tourStep: null,
  tourOffered: false,
  tourSeenGames: readList(TOUR_SEEN_KEY),
  tipsDisabled: read(TIPS_OFF_KEY) === "1",
  seenTips: readList(TIPS_SEEN_KEY),
  pulseTarget: null,

  openGuide: (chapter = "goal") => set({ chapter }),
  closeGuide: () => set({ chapter: null }),
  setCoachOpen: (coachOpen) => {
    write(COACH_KEY, coachOpen ? "open" : "closed");
    set({ coachOpen });
  },

  offerTourIfFirstVisit: (gameId) => {
    const s = get();
    if (s.tipsDisabled || s.tourStep != null || s.tourSeenGames.includes(gameId)) return;
    set({ tourOffered: true });
  },
  startTour: () => set({ tourStep: 0, tourOffered: false, chapter: null }),
  setTourStep: (tourStep) => set({ tourStep: Math.max(0, tourStep) }),
  endTour: (gameId) => {
    const seen = get().tourSeenGames;
    const tourSeenGames = gameId && !seen.includes(gameId) ? [...seen, gameId] : seen;
    writeList(TOUR_SEEN_KEY, tourSeenGames);
    set({ tourStep: null, tourOffered: false, tourSeenGames });
  },
  skipAll: (gameId) => {
    get().endTour(gameId);
    write(TIPS_OFF_KEY, "1");
    set({ tipsDisabled: true, pulseTarget: null });
  },
  restartTour: () => {
    write(TIPS_OFF_KEY, "0");
    writeList(TIPS_SEEN_KEY, []);
    set({ tipsDisabled: false, seenTips: [], tourOffered: false, tourStep: 0, chapter: null });
  },
  markTipSeen: (id) => {
    const seen = get().seenTips;
    if (seen.includes(id)) return;
    const seenTips = [...seen, id];
    writeList(TIPS_SEEN_KEY, seenTips);
    set({ seenTips });
  },
  pulse: (pulseTarget) => set({ pulseTarget }),
  clearPulse: () => set({ pulseTarget: null }),
}));

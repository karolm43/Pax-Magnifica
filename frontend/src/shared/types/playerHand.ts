export type PlayerHandData = {
  actionCards: string[];
  secretObjectives: string[];
  promissoryNotes: string[];
  /** Wierzchnie agendy podejrzane kartą Insider Information (tylko właściciel ręki). */
  agendaPeek?: string[];
  /** Tajne cele pokazane przez Extreme Duress: {właściciel: [cele]}. */
  revealedSecrets?: Record<string, string[]>;
};

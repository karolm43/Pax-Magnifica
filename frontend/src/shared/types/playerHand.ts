export type PlayerHandData = {
  actionCards: string[];
  secretObjectives: string[];
  promissoryNotes: string[];
  /**
   * Wiedza o talii agend (tylko właściciel ręki; RULES.md 53.5.a1): znane karty od góry
   * (Insider Information, Politics) i od spodu (Politics; ostatnia = sam spód).
   */
  agendaPeek?: string[];
  agendaPeekBottom?: string[];
  /** Tajne cele pokazane przez Extreme Duress: {właściciel: [cele]}. */
  revealedSecrets?: Record<string, string[]>;
};

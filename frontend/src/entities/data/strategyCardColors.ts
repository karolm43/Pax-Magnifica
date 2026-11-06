export const SC_COLORS: Record<number, string> = {
  1: "red",
  2: "orange",
  3: "yellow",
  4: "green",
  5: "teal",
  6: "cyan",
  7: "blue",
  8: "purple",
};

export const SC_NUMBER_COLORS: Record<string, string> = {
  red: "red.9",
  orange: "orange.9",
  yellow: "yellow.3",
  green: "green.9",
  teal: "teal.9",
  cyan: "cyan.9",
  blue: "blue.9",
  purple: "violet.9",
};

export const SC_NAMES: Record<number, string> = {
  1: "LEADERSHIP",
  2: "DIPLOMACY",
  3: "POLITICS",
  4: "CONSTRUCTION",
  5: "TRADE",
  6: "WARFARE",
  7: "TECHNOLOGY",
  8: "IMPERIAL",
};

/**
 * Barwa (hex) karty strategii po numerze inicjatywy — akcent wizualny/fallback,
 * gdy dane karty nie niosą ``colourHexCode``. Współdzielone przez panele tury
 * (``TurnControls``) i okno follow secondary (``SecondaryDecisionModal``).
 */
export const SC_HUES: Record<number, string> = {
  1: "#ec1c24",
  2: "#f69421",
  3: "#fff200",
  4: "#39b54a",
  5: "#00a99d",
  6: "#008ed4",
  7: "#15489f",
  8: "#752b90",
};

import { describe, expect, it } from "vitest";
import type { GameData } from "@/entities/game/types";
import { actionCards } from "@/entities/data/actionCards";
import { buildSearchIndex } from "./searchIndex";

/*
 * Zakryte talie (ustawienie „Look inside decks” (Settings → Testing), domyślnie wyłączone): wyszukiwarka nie
 * zdradza, co leży w talii ani co jest w czyjejś ręce - znajduje tylko jawne stosy.
 */
const discarded = actionCards.find((card) => card.alias === "sabo1") ?? actionCards[0];

const gameData = {
  playerData: [],
  tiles: {},
  factionColorMap: {},
  lawsInPlay: [],
  objectives: { allObjectives: [] },
  planetIdToPlanetTile: {},
  strategyCards: [],
  cardPool: {
    actionCardDeck: [],
    actionCardDiscard: [discarded.alias],
    culturalExploreDeck: [],
    culturalExploreDiscard: [],
    industrialExploreDeck: [],
    industrialExploreDiscard: [],
    hazardousExploreDeck: [],
    hazardousExploreDiscard: [],
    frontierExploreDeck: [],
    frontierExploreDiscard: [],
    purgedCards: [],
  },
} as unknown as GameData;

const cards = (browseDecks: boolean) =>
  buildSearchIndex(gameData, { browseDecks }).filter((entry) => entry.kind === "card");

describe("buildSearchIndex - zakryte talie", () => {
  it("bez ustawienia: tylko karty z jawnych stosów (odrzucone / purge)", () => {
    const found = cards(false);
    expect(found.length).toBeGreaterThan(0);
    expect(found.every((entry) => entry.deck?.tab === "discard" || entry.deck?.tab === "purged")).toBe(
      true,
    );
    expect(found.some((entry) => entry.detail === "Agenda deck")).toBe(false);
  });

  it("z ustawieniem: pełne pule talii", () => {
    expect(cards(true).some((entry) => entry.detail === "Agenda deck")).toBe(true);
  });
});

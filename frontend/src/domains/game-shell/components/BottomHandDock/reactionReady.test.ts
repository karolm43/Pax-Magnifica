import { describe, expect, it } from "vitest";
import { readyReactions } from "./reactionReady";

const card = (card_id: string, playable: boolean, reaction: boolean) => ({
  card_id, playable, reaction, reason: null, implemented: true,
});
const note = (note_id: string, playable: boolean, reaction: boolean) => ({
  note_id, template: note_id, owner_id: "p2", playable, reaction, reason: null, implemented: true,
});

describe("readyReactions", () => {
  it("liczy tylko zagrywalne karty i notki REAKCJI", () => {
    const ready = readyReactions(
      { sabo1: card("sabo1", true, true), ec: card("ec", true, false), dh: card("dh", false, true) },
      { red_ms: note("red_ms", true, true), red_ta: note("red_ta", true, false) },
    );
    expect(ready).toEqual([
      { tab: "actions", id: "sabo1" },
      { tab: "notes", id: "red_ms" },
    ]);
  });

  it("bez danych - pusto", () => {
    expect(readyReactions(undefined, undefined)).toEqual([]);
  });
});

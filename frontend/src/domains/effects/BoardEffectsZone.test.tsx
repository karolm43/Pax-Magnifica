import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ActiveEffectData } from "@/entities/data/types";
import type { GameData } from "@/entities/game/types";
import { TILE_HEIGHT, TILE_WIDTH, calculateSingleTilePosition } from "@/entities/geometry/tilePositioning";
import { BoardEffectsZone, BoardLawsZone } from "./BoardEffectsZone";
import { ZONE_GAP, effectsZoneAnchor, zoneCells } from "./effectsZoneAnchor";

const effectsRef: { current: ActiveEffectData[] } = { current: [] };

vi.mock("@/api/useGameState", () => ({
  useGameState: () => ({ data: { activeEffects: effectsRef.current } }),
}));

/** Pola graczy z mapy 6-osobowej (3 pierścienie), w kolejności miejsc od góry zgodnie z zegarem. */
const SIX_PLAYERS: Record<string, string[]> = {
  yin: ["401", "402", "424"],
  crimson: ["405", "404", "406"],
  ralnel: ["409", "408", "410"],
  letnev: ["413", "412", "414"],
  keleresx: ["417", "416", "418"],
  sol: ["421", "420", "422"],
};

const gameData = { statTilePositions: SIX_PLAYERS, ringCount: 3, tilePositions: [], playerData: [] };

const effect = (over: Partial<ActiveEffectData> = {}): ActiveEffectData => ({
  id: "e1",
  key: "leaders:letnevhero",
  name: "Darktalon Treilla",
  kind: "Hero",
  text: "Until the end of the game round, you may have more ships than your fleet pool.",
  owner: null,
  scope: "round",
  until: "this game round",
  detail: "",
  round: 1,
  ...over,
});

const renderZone = () =>
  render(
    <MemoryRouter>
      <BoardEffectsZone gameData={gameData as unknown as GameData} tiles={[]} />
    </MemoryRouter>,
  );

describe("effectsZoneAnchor", () => {
  it("6 graczy: heks w wolnej komórce 407 między polami graczy 2 i 3, równo z planszą", () => {
    const anchor = effectsZoneAnchor(SIX_PLAYERS, 3, []);
    const gapHex = calculateSingleTilePosition("407", 3);
    expect(anchor).toEqual({ x: gapHex.x, y: gapHex.y });
    // Pole gracza 2 (406) kończy się nad tacą, pole gracza 3 (408) zaczyna pod nią.
    expect(calculateSingleTilePosition("406", 3).y + TILE_HEIGHT).toBeLessThanOrEqual(anchor!.y);
    expect(calculateSingleTilePosition("408", 3).y).toBeGreaterThanOrEqual(anchor!.y + TILE_HEIGHT);
  });

  it("komórka zajęta przez kafel planszy - taca za prawą krawędzią planszy", () => {
    const gapHex = calculateSingleTilePosition("407", 3);
    const far = { x: 99999, y: 0 };
    const anchor = effectsZoneAnchor(SIX_PLAYERS, 3, [], [gapHex, far]);
    expect(anchor?.x).toBe(far.x + TILE_WIDTH + ZONE_GAP);
  });

  it("więcej efektów niż mieści heks - kolejne heksy w prawo po siatce", () => {
    expect(zoneCells(0)).toEqual([{ x: 0, y: 0 }]);
    expect(zoneCells(6)).toHaveLength(1);
    expect(zoneCells(7)).toEqual([{ x: 0, y: 0 }, { x: 260, y: 150 }]);
  });

  it("lewa strona: taca leży na lewo od środka planszy, kolejne heksy w lewo", () => {
    const right = effectsZoneAnchor(SIX_PLAYERS, 3, [])!;
    const left = effectsZoneAnchor(SIX_PLAYERS, 3, [], [], "left")!;
    expect(left.x).toBeLessThan(right.x);
    expect(zoneCells(7, "left")).toEqual([{ x: 0, y: 0 }, { x: -260, y: 150 }]);
  });

  it("bez pól graczy nie ma gdzie położyć tacy", () => {
    expect(effectsZoneAnchor({}, 3, [])).toBeNull();
  });
});

describe("BoardEffectsZone", () => {
  beforeEach(() => {
    effectsRef.current = [];
  });

  it("taca leży na planszy także bez efektów", () => {
    renderZone();
    expect(screen.getByRole("region", { name: "Active effects" })).toBeInTheDocument();
    expect(screen.getByText("None in play")).toBeInTheDocument();
  });

  it("każdy efekt to żeton na tacy", () => {
    effectsRef.current = ["A", "B", "C", "D"].map((name, i) => effect({ id: `e${i}`, name }));
    renderZone();
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
  });

  it("klik w efekt pokazuje kartę z tekstem i czasem trwania", async () => {
    effectsRef.current = [effect()];
    renderZone();
    const chip = screen.getByRole("button", { name: /Darktalon Treilla/ });
    expect(chip).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(chip);
    // SmoothPopover uzbraja się przy pierwszym otwarciu i podmienia węzeł celu.
    expect(screen.getByRole("button", { name: /Darktalon Treilla/ })).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByText(/more ships than your fleet pool/)).toBeInTheDocument();
    expect(screen.getByText("this game round")).toBeInTheDocument();
  });
});

describe("BoardLawsZone", () => {
  it("lewa taca praw: pusta i napis wyjaśnia, co pokazuje", async () => {
    render(
      <MemoryRouter>
        <BoardLawsZone gameData={gameData as unknown as GameData} tiles={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("region", { name: "Laws in play" })).toBeInTheDocument();
    expect(screen.getByText("No laws in play")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Laws - what is this/ }));
    expect(await screen.findByText(/passed in the Agenda phase/)).toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ActiveEffectData } from "@/entities/data/types";
import type { GameData } from "@/entities/game/types";
import { calculateSingleTilePosition } from "@/entities/geometry/tilePositioning";
import { BoardEffectsZone } from "./BoardEffectsZone";
import { effectsZoneAnchor } from "./effectsZoneAnchor";

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
      <BoardEffectsZone gameData={gameData as unknown as GameData} />
    </MemoryRouter>,
  );

describe("effectsZoneAnchor", () => {
  it("6 graczy: taca na pozycji 407, między polami gracza 2 i 3 po prawej", () => {
    expect(effectsZoneAnchor(SIX_PLAYERS, 3, [])).toEqual(calculateSingleTilePosition("407", 3));
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

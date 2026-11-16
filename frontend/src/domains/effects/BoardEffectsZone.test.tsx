import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ActiveEffectData } from "@/entities/data/types";
import { BoardEffectsZone } from "./BoardEffectsZone";

const effectsRef: { current: ActiveEffectData[] } = { current: [] };

vi.mock("@/api/useGameState", () => ({
  useGameState: () => ({ data: { activeEffects: effectsRef.current } }),
}));
vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({ playerData: [] }),
}));

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

describe("BoardEffectsZone", () => {
  beforeEach(() => {
    effectsRef.current = [];
  });

  it("pole leży przy planszy także bez efektów", () => {
    render(<BoardEffectsZone gameId="g" bleedRight={0} />);
    expect(screen.getByRole("region", { name: "Active effects" })).toBeInTheDocument();
    expect(screen.getByText("No lasting effects in play")).toBeInTheDocument();
  });

  it("karta efektu pokazuje czas trwania, a po kliknięciu tekst", () => {
    effectsRef.current = [effect()];
    render(<BoardEffectsZone gameId="g" bleedRight={0} />);
    expect(screen.getByText("this game round")).toBeInTheDocument();
    const card = screen.getByRole("button", { name: /Darktalon Treilla/ });
    expect(card).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(card);
    expect(card).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/more ships than your fleet pool/)).toBeInTheDocument();
  });
});

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerData, ReactionPrefsData } from "@/entities/data/types";
import type { ReactionPrefsChange } from "@/api/useActionCard";
import { ReactionSettings, reactionSummary } from "./ReactionSettings";

const post = vi.fn<(actor: string, change: ReactionPrefsChange) => Promise<void>>();

vi.mock("@/api/useActionCard", () => ({
  postReactionPrefs: (actor: string, change: ReactionPrefsChange) => post(actor, change),
}));

/** Czeka, aż zapis się zakończy (przyciski są wyłączone na czas zapisu). */
const settle = () => act(async () => {});

const prefs = (over: Partial<ReactionPrefsData> = {}): ReactionPrefsData => ({
  passes: {},
  onlyInvolved: false,
  mutedCards: [],
  mutedOffers: [],
  ...over,
});
const player = (over: Partial<ReactionPrefsData> = {}) =>
  ({ discordId: "p1", reactionPrefs: prefs(over) }) as PlayerData;

describe("ReactionSettings (RULES.md 54.11-54.12)", () => {
  beforeAll(() => {
    // jsdom nie ma PointerEvent, a Base UI Switch tworzy go przy kliknięciu.
    window.PointerEvent ??= MouseEvent as unknown as typeof PointerEvent;
  });
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue(undefined);
  });

  it("deklaracja pasu: kategoria i czas trwania", async () => {
    render(<ReactionSettings player={player()} />);
    fireEvent.click(screen.getByRole("button", { name: "Reaction settings" }));
    await screen.findByRole("dialog", { name: "Reaction settings" });
    const agenda = screen.getByRole("radiogroup", { name: "Pass on Agendas" });
    expect(agenda).toHaveTextContent("This agenda");
    fireEvent.click(screen.getAllByRole("radio", { name: "This agenda" })[0]);
    expect(post).toHaveBeenCalledWith("p1", { declare: { agenda: "agenda" } });
    await settle();
    fireEvent.click(screen.getAllByRole("radio", { name: "This turn" })[0]);
    expect(post).toHaveBeenLastCalledWith("p1", { declare: { all: "turn" } });
  });

  it("odwołanie deklaracji i „only when it concerns me”", async () => {
    render(<ReactionSettings player={player({ passes: { combat: "round" } })} />);
    fireEvent.click(screen.getByRole("button", { name: /Reaction settings/ }));
    await screen.findByRole("dialog", { name: "Reaction settings" });
    const combat = screen.getByRole("radiogroup", { name: "Pass on Combat" });
    const off = [...combat.querySelectorAll("button")].find((b) => b.textContent === "Off");
    fireEvent.click(off!);
    expect(post).toHaveBeenCalledWith("p1", { declare: { combat: null } });
    await settle();
    fireEvent.click(screen.getByRole("switch"));
    expect(post).toHaveBeenLastCalledWith("p1", { only_involved: true });
  });

  it("wyciszone karty i oferty: chip przywraca pytanie", async () => {
    render(
      <ReactionSettings
        player={player({
          mutedCards: ["Sabotage"],
          mutedOffers: [{ key: "leaders:x", name: "Magmus" }],
        })}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Reaction settings" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ask again about Sabotage" }));
    expect(post).toHaveBeenCalledWith("p1", { mute_cards: { Sabotage: false } });
    await settle();
    fireEvent.click(screen.getByRole("button", { name: "Ask again about Magmus" }));
    expect(post).toHaveBeenLastCalledWith("p1", { mute_offers: { "leaders:x": false } });
  });

  it("przycisk pokazuje aktywną deklarację", () => {
    expect(reactionSummary(prefs({ passes: { all: "always" } }))).toBe("Auto-pass");
    expect(reactionSummary(prefs({ passes: { all: "round" } }))).toBe("Passing: this round");
    expect(reactionSummary(prefs({ passes: { agenda: "agenda", combat: "turn" } }))).toBe(
      "Passing 2",
    );
    expect(reactionSummary(prefs())).toBeNull();
    render(<ReactionSettings player={player({ passes: { all: "always" } })} />);
    expect(screen.getByRole("button", { name: "Reaction settings: Auto-pass" })).toHaveTextContent(
      "Auto-pass",
    );
  });
});

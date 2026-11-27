import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerData, ReactionPrefsData } from "@/entities/data/types";
import type { ReactionPrefsChange } from "@/api/useActionCard";
import { ReactionSettings, reactionSummary } from "./ReactionSettings";

const post = vi.fn<(actor: string, change: ReactionPrefsChange) => Promise<void>>();

vi.mock("@/api/useActionCard", () => ({
  postReactionPrefs: (actor: string, change: ReactionPrefsChange) => post(actor, change),
}));

// Cooperative effects (RULES.md 54.15): the owner's terms come from /boosts.
const configure = vi.fn(async () => {});
const watch = vi.fn(async () => {});
let owned: { source: string; name: string; text: string; kind: string; mode: string; price: number; freeFor: string[] }[] = [];
vi.mock("@/api/useBoosts", () => ({
  useBoosts: () => ({ data: { available: [], outgoing: [], owned, watch: null } }),
  useBoostActions: () => ({ configure, watch, request: vi.fn(), withdraw: vi.fn() }),
}));
vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({
    playerData: [
      { discordId: "p1", color: "red", faction: "saar" },
      { discordId: "p2", color: "blue", faction: "sol", displayName: "Blue" },
    ],
  }),
}));
vi.mock("@/shared/ui/PlayerTag", () => ({
  PlayerTag: ({ playerId }: { playerId: string }) => <span>{playerId}</span>,
}));
vi.mock("@/domains/player/components/Leader/LeaderChip", () => ({ LeaderChip: () => null }));

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
    configure.mockClear();
    watch.mockClear();
    owned = [];
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
    fireEvent.click(screen.getByRole("switch", { name: /Ask me only when it concerns me/ }));
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

  it("unless something changes: the next declaration is conditional (54.13)", async () => {
    render(<ReactionSettings player={player({ unlessChanges: ["combat"], passes: { combat: "turn" } })} />);
    fireEvent.click(screen.getByRole("button", { name: /Reaction settings/ }));
    await screen.findByRole("dialog", { name: "Reaction settings" });
    expect(screen.getByRole("radiogroup", { name: "Pass on Combat" }).parentElement).toHaveTextContent(
      "unless something changes",
    );
    fireEvent.click(screen.getByRole("switch", { name: /unless something changes/ }));
    fireEvent.click(screen.getAllByRole("radio", { name: "This agenda" })[0]);
    expect(post).toHaveBeenCalledWith("p1", { declare: { agenda: "agenda" }, unless_changes: true });
  });

  it("cancelled pre-pass notice and Got it", async () => {
    render(
      <ReactionSettings
        player={player({ notices: [{ category: "sabotage", actor: "p2", reason: "played an action card" }] })}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Reaction settings/ }));
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("Your pass on Cards played by others was cancelled: p2 played an action card.");
    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    expect(post).toHaveBeenCalledWith("p1", { clear_notices: true });
  });

  it("combat hits policy (54.14)", async () => {
    render(<ReactionSettings player={player()} />);
    fireEvent.click(screen.getByRole("button", { name: /Reaction settings/ }));
    await screen.findByRole("dialog", { name: "Reaction settings" });
    fireEvent.click(screen.getByRole("radio", { name: "Sustain + fodder" }));
    expect(post).toHaveBeenCalledWith("p1", { auto_hits: "cheap" });
  });

  it("agents & abilities: Ask me / Standing offer / Self-only and Watch (54.15)", async () => {
    owned = [{ source: "leaders:saaragent", name: "Captain Mendosa", text: "", kind: "Agent", mode: "ask", price: 0, freeFor: [] }];
    const { rerender } = render(<ReactionSettings player={player()} othersTurn />);
    fireEvent.click(screen.getByRole("button", { name: /Reaction settings/ }));
    await screen.findByRole("region", { name: "Agents and abilities" });
    fireEvent.click(screen.getByRole("radio", { name: "Standing offer" }));
    expect(configure).toHaveBeenCalledWith("p1", "leaders:saaragent", "standing", 0, []);
    await settle();
    const watchGroup = screen.getByRole("radiogroup", { name: "Watch" });
    fireEvent.click([...watchGroup.querySelectorAll("button")].find((b) => b.textContent === "This turn")!);
    expect(watch).toHaveBeenCalledWith("p1", "turn");
    await settle();
    owned = [{ ...owned[0], mode: "standing", price: 2 }];
    rerender(<ReactionSettings player={player()} othersTurn />);
    const allies = await screen.findByRole("group", { name: "Free Captain Mendosa for" });
    fireEvent.click(allies.querySelector("button")!);
    expect(configure).toHaveBeenLastCalledWith("p1", "leaders:saaragent", "standing", 2, ["p2"]);
  });
});

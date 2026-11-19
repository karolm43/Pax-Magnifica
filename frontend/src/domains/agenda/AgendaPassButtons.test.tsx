import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayerData, ReactionPrefsData } from "@/entities/data/types";
import type { ReactionPrefsChange } from "@/api/useActionCard";
import { AgendaPassButtons } from "./AgendaPassButtons";

const post = vi.fn<(actor: string, change: ReactionPrefsChange) => Promise<void>>();

vi.mock("@/api/useActionCard", () => ({
  postReactionPrefs: (actor: string, change: ReactionPrefsChange) => post(actor, change),
}));

const settle = () => act(async () => {});

const me = (passes: ReactionPrefsData["passes"] = {}) =>
  ({
    discordId: "p1",
    reactionPrefs: { passes, onlyInvolved: false, mutedCards: [], mutedOffers: [] },
  }) as unknown as PlayerData;

describe("AgendaPassButtons (RULES.md 54.12)", () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue(undefined);
  });

  it("No whens / No afters deklarują pas na bieżącą agendę", async () => {
    render(<AgendaPassButtons me={me()} />);
    fireEvent.click(screen.getByRole("button", { name: "No whens" }));
    await settle();
    expect(post).toHaveBeenLastCalledWith("p1", { declare: { agenda_when: "agenda" } });
    fireEvent.click(screen.getByRole("button", { name: "No afters" }));
    await settle();
    expect(post).toHaveBeenLastCalledWith("p1", { declare: { agenda_after: "agenda" } });
  });

  it("włączona połowa: wciśnięta, kliknięcie odwołuje", async () => {
    render(<AgendaPassButtons me={me({ agenda_after: "agenda" })} />);
    const afters = screen.getByRole("button", { name: "No afters" });
    expect(afters).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "No whens" })).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(afters);
    await settle();
    expect(post).toHaveBeenLastCalledWith("p1", { declare: { agenda_after: null } });
  });

  it("pas na całą agendę z panelu Reactions obejmuje obie połowy", () => {
    render(<AgendaPassButtons me={me({ agenda: "round" })} />);
    for (const name of ["No whens", "No afters"]) {
      const button = screen.getByRole("button", { name });
      expect(button).toHaveAttribute("aria-pressed", "true");
      expect(button).toBeDisabled();
    }
  });
});

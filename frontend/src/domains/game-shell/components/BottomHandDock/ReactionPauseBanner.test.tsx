import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactionPauseData } from "@/entities/data/types";
import { ReactionPauseBanner } from "./ReactionPauseBanner";

const pauseRef: { current: ReactionPauseData | null } = { current: null };
const post = vi.fn<(action: string, actor: string) => void>();

vi.mock("@/api/useGameState", () => ({
  useGameState: () => ({ data: { reactionPause: pauseRef.current } }),
}));
vi.mock("@/api/useActionCard", () => ({
  postReactionPause: (action: string, actor: string) => {
    post(action, actor);
  },
}));
vi.mock("@/shared/ui/PlayerTag", () => ({
  PlayerTag: ({ playerId }: { playerId: string }) => <span>{playerId}</span>,
}));

const pause = (over: Partial<ReactionPauseData> = {}): ReactionPauseData => ({
  key: "3|agenda.revealed|after|{}",
  label: "After an agenda is revealed",
  event: "agenda.revealed",
  subject: null,
  subjectColor: null,
  openedAt: 100,
  pauseSeconds: 10,
  eligible: ["p1", "p3"],
  passed: [],
  ...over,
});

const show = (viewer: string | null, onNeedHand = vi.fn()) =>
  render(
    <MemoryRouter>
      <ReactionPauseBanner viewerId={viewer} onNeedHand={onNeedHand} />
    </MemoryRouter>,
  );

describe("ReactionPauseBanner (RULES.md 54.10–54.11)", () => {
  beforeEach(() => {
    post.mockReset();
    pauseRef.current = null;
  });

  it("bez pauzy nic nie pokazuje", () => {
    show("p1");
    expect(screen.queryByRole("status", { name: "Reaction window" })).toBeNull();
  });

  it("pytany gracz widzi okno, licznik i Pass; ręka się rozwija", () => {
    pauseRef.current = pause();
    const onNeedHand = vi.fn();
    show("p1", onNeedHand);
    expect(screen.getByRole("status", { name: "Reaction window" })).toHaveTextContent(
      "After an agenda is revealed",
    );
    expect(screen.getByLabelText("Seconds left")).toHaveTextContent("10s");
    expect(onNeedHand).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Pass" }));
    expect(post).toHaveBeenCalledWith("pass", "p1");
    fireEvent.click(screen.getByRole("button", { name: "+10s" }));
    expect(post).toHaveBeenCalledWith("wait", "p1");
  });

  it("gracz spoza pytanych tylko czeka i nie widzi, ilu spasowało", () => {
    pauseRef.current = pause({ passed: [], extensions: 1 });
    show("p2");
    expect(screen.queryByRole("button", { name: "Pass" })).toBeNull();
    expect(screen.queryByRole("button", { name: "+10s" })).toBeNull();
    const banner = screen.getByRole("status", { name: "Reaction window" });
    expect(banner).toHaveTextContent("Waiting for reactions");
    expect(banner).toHaveTextContent("Someone asked for more time");
    expect(banner).not.toHaveTextContent("passed");
  });

  it("za gracza bez karty silnik spasował: bez Pass i bez rozwijania ręki, ale z More time", () => {
    pauseRef.current = pause({ passed: ["p3"] });
    const onNeedHand = vi.fn();
    show("p3", onNeedHand);
    expect(onNeedHand).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Pass" })).toBeNull();
    expect(screen.getByRole("button", { name: "+10s" })).toBeEnabled();
    expect(screen.getByRole("status", { name: "Reaction window" })).toHaveTextContent(
      "You're not reacting",
    );
  });

  it("More time raz na okno", () => {
    pauseRef.current = pause({ askedForTime: ["p1"], pauseSeconds: 14, extensions: 1 });
    show("p1");
    expect(screen.getByRole("button", { name: "+10s" })).toBeDisabled();
    expect(screen.getByLabelText("Seconds left")).toHaveTextContent("14s");
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ActivityEntry } from "@/api/useBoardEditor";
import { getTechData } from "@/entities/lookup/tech";
import { ToastCard } from "./ActivityToasts";
import type { ActivityContext } from "./describeActivity";

const ctx: ActivityContext = {
  players: { p2: { faction: "sol", color: "red", display_name: "Ala", is_bot: false } },
  systemName: (pos) => pos,
  systemHint: () => "",
};

const entry = {
  seq: 7,
  is_current: true,
  created_at: null,
  activity: {
    kind: "tactical",
    action: "tech.exhaust",
    actor_id: "p2",
    target_id: null,
    subject: "gd",
    detail: null,
    round: 1,
    phase: "action",
    facts: [],
  },
} as ActivityEntry;

describe("ToastCard", () => {
  it("zwinięte pokazuje tylko kto co zrobił, kliknięcie rozwija tekst technologii", () => {
    const tech = getTechData("gd");
    expect(tech).toBeDefined();
    render(<ToastCard entry={entry} ctx={ctx} onClose={vi.fn()} />);
    expect(screen.getByText(/exhausted/)).toBeTruthy();
    expect(screen.queryByText(tech!.text)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Show details" }));
    expect(screen.getByText(tech!.text)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Hide details" })).toBeTruthy();
  });
});

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import { AchievementBoard, type AchievementData } from "./AchievementCard";
import { Podium, type PodiumPlace } from "./Podium";
import type { PlayerSummary } from "./gameStats";

const sol = { id: "p1", faction: "sol", factionName: "Federation of Sol", playerName: "Ann" };
const hacan = { id: "p2", faction: "hacan", factionName: "Emirates of Hacan", playerName: "Bob" };

const items: AchievementData[] = [
  { key: "warmonger", title: "The Warmonger", detail: "", stat: "3", players: [sol] },
  { key: "saboteur", title: "The Saboteur", detail: "", stat: "1", players: [hacan] },
  { key: "silk_road", title: "Silk Road", detail: "", stat: "2", players: [hacan] },
];

const cards = () => within(screen.getByRole("list")).getAllByRole("heading").map((h) => h.textContent);

describe("AchievementBoard", () => {
  it("pokazuje wszystkie karty w siatce i filtruje po kategorii", () => {
    render(
      <AchievementBoard
        title="Hall"
        items={items}
        players={[sol, hacan]}
        playerId={null}
        onSelectPlayer={() => {}}
      />,
    );
    expect(cards()).toEqual(["The Warmonger", "The Saboteur", "Silk Road"]);
    fireEvent.click(screen.getByRole("button", { name: /Treachery/ }));
    expect(cards()).toEqual(["The Saboteur"]);
    fireEvent.click(screen.getByRole("button", { name: /^All 3/ }));
    expect(cards()).toHaveLength(3);
  });

  it("każdy gracz (nie tylko z podium) może wybrać swoje osiągnięcia", () => {
    const select = vi.fn();
    const { rerender } = render(
      <AchievementBoard
        title="Hall"
        items={items}
        players={[sol, hacan]}
        playerId={null}
        onSelectPlayer={select}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Emirates of Hacan/ }));
    expect(select).toHaveBeenCalledWith("p2");
    rerender(
      <AchievementBoard
        title="Hall"
        items={items}
        players={[sol, hacan]}
        playerId="p2"
        onSelectPlayer={select}
      />,
    );
    expect(cards()).toEqual(["The Saboteur", "Silk Road"]);
    fireEvent.click(screen.getByRole("button", { name: "All players" }));
    expect(select).toHaveBeenLastCalledWith(null);
  });
});

describe("Podium", () => {
  const place = (id: string, faction: string, vp: number): PodiumPlace => ({
    row: { player: { discordId: id, faction } as PlayerData, vp } as PlayerSummary,
    factionName: faction,
    playerName: id,
    honors: 1,
  });

  it("ustawia 2 · 1 · 3 i wybiera gracza kliknięciem", () => {
    const onSelect = vi.fn();
    render(
      <Podium
        places={[place("a", "sol", 10), place("b", "hacan", 8), place("c", "xxcha", 6)]}
        factionById={new Map()}
        selected={null}
        onSelect={onSelect}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("aria-label")?.split(":")[0])).toEqual([
      "2nd place",
      "1st place",
      "3rd place",
    ]);
    fireEvent.click(screen.getByRole("button", { name: /1st place/ }));
    expect(onSelect).toHaveBeenCalledWith("a");
  });
});

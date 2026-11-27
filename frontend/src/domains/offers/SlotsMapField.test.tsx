import { useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { useAppStore, type MapPick } from "@/state/appStore";
import { DecisionFields } from "./DecisionFields";

// Plansza: dom Yin (301, planeta Darien) i system 102 z samą przestrzenią.
vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({
    playerData: [],
    tiles: { "301": { planets: { darien: {} } }, "102": { planets: {} } },
  }),
}));

function Harness({ inputs }: { inputs: ActionCardInput[] }) {
  const [values, setValues] = useState<Record<string, FormValue>>({});
  return (
    <DecisionFields
      inputs={inputs}
      values={values}
      disabled={false}
      onChange={(key, next) => setValues((prev) => ({ ...prev, [key]: next }))}
    />
  );
}

const pick = (): MapPick | null => useAppStore.getState().mapPick;

/** Trzy jednakowe sloty („Infantry N commits to”, każdy z „No infantry”) = jedno pole slotów. */
const slots: ActionCardInput[] = [1, 2, 3].map((n) => ({
  key: `inf${n}`,
  kind: "choice",
  label: `Infantry ${n} commits to`,
  hint: "",
  merge: false,
  options: [
    { id: "none", value: "none", label: "No infantry" },
    { id: "301|darien", value: "301|darien", label: "Darien" },
    { id: "102|space", value: "102|space", label: "Space area of system 102" },
  ],
}));

describe("SlotsMapField - chip wybranego miejsca", () => {
  afterEach(() => act(() => useAppStore.setState({ mapPicks: [], mapPick: null })));

  it("jedna sztuka: tylko ×; dwie: − i ×; − zdejmuje jedną", () => {
    render(<Harness inputs={slots} />);
    act(() => pick()?.onPick("darien", "planet"));
    // n === 1: − robiłby to samo co × - nie ma go.
    expect(screen.queryByRole("button", { name: "One less on Darien" })).toBeNull();
    expect(screen.getByRole("button", { name: "Remove Darien" })).toBeInTheDocument();

    act(() => pick()?.onPick("darien", "planet"));
    expect(screen.getByRole("button", { name: "One less on Darien" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove Darien" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "One less on Darien" }));
    expect(screen.queryByRole("button", { name: "One less on Darien" })).toBeNull();
    expect(screen.getByText("1 / 3 placed")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remove Darien" }));
    expect(screen.queryByRole("button", { name: "Remove Darien" })).toBeNull();
    expect(screen.getByText("0 / 3 placed")).toBeInTheDocument();
  });
});

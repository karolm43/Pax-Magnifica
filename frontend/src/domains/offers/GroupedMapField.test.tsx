import { useState } from "react";
import { act, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { useAppStore, type MapPick } from "@/state/appStore";
import { useMapPick } from "@/domains/strategy/mapPick";
import { DecisionFields } from "./DecisionFields";

// Plansza: dom Yin (301, planeta Darien) i dwa systemy z samą przestrzenią.
vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({
    playerData: [],
    tiles: { "301": { planets: { darien: {} } }, "102": { planets: {} }, "103": { planets: {} } },
  }),
}));

function Harness({ inputs }: { inputs: ActionCardInput[] }) {
  const [values, setValues] = useState<Record<string, FormValue>>({});
  return (
    <>
      <DecisionFields
        inputs={inputs}
        values={values}
        disabled={false}
        onChange={(key, next) => setValues((prev) => ({ ...prev, [key]: next }))}
      />
      <pre data-testid="values">{JSON.stringify(values)}</pre>
    </>
  );
}

const values = () => JSON.parse(screen.getByTestId("values").textContent ?? "{}") as Record<string, unknown>;
const pick = (): MapPick | null => useAppStore.getState().mapPick;

/** Yin Spinner Ω: „any planet you control or any space area that contains your ships”. */
const spinner = (positions: string[]): ActionCardInput[] => [
  {
    key: "where",
    kind: "choice",
    label: "Place the infantry together on/in",
    hint: "",
    merge: false,
    options: [
      { id: "301|darien", value: "301|darien", label: "Darien" },
      ...positions.map((p) => ({ id: `${p}|space`, value: `${p}|space`, label: `Space area of system ${p}` })),
    ],
  },
  { key: "count", kind: "number", label: "Infantry to place", hint: "", min: 1, max: 2 },
];

describe("GroupedMapField - wybór na planecie ALBO w przestrzeni", () => {
  afterEach(() => act(() => useAppStore.setState({ mapPicks: [], mapPick: null })));

  it.each([[["301"]], [["102", "103", "301"]]])(
    "Yin Spinner (%j): planeta = klik w planetę, przestrzeń = klik w heks - jednym kliknięciem",
    (positions) => {
      render(<Harness inputs={spinner(positions)} />);
      // Nic nie wisi jako kafelek obok mapy - oba rodzaje celów świecą NA MAPIE.
      expect(screen.queryByRole("button", { name: /Space area/ })).toBeNull();
      expect(pick()?.planets).toEqual(["darien"]);
      expect(pick()?.systems).toEqual(positions);
      act(() => pick()?.onPick("301", "system"));
      expect(values()).toEqual({ where: "301|space" });
      act(() => pick()?.onPick("darien", "planet"));
      expect(values()).toEqual({ where: "301|darien" });
      expect(screen.getByRole("button", { name: "Darien" })).toBeInTheDocument();
    },
  );
});

/** Okno z własnym wyborem systemu (jak karta strategii obok otwartej decyzji). */
function Window({ targets, onPick }: { targets: string[]; onPick: (t: string) => void }) {
  const handle = useMapPick("system", targets, onPick);
  return (
    <button type="button" onClick={handle.claim}>
      {handle.active ? "active" : "waiting"} {targets.join(",")}
    </button>
  );
}

describe("rejestr wyborów na mapie", () => {
  afterEach(() => act(() => useAppStore.setState({ mapPicks: [], mapPick: null })));

  it("dwa okna nie kasują sobie wyboru; zamknięcie jednego oddaje mapę drugiemu", () => {
    const a = vi.fn();
    const b = vi.fn();
    const first = render(<Window targets={["101"]} onPick={a} />);
    const second = render(<Window targets={["202"]} onPick={b} />);
    // Nowsze okno trzyma mapę, starsze czeka (nie znika).
    expect(pick()?.systems).toEqual(["202"]);
    expect(screen.getByRole("button", { name: "waiting 101" })).toBeInTheDocument();
    // Klik w starsze okno przejmuje mapę.
    act(() => screen.getByRole("button", { name: "waiting 101" }).click());
    expect(pick()?.systems).toEqual(["101"]);
    act(() => pick()?.onPick("101", "system"));
    expect(a).toHaveBeenCalledWith("101");
    // Zamknięcie aktywnego okna oddaje mapę drugiemu (wcześniej mapa zostawała pusta).
    first.unmount();
    expect(pick()?.systems).toEqual(["202"]);
    second.unmount();
    expect(pick()).toBeNull();
  });
});

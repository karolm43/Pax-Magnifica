import { useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { useAppStore } from "@/state/appStore";
import { DecisionFields } from "./DecisionFields";

vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({ playerData: [], tiles: {} }),
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

const values = () =>
  JSON.parse(screen.getByTestId("values").textContent ?? "{}") as Record<string, string[]>;

/** ``offer_inputs.unit_moves``: 2 krążowniki w 102, cele 103 i 104 (jak Wing Transfer). */
const unit = (i: number, to: string) => ({
  id: `102|cruiser|${i}>${to}`,
  value: `102|cruiser|${i}>${to}`,
  label: `Cruiser → ${to}`,
  meta: {
    unit: "cruiser",
    faction: "argent",
    position: "102",
    move: { unit: `102|cruiser|${i}`, from: "102", to },
  },
});
const inputs: ActionCardInput[] = [
  {
    key: "moves",
    kind: "multi",
    label: "Move ships",
    hint: "Click a glowing system, choose units, then click the destination (or drag).",
    min: 0,
    max: 2,
    options: [unit(0, "103"), unit(0, "104"), unit(1, "103"), unit(1, "104")],
  },
];

const pick = () => useAppStore.getState().mapPick;
const reset = () =>
  act(() =>
    useAppStore.setState({
      effectMove: null,
      effectMoveDrag: null,
      multiSelect: null,
      mapPicks: [],
      mapPick: null,
    }),
  );

describe("UnitMovesField - ruch z efektu jak zwykły ruch", () => {
  afterEach(reset);

  it("klik w system -> wybór jednostek (+/Shift) -> klik w cel planuje ruch i rysuje linię", () => {
    render(<Harness inputs={inputs} />);
    // Żadnych slotów „Destination N” ani list systemów - świecą systemy na mapie.
    expect(screen.queryByText(/Destination/)).toBeNull();
    expect(pick()?.systems).toEqual(["102"]);
    expect(useAppStore.getState().effectMove?.dests).toEqual({ "102|cruiser": ["103", "104"] });

    act(() => pick()?.onPick("102", "system"));
    expect(pick()?.systems).toEqual(["102", "103", "104"]);
    // Cel bez wybranych jednostek - podpowiedź, nic się nie rusza.
    act(() => pick()?.onPick("103", "system"));
    expect(values().moves).toBeUndefined();
    expect(screen.getByRole("status")).toHaveTextContent(/Choose the units first/);

    // Shift+klik = wszystkie; wybór to zaznaczenie Ctrl na mapie (licznik na stosie).
    fireEvent.click(screen.getByRole("button", { name: /0 of 2 selected/ }), { shiftKey: true });
    expect(useAppStore.getState().multiSelect?.items["ca|space"]?.count).toBe(2);
    act(() => pick()?.onPick("103", "system"));
    expect(values().moves).toEqual(["102|cruiser|0>103", "102|cruiser|1>103"]);
    expect(useAppStore.getState().multiSelect).toBeNull();
    expect(useAppStore.getState().effectMove?.lines).toEqual([
      { from: "102", to: "103", count: 2 },
    ]);
  });

  it("ponowny klik w wybrany system odznacza go", () => {
    render(<Harness inputs={inputs} />);
    act(() => pick()?.onPick("102", "system"));
    expect(screen.getByRole("region", { name: /Units in/ })).toBeInTheDocument();
    act(() => pick()?.onPick("102", "system"));
    expect(screen.queryByRole("region", { name: /Units in/ })).toBeNull();
    expect(pick()?.systems).toEqual(["102"]);
  });

  it("Ctrl+klik na mapie wybiera system i jednostki; przeciągnięcie stosu/grupy też planuje ruch", () => {
    render(<Harness inputs={inputs} />);
    act(() =>
      useAppStore.getState().ctrlPickUnit({
        fromPosition: "102",
        faction: "argent",
        asyncId: "ca",
        fromZone: "space",
        max: 2,
      }),
    );
    expect(screen.getByRole("button", { name: /1 of 2 selected/ })).toBeInTheDocument();

    act(() => useAppStore.getState().effectMove?.onDrop([{ key: "102|cruiser", count: 2 }], "103"));
    expect(values().moves).toEqual(["102|cruiser|0>103", "102|cruiser|1>103"]);
    // Ten sam stos na inny cel: jednostki przechodzą, nie dublują się.
    act(() => useAppStore.getState().effectMove?.onDrop([{ key: "102|cruiser", count: 1 }], "104"));
    expect(values().moves).toEqual(["102|cruiser|1>103", "102|cruiser|0>104"]);

    fireEvent.contextMenu(screen.getAllByRole("button", { name: /1 of 1 selected/ })[0]);
    expect(values().moves).toHaveLength(1);
  });

  it("w trakcie przeciągania świecą cele przeciąganego stosu", () => {
    render(<Harness inputs={inputs} />);
    act(() => useAppStore.setState({ effectMoveDrag: "102|cruiser" }));
    expect(useAppStore.getState().moveRangeSources).toEqual(new Set(["103", "104"]));
  });
});

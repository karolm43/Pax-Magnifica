import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { DecisionFields } from "./DecisionFields";

/** Formularz z prawdziwym stanem, jak w oknach decyzji. */
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

describe("DecisionFields", () => {
  it("wybór jednej opcji to kafelki, nie lista rozwijana", () => {
    render(
      <Harness
        inputs={[
          {
            key: "ship",
            kind: "choice",
            label: "Ship",
            hint: "",
            merge: false,
            options: [
              { id: "p1|cruiser", value: "p1|cruiser", label: "Cruiser I - Barony of Letnev" },
              { id: "p2|destroyer", value: "p2|destroyer", label: "Destroyer I - Federation of Sol" },
            ],
          },
        ]}
      />,
    );
    expect(screen.queryByRole("combobox")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Destroyer I/ }));
    expect(values()).toEqual({ ship: "p2|destroyer" });
    expect(screen.getByRole("button", { name: /Destroyer I/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("płatność: kafelki planet + licznik TG w jednym widżecie z paskiem", () => {
    render(
      <Harness
        inputs={[
          {
            key: "planets",
            kind: "multi",
            label: "Planets to exhaust",
            hint: "",
            min: 0,
            max: 2,
            options: [
              { id: "a", value: "a", label: "Arc Prime (4)", meta: { planet: "a", value: 4, valueKind: "resources" } },
              { id: "b", value: "b", label: "Wren Terra (2)", meta: { planet: "b", value: 2, valueKind: "resources" } },
            ],
            payment: { cost: 2, valueKind: "resources", tradeGoods: "trade_goods" },
          },
          { key: "trade_goods", kind: "number", label: "Trade goods to spend", hint: "", min: 0, max: 2 },
        ]}
      />,
    );
    expect(screen.getByText("Pay 2 resources")).toBeInTheDocument();
    // Osobnego pola liczbowego TG nie ma - jest stepper w widżecie płatności.
    expect(screen.getAllByRole("group", { name: "Trade goods" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Trade goods: more" }));
    fireEvent.click(screen.getByRole("button", { name: "Trade goods: more" }));
    expect(values()).toEqual({ trade_goods: 2 });
    expect(screen.getByText(/Paid/)).toHaveTextContent("Paid 2 / 2");
    fireEvent.click(screen.getByRole("button", { name: /Wren Terra/ }));
    expect(values()).toEqual({ trade_goods: 2, planets: ["b"] });
    expect(screen.getByText(/Paid/)).toHaveTextContent("Paid 4 / 2 · overpaying");
  });
});

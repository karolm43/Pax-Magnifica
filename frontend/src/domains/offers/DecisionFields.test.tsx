import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ActionCardInput, FormValue } from "@/api/useActionCard";
import { act } from "react";
import { vi } from "vitest";
import { useAppStore } from "@/state/appStore";
import { DecisionFields } from "./DecisionFields";

vi.mock("@/domains/game-shell/components/TurnControls/useDeskPlayer", () => ({
  useDeskPlayer: () => ({ discordId: "p1", faction: "sol", color: "blue", techs: ["amd"] }),
}));

/** Klik w świecący cel NA MAPIE (to, co robi warstwa mapy z ``appStore.mapPick``). */
function clickOnMap(target: string) {
  const pick = useAppStore.getState().mapPick;
  const kind = pick?.planets.includes(target) ? "planet" : "system";
  expect([...(pick?.systems ?? []), ...(pick?.planets ?? [])]).toContain(target);
  act(() => pick?.onPick(target, kind));
}

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

  it("technologia: wybór w drzewie technologii, nie lista", () => {
    render(
      <Harness
        inputs={[
          {
            key: "tech",
            kind: "choice",
            label: "Technology",
            hint: "",
            merge: false,
            options: [
              { id: "amd", value: "amd", label: "Antimass Deflectors" },
              { id: "gd", value: "gd", label: "Gravity Drive" },
            ],
          },
        ]}
      />,
    );
    // W formularzu nie ma listy technologii - tylko wejście do drzewa.
    expect(screen.queryByRole("button", { name: /Gravity Drive/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Choose in the technology tree" }));
    expect(screen.getAllByText("Gravity Drive").length).toBeGreaterThan(0);
  });

  it("cel: kafelek z punktami i warunkiem celu", () => {
    render(
      <Harness
        inputs={[
          {
            key: "objectives",
            kind: "multi",
            label: "Return to the deck",
            hint: "",
            min: 1,
            max: 1,
            options: [
              { id: "diversify", value: "diversify", label: "Diversify Research" },
              { id: "x", value: "x", label: "Something else" },
            ],
          },
        ]}
      />,
    );
    expect(screen.getByText("Own 2 technologies in each of 2 colors.")).toBeInTheDocument();
    expect(screen.getByText(/1 VP/)).toBeInTheDocument();
  });

  it("karta strategii z odnośnikiem: na kafelku sama nazwa, pełna karta po kliknięciu ⓘ", () => {
    render(
      <Harness
        inputs={[
          {
            key: "initiative",
            kind: "choice",
            label: "Readied or unchosen strategy card",
            hint: "",
            merge: false,
            options: [
              {
                id: "1",
                value: 1,
                label: "Leadership - initiative 1",
                meta: { ref: { kind: "strategy", id: "1" } },
              },
              {
                id: "8",
                value: 8,
                label: "Imperial - initiative 8",
                meta: { ref: { kind: "strategy", id: "8" } },
              },
            ],
          },
        ]}
      />,
    );
    // Decyzja użytkownika: bez drobnego tekstu primary/secondary na kafelku - jest pod ⓘ.
    expect(screen.queryAllByText(/^Secondary:/)).toHaveLength(0);
    expect(screen.getByText("initiative 1")).toBeInTheDocument();
    // Klik w ⓘ nie wybiera opcji, tylko otwiera pełną kartę.
    fireEvent.click(screen.getByRole("button", { name: "About Leadership" }));
    expect(values()).toEqual({});
    expect(screen.getByRole("button", { name: "About Leadership" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: /^Imperial/ }));
    expect(values()).toEqual({ initiative: "8" });
  });

  it("Xxekir Grom: planeta na mapie, potem licznik PDS i mechów - nie lista", () => {
    const unit = (u: string, planet: string, n: number) => ({
      id: `${u}|${planet}|${n}`,
      value: `${u}|${planet}|${n}`,
      label: `${u === "pds" ? "PDS I" : "Mech"} on ${planet}`,
      meta: { unit: u, player: "p1", faction: "xxcha", color: "green", planet },
    });
    render(
      <Harness
        inputs={[
          {
            key: "units",
            kind: "multi",
            label: "PDS and mechs to place (up to 4)",
            hint: "",
            min: 1,
            max: 4,
            options: [unit("pds", "jord", 0), unit("mech", "jord", 0), unit("mech", "jord", 1), unit("mech", "mr", 0)],
          },
        ]}
      />,
    );
    // Bez wybranej planety nie ma listy jednostek ani listy planet - tylko mapa.
    expect(screen.queryByRole("group", { name: /^Mech/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Jord/ })).toBeNull();
    clickOnMap("jord");
    fireEvent.click(screen.getByRole("button", { name: "Mech on jord: more" }));
    fireEvent.click(screen.getByRole("button", { name: "Mech on jord: more" }));
    expect(values()).toEqual({ units: ["mech|jord|0", "mech|jord|1"] });
    // Planeta z jedną możliwością: klik w nią od razu wybiera.
    clickOnMap("mr");
    expect(values()).toEqual({ units: ["mech|jord|0", "mech|jord|1", "mech|mr|0"] });
  });

  it("Bioplasmosis: źródło i cel na mapie = +1 (bez listy planet)", () => {
    const route = (from: string, to: string) => ({
      key: `bio:${from}:${to}`,
      kind: "number" as const,
      label: `${from} -> ${to}`,
      hint: "",
      min: 0,
      max: 2,
      meta: { from, to, unit: "infantry" },
    });
    render(<Harness inputs={[route("jord", "mr"), route("mr", "jord")]} />);
    expect(screen.queryByRole("group", { name: /→/ })).toBeNull();
    clickOnMap("jord");
    clickOnMap("mr");
    clickOnMap("mr");
    expect(values()).toEqual({ "bio:jord:mr": 2 });
    // Na Jord nie zostało już piechoty - kolejny klik nic nie dokłada.
    clickOnMap("mr");
    expect(values()).toEqual({ "bio:jord:mr": 2 });
  });
});


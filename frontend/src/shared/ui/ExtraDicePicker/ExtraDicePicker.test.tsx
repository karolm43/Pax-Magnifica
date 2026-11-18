import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  defaultPicks,
  extraByGroup,
  ExtraDicePicker,
  type ExtraDicePicks,
} from "./ExtraDicePicker";

const sources = [
  { key: "technologies:ps", name: "Plasma Scoring", dice: 1 },
  { key: "leaders:argentcommander", name: "Trrakan Aun Zulok", dice: 1 },
];
const groups = [
  { key: "pds", label: "PDS", hitsOn: 6 },
  { key: "flagship", label: "Quetzecoatl", hitsOn: 5 },
];

describe("ExtraDicePicker (każde źródło osobno, RULES.md 62.11)", () => {
  it("Auto = najcelniejsza grupa, źródła niezależnie", () => {
    expect(extraByGroup(sources, groups, defaultPicks(sources))).toEqual({ flagship: 2 });
    expect(
      extraByGroup(sources, groups, { "technologies:ps": "pds", "leaders:argentcommander": "none" }),
    ).toEqual({ pds: 1 });
  });

  it("gracz przypisuje każde źródło osobno", () => {
    let seen: ExtraDicePicks = {};
    function Harness() {
      const [value, setValue] = useState<ExtraDicePicks>(defaultPicks(sources));
      seen = value;
      return <ExtraDicePicker sources={sources} groups={groups} value={value} onChange={setValue} />;
    }
    render(<Harness />);
    const plasma = screen.getByRole("radiogroup", { name: /Plasma Scoring/ });
    fireEvent.click(plasma.querySelectorAll("[role=radio]")[1]); // PDS
    expect(seen).toEqual({ "technologies:ps": "pds", "leaders:argentcommander": "auto" });
  });
});

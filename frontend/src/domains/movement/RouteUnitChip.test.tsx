import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { RouteUnitChip } from "./RouteUnitChip";

function chip(picked: number, max: number, onChange = vi.fn()) {
  render(
    <RouteUnitChip
      asyncId="ca"
      colorAlias="red"
      faction="sol"
      name="Carrier"
      picked={picked}
      max={max}
      variant="row"
      onChange={onChange}
    />,
  );
  return { button: screen.getByRole("button", { name: /Carrier/ }), onChange };
}

describe("RouteUnitChip", () => {
  it("klik dodaje 1, dopóki nie ma kompletu", () => {
    const { button, onChange } = chip(1, 2);
    fireEvent.click(button);
    expect(onChange).toHaveBeenCalledWith(1);
  });

  it("klik na komplecie (2/2) przekręca licznik do 0", () => {
    const { button, onChange } = chip(2, 2);
    fireEvent.click(button);
    expect(onChange).toHaveBeenCalledWith(-2);
  });

  it("prawy przycisk nadal odejmuje 1", () => {
    const { button, onChange } = chip(2, 2);
    fireEvent.contextMenu(button);
    expect(onChange).toHaveBeenCalledWith(-1);
  });
});

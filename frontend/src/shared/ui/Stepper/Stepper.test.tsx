import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AutoButton } from "@/shared/ui/AutoButton/AutoButton";
import { CommandPools } from "@/shared/ui/CommandPools/CommandPools";
import { Stepper } from "./Stepper";

describe("Stepper", () => {
  it("−/+ w granicach min..max i „max N”", () => {
    const onChange = vi.fn();
    render(<Stepper label="Gold" value={1} min={0} max={3} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "More Gold" }));
    expect(onChange).toHaveBeenLastCalledWith(2);
    fireEvent.click(screen.getByRole("button", { name: "Less Gold" }));
    expect(onChange).toHaveBeenLastCalledWith(0);
    fireEvent.click(screen.getByRole("button", { name: "max 3" }));
    expect(onChange).toHaveBeenLastCalledWith(3);
  });

  it("blokuje przyciski na granicach", () => {
    render(<Stepper bare label="Gold" value={3} max={3} onChange={() => undefined} />);
    expect(screen.getByRole("button", { name: "More Gold" })).toBeDisabled();
  });
});

describe("AutoButton / CommandPools", () => {
  it("AutoButton woła akcję", () => {
    const onClick = vi.fn();
    render(<AutoButton onClick={onClick} />);
    fireEvent.click(screen.getByRole("button", { name: "Auto" }));
    expect(onClick).toHaveBeenCalled();
  });

  it("CommandPools: „+” tylko dopóki są żetony do rozłożenia, bez Auto", () => {
    const onChange = vi.fn();
    render(<CommandPools alloc={{ t: 1, f: 0, s: 0 }} total={1} onChange={onChange} />);
    expect(screen.getByRole("button", { name: "More Fleet tokens" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Less Tactic tokens" }));
    expect(onChange).toHaveBeenCalledWith({ t: 0, f: 0, s: 0 });
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });
});

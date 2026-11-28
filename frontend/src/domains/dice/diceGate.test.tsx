import { act, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { DICE_GRACE_MS, useAfterDice, useDiceGate } from "./diceGate";

function Probe({ k }: { k: string }) {
  const open = useAfterDice(k);
  return <span data-testid="probe">{open ? "open" : "held"}</span>;
}

const probe = () => screen.getByTestId("probe").textContent;

describe("diceGate - nic nie wyprzedza kości", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useDiceGate.setState({ until: 0 });
  });
  afterEach(() => vi.useRealTimers());

  it("nowa treść czeka na koniec rzutu (i krótką chwilę na dane rzutu)", () => {
    const { rerender } = render(<Probe k="" />);
    expect(probe()).toBe("open"); // nic do pokazania
    rerender(<Probe k="offer-1" />);
    expect(probe()).toBe("held");
    act(() => useDiceGate.getState().hold(2000)); // dane rzutu przyszły chwilę później
    act(() => {
      vi.advanceTimersByTime(DICE_GRACE_MS);
    });
    expect(probe()).toBe("held");
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(probe()).toBe("open");
  });

  it("bez rzutu treść pojawia się po krótkiej chwili; widoczna nie miga przy kolejnym rzucie", () => {
    const { rerender } = render(<Probe k="" />);
    rerender(<Probe k="offer-1" />);
    act(() => {
      vi.advanceTimersByTime(DICE_GRACE_MS + 10);
    });
    expect(probe()).toBe("open");
    act(() => useDiceGate.getState().hold(3000));
    expect(probe()).toBe("open");
  });
});

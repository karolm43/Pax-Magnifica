import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionFrame } from "./DecisionFrame";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const frameCss = readFileSync(resolve(__dirname, "DecisionFrame.module.css"), "utf-8");

describe("DecisionFrame", () => {
  it("Enter używa, Esc pomija; pole formularza przejmuje klawisze", () => {
    const onUse = vi.fn();
    const onSkip = vi.fn();
    render(
      <DecisionFrame ariaLabel="Decision: X" title="X" onUse={onUse} onSkip={onSkip}>
        <input aria-label="pole" />
      </DecisionFrame>,
    );
    fireEvent.keyDown(window, { key: "Enter" });
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onUse).toHaveBeenCalledTimes(1);
    expect(onSkip).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(screen.getByLabelText("pole"), { key: "Enter" });
    expect(onUse).toHaveBeenCalledTimes(1);
  });

  it("nieaktywna akcja główna nie reaguje na Enter", () => {
    const onUse = vi.fn();
    render(<DecisionFrame ariaLabel="Decision: X" title="X" onUse={onUse} canUse={false} />);
    fireEvent.keyDown(window, { key: "Enter" });
    expect(onUse).not.toHaveBeenCalled();
  });

  it("Required, kolejka i brak Skip przy decyzji wymaganej", () => {
    render(<DecisionFrame ariaLabel="Decision: X" title="X" required queued={2} onUse={() => {}} />);
    expect(screen.getByText("Required")).toBeTruthy();
    expect(screen.getByText("+2 more")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Skip/ })).toBeNull();
  });

  it("w oknie (embedded) Esc obsługuje okno, nie rama", () => {
    const onSkip = vi.fn();
    render(<DecisionFrame embedded ariaLabel="Decision: X" title="X" onSkip={onSkip} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onSkip).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it("stopka: Never ask, Skip, Secondary, Use w tej kolejności; zawija się zamiast wychodzić poza ramę", () => {
    render(
      <DecisionFrame
        ariaLabel="Decision: X"
        title="X"
        onNeverAsk={() => {}}
        onSkip={() => {}}
        secondary={{ label: "Unlock", onClick: () => {} }}
        onUse={() => {}}
        useLabel="Play A Very Long Action Card Name Indeed"
      />,
    );
    const names = screen.getAllByRole("button").map((b) => b.textContent?.trim());
    expect(names).toEqual([
      "Never ask",
      "Skip Esc",
      "Unlock",
      "Play A Very Long Action Card Name Indeed Enter",
    ]);
    const actions = /\.actions\s*\{([^}]*)\}/.exec(frameCss)?.[1] ?? "";
    expect(actions).toMatch(/flex-wrap:\s*wrap/);
    expect(actions).toMatch(/justify-content:\s*flex-end/);
  });

  it("bez skrótów (karta obok bieżącej decyzji): Enter/Esc nic nie robią, brak podpowiedzi klawiszy", () => {
    const onUse = vi.fn();
    const onSkip = vi.fn();
    render(
      <DecisionFrame ariaLabel="Decision: X" title="X" shortcuts={false} onUse={onUse} onSkip={onSkip} skipLabel="Not now" />,
    );
    fireEvent.keyDown(window, { key: "Enter" });
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onUse).not.toHaveBeenCalled();
    expect(onSkip).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Not now" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Use" })).toBeTruthy();
  });

  it("bez akcji nie ma pustej stopki; ton, ikona i podtytuł trafiają do ramy", () => {
    render(
      <DecisionFrame
        ariaLabel="Window closed: X"
        title="X"
        tone="closed"
        icon={<i data-testid="icon" />}
        subtitle="At the start of combat"
        text="The game moved on."
      />,
    );
    const frame = screen.getByRole("group", { name: "Window closed: X" });
    expect(frame.getAttribute("data-tone")).toBe("closed");
    expect(frame.querySelector("footer")).toBeNull();
    expect(screen.getByTestId("icon")).toBeTruthy();
    expect(screen.getByText("At the start of combat")).toBeTruthy();
  });
});

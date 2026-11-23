import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionFrame } from "./DecisionFrame";

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
});

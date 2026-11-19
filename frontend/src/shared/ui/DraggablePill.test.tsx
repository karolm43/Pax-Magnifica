import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { DraggablePill } from "./DraggablePill";

describe("DraggablePill", () => {
  beforeAll(() => {
    // jsdom nie ma PointerEvent - bez niego zdarzenie gubi współrzędne kursora.
    window.PointerEvent ??= MouseEvent as unknown as typeof PointerEvent;
  });
  beforeEach(() => localStorage.clear());

  it("klik przywraca okno, przeciągnięcie przesuwa pigułkę bez przywracania", () => {
    const restore = vi.fn();
    render(
      <DraggablePill storageKey="t.pill" className="pill" title="Show decisions" onRestore={restore}>
        Decisions
      </DraggablePill>,
    );
    const pill = screen.getByRole("button", { name: "Decisions" });
    fireEvent.pointerDown(pill, { button: 0, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(window, { clientX: 200, clientY: 150 });
    fireEvent.pointerUp(window);
    fireEvent.click(pill, { clientX: 200, clientY: 150 });
    expect(restore).not.toHaveBeenCalled();
    expect(pill.style.position).toBe("fixed");
    expect(localStorage.getItem("t.pill")).not.toBeNull();

    fireEvent.pointerDown(pill, { button: 0, clientX: 200, clientY: 150 });
    fireEvent.pointerUp(window);
    fireEvent.click(pill, { clientX: 201, clientY: 150 });
    expect(restore).toHaveBeenCalledTimes(1);
  });
});

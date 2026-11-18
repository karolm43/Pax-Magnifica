import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "./overlays";

/**
 * Okno pływające (``floating``) współistnieje z planszą: klik w coś poza oknem (np. Ctrl+klik
 * jednostki na mapie przy ruchu bohaterem Argent) zabiera fokus, ale nie zamyka okna.
 */
describe("Modal floating", () => {
  it("nie zamyka się, gdy fokus ucieka do elementu poza oknem", async () => {
    const onClose = vi.fn();
    render(
      <>
        <button type="button">Unit on the map</button>
        <Modal opened floating onClose={onClose} title="Hero">
          <button type="button">Inside</button>
        </Modal>
      </>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Inside" }));
    await userEvent.click(screen.getByRole("button", { name: "Unit on the map" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Inside" })).toBeInTheDocument();
  });

  it("zwykłe okno nadal zamyka się przyciskiem zamknięcia", async () => {
    const onClose = vi.fn();
    render(
      <Modal opened onClose={onClose} title="Plain">
        <span>Body</span>
      </Modal>,
    );
    const buttons = await screen.findAllByRole("button");
    await userEvent.click(buttons[buttons.length - 1]);
    expect(onClose).toHaveBeenCalled();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusInfo } from "./StatusInfo";

describe("StatusInfo", () => {
  it("klik w status otwiera opis, bez podpowiedzi po najechaniu", async () => {
    render(
      <StatusInfo status="initiativeZero">
        <span>0</span>
      </StatusInfo>,
    );
    const target = screen.getByRole("button", { name: /Naalu "0" token - what is this/ });
    expect(target).not.toHaveAttribute("title");
    fireEvent.click(target);
    expect(await screen.findByText(/initiative is 0/)).toBeInTheDocument();
  });
});

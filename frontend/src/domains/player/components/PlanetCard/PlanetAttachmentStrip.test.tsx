import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PlanetAttachmentStrip } from "./PlanetAttachmentStrip";

describe("PlanetAttachmentStrip", () => {
  it("pokazuje żeton attachmentu z nazwą i skipem w opisie", () => {
    render(<PlanetAttachmentStrip attachments={["biotic"]} />);
    const strip = screen.getByRole("img", { name: /Attachments: Biotic Research Facility/ });
    expect(strip.getAttribute("title")).toContain("biotic skip");
    expect(strip.querySelectorAll("img")).toHaveLength(1);
  });

  it("bez attachmentów nic nie renderuje", () => {
    const { container } = render(<PlanetAttachmentStrip attachments={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

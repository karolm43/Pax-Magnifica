import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { topicBody } from "./topicBody";

describe("topicBody", () => {
  it("drops the duplicate title and the source blockquote", () => {
    const md = "# Movement\n\n> Źródło: [x](https://www.tirules2.com/R_movement) — © FFG.\n> Zrzut z repo tirules.\n\n## Moving\n\n- note";
    expect(topicBody(md)).toBe("## Moving\n\n- note");
  });

  it("keeps blockquotes that are rule content", () => {
    expect(topicBody("# T\n\n> A quoted rule\n\ntext")).toBe("> A quoted rule\n\ntext");
  });

  it("strips the header of a real dump file (CRLF-safe)", () => {
    const md = readFileSync(resolve(__dirname, "../../../../docs/rules_tirules/F_nekro.md"), "utf-8");
    const body = topicBody(md);
    expect(body).not.toContain("Źródło");
    expect(body.startsWith("## ")).toBe(true);
  });
});

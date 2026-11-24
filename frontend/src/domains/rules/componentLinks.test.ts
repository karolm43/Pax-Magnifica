import { readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { findComponentsByName, resolveComponentLink } from "./componentLinks";

const WIKI = "https://twilight-imperium.fandom.com/wiki/";
const DUMP_DIR = resolve(__dirname, "../../../../docs/rules_tirules");

/** Every `[label](wiki-url)` link in the rules dump. */
function wikiLinksInDump(): { label: string; href: string; file: string }[] {
  const links: { label: string; href: string; file: string }[] = [];
  for (const file of readdirSync(DUMP_DIR).filter((f) => f.endsWith(".md"))) {
    const text = readFileSync(join(DUMP_DIR, file), "utf-8");
    for (const m of text.matchAll(/\[([^\]]*)\]\((https:\/\/twilight-imperium\.fandom\.com\/wiki\/[^)]*)\)/g)) {
      links.push({ label: m[1], href: m[2], file });
    }
  }
  return links;
}

describe("resolveComponentLink", () => {
  it("resolves a faction ability from the URL text fragment", () => {
    expect(resolveComponentLink(`${WIKI}The_Mentak_Coalition#Faction_Abilities:~:text=Pillage`, "x")).toEqual([
      { kind: "ability", id: "pillage", name: "Pillage" },
    ]);
  });

  it("resolves a name prefix to every component it starts (Valefar Assimilator X and Y)", () => {
    const refs = resolveComponentLink(
      `${WIKI}The_Nekro_Virus#Faction_Technologies:~:text=Valefar%20Assimilator`,
      "Valefar Assimilator",
    );
    expect(refs.map((r) => r.kind)).toEqual(["tech", "tech"]);
    expect(refs.map((r) => r.name).sort()).toEqual(["Valefar Assimilator X", "Valefar Assimilator Y"]);
  });

  it("resolves hero ability names, units and promissory notes regardless of case", () => {
    expect(findComponentsByName("Benediction")[0]?.kind).toBe("leader");
    expect(findComponentsByName("Hil Colish")[0]?.kind).toBe("unit");
    expect(findComponentsByName("Creuss Iff")[0]?.kind).toBe("promissory");
  });

  it("narrows an ambiguous name to the faction of the wiki page", () => {
    const refs = resolveComponentLink(`${WIKI}The_Mentak_Coalition#Leaders:~:text=Suffi%20An`, "Suffi An");
    expect(refs).toHaveLength(1);
    expect(refs[0].kind).toBe("leader");
  });

  it("leaves non-wiki links and unknown names unresolved", () => {
    expect(resolveComponentLink("https://www.tirules2.com/R_movement", "Movement")).toEqual([]);
    expect(resolveComponentLink(`${WIKI}Thunder's_Edge`, "Thunder's Edge")).toEqual([]);
  });

  it("drops a leading 'The' and resolves planets (The Sorrow, Custodia Vigilia)", () => {
    expect(resolveComponentLink(`${WIKI}The_Crimson_Rebellion#Faction_Abilities:~:text=The%20Sorrow`, "The Sorrow")[0])
      .toMatchObject({ kind: "ability", id: "sorrow" });
    expect(findComponentsByName("Custodia Vigilia").map((r) => r.kind)).toContain("planet");
  });

  it("resolves every component link in the rules dump to an in-game card", () => {
    // Components the game data does not have yet: these links stay external (wiki).
    const notInGameData = new Set(["Agnlan Oln", "Trillossa Aun Mirik", "*Enervate*"]);
    const unresolved = wikiLinksInDump()
      .filter(({ href, label }) => href.includes(":~:text=") && !notInGameData.has(label))
      .filter(({ href, label }) => resolveComponentLink(href, label).length === 0)
      .map(({ file, label, href }) => `${file}: [${label}] ${href.slice(WIKI.length)}`);
    expect(unresolved).toEqual([]);
  });
});

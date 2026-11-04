/*
 * Testy Vitest frontendu (zadanie 11.6): sprawdzają, że po przejściu na
 * Resolver_Zasobów (zadania 11.2–11.3) grafiki pochodzą wyłącznie z Zasobów
 * Lokalnych.
 *
 * Zakres:
 *  - brak importu usuniętego `cdnImage` w `frontend/src` (R2.2);
 *  - `getFactionImage` (w tym dla dawnych ikon typu EMOJI/DISCORD) nie zwraca
 *    URL zewnętrznego, tylko ścieżkę lokalną (R2.4);
 *  - `unitSprites`/`TokenSprite` korzystają z `sheetUrl`, więc dają ścieżki
 *    lokalne;
 *  - zgodność `assetManifest.json` (artefakt frontendu) z jednym źródłem prawdy
 *    `audit/assets_manifest.json` (R3.1).
 */

import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve, sep } from "node:path";

import { getFactionImage } from "@/entities/lookup/factions";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import { sheetUrl, PLACEHOLDER_URL } from "./resolveAsset";
import frontendManifest from "./assetManifest.json";

const HERE = dirname(fileURLToPath(import.meta.url));
// `src/shared/assets` -> `frontend/src` -> `frontend` -> repo root.
const FRONTEND_SRC = resolve(HERE, "..", "..");
const REPO_ROOT = resolve(HERE, "..", "..", "..", "..");

/** Napis lokalny: `/static/...` albo placeholder, nigdy ze schematem URL. */
function assertLocal(result: string | undefined): void {
  expect(result).toBeDefined();
  const value = result as string;
  expect(value).not.toContain("://");
  expect(value.startsWith("/static/") || value === PLACEHOLDER_URL).toBe(true);
}

/** Rekurencyjnie zbiera pliki `.ts`/`.tsx` (z pominięciem plików testowych). */
function collectSourceFiles(root: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(root)) {
    const full = join(root, entry);
    if (statSync(full).isDirectory()) {
      out.push(...collectSourceFiles(full));
      continue;
    }
    const isSource = /\.(ts|tsx)$/.test(entry);
    const isTest = /\.test\.(ts|tsx)$/.test(entry);
    if (isSource && !isTest) out.push(full);
  }
  return out;
}

describe("Frontend — brak zależności od usuniętego cdnImage (R2.2)", () => {
  it("żaden plik źródłowy w frontend/src nie importuje cdnImage", () => {
    const offenders: string[] = [];
    const importRe = /\bimport\b[^;]*\bcdnImage\b/;
    for (const file of collectSourceFiles(FRONTEND_SRC)) {
      const text = readFileSync(file, "utf8");
      if (importRe.test(text)) {
        offenders.push(file.slice(REPO_ROOT.length + 1).split(sep).join("/"));
      }
    }
    expect(offenders).toEqual([]);
  });

  it("plik cdnImage.ts nie istnieje już w frontend/src", () => {
    const all = collectSourceFiles(FRONTEND_SRC).map((f) =>
      f.split(sep).join("/"),
    );
    expect(all.some((f) => /\/cdnImage\.ts$/.test(f))).toBe(false);
  });
});

describe("Frontend — getFactionImage zwraca ścieżkę lokalną (R2.4)", () => {
  it("zwykła frakcja -> /static/factions/<id>.png lub placeholder", () => {
    assertLocal(getFactionImage("sol"));
  });

  it("dawna ikona EMOJI nie przechodzi na URL zewnętrzny", () => {
    // Trzeci argument (typ) był kiedyś 'EMOJI'/'DISCORD' i sterował CDN.
    assertLocal(getFactionImage("sol", "😀", "EMOJI"));
    assertLocal(
      getFactionImage("sol", "https://cdn.discordapp.com/x.png", "DISCORD"),
    );
  });

  it("dowolna frakcja daje wynik lokalny", () => {
    for (const faction of ["arborec", "muaat", "nekro", "xxcha", "nieznana"]) {
      assertLocal(getFactionImage(faction));
    }
  });
});

describe("Frontend — sprite sheety są lokalne (R2.1)", () => {
  it("sheetUrl jednostek i żetonów jest lokalny", () => {
    assertLocal(sheetUrl("units", "blu"));
    assertLocal(sheetUrl("tokens", "attachments"));
  });

  it("getUnitSprite dla znanej jednostki ma lokalny obraz sheetu", () => {
    const sprite = getUnitSprite("blu", "fs");
    expect(sprite).toBeDefined();
    // Dla kolorowej jednostki sheet istnieje -> `image` jest ustawiony i lokalny.
    assertLocal(sprite!.image);
  });

  it("getUnitSprite dla jednostki współdzielonej ma lokalny obraz sheetu", () => {
    const sprite = getUnitSprite("blu", "plenaryorbital");
    expect(sprite).toBeDefined();
    assertLocal(sprite!.image);
  });
});

describe("Frontend — manifest zgodny z audit/assets_manifest.json (R3.1)", () => {
  it("assetManifest.json listuje dokładnie ścieżki z audit/assets_manifest.json", () => {
    const auditRaw = readFileSync(
      join(REPO_ROOT, "audit", "assets_manifest.json"),
      "utf8",
    );
    const audit = JSON.parse(auditRaw) as { files: { path: string }[] };
    const auditPaths = new Set(audit.files.map((f) => f.path));
    const frontPaths = new Set<string>(frontendManifest.paths ?? []);

    // Dokładna równość zbiorów: żadnych ścieżek nadmiarowych ani brakujących.
    const missingInFront = [...auditPaths].filter((p) => !frontPaths.has(p));
    const extraInFront = [...frontPaths].filter((p) => !auditPaths.has(p));
    expect({ missingInFront, extraInFront }).toEqual({
      missingInFront: [],
      extraInFront: [],
    });
  });
});

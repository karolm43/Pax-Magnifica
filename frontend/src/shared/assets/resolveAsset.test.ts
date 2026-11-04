/*
 * Test właściwościowy Resolvera_Zasobów (zadanie 11.5, Property 17).
 *
 * Niezmiennik: dla DOWOLNEJ logicznej ścieżki zasobu `assetUrl` zwraca wyłącznie
 * ścieżkę LOKALNĄ — zaczyna się od `/static/` albo jest równa `PLACEHOLDER_URL` —
 * i NIGDY nie zawiera `://` ani hosta zewnętrznego. To bezpośrednie odwzorowanie
 * wymagań 2.1 (grafiki tylko z backendu/`public`) i 2.6 (placeholder dla braków).
 *
 * Validates: Requirements 2.1, 2.6
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { assetUrl, sheetUrl, PLACEHOLDER_URL } from "./resolveAsset";

/** Sprawdza niezmiennik „wynik jest lokalny" dla pojedynczego wyniku. */
function assertLocal(result: string): void {
  // Nigdy schemat URL ani znacznik hosta zewnętrznego.
  expect(result).not.toContain("://");
  // Dokładnie jedna z dwóch dozwolonych postaci lokalnych.
  const isStatic = result.startsWith("/static/");
  const isPlaceholder = result === PLACEHOLDER_URL;
  expect(isStatic || isPlaceholder).toBe(true);
}

describe("Resolver_Zasobów — Property 17: wyłącznie ścieżki lokalne", () => {
  it("assetUrl dla dowolnej ścieżki zwraca /static/... albo placeholder, bez ://", () => {
    fc.assert(
      fc.property(fc.string(), (logicalPath) => {
        assertLocal(assetUrl(logicalPath));
      }),
      { numRuns: 100 },
    );
  });

  it("assetUrl dla ścieżek przypominających URL zewnętrzny nadal jest lokalny", () => {
    // Generator celowo wstrzykuje hosty/scheme'y, których wynik NIE może przepuścić.
    const hostile = fc.oneof(
      fc.constantFrom(
        "https://images.asyncti4.com/units/blu_cruiser.png",
        "http://emoji-cdn.mqrio.dev/x.png",
        "//cdn.statically.io/relic.png",
        "https://example.com/a.webp",
      ),
      fc.webUrl(),
      fc
        .tuple(
          fc.constantFrom("http", "https", "ftp"),
          fc.domain(),
          fc.string(),
        )
        .map(([scheme, host, path]) => `${scheme}://${host}/${path}`),
    );
    fc.assert(
      fc.property(hostile, (logicalPath) => {
        assertLocal(assetUrl(logicalPath));
      }),
      { numRuns: 100 },
    );
  });

  it("assetUrl dla ścieżki z wiodącymi slashami i rozszerzeniem jest lokalny", () => {
    const logical = fc
      .tuple(
        fc.array(fc.constantFrom("units", "factions", "tokens", "extra", "x")),
        fc.stringMatching(/^[a-z0-9_]{1,12}$/),
        fc.constantFrom(".png", ".jpg", ".jpeg", ".webp", ".svg", ""),
      )
      .map(([dirs, name, ext]) => "/" + [...dirs, name].join("/") + ext);
    fc.assert(
      fc.property(logical, (logicalPath) => {
        assertLocal(assetUrl(logicalPath));
      }),
      { numRuns: 100 },
    );
  });

  it("sheetUrl dla jednostek i żetonów zwraca wyłącznie ścieżki lokalne", () => {
    fc.assert(
      fc.property(
        fc.constantFrom("units" as const, "tokens" as const),
        fc.string(),
        (kind, name) => {
          assertLocal(sheetUrl(kind, name));
        },
      ),
      { numRuns: 100 },
    );
  });

  it("pusta ścieżka zwraca PLACEHOLDER_URL", () => {
    expect(assetUrl("")).toBe(PLACEHOLDER_URL);
    expect(assetUrl("///")).toBe(PLACEHOLDER_URL);
  });
});

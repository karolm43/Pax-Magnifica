/**
 * Frontendowy odpowiednik backendowego `map_link` z `src/core/rules_content.py`.
 *
 * Odwzorowuje URL hiperłącza z treści tematu na cel nawigacji (Link_Mapper),
 * spójnie z regułą rdzenia: URL postaci `https://www.tirules2.com/<slug>`
 * (z opcjonalnym `www.` i opcjonalnym trailing slash) → Internal_Link WTEDY
 * i TYLKO WTEDY, gdy wydobyty slug należy do zbioru znanych lokalnych slugów;
 * w każdym innym przypadku → External_Link zachowujący oryginalny URL.
 *
 * Reguła musi być identyczna jak na backendzie, aby nawigacja po treści
 * renderowanej klient-side zachowywała się tak samo jak serwerowe `map_link`.
 */

import type { LinkTarget } from "@/domains/rules/types";

/**
 * Wzorzec URL tirules2.com — analogiczny do backendowego `TIRULES_URL_RE`.
 * Grupa 1 to Topic_Slug (np. `R_movement`). Klasa znaków slug ograniczona do
 * `[A-Za-z0-9_]` — bez separatorów ścieżki, więc odwzorowanie nie wpuszcza prób
 * path-traversal. Obsługuje opcjonalne `www.` oraz opcjonalny trailing slash.
 */
export const TIRULES_URL_RE =
  /^https?:\/\/(?:www\.)?tirules2\.com\/([A-Za-z0-9_]+)\/?$/;

/**
 * Odwzorowuje URL na cel nawigacji (Internal_Link albo External_Link).
 *
 * @param href - oryginalny URL hiperłącza z treści tematu.
 * @param knownSlugs - zbiór znanych lokalnych slugów (sprawdzenie przez `has`);
 *   typowo zbudowany z pozycji indeksu (`useRulesIndex`).
 * @returns `{ kind: "internal", slug }` gdy URL pasuje do tirules2.com, a slug
 *   jest znany lokalnie; w przeciwnym razie `{ kind: "external", url: href }`
 *   z oryginalnym adresem bez zmian.
 */
export function mapLink(
  href: string,
  knownSlugs: Set<string> | ReadonlySet<string>,
): LinkTarget {
  const match = TIRULES_URL_RE.exec(href);
  if (match !== null) {
    const slug = match[1];
    if (knownSlugs.has(slug)) {
      return { kind: "internal", slug };
    }
  }
  return { kind: "external", url: href };
}

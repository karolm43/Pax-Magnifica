/*
 * Resolver_Zasobów — mapuje logiczne ścieżki grafik na LOKALNE adresy backendu
 * (`/static/...`), bez żadnego CDN. Zastępuje `cdnImage()` (patrz design.md,
 * sekcja „Frontend: Resolver_Zasobów", wymagania 2.1, 2.2, 2.6).
 *
 * Założenia (potwierdzone w design.md):
 * - Backend serwuje `assets/` pod `/static` (`app.mount("/static", ...)`), a w dev
 *   proxy Vite kieruje `/static` na backend :8000. Dlatego Resolver zwraca ścieżki
 *   WZGLĘDNE zaczynające się od `/static/` — działają w dev i prod bez hosta.
 * - Manifest (`assetManifest.json`) zawiera logiczne ścieżki WZGLĘDEM `assets/`
 *   (np. `units/blu_cruiser.png`). Jest generowany z `audit/assets_manifest.json`
 *   poleceniem `uv run python -m src.audit --write-manifest`.
 * - Sprite sheety (`units/sheets`, `tokens/sheets`) są WYŁĄCZNIE w `.webp`;
 *   stare `cdnImage()` zamieniało `.png/.jpg -> .webp`, ale Resolver NIE kopiuje
 *   tej konwersji — rozszerzenie rozstrzyga manifest (design.md).
 */

import manifest from "./assetManifest.json";

/** Prefiks, pod którym backend serwuje `assets/` (StaticFiles). */
const STATIC_PREFIX = "/static";

/** Lokalny placeholder pokazywany, gdy grafiki nie ma w Zasobach_Lokalnych (R2.6). */
export const PLACEHOLDER_URL = "/placeholder.svg";

/**
 * Zbiór logicznych ścieżek obecnych w manifeście (klucz: POSIX względem `assets/`,
 * bez wiodącego `/`, np. `units/blu_cruiser.png`). Budowany raz przy starcie.
 */
const MANIFEST_PATHS: ReadonlySet<string> = new Set(manifest.paths ?? []);

/** Alternatywne rozszerzenia próbowane, gdy dokładna ścieżka nie jest w manifeście. */
const ALT_SUFFIXES = [".png", ".jpg", ".jpeg", ".webp"] as const;

/** Usuwa wiodące `/`, normalizując logiczną ścieżkę do klucza manifestu. */
function toManifestKey(logicalPath: string): string {
  return logicalPath.replace(/^\/+/, "");
}

/** Buduje lokalny URL `/static/...` z logicznego klucza manifestu. */
function toStaticUrl(manifestKey: string): string {
  return `${STATIC_PREFIX}/${manifestKey}`;
}

/**
 * Zwraca kandydatów rozszerzeń dla ścieżki z rozszerzeniem graficznym:
 * najpierw oryginalne, potem pozostałe z `ALT_SUFFIXES`. Dla ścieżek bez
 * znanego rozszerzenia zwraca samą ścieżkę.
 */
function candidateKeys(manifestKey: string): string[] {
  const match = /\.[a-zA-Z0-9]+$/.exec(manifestKey);
  if (!match) return [manifestKey];
  const stem = manifestKey.slice(0, match.index);
  const original = match[0].toLowerCase();
  const alts = ALT_SUFFIXES.filter((suffix) => suffix !== original);
  return [manifestKey, ...alts.map((suffix) => stem + suffix)];
}

/**
 * Zamienia logiczną ścieżkę zasobu na LOKALNY URL `/static/...`.
 *
 * Zachowuje się jak dawne `cdnImage()` (sygnatura `string -> string`), ale:
 * - zwraca wyłącznie ścieżki lokalne (`/static/...` albo `PLACEHOLDER_URL`),
 * - nigdy nie zawiera `://`,
 * - gdy dokładna ścieżka nie jest w manifeście, próbuje alternatywnych rozszerzeń,
 * - gdy żaden wariant nie istnieje, zwraca `PLACEHOLDER_URL` (R2.6).
 *
 * @example assetUrl("/units/blu_cruiser.png") // -> "/static/units/blu_cruiser.png"
 */
export function assetUrl(logicalPath: string): string {
  const key = toManifestKey(logicalPath);
  if (key === "") return PLACEHOLDER_URL;

  // Pusty manifest (np. grafiki jeszcze niezsynchronizowane) — zwróć lokalną
  // ścieżkę bezpośrednio, nie placeholder, by nie psuć działającego dev-setupu.
  if (MANIFEST_PATHS.size === 0) return toStaticUrl(key);

  for (const candidate of candidateKeys(key)) {
    if (MANIFEST_PATHS.has(candidate)) return toStaticUrl(candidate);
  }
  return PLACEHOLDER_URL;
}

/**
 * Buduje lokalny URL do sprite sheetu jednostek lub żetonów. Sheety są wyłącznie
 * w `.webp` (design.md), więc rozszerzenie jest stałe.
 *
 * @example sheetUrl("units", "blu") // -> "/static/units/sheets/blu.webp"
 */
export function sheetUrl(kind: "units" | "tokens", name: string): string {
  return assetUrl(`/${kind}/sheets/${name}.webp`);
}

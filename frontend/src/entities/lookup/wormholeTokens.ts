import { tokens } from "@/entities/data/tokens";

/**
 * Creuss wormhole tokens (RULES.md 62.19) — the kinds of `faction_token` facts and map entities.
 * Names and wormhole types come from the token data (`assets/data/tokens`), never from memory.
 */
export const CREUSS_WORMHOLE_TOKENS = ["creussalpha", "creussbeta", "creussgamma"] as const;

const CREUSS = new Set<string>(CREUSS_WORMHOLE_TOKENS);

export function isCreussWormholeToken(id: string | null | undefined): boolean {
  return !!id && CREUSS.has(id);
}

/** Wormhole type the token creates (`ALPHA` / `BETA` / `GAMMA`), or null. */
export function wormholeTokenType(id: string | null | undefined): string | null {
  return tokens.find((t) => t.id === id)?.wormholes?.[0] ?? null;
}

/** "Alpha wormhole token" (type from the data; id as a fallback). */
export function wormholeTokenName(id: string | null | undefined): string {
  const type = wormholeTokenType(id);
  if (!type) return id ?? "wormhole token";
  return `${type.charAt(0)}${type.slice(1).toLowerCase()} wormhole token`;
}

/** Token image path under `/tokens/` (as in `factionComponents`), or null. */
export function wormholeTokenImage(id: string | null | undefined): string | null {
  const path = tokens.find((t) => t.id === id)?.imagePath;
  return path ? `/tokens/${path}` : null;
}

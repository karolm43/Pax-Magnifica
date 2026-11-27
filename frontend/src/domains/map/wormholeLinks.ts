import { create } from "zustand";
import type { Tile } from "@/entities/game/types";
import { getTileById } from "@/entities/lookup/systems";
import { getPrintedLinkPoints, linkKindsOfToken } from "@/entities/geometry/wormholePoints";
import { linkedPositions } from "./components/SystemDossier/featureRules";

/**
 * Podgląd „dokąd prowadzi” po najechaniu na wormhole albo portal The Fracture.
 *
 * Rodzaj połączenia: typ wormhole (``ALPHA``, ``BETA``…) albo ``INGRESS`` / ``EGRESS``.
 * Wormhole łączy systemy z tym samym typem; ingress prowadzi do każdego egress
 * (i odwrotnie) — jak opis w dossier systemu (``featureRules``).
 */
export type LinkKind = string;

export type WormholeHover = { position: string; kinds: LinkKind[] };

type WormholeHoverState = {
  hovered: WormholeHover | null;
  setHovered: (hovered: WormholeHover | null) => void;
  /** Gasi podgląd, o ile wciąż dotyczy systemu ``position`` (inny hover zostaje). */
  clearHovered: (position: string) => void;
};

export const useWormholeHoverStore = create<WormholeHoverState>((set) => ({
  hovered: null,
  setHovered: (hovered) => set({ hovered }),
  clearHovered: (position) =>
    set((state) => (state.hovered?.position === position ? { hovered: null } : state)),
}));

export { linkKindsOfToken };

function hasIngress(tile: Tile): boolean {
  return tile.tokens.includes("ingress");
}

function hasEgress(tile: Tile): boolean {
  return !!getTileById(tile.systemId)?.hasEgress || tile.tokens.includes("egress");
}

const isGate = (kind: LinkKind) => kind === "INGRESS" || kind === "EGRESS";

/**
 * Kinds to preview when ``hovered`` kinds are under the cursor: hovering any wormhole shows EVERY
 * wormhole of the system (printed + tokens); Fracture gates (ingress / egress) stay on their own.
 */
export function kindsToShow(tile: Tile, hovered: LinkKind[]): LinkKind[] {
  if (hovered.every(isGate)) return hovered;
  const present = [
    ...getPrintedLinkPoints(tile.systemId).flatMap((point) => point.kinds),
    ...tile.tokens.flatMap(linkKindsOfToken),
  ].filter((kind) => !isGate(kind));
  return [...new Set([...hovered, ...present])];
}

/** Pozycje systemów, do których prowadzi połączenie ``kind`` z systemu ``position``. */
export function linkTargets(
  kind: LinkKind,
  position: string,
  tiles: Tile[],
): string[] {
  if (kind === "INGRESS" || kind === "EGRESS") {
    const leadsTo = kind === "INGRESS" ? hasEgress : hasIngress;
    return tiles
      .filter((tile) => tile.position !== position && leadsTo(tile))
      .map((tile) => tile.position)
      .sort();
  }
  return linkedPositions(kind, position, tiles);
}

/**
 * Systems linked to ``position`` only for ``player`` (web-data ``wormholeLinks``, the engine's
 * ``adjacency.extra_for_player`` layer, RULES.md 61.7 - Quantum Entanglement: alpha <-> beta for
 * Creuss) - minus those every player reaches through the hovered wormhole anyway (``common``).
 */
export function playerLinkTargets(
  position: string,
  player: { wormholeLinks?: Record<string, string[]> } | undefined,
  common: Set<string>,
): string[] {
  return (player?.wormholeLinks?.[position] ?? []).filter((target) => !common.has(target));
}

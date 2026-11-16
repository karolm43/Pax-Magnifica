import { create } from "zustand";
import type { Tile } from "@/entities/game/types";
import { getTileById } from "@/entities/lookup/systems";
import { getTokenData } from "@/entities/lookup/tokens";
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

/** Rodzaje połączeń, które niesie żeton (pusta lista = żeton nic nie łączy). */
export function linkKindsOfToken(tokenId: string): LinkKind[] {
  if (tokenId === "ingress") return ["INGRESS"];
  if (tokenId === "egress") return ["EGRESS"];
  return (getTokenData(tokenId)?.wormholes ?? []).map((w) => w.toUpperCase());
}

function hasIngress(tile: Tile): boolean {
  return tile.tokens.includes("ingress");
}

function hasEgress(tile: Tile): boolean {
  return !!getTileById(tile.systemId)?.hasEgress || tile.tokens.includes("egress");
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

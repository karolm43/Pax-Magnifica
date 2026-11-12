import type { RelicReveal } from "@/entities/data/types";
import { assetUrl } from "@/shared/assets/resolveAsset";

/*
 * Czysta logika sceny odsłonięcia reliktu (RULES.md 59.8): nagłówki, grafiki fragmentów,
 * awers karty. Komponent (`RelicRevealScene`) tylko to renderuje i animuje.
 */

/** Rewers karty reliktu - dziś także awers (placeholder do czasu grafik kart). */
export const RELIC_BACK = "/player_area/cardback_relic.jpg";

/**
 * Grafika awersu reliktu. PLACEHOLDER: zwraca null, więc scena pokazuje rewers z nazwą i
 * tekstem karty. Gdy dojdą grafiki kart, wystarczy zwrócić tu ścieżkę (np.
 * `/relics/${relicId}.jpg` przez `assetUrl`) - reszta sceny się nie zmienia.
 */
export function relicFaceImage(relicId: string): string | null {
  void relicId;
  return null;
}

const FRAGMENT_SPRITES = ["crf", "hrf", "irf", "urf"] as const;
type FragmentSprite = (typeof FRAGMENT_SPRITES)[number];

const KIND_SPRITE: Record<string, FragmentSprite> = {
  cultural: "crf",
  hazardous: "hrf",
  industrial: "irf",
};

/** Sprite żetonu fragmentu po id karty (`crf3`, `urf1`…); nieznany = typ łączenia. */
export function fragmentSprite(cardId: string, kind?: string): string {
  const prefix = FRAGMENT_SPRITES.find((p) => cardId.startsWith(p));
  const type = prefix ?? KIND_SPRITE[kind ?? ""] ?? "urf";
  return assetUrl(`/player_area/pa_fragment_${type}.png`);
}

/** Trzy (lub tyle, ile purge'owano) fragmenty do animacji łączenia. */
export function revealFragments(reveal: RelicReveal): string[] {
  const ids = reveal.fragments?.length ? reveal.fragments : ["", "", ""];
  return ids.map((id) => fragmentSprite(id, reveal.kind));
}

/** Nagłówek sceny: kto i skąd zdobył relikt. */
export function revealHeadline(
  reveal: RelicReveal,
  who: string,
  names: { planet?: string; card?: string },
): { title: string; subtitle: string } {
  const empty = reveal.relicId === null;
  switch (reveal.source) {
    case "fragments": {
      const kind = reveal.kind ? `${reveal.kind} ` : "";
      return {
        title: empty ? `${who} purges relic fragments` : `${who} forges a relic`,
        subtitle: `${reveal.fragments?.length ?? 3} ${kind}relic fragments were purged`,
      };
    }
    case "fracture":
      return {
        title: empty ? `${who} breaches The Fracture` : `The Fracture yields a relic`,
        subtitle: `${who} claimed ${names.planet ?? reveal.planet ?? "a planet"} in The Fracture`,
      };
    case "explore":
      return {
        title: empty ? `${who} finds nothing` : `${who} uncovers a relic`,
        subtitle: names.card ? `Exploration: ${names.card}` : "Exploration",
      };
    default:
      return { title: `${who} gains a relic`, subtitle: "Drawn from the relic deck" };
  }
}

import { PlayerDataResponse } from "@/entities/data/types";
import { getPlanetData } from "@/entities/lookup/planets";
import { getAttachmentData } from "@/entities/lookup/attachments";

function isOceanPlanet(planetId: string): boolean {
  return planetId.startsWith("ocean");
}

export function filterPlanetsByOcean(
  planets: string[]
): { regularPlanets: string[]; oceanPlanets: string[] } {
  const regularPlanets = planets.filter((id) => !isOceanPlanet(id));
  const oceanPlanets = planets.filter(isOceanPlanet);
  return { regularPlanets, oceanPlanets };
}

export function computeAllExhaustedPlanets(
  data: PlayerDataResponse
): string[] {
  if (!data.playerData) return [];
  return data.playerData.flatMap((player) =>
    player.exhaustedPlanets.filter((planet) => planet)
  );
}

export type AttachmentModifiers = {
  resources: number;
  influence: number;
  techSpecialties: string[];
  planetTypes: string[];
};

/**
 * Summed resource/influence bonuses and granted skips/traits from a planet's attachments.
 *
 * Lustro `core/planet_stats.planet_stats` (RULES 46, Research Facility): attachment ze
 * specjalnością daje ją tylko planecie BEZ specjalności; jeśli planeta już ją ma (z danych
 * albo z wcześniejszego attachmentu), zasoby i wpływy rosną o 1 ZAMIAST tego.
 * `techSpecialties` zawiera wyłącznie specjalności DODANE przez attachmenty.
 */
export function getAttachmentModifiers(
  attachments: string[],
  baseSpecialties: readonly string[] = []
): AttachmentModifiers {
  const totals: AttachmentModifiers = {
    resources: 0,
    influence: 0,
    techSpecialties: [],
    planetTypes: [],
  };
  let hasSpecialty = baseSpecialties.length > 0;
  for (const attachmentId of attachments) {
    const data = getAttachmentData(attachmentId);
    if (!data) continue;
    totals.resources += data.resourcesModifier ?? 0;
    totals.influence += data.influenceModifier ?? 0;
    const granted = data.techSpeciality ?? [];
    if (granted.length > 0) {
      if (hasSpecialty) {
        totals.resources += 1;
        totals.influence += 1;
      } else {
        totals.techSpecialties.push(...granted);
        hasSpecialty = true;
      }
    }
    totals.planetTypes.push(...(data.planetTypes ?? []));
  }
  return totals;
}

export function getTechSpecialties(
  planetName: string,
  attachments: string[]
): string[] {
  const base = getPlanetData(planetName)?.techSpecialties ?? [];
  return [...base, ...getAttachmentModifiers(attachments, base).techSpecialties];
}

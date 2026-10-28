import { Group, Box } from "@/ds";
import { PlanetCard } from "../PlanetCard";
import { filterPlanetsByOcean } from "@/entities/game/planets";

type Props = {
  planets: string[];
  exhaustedPlanetAbilities?: string[];
  exhaustedPlanets?: string[];
  wrap?: "wrap" | "nowrap";
  /** Właściciel (``discordId``) — włącza menu kontekstowe na kartach planet. */
  playerId?: string;
};

export function PlayerCardPlanetsArea({
  planets,
  exhaustedPlanetAbilities = [],
  exhaustedPlanets = [],
  wrap = "wrap",
  playerId,
}: Props) {
  const { regularPlanets, oceanPlanets } = filterPlanetsByOcean(planets);

  return (
    <>
      <Group gap={4} wrap={wrap} align="flex-start">
        {regularPlanets.map((planetId, index) => (
          <PlanetCard
            key={index}
            planetId={planetId}
            legendaryAbilityExhausted={exhaustedPlanetAbilities.includes(planetId)}
            isExhausted={exhaustedPlanets.includes(planetId)}
            playerId={playerId}
          />
        ))}
      </Group>
      {oceanPlanets.length > 0 && (
        <>
          <Box style={{ marginLeft: "2px" }} />
          <Group gap={1} wrap={wrap} align="flex-start">
            {oceanPlanets.map((planetId, index) => (
              <PlanetCard
                key={`ocean-${index}`}
                planetId={planetId}
                legendaryAbilityExhausted={exhaustedPlanetAbilities.includes(planetId)}
                isExhausted={exhaustedPlanets.includes(planetId)}
                playerId={playerId}
              />
            ))}
          </Group>
        </>
      )}
    </>
  );
}

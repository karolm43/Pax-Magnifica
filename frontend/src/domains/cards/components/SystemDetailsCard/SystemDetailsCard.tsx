import { Image } from "@/ds";
import InfluenceIcon from "@/shared/ui/InfluenceIcon";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { getTileById } from "@/entities/lookup/systems";
import { getPlanetData } from "@/entities/lookup/planets";
import { getAttachmentModifiers } from "@/entities/game/planets";
import { lookupLoreOr } from "@/entities/lore/lookupLore";
import type { Tile } from "@/entities/game/types";
import { SystemForces } from "./SystemForces";
import { getSystemFeatures, systemAnomalies } from "@/domains/map/components/SystemDossier/featureRules";

type Props = {
  tile: Tile;
  allTiles: Record<string, Tile>;
};

/** Zdjęcie kursywy `*...*` z lore w danych. */
const clean = (text: string) => text.replace(/^\*+|\*+$/g, "").trim();

/**
 * Dymek systemu po najechaniu na kafel — ta sama karta (`DetailsCard`) co planeta:
 * nazwa, zasoby/wpływy, anomalia, wormhole, planety i lore systemu (`cardLore.ts`).
 */
export function SystemDetailsCard({ tile, allTiles }: Props) {
  const data = getTileById(tile.systemId);
  const features = getSystemFeatures(tile, allTiles);
  const anomalyIds = new Set<string>(systemAnomalies(tile));
  const anomalies = features.filter((f) => anomalyIds.has(f.id)).map((f) => f.name);
  const wormholes = features
    .filter((f) => f.id.startsWith("wormhole-"))
    .map((f) => f.glyph ?? f.name);

  let resources = 0;
  let influence = 0;
  const planetNames: string[] = [];
  for (const [planetId, planetTile] of Object.entries(tile.planets)) {
    const planet = getPlanetData(planetId);
    const bonus = getAttachmentModifiers(
      planetTile.attachments ?? [],
      planet?.techSpecialties ?? [],
    );
    resources += (planet?.resources ?? 0) + bonus.resources;
    influence += (planet?.influence ?? 0) + bonus.influence;
    planetNames.push(planet?.name ?? planetId);
  }

  const lore = lookupLoreOr("system", tile.systemId, data?.flavourText);
  const name = data?.name && data.name !== "None" ? data.name : `System ${tile.position}`;
  const facts =
    planetNames.length > 0
      ? [
          {
            key: "res",
            icon: <Image src="/pa_resources.png" alt="" w={18} h={18} />,
            value: resources,
            label: "resources",
          },
          { key: "inf", icon: <InfluenceIcon size={18} />, value: influence, label: "influence" },
        ]
      : [];

  return (
    <DetailsCard width={340} color="none">
      <DetailsCard.Title
        title={name}
        type="System"
        meta={[`Position ${tile.position}`, tile.controlledBy]}
      />
      {facts.length > 0 && <DetailsCard.Facts facts={facts} />}
      {planetNames.length > 0 && (
        <DetailsCard.Section title="Planets" content={planetNames.join(", ")} />
      )}
      {anomalies.length > 0 && (
        <DetailsCard.Section title="Anomaly" content={anomalies.join(", ")} />
      )}
      {wormholes.length > 0 && (
        <DetailsCard.Section title="Wormhole" content={wormholes.join(" ")} />
      )}
      <SystemForces tile={tile} />
      {planetNames.length === 0 && anomalies.length === 0 && wormholes.length === 0 && (
        <DetailsCard.Section title="Empty space" content="No planets, anomalies or wormholes." />
      )}
      {lore && <DetailsCard.Flavor quiet>{clean(lore)}</DetailsCard.Flavor>}
    </DetailsCard>
  );
}

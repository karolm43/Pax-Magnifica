import { Image } from "@/ds";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getPlanetData } from "@/entities/lookup/planets";
import { typeset } from "@/entities/lore/typography";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { PlanetActionCardsSection } from "./PlanetActionCardsSection";

type Props = {
  planetId: string;
  abilityName: string;
  abilityText: string;
  actionCards?: string[];
};

export function PlanetAbilityDetailsCard({
  planetId,
  abilityName,
  abilityText,
  actionCards,
}: Props) {
  const planetData = getPlanetData(planetId);

  if (!planetData) return null;

  // Data wraps flavour in `*...*`; some entries are just "**".
  const flavour = (planetData.legendaryAbilityFlavourText ?? "").replace(/^\*+|\*+$/g, "").trim();

  return (
    <DetailsCard width={340} color="gold">
      <DetailsCard.Title
        title={abilityName}
        type="Planet ability"
        meta={[planetData.shortName ?? planetData.name]}
        icon={
          <DetailsCard.Icon
            shape="round"
            icon={
              <Image
                src={assetUrl("/planet_cards/pc_legendary_rdy.png")}
                alt=""
              />
            }
          />
        }
      />
      <DetailsCard.Section title="Ability" content={abilityText} />
      <PlanetActionCardsSection actionCards={actionCards} />
      {flavour && <DetailsCard.Flavor quiet>{typeset(flavour)}</DetailsCard.Flavor>}
    </DetailsCard>
  );
}

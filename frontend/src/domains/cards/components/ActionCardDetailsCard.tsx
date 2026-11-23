import { Image } from "@/ds";
import { getActionCard } from "@/entities/lookup/actionCards";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { lookupLoreOr } from "@/entities/lore/lookupLore";

type Props = {
  actionCardId: string;
};

export function ActionCardDetailsCard({ actionCardId }: Props) {
  const actionCardData = getActionCard(actionCardId);

  if (!actionCardData) return null;
  const flavor = lookupLoreOr("actionCard", actionCardData.alias, actionCardData.flavorText);

  return (
    <DetailsCard width={340} color="yellow">
      <DetailsCard.Title
        title={actionCardData.name}
        type="Action card"
        meta={[actionCardData.phase && `${actionCardData.phase} phase`]}
        icon={
          <DetailsCard.Icon
            shape="card"
            icon={
              <Image
                src={assetUrl("/player_area/cardback_action.jpg")}
                alt=""
              />
            }
          />
        }
      />
      <DetailsCard.Section
        title={actionCardData.window}
        content={actionCardData.text}
      />
      {flavor && <DetailsCard.Flavor>{flavor}</DetailsCard.Flavor>}
    </DetailsCard>
  );
}

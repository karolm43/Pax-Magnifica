import { assetUrl } from "@/shared/assets/resolveAsset";
import { RelicDeckDetailsCard } from "@/domains/cards/components/RelicDeckDetailsCard";
import { CardbackModal } from "@/shared/ui/CardbackModal";

type Props = {
  deck: string[];
  discard: string[];
};

export function RelicDeckCardBack({ deck, discard }: Props) {
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_relic.jpg")}
      alt="relics"
      title="Relics"
      count={deck.length}
    >
      <RelicDeckDetailsCard deck={deck} discard={discard} />
    </CardbackModal>
  );
}

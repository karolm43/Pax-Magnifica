import { assetUrl } from "@/shared/assets/resolveAsset";
import { SecretDeckDetailsCard } from "@/domains/cards/components/SecretDeckDetailsCard";
import { CardbackModal } from "@/shared/ui/CardbackModal";

type Props = {
  deck: string[];
  discard: string[];
};

export function SecretDeckCardBack({ deck, discard }: Props) {
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_secret.jpg")}
      alt="secret objectives"
      title="Not scored secrets"
      count={deck.length}
    >
      <SecretDeckDetailsCard deck={deck} discard={discard} />
    </CardbackModal>
  );
}

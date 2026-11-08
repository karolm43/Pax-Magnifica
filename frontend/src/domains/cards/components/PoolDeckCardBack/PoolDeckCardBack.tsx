import { useMemo } from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { CardbackModal } from "@/shared/ui/CardbackModal";
import { CardPoolBrowser } from "@/domains/cards/components/CardPoolBrowser/CardPoolBrowser";
import {
  actionCardPool,
  agendaPool,
  explorationPool,
  publicObjectivePool,
  relicPool,
  secretObjectivePool,
  type PoolGroup,
} from "@/domains/cards/model/cardPoolBrowser";

/** Liczba FIZYCZNYCH kart we wszystkich grupach puli (sumuje kopie). */
function totalCount(groups: PoolGroup[]): number {
  return groups.reduce(
    (sum, group) =>
      sum + group.entries.reduce((n, e) => n + (e.copies ?? 1), 0),
    0,
  );
}

type BackProps = {
  /**
   * Liczba pozostała w talii stanu gry. Gdy brak lub 0 (backend nie śledzi
   * jeszcze talii agend/kart akcji), pokazujemy rozmiar całej puli — rewers
   * odzwierciedla wtedy liczbę kart do przejrzenia, nie „0".
   */
  count?: number;
};

/** Rewers talii agend; klik → pełna pula agend (prawa i dyrektywy). */
export function AgendaDeckCardBack({
  count,
  variant,
}: BackProps & {
  /** Wariant talii agend gry (`cardPool.agendaVariant`): "standard" albo "absol". */
  variant?: string;
}) {
  const groups = useMemo(() => agendaPool(variant), [variant]);
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_agenda.png")}
      alt="agenda cards"
      title="Agendas"
      deckId="agenda"
      count={count || totalCount(groups)}
      modalSize={880}
    >
      <CardPoolBrowser groups={groups} deckId="agenda" />
    </CardbackModal>
  );
}

/** Rewers talii kart akcji; klik → pełna pula kart akcji. */
export function ActionCardDeckCardBack({ count }: BackProps) {
  const groups = useMemo(() => actionCardPool(), []);
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_action.jpg")}
      alt="action cards"
      title="Action cards"
      deckId="action"
      count={count || totalCount(groups)}
      modalSize={880}
    >
      <CardPoolBrowser groups={groups} deckId="action" />
    </CardbackModal>
  );
}

type ObjectiveBackProps = BackProps & {
  /** Etap celu publicznego: 1 (Etap I) albo 2 (Etap II). */
  stage: 1 | 2;
};

/** Rewers talii celów publicznych danego etapu; klik → pełna pula tego etapu. */
export function PublicObjectiveDeckCardBack({ stage, count }: ObjectiveBackProps) {
  const groups = useMemo(() => publicObjectivePool(stage), [stage]);
  const image = stage === 1 ? "cardback_public1.png" : "cardback_public2.png";
  const title = stage === 1 ? "Stage I objectives" : "Stage II objectives";
  return (
    <CardbackModal
      imageSrc={assetUrl(`/player_area/${image}`)}
      alt={`public stage ${stage} objectives`}
      title={title}
      deckId={`stage${stage}`}
      count={count || totalCount(groups)}
      modalSize={880}
    >
      <CardPoolBrowser groups={groups} deckId={`stage${stage}`} />
    </CardbackModal>
  );
}

/** Rewers talii celów sekretnych; klik → pełna pula sekretów (referencja). */
export function SecretObjectiveDeckCardBack({ count }: BackProps) {
  const groups = useMemo(() => secretObjectivePool(), []);
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_secret.jpg")}
      alt="secret objectives"
      title="Secret objectives"
      deckId="secret"
      count={count || totalCount(groups)}
      modalSize={880}
    >
      <CardPoolBrowser groups={groups} deckId="secret" />
    </CardbackModal>
  );
}

/** Rewers talii relikwii; klik → pełna pula relikwii. */
export function RelicDeckCardBack({ count }: BackProps) {
  const groups = useMemo(() => relicPool(), []);
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_relic.jpg")}
      alt="relics"
      title="Relics"
      deckId="relic"
      count={count || totalCount(groups)}
      modalSize={880}
    >
      <CardPoolBrowser groups={groups} deckId="relic" />
    </CardbackModal>
  );
}

type ExploreBackProps = BackProps & {
  /** Cecha eksploracji: Cultural / Industrial / Hazardous / Frontier. */
  type: "Cultural" | "Industrial" | "Hazardous" | "Frontier";
};

/** Rewers talii eksploracji danej cechy; klik → pełna pula tej cechy. */
export function ExplorationDeckCardBack({ type, count }: ExploreBackProps) {
  const groups = useMemo(() => explorationPool(type), [type]);
  return (
    <CardbackModal
      cardKey={type}
      imageSrc={assetUrl(`/player_area/cardback_${type.toLowerCase()}.jpg`)}
      alt={`${type} explore`}
      title={`${type} exploration`}
      deckId={type.toLowerCase()}
      count={count || totalCount(groups)}
      modalSize={880}
    >
      <CardPoolBrowser groups={groups} deckId={type.toLowerCase()} />
    </CardbackModal>
  );
}

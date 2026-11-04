import { useMemo } from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { CardbackModal } from "@/shared/ui/CardbackModal";
import { CardPoolBrowser } from "@/domains/cards/components/CardPoolBrowser/CardPoolBrowser";
import {
  actionCardPool,
  agendaPool,
  publicObjectivePool,
} from "@/domains/cards/model/cardPoolBrowser";

/** Liczba kart we wszystkich grupach puli. */
function totalCount(groups: { entries: unknown[] }[]): number {
  return groups.reduce((sum, group) => sum + group.entries.length, 0);
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
export function AgendaDeckCardBack({ count }: BackProps) {
  const groups = useMemo(() => agendaPool(), []);
  return (
    <CardbackModal
      imageSrc={assetUrl("/player_area/cardback_agenda.png")}
      alt="agenda cards"
      title="Agendas"
      count={count || totalCount(groups)}
    >
      <CardPoolBrowser groups={groups} />
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
      count={count || totalCount(groups)}
    >
      <CardPoolBrowser groups={groups} />
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
      count={count || totalCount(groups)}
    >
      <CardPoolBrowser groups={groups} />
    </CardbackModal>
  );
}

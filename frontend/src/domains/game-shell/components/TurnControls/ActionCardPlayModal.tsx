import { useMemo } from "react";
import { DecisionField } from "@/domains/offers/DecisionFields";
import { ComponentUseModal, formError } from "./ComponentUseModal";
import { useBoardEditor } from "@/api/useBoardEditor";
import {
  useActionCardForm,
  type ActionCardInput,
  type FormValue,
} from "@/api/useActionCard";
import { useRelicForm } from "@/api/useRelics";
import { usePromissoryForm } from "@/api/useFactionComponents";
import { useAppStore } from "@/state/appStore";
import { DECISION_WIDTH } from "@/shared/ui/DecisionFrame";

type Props = {
  onClose: () => void;
  onPlayed: () => void;
  cardId: string;
  cardName: string;
  /** Gracz zagrywający kartę (aktywny w fazie akcji). */
  playerId: string;
  /** Migawka historii (HOLD): karta zostanie zagrana po cofnięciu gry do tego kroku. */
  seq?: number;
  /** Co zostanie cofnięte (etykieta kroku), pokazywane przy HOLD. */
  rewindNote?: string;
  /**
   * ``relic`` = zagranie „ACTION:" reliktu (RULES.md 59): ten sam formularz, ale relikt zostaje
   * przed graczem (``cardId`` to id reliktu), a zagranie idzie przez ``/relic/play``.
   * ``frontier`` = karta frontier z ręki (Enigmatic Device): ten sam formularz, ``/frontier-card/play``.
   */
  kind?: "card" | "relic" | "frontier" | "note";
};

/** Jedno pole formularza wg rodzaju wejścia opisanego przez backend (kafelki / stepper). */
export function InputField(props: {
  input: ActionCardInput;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
}) {
  return <DecisionField {...props} />;
}

/**
 * Zagranie karty akcji (okno „Action”) jako akcji komponentu. Formularz buduje się z opisu
 * wyborów z backendu (``/action-card/{id}/inputs``) — front nie zna kart. Silnik waliduje
 * wszystko ponownie; przy błędzie powód pojawia się w komunikacie, a okno zostaje otwarte.
 */
export function ActionCardPlayModal({
  onClose,
  onPlayed,
  cardId,
  cardName,
  playerId,
  seq,
  rewindNote,
  kind = "card",
}: Props) {
  const isFrontier = kind === "frontier";
  const isNote = kind === "note";
  const isRelic = kind === "relic" || isFrontier;
  const cardForm = useActionCardForm(isRelic || isNote ? null : cardId, playerId, seq);
  // Promissory note z ręki (RULES.md 61.2): ten sam formularz, zagranie przez /promissory/play.
  const noteForm = usePromissoryForm(isNote ? cardId : null, playerId);
  const relicForm = useRelicForm(
    isRelic ? cardId : null,
    playerId,
    isFrontier ? "frontier-card" : "relic",
  );
  const form = isNote ? noteForm : isRelic ? relicForm : cardForm;
  const { playActionCard, playRelic, playPromissory } = useBoardEditor();
  const setNotice = useAppStore((state) => state.setNotice);
  const inputs = useMemo(() => form.data?.inputs ?? [], [form.data]);

  const play = async (params: Record<string, unknown>) => {
    if (isNote) {
      const result = await playPromissory(playerId, cardId, params);
      if (!result.implemented) {
        setNotice(
          `${cardName} is not automated yet - it was played. Resolve its effect by hand.`,
          "info",
        );
      }
      onPlayed();
      return;
    }
    if (isRelic) {
      const result = await playRelic(
        playerId,
        cardId,
        params,
        isFrontier ? "/frontier-card/play" : "/relic/play",
      );
      if (!result.implemented) {
        setNotice(
          `${cardName} is not automated yet - it counts as your action. Resolve its effect by hand.`,
          "info",
        );
      }
      onPlayed();
      return;
    }
    const result = await playActionCard(playerId, cardId, params, seq);
    if (result.held) {
      setNotice(`${cardName} is on the table - other players may answer with Sabotage.`, "info");
    }
    if (!result.implemented) {
      setNotice(
        `${cardName} is not automated yet - it was played and discarded. Resolve its effect by hand.`,
        "info",
      );
    }
    onPlayed();
  };

  const data = form.data;
  const notes: string[] = [];
  if (seq !== undefined) {
    notes.push(
      `HOLD: the game goes back to this step${rewindNote ? ` (${rewindNote})` : ""} and everything after it is undone.`,
    );
  }
  if (data && "summary" in data && data.summary) notes.push(data.summary);
  if (data && !data.implemented) {
    notes.push(
      isRelic
        ? "The engine does not automate this relic yet. Using it counts as your action - resolve the effect by hand."
        : "The engine does not automate this card yet. Playing it counts as your action and discards it - resolve the effect by hand.",
    );
  }
  const infoKind = isNote ? "promissory" : isRelic ? "relic" : "actionCard";

  return (
    <ComponentUseModal
      title={cardName}
      kind={isNote ? "Promissory note" : isFrontier ? "Frontier card" : isRelic ? "Relic" : "Action card"}
      infoRef={isFrontier ? undefined : { kind: infoKind, id: cardId }}
      infoName={cardName}
      loading={form.isLoading}
      error={formError(form.error, "Could not load this card.")}
      text={data?.text}
      notes={notes}
      inputs={inputs}
      noOptionsMessage="There is no legal target for this card right now."
      useLabel={isRelic ? "Use relic" : isNote ? "Play note" : "Play card"}
      onUse={play}
      onClose={onClose}
      size={DECISION_WIDTH.standard}
    />
  );
}

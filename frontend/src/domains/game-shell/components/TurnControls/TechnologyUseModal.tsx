import { useBoardEditor } from "@/api/useBoardEditor";
import { useTechnologyAbilityUse, useTechnologyForm } from "@/api/useTechnology";
import { Tech } from "@/domains/player/components/Tech";
import { getTechData } from "@/entities/lookup/tech";
import { ComponentUseModal, formError } from "./ComponentUseModal";

type Props = {
  techId: string;
  techName: string;
  /** Gracz używający technologii (aktywny w fazie akcji). */
  playerId: string;
  onClose: () => void;
  onDone: () => void;
};

/**
 * Użycie technologii przez gracza (RULES.md 57). Formularz buduje się z opisu wyborów z silnika
 * (`/technology/{id}/form`): technologia z „ACTION:" jest zagrywana jako akcja komponentu,
 * a zdolność poza akcją (Psychoarchaeology) nie zużywa akcji tury. Silnik waliduje odpowiedź
 * ponownie; przy błędzie powód pojawia się w komunikacie, a okno zostaje otwarte.
 */
export function TechnologyUseModal({ techId, techName, playerId, onClose, onDone }: Props) {
  const form = useTechnologyForm(techId, playerId);
  const { playComponentAction } = useBoardEditor();
  const useAbility = useTechnologyAbilityUse();
  const data = form.data;
  const isFree = data?.kind === "free";
  const exhausted = data?.exhausted === true && !isFree;

  return (
    <ComponentUseModal
      // Ten sam chip co w panelu gracza (pełna karta po kliknięciu).
      title={getTechData(techId) ? <Tech techId={techId} /> : techName}
      infoName={techName}
      kind="Technology"
      loading={form.isLoading}
      error={formError(form.error, "Could not load this technology.")}
      text={data?.text}
      notes={
        data
          ? [
              isFree
                ? "This ability is not an action - using it does not end your action for the turn."
                : data.implemented
                  ? "Using it counts as your action for this turn."
                  : "The engine does not automate this technology yet. Playing it counts as your action - resolve the effect by hand.",
            ]
          : []
      }
      warnings={exhausted ? ["This technology is exhausted."] : []}
      inputs={data?.inputs ?? []}
      blocked={exhausted}
      useLabel={isFree ? "Use ability" : "Use technology"}
      onUse={async (params) => {
        if (isFree) await useAbility(playerId, techId, params);
        else await playComponentAction(playerId, techId, params);
        onDone();
      }}
      onClose={onClose}
    />
  );
}

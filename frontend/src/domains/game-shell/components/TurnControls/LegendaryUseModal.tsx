import { useBoardEditor } from "@/api/useBoardEditor";
import { planetComponentId, usePlanetAbilityForm } from "@/api/usePlanetAbility";
import { ComponentUseModal, formError } from "./ComponentUseModal";

type Props = {
  planetId: string;
  abilityName: string;
  /** Gracz używający karty (aktywny w fazie akcji). */
  playerId: string;
  onClose: () => void;
  onDone: () => void;
};

/**
 * Użycie „ACTION:" karty zdolności legendarnej planety (RULES.md 60.3). Formularz buduje się z
 * opisu wyborów silnika (`/planet-ability/{id}/form`); zagranie to akcja komponentu tury, a karta
 * zostaje u gracza i się wyczerpuje. Silnik waliduje odpowiedź ponownie; przy błędzie powód
 * pojawia się w komunikacie, a okno zostaje otwarte.
 */
export function LegendaryUseModal({ planetId, abilityName, playerId, onClose, onDone }: Props) {
  const form = usePlanetAbilityForm(planetId, playerId);
  const { playComponentAction } = useBoardEditor();
  const data = form.data;
  const exhausted = data?.exhausted === true;

  return (
    <ComponentUseModal
      title={abilityName}
      kind="Legendary planet"
      infoRef={{ kind: "planet", id: planetId }}
      infoName={abilityName}
      loading={form.isLoading}
      error={formError(form.error, "Could not load this ability.")}
      text={data?.text}
      notes={
        data
          ? [
              data.implemented
                ? "Using it counts as your action for this turn."
                : "The engine does not automate this ability yet. Playing it counts as your action - resolve the effect by hand.",
            ]
          : []
      }
      warnings={exhausted ? ["This legendary planet ability card is exhausted."] : []}
      inputs={data?.inputs ?? []}
      blocked={exhausted}
      useLabel="Use ability"
      onUse={async (params) => {
        await playComponentAction(playerId, planetComponentId(planetId), params);
        onDone();
      }}
      onClose={onClose}
    />
  );
}

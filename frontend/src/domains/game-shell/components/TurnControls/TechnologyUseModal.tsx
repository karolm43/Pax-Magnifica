import { useMemo, useState } from "react";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { useBoardEditor } from "@/api/useBoardEditor";
import { buildActionCardParams, type FormValue } from "@/api/useActionCard";
import { useTechnologyAbilityUse, useTechnologyForm } from "@/api/useTechnology";
import { DecisionFields } from "@/domains/offers/DecisionFields";

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
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);

  const inputs = useMemo(() => form.data?.inputs ?? [], [form.data]);
  const { params, ready } = useMemo(() => buildActionCardParams(inputs, values), [inputs, values]);
  const noOptions = inputs.some(
    (input) =>
      input.kind !== "number" &&
      input.options.length < (input.kind === "multi" ? input.min : 1),
  );
  const isFree = form.data?.kind === "free";
  const exhausted = form.data?.exhausted === true && !isFree;

  const confirm = async () => {
    setBusy(true);
    try {
      if (isFree) await useAbility(playerId, techId, params);
      else await playComponentAction(playerId, techId, params);
      onDone();
    } catch {
      // Powód pokazał już komunikat; okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppModal floating opened onClose={onClose} title={techName} size={480}>
      <Stack gap="md">
        {form.isLoading && (
          <Text size="sm" c="dimmed">
            Loading technology…
          </Text>
        )}
        {form.isError && (
          <Text size="sm" c="red">
            {form.error instanceof Error ? form.error.message : "Could not load this technology."}
          </Text>
        )}
        {form.data && (
          <>
            <Text size="sm" c="dimmed">
              {form.data.text}
            </Text>
            <Text size="sm">
              {isFree
                ? "This ability is not an action - using it does not end your action for the turn."
                : form.data.implemented
                  ? "Using it counts as your action for this turn."
                  : "The engine does not automate this technology yet. Playing it counts as your action - resolve the effect by hand."}
            </Text>
            {exhausted && (
              <Text size="sm" c="red">
                This technology is exhausted.
              </Text>
            )}
            {(
              <DecisionFields
                inputs={inputs}
                values={values}
                disabled={busy}
                onChange={(key, next) => setValues((prev) => ({ ...prev, [key]: next }))}
              />
            )}
            {noOptions && (
              <Text size="sm" c="red">
                There is nothing to use it on right now.
              </Text>
            )}
          </>
        )}
        <Group justify="flex-end" gap="sm">
          <Button variant="default" disabled={busy} onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !form.data || !ready || noOptions || exhausted}
            onClick={() => void confirm()}
          >
            {isFree ? "Use ability" : "Use technology"}
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}

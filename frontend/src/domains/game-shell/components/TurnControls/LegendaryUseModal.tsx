import { useMemo, useState } from "react";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { useBoardEditor } from "@/api/useBoardEditor";
import { buildActionCardParams, type FormValue } from "@/api/useActionCard";
import { planetComponentId, usePlanetAbilityForm } from "@/api/usePlanetAbility";
import { InputField } from "./ActionCardPlayModal";

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
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);

  const inputs = useMemo(() => form.data?.inputs ?? [], [form.data]);
  const { params, ready } = useMemo(() => buildActionCardParams(inputs, values), [inputs, values]);
  const noOptions = inputs.some(
    (input) =>
      input.kind !== "number" &&
      input.options.length < (input.kind === "multi" ? input.min : 1),
  );
  const exhausted = form.data?.exhausted === true;

  const confirm = async () => {
    setBusy(true);
    try {
      await playComponentAction(playerId, planetComponentId(planetId), params);
      onDone();
    } catch {
      // Powód pokazał już komunikat; okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppModal opened onClose={onClose} title={abilityName} size={480}>
      <Stack gap="md">
        {form.isLoading && (
          <Text size="sm" c="dimmed">
            Loading legendary planet ability…
          </Text>
        )}
        {form.isError && (
          <Text size="sm" c="red">
            {form.error instanceof Error ? form.error.message : "Could not load this ability."}
          </Text>
        )}
        {form.data && (
          <>
            <Text size="sm" c="dimmed">
              {form.data.text}
            </Text>
            <Text size="sm">
              {form.data.implemented
                ? "Using it counts as your action for this turn."
                : "The engine does not automate this ability yet. Playing it counts as your action - resolve the effect by hand."}
            </Text>
            {exhausted && (
              <Text size="sm" c="red">
                This legendary planet ability card is exhausted.
              </Text>
            )}
            {inputs.map((input) => (
              <InputField
                key={input.key}
                input={input}
                value={values[input.key]}
                disabled={busy}
                onChange={(next) => setValues((prev) => ({ ...prev, [input.key]: next }))}
              />
            ))}
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
            Use ability
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}

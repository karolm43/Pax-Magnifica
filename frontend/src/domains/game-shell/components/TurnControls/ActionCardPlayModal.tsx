import { useMemo, useState } from "react";
import { Button, Group, MultiSelect, NumberInput, Select, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { useBoardEditor } from "@/api/useBoardEditor";
import {
  buildActionCardParams,
  useActionCardForm,
  type ActionCardInput,
  type FormValue,
} from "@/api/useActionCard";
import { useAppStore } from "@/state/appStore";

type Props = {
  onClose: () => void;
  onPlayed: () => void;
  cardId: string;
  cardName: string;
  /** Gracz zagrywający kartę (aktywny w fazie akcji). */
  playerId: string;
};

/** Jedno pole formularza wg rodzaju wejścia opisanego przez backend. */
function InputField({
  input,
  value,
  disabled,
  onChange,
}: {
  input: ActionCardInput;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
}) {
  if (input.kind === "number") {
    return (
      <NumberInput
        label={input.label}
        description={input.hint || undefined}
        min={input.min}
        max={input.max}
        value={typeof value === "number" ? value : input.min}
        disabled={disabled}
        onChange={(next) => onChange(typeof next === "number" ? next : input.min)}
      />
    );
  }
  const data = input.options.map((o) => ({ value: o.id, label: o.label }));
  if (input.kind === "multi") {
    const range = input.min === input.max ? `${input.min}` : `${input.min}-${input.max}`;
    return (
      <MultiSelect
        label={input.label}
        description={[input.hint, `Pick ${range}.`].filter(Boolean).join(" ")}
        data={data}
        value={Array.isArray(value) ? value : []}
        disabled={disabled}
        placeholder={data.length ? "Choose…" : "Nothing to choose"}
        onChange={(next) => onChange(next.slice(0, input.max))}
      />
    );
  }
  return (
    <Select
      label={input.label}
      description={input.hint || undefined}
      data={data}
      value={typeof value === "string" ? value : null}
      disabled={disabled}
      placeholder={data.length ? "Choose…" : "Nothing to choose"}
      onChange={onChange}
    />
  );
}

/**
 * Zagranie karty akcji (okno „Action”) jako akcji komponentu. Formularz buduje się z opisu
 * wyborów z backendu (``/action-card/{id}/inputs``) — front nie zna kart. Silnik waliduje
 * wszystko ponownie; przy błędzie powód pojawia się w komunikacie, a okno zostaje otwarte.
 */
export function ActionCardPlayModal({ onClose, onPlayed, cardId, cardName, playerId }: Props) {
  const form = useActionCardForm(cardId, playerId);
  const { playActionCard } = useBoardEditor();
  const setNotice = useAppStore((state) => state.setNotice);
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);

  const inputs = useMemo(() => form.data?.inputs ?? [], [form.data]);
  const { params, ready } = useMemo(
    () => buildActionCardParams(inputs, values),
    [inputs, values],
  );
  const noTargets = inputs.some(
    (input) => input.kind !== "number" && input.options.length < (input.kind === "multi" ? input.min : 1),
  );

  const play = async () => {
    setBusy(true);
    try {
      const result = await playActionCard(playerId, cardId, params);
      if (!result.implemented) {
        setNotice(
          `${cardName} is not automated yet - it was played and discarded. Resolve its effect by hand.`,
          "info",
        );
      }
      onPlayed();
    } catch {
      // Powód pokazał już komunikat (useBoardEditor.post); okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppModal opened onClose={onClose} title={cardName} size={460}>
      <Stack gap="md">
        {form.isLoading && <Text size="sm" c="dimmed">Loading card…</Text>}
        {form.isError && (
          <Text size="sm" c="red">
            This card cannot be played right now (is it still in your hand?).
          </Text>
        )}
        {form.data && (
          <>
            <Text size="sm" c="dimmed">{form.data.text}</Text>
            {!form.data.implemented && (
              <Text size="sm">
                The engine does not automate this card yet. Playing it counts as your action and
                discards it - resolve the effect by hand.
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
            {noTargets && (
              <Text size="sm" c="red">
                There is no legal target for this card right now.
              </Text>
            )}
          </>
        )}
        <Group justify="flex-end" gap="sm">
          <Button variant="default" disabled={busy} onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={busy || !form.data || !ready || noTargets} onClick={() => void play()}>
            Play card
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}

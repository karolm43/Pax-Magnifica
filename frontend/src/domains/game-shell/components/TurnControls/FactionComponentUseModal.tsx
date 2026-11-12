import { useMemo, useState } from "react";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { buildActionCardParams, type FormValue } from "@/api/useActionCard";
import {
  useFactionComponentForm,
  type FactionComponentKind,
} from "@/api/useFactionComponents";
import { InputField } from "./ActionCardPlayModal";

type Props = {
  kind: FactionComponentKind;
  componentId: string;
  name: string;
  /** Gracz-właściciel komponentu. */
  playerId: string;
  onClose: () => void;
  onDone: () => void;
};

const STATUS_COPY: Record<string, string> = {
  locked: "Locked",
  unlocked: "Ready",
  exhausted: "Exhausted",
  purged: "Purged",
};

/**
 * Lider / zdolność frakcji / przełom (RULES.md 61.1, 61.3). Formularz z opisu silnika
 * (`/faction-component/{kind}/{id}/form`). „ACTION:" zagrywa się jako akcja tury, koszt (wyczerpanie
 * agenta, purge bohatera, wyczerpanie przełomu) płaci silnik. Zablokowany lider bez sprawdzanego
 * warunku ma przycisk ręcznego odblokowania; reszta odblokowuje się sama.
 */
export function FactionComponentUseModal({
  kind,
  componentId,
  name,
  playerId,
  onClose,
  onDone,
}: Props) {
  const form = useFactionComponentForm(kind, componentId, playerId);
  const { playFactionComponent, claimLeaderUnlock } = useBoardEditor();
  const setNotice = useAppStore((state) => state.setNotice);
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);

  const inputs = useMemo(() => form.data?.inputs ?? [], [form.data]);
  const { params, ready } = useMemo(() => buildActionCardParams(inputs, values), [inputs, values]);
  const noOptions = inputs.some(
    (input) =>
      input.kind !== "number" &&
      input.options.length < (input.kind === "multi" ? input.min : 1),
  );
  const status = form.data?.status ?? "";
  const notReady = kind !== "ability" && status !== "" && status !== "unlocked";
  const isAction = form.data?.mode === "action";

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
      onDone();
    } catch {
      // Powód pokazał już komunikat (useBoardEditor); okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  const use = () =>
    run(async () => {
      const result = await playFactionComponent(playerId, kind, componentId, params);
      if (!result.implemented) {
        setNotice(
          `${name} is not automated yet - it counts as your action. Resolve its effect by hand.`,
          "info",
        );
      }
    });

  return (
    <AppModal opened onClose={onClose} title={name} size={480}>
      <Stack gap="md">
        {form.isLoading && (
          <Text size="sm" c="dimmed">
            Loading…
          </Text>
        )}
        {form.isError && (
          <Text size="sm" c="red">
            {form.error instanceof Error ? form.error.message : "Could not load this component."}
          </Text>
        )}
        {form.data && (
          <>
            {status && (
              <Text size="sm" fw={600}>
                {STATUS_COPY[status] ?? status}
                {form.data.leader_type ? ` ${form.data.leader_type}` : ""}
              </Text>
            )}
            <Text size="sm" c="dimmed">
              {form.data.text}
            </Text>
            {status === "locked" && form.data.unlock_condition && (
              <Text size="sm">
                Unlock: {form.data.unlock_condition}
                {form.data.can_claim_unlock
                  ? " The engine does not check this condition yet - unlock it yourself when you meet it."
                  : " It unlocks automatically when you meet it."}
              </Text>
            )}
            {isAction && !form.data.implemented && (
              <Text size="sm">
                The engine does not automate this ability yet. Using it counts as your action -
                resolve the effect by hand.
              </Text>
            )}
            {!isAction && (
              <Text size="sm">
                {form.data.implemented
                  ? "This ability works on its own - the engine asks you at the right moment."
                  : "This ability is not automated yet - resolve it by hand when it applies."}
              </Text>
            )}
            {isAction &&
              !notReady &&
              inputs.map((input) => (
                <InputField
                  key={input.key}
                  input={input}
                  value={values[input.key]}
                  disabled={busy}
                  onChange={(next) => setValues((prev) => ({ ...prev, [input.key]: next }))}
                />
              ))}
            {isAction && !notReady && noOptions && (
              <Text size="sm" c="red">
                There is nothing to use it on right now.
              </Text>
            )}
          </>
        )}
        <Group justify="flex-end" gap="sm">
          <Button variant="default" disabled={busy} onClick={onClose}>
            Close
          </Button>
          {form.data?.can_claim_unlock && (
            <Button
              disabled={busy}
              onClick={() => void run(() => claimLeaderUnlock(playerId, componentId))}
            >
              Unlock
            </Button>
          )}
          {isAction && (
            <Button
              disabled={busy || !form.data || !ready || noOptions || notReady}
              onClick={() => void use()}
            >
              Use ability
            </Button>
          )}
        </Group>
      </Stack>
    </AppModal>
  );
}

import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useOfferActions, useOffers, type OfferView } from "@/api/useOffers";
import { buildActionCardParams, type FormValue } from "@/api/useActionCard";
import { InputField } from "@/domains/game-shell/components/TurnControls/ActionCardPlayModal";

/** Jedna decyzja gracza: tekst karty z assetów + formularz z opcji policzonych przez silnik. */
function OfferForm({ offer }: { offer: OfferView }) {
  const actions = useOfferActions();
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);

  // Nowa oferta → czysty formularz.
  useEffect(() => setValues({}), [offer.id]);

  const { params, ready } = useMemo(
    () => buildActionCardParams(offer.inputs, values),
    [offer.inputs, values],
  );
  const noOptions = offer.inputs.some(
    (input) =>
      input.kind !== "number" &&
      input.options.length < (input.kind === "multi" ? input.min : 1),
  );

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód (422) pokazał komunikat; okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppModal
      opened
      onClose={() => undefined}
      title={offer.name}
      size={460}
      closeOnClickOutside={false}
      closeOnEscape={false}
      withCloseButton={false}
      minimizable
    >
      <Stack gap="md">
        {offer.text && (
          <Text size="sm" c="dimmed">
            {offer.text}
          </Text>
        )}
        <Text size="sm">
          {offer.mandatory
            ? "You must decide - the engine never chooses for you."
            : "You may use this now. Skipping is fine."}
        </Text>
        {offer.inputs.map((input) => (
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
            There is no legal option for this right now.
          </Text>
        )}
        <Group justify="flex-end" gap="sm">
          {!offer.mandatory && (
            <Button
              variant="default"
              disabled={busy}
              onClick={() => void run(() => actions.decline(offer.player_id, offer.id))}
            >
              Skip
            </Button>
          )}
          <Button
            disabled={busy || !ready || noOptions}
            onClick={() => void run(() => actions.accept(offer.player_id, offer.id, params))}
          >
            {offer.mandatory ? "Confirm" : "Use"}
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}

/**
 * Okno DECYZJI graczy (RULES.md 56): technologie i zdolności z „may" oraz wybory celu (np. ofiara
 * Assault Cannon, cel Magen Defense Grid, naprawa Duranium Armor). Samo się pojawia, gdy
 * `gameState.pendingOffers` nie jest puste; pokazuje po jednej decyzji, a gracz zawsze wybiera sam.
 */
export function OffersModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const pending = (gameState?.pendingOffers ?? []).length > 0;
  const { data: offers, refetch } = useOffers(pending);

  // Każda zmiana stanu gry odświeża opcje (zależą od bieżącej planszy).
  useEffect(() => {
    if (pending) void refetch();
  }, [gameState, pending, refetch]);

  if (!pending || !offers || offers.length === 0) return null;
  return <OfferForm key={offers[0].id} offer={offers[0]} />;
}

export default OffersModal;

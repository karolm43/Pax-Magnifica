import { useState } from "react";
import { useParams } from "react-router-dom";
import { Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor } from "@/api/useBoardEditor";
import { SC_HUES, SC_NAMES } from "@/entities/data/strategyCardColors";
import { getStrategyCardById } from "@/entities/lookup/strategyCards";
import { PRIMARY_STEP_MODE, PRIMARY_VIEWS } from "@/domains/strategy/cards";
import promptStyles from "@/domains/strategy/StrategyPrompt.module.css";
import type { CardShell } from "@/domains/strategy/cards/types";
import { useStrategyPrompt, type PromptPlayer } from "@/domains/strategy/strategyPrompt";

/**
 * Okno kroku WIELOETAPOWEGO primary karty strategii (RULES.md 30.5).
 *
 * Gdy karta wymaga wyborów aktywnego gracza, silnik ustawia ``pendingStrategy`` (krok +
 * szkic) i blokuje End turn. Ten modal pobiera z backendu opcje bieżącego kroku
 * (``GET /strategy/options``) i renderuje widok karty z ``domains/strategy/cards``;
 * wybór leci do ``/strategy/primary-step``. Modal jest NIEODRZUCALNY - znika, gdy
 * backend zastosuje primary i otworzy okno secondary. Walidacja jest po stronie serwera
 * (tylko właściciel karty), więc w sieci inni gracze widzą ten sam stan, ale go nie
 * rozstrzygną.
 */
export function StrategyPrimaryStepModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { strategyPrimaryStep } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const pending = gameState?.pendingStrategy ?? null;
  const players = (gameData?.playerData ?? []) as PromptPlayer[];
  const owner = players.find((p) => p.discordId === pending?.ownerId);
  const version = pending ? `${pending.initiative}:${pending.step}` : "none";
  const { data: prompt } = useStrategyPrompt(pending?.ownerId ?? null, version);

  const card = pending
    ? gameData?.strategyCards?.find((c) => c.initiative === pending.initiative)
    : undefined;
  const shell: CardShell | null = pending
    ? {
        hue:
          (card ? getStrategyCardById(card.id)?.colourHexCode : undefined) ||
          SC_HUES[pending.initiative] ||
          "#8a8f98",
        initiative: pending.initiative,
        title:
          card?.name ?? SC_NAMES[pending.initiative] ?? `Strategy Card ${pending.initiative}`,
      }
    : null;

  const submit = (payload: Record<string, unknown>) => {
    if (!pending || busy) return;
    setBusy(true);
    void strategyPrimaryStep(pending.ownerId, payload).finally(() => setBusy(false));
  };

  const View = pending ? PRIMARY_VIEWS[pending.initiative] : undefined;
  const ready = prompt != null && prompt.kind === "primary" && prompt.step === pending?.step;
  const mode =
    (pending ? PRIMARY_STEP_MODE[pending.initiative]?.[pending.step] : undefined) ?? "modal";

  // Kroki "hidden" (produkcja) oddają ekran innemu oknu; "dock" zostawia mapę klikalną.
  if (pending == null || mode === "hidden") return null;

  const body =
    View && shell && ready ? (
      <View
        key={`${pending.initiative}:${pending.step}`}
        prompt={prompt}
        shell={shell}
        owner={owner}
        players={players}
        busy={busy}
        submit={submit}
      />
    ) : (
      <Text size="sm" c="dimmed">
        {!View ? `Unsupported card: ${pending.initiative}` : "Loading..."}
      </Text>
    );

  if (mode === "dock") return <div className={promptStyles.dock}>{body}</div>;

  return (
    <AppModal
      opened
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title="Strategic action"
      size={560}
    >
      {body}
    </AppModal>
  );
}

export default StrategyPrimaryStepModal;

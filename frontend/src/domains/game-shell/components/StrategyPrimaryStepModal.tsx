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
import { PRIMARY_MODAL_SIZE, PRIMARY_STEP_MODE, PRIMARY_VIEWS } from "@/domains/strategy/cards";
import { PromptDock } from "@/domains/strategy/PromptDock";
import type { CardShell } from "@/domains/strategy/cards/types";
import { useStrategyPrompt, type PromptPlayer } from "@/domains/strategy/strategyPrompt";
import { useCanActAs } from "@/domains/network/useNetworkMe";
import { DECISION_WIDTH } from "@/shared/ui/DecisionFrame";

/**
 * Okno kroku WIELOETAPOWEGO primary karty strategii (RULES.md 30.5).
 *
 * Gdy karta wymaga wyborów aktywnego gracza, silnik ustawia ``pendingStrategy`` (krok +
 * szkic) i blokuje End turn. Ten modal pobiera z backendu opcje bieżącego kroku
 * (``GET /strategy/options``) i renderuje widok karty z ``domains/strategy/cards``;
 * wybór leci do ``/strategy/primary-step``. Modal jest NIEODRZUCALNY - znika, gdy
 * backend zastosuje primary i otworzy okno secondary. Walidacja jest po stronie serwera
 * (tylko właściciel karty). W sieci okno widzi TYLKO właściciel karty (opcje kroku to jego
 * dane prywatne — inni dostaliby 403); pozostali mają status „Waiting for X" w nagłówku.
 */
export function StrategyPrimaryStepModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { strategyPrimaryStep } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const canActAs = useCanActAs();
  const pendingRaw = gameState?.pendingStrategy ?? null;
  const pending = pendingRaw && canActAs(pendingRaw.ownerId) ? pendingRaw : null;
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
        table={{
          seating: gameState?.seatingOrder ?? [],
          speaker: gameState?.speaker ?? null,
        }}
        busy={busy}
        submit={submit}
      />
    ) : (
      <Text size="sm" c="dimmed">
        {!View ? `Unsupported card: ${pending.initiative}` : "Loading..."}
      </Text>
    );

  const label = `${shell?.title ?? "Strategic action"} - primary`;
  if (mode === "dock") return <PromptDock label={label}>{body}</PromptDock>;
  if (mode === "overlay") return body; // widok sam rysuje pełnoekranowe okno

  return (
    <AppModal
      floating
      opened
      minimizable={label}
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      // Widok karty ma własny nagłówek (PromptShell: karta + plakietka Primary) - bez drugiego tytułu.
      size={PRIMARY_MODAL_SIZE[pending.initiative] ?? DECISION_WIDTH.wide}
    >
      {body}
    </AppModal>
  );
}

export default StrategyPrimaryStepModal;

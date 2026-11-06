import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Text } from "@/ds";
import { IconBolt, IconHandStop } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor } from "@/api/useBoardEditor";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import {
  getPlayerDisplayName,
  type GameStatePlayer,
} from "./gameStatePlayers";

/**
 * Popup decyzji SECONDARY karty strategii (RULES.md 29.2, 31.6).
 *
 * Gdy aktywny gracz ZAGRA kartę strategii, silnik otwiera okno ``STRATEGY_SECONDARY``
 * i pyta pozostałych graczy PO KOLEI — „beginning with the player to the left of the
 * active player and proceeding clockwise" (R_strategic_action). Ten modal adresuje
 * BIEŻĄCEGO respondenta i daje wybór w języku planszówki:
 *  - „Follow" — gracz rozwija secondary (``execute=true``);
 *  - „Don't follow" — rezygnuje (``execute=false``).
 * Follow jest DOBROWOLNY (reguła: „Players do not have to resolve the secondary").
 *
 * ZAKRES (świadomy): modal daje tylko WYBÓR i przesuwa kolejkę okna. CO dokładnie robi
 * „follow" (efekt liczbowy secondary) dojdzie kartą po karcie w ``strategic_action``
 * (RULES.md 30) — tu nie kodujemy skutków.
 *
 * Modal jest NIEODRZUCALNY (brak krzyżyka, klik poza/Escape nie zamyka): decyzja o
 * secondary jest wymagana od każdego gracza po kolei, zanim aktywny gracz zakończy turę
 * (End turn zablokowany, dopóki trwa okno — RULES.md 31.6). Po decyzji ostatniego gracza
 * okno zamyka się samo i modal znika.
 *
 * Adresowanie respondenta: ``currentResponderId`` (stabilny player_id) do wysyłki;
 * ``currentResponder`` (KOLOR) do dopasowania ikony/nazwy w ``playerData`` — spójnie
 * z resztą UI (activePlayer to też kolor).
 */
export function SecondaryDecisionModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { strategySecondary } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const window = gameState?.pendingWindow ?? null;
  // Pokazujemy TYLKO dla okna secondary z czekającym respondentem. Pozostałe typy
  // okien (walka, reakcje) mają własne panele/modale — nie ten popup.
  const isSecondary =
    !!window &&
    window.windowType === "STRATEGY_SECONDARY" &&
    !window.isComplete &&
    !!window.currentResponderId;

  const playerData = (gameData?.playerData ?? []) as GameStatePlayer[];
  const responderColor = window?.currentResponder ?? null;
  const responder = responderColor
    ? playerData.find((p) => p.color === responderColor)
    : undefined;
  const responderName = responder
    ? getPlayerDisplayName(responder, responderColor ?? "")
    : (window?.currentResponderId ?? "");

  // Nazwa karty, której dotyczy secondary (z kontekstu okna: {"initiative": n}).
  const initiativeRaw = window?.context?.initiative;
  const initiative =
    typeof initiativeRaw === "number"
      ? initiativeRaw
      : typeof initiativeRaw === "string"
        ? Number(initiativeRaw)
        : null;
  const cardName =
    initiative != null
      ? getStrategyCardByInitiative(initiative)?.name ||
        SC_NAMES[initiative] ||
        `Strategy Card ${initiative}`
      : "Strategy Card";

  const decide = (execute: boolean) => {
    const id = window?.currentResponderId;
    if (!id || busy) return;
    setBusy(true);
    void strategySecondary(id, execute).finally(() => setBusy(false));
  };

  return (
    <AppModal
      opened={isSecondary}
      // Modal wymuszony: nie zamykamy go samodzielnie — zniknie, gdy backend domknie
      // okno (po decyzji ostatniego gracza). onClose to no-op (wymagany przez typ).
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title="Strategy Card — secondary ability"
      size={460}
    >
      <Stack gap="md">
        {/* Kto teraz decyduje. */}
        <Group gap="sm" wrap="nowrap">
          {responder?.faction ? (
            <CircularFactionIcon faction={responder.faction} size={34} />
          ) : null}
          <Stack gap={2}>
            <Text size="xs" c="dimmed">
              Your call
            </Text>
            <Text fw={700}>{responderName}</Text>
          </Stack>
        </Group>

        <Text size="sm">
          <b>{cardName}</b> was played. Do you want to <b>follow</b> and resolve
          its secondary ability?
        </Text>

        <Text size="xs" c="dimmed">
          Following is optional. Players respond in turn order — the player to
          the left of the active player first, then clockwise.
          {window ? ` Remaining after you: ${Math.max(window.remaining - 1, 0)}.` : ""}
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="default"
            disabled={busy}
            leftSection={<IconHandStop size={16} />}
            onClick={() => decide(false)}
          >
            Don't follow
          </Button>
          <Button
            disabled={busy}
            leftSection={<IconBolt size={16} />}
            onClick={() => decide(true)}
          >
            Follow
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}

export default SecondaryDecisionModal;

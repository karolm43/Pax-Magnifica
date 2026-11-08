import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Text } from "@/ds";
import { IconBolt, IconHandStop } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor } from "@/api/useBoardEditor";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import {
  getStrategyCardById,
  getStrategyCardByInitiative,
} from "@/entities/lookup/strategyCards";
import { SC_NAMES, SC_HUES } from "@/entities/data/strategyCardColors";
import {
  getPlayerDisplayName,
  type GameStatePlayer,
} from "./gameStatePlayers";
import { StrategyPrimaryStepModal } from "./StrategyPrimaryStepModal";

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

  // Karta, której dotyczy secondary (z kontekstu okna: {"initiative": n}).
  const initiativeRaw = window?.context?.initiative;
  const initiative =
    typeof initiativeRaw === "number"
      ? initiativeRaw
      : typeof initiativeRaw === "string"
        ? Number(initiativeRaw)
        : null;
  // WARIANT KANONICZNY wybiera BACKEND i podaje jego ``id`` w ``gameData.strategyCards``
  // (przy włączonym Thunder's Edge init 4/6 → te4construction/te6warfare, nie
  // base/pok — RULES.md 14). Bierzemy kartę PO TYM ``id`` (getStrategyCardById), żeby
  // teksty były zgodne z aktywnym zestawem gry. Dopiero gdy nie znajdziemy wpisu,
  // spadamy na lookup po initiative (stare migawki / brak puli).
  const cardId =
    initiative != null
      ? gameData?.strategyCards?.find((c) => c.initiative === initiative)?.id
      : undefined;
  const card =
    (cardId ? getStrategyCardById(cardId) : undefined) ??
    (initiative != null
      ? getStrategyCardByInitiative(initiative, gameData?.strategyCardIdMap)
      : undefined);
  const cardName =
    card?.name ||
    (initiative != null ? SC_NAMES[initiative] : undefined) ||
    (initiative != null ? `Strategy Card ${initiative}` : "Strategy Card");
  const secondaryLines = card?.secondaryTexts ?? [];
  const hue =
    card?.colourHexCode ||
    (initiative != null ? SC_HUES[initiative] : undefined) ||
    "#8a8f98";

  const decide = (execute: boolean) => {
    const id = window?.currentResponderId;
    if (!id || busy) return;
    setBusy(true);
    void strategySecondary(id, execute).finally(() => setBusy(false));
  };

  // Koszt follow: żeton ze strategy pool (window.context.cost = 1), chyba że respondent
  // został wskazany jako „free" (wtedy secondary jest DARMOWE i OBOWIĄZKOWE).
  const isFree = (String(window?.context?.free ?? "").split(",") as string[]).includes(
    window?.currentResponderId ?? "\0",
  );
  const needsToken = Number(window?.context?.cost ?? 0) > 0 && !isFree;
  const poolTokens = (responder as { strategicCC?: number } | undefined)?.strategicCC;
  const cannotAfford = needsToken && (poolTokens ?? 1) < 1;

  return (
    <>
    <StrategyPrimaryStepModal />
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

        {/* Treść SECONDARY tej karty — to samo źródło co hover karty strategii
            (getStrategyCardByInitiative). Odpowiada na „co robi follow". */}
        <div
          style={
            {
              "--sc-hue": hue,
              borderLeft: "3px solid var(--sc-hue)",
              background:
                "color-mix(in srgb, var(--sc-hue) 10%, transparent)",
              borderRadius: 8,
              padding: "10px 12px",
            } as CSSProperties
          }
        >
          <Text
            size="xs"
            fw={700}
            style={{
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--sc-hue)",
              marginBottom: 4,
            }}
          >
            Secondary
          </Text>
          {secondaryLines.length > 0 ? (
            <Stack gap={6}>
              {secondaryLines.map((line, i) => (
                <Text key={i} size="sm" style={{ lineHeight: 1.4 }}>
                  {line}
                </Text>
              ))}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">
              No secondary ability text available.
            </Text>
          )}
        </div>

        <Text size="xs" c="dimmed">
          {isFree
            ? "The active player chose you: you must resolve this ability and it costs no command token. "
            : needsToken
              ? `Following costs 1 command token from your strategy pool${
                  poolTokens != null ? ` (you have ${poolTokens})` : ""
                }. `
              : "Following is optional. "}
          Players respond in turn order — the player to the left of the active
          player first, then clockwise.
          {window ? ` Remaining after you: ${Math.max(window.remaining - 1, 0)}.` : ""}
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="default"
            disabled={busy || isFree}
            leftSection={<IconHandStop size={16} />}
            onClick={() => decide(false)}
          >
            Don't follow
          </Button>
          <Button
            disabled={busy || cannotAfford}
            leftSection={<IconBolt size={16} />}
            onClick={() => decide(true)}
            title={cannotAfford ? "No command token in your strategy pool" : undefined}
          >
            Follow
          </Button>
        </Group>
      </Stack>
    </AppModal>
    </>
  );
}

export default SecondaryDecisionModal;

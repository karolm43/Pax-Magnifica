import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Switch, Text } from "@/ds";
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
import { getAbility } from "@/entities/lookup/abilities";
import { getAgenda } from "@/entities/lookup/agendas";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import {
  getPlayerDisplayName,
  type GameStatePlayer,
} from "./gameStatePlayers";
import { StrategyPrimaryStepModal } from "./StrategyPrimaryStepModal";
import { SECONDARY_MODE, SECONDARY_VIEWS } from "@/domains/strategy/cards";
import { DrawnActionCards } from "@/domains/strategy/cards/Politics";
import { PromptDock } from "@/domains/strategy/PromptDock";
import { fetchJson } from "@/api/fetchJson";
import { getBotApiUrl } from "@/api/auth/botApiUrl";
import type { PlayerHandData } from "@/shared/types/playerHand";

const POLITICS_INITIATIVE = 3;

/**
 * Nazwa komponentu, który zwalnia respondenta z żetonu (kontekst okna ``no_cost_why``:
 * ``"p1=abilities:master_of_trade;p2=promissory_notes:acq"``) — pełna nazwa z danych.
 */
function noCostSourceName(raw: unknown, playerId: string | null | undefined): string | null {
  if (!playerId) return null;
  const entry = (typeof raw === "string" ? raw : "")
    .split(";")
    .map((item) => item.split("="))
    .find(([pid]) => pid === playerId);
  const key = entry?.[1];
  if (!key) return null;
  const [category, id] = key.split(":");
  if (!id) return null;
  if (category === "abilities") return getAbility(id)?.name ?? null;
  if (category === "promissory_notes") return getPromissoryNoteData(id, {})?.displayName ?? null;
  if (category === "agendas") return getAgenda(id)?.name ?? null;
  return null;
}

/** Karty akcji na ręce gracza (lokalny tryb: operator widzi każdą rękę). */
async function fetchActionCards(gameId: string, playerId: string): Promise<string[]> {
  try {
    const hand = await fetchJson<PlayerHandData>(
      getBotApiUrl(`/game/${gameId}/hand?player=${encodeURIComponent(playerId)}`),
      "player hand",
    );
    return [...(hand.actionCards ?? [])];
  } catch {
    return [];
  }
}
import type { CardShell } from "@/domains/strategy/cards/types";
import { useStrategyPrompt, type PromptPlayer } from "@/domains/strategy/strategyPrompt";
import { useCanActAs } from "@/domains/network/useNetworkMe";
import { PHASE_WINDOW } from "@/hooks/useDecisionZone";

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
  // Kursor okna, dla którego respondent wybiera dane do „follow" (null = decyzja).
  const [composingCursor, setComposingCursor] = useState<number | null>(null);
  // Karty akcji dobrane przez „follow" (Politics) - pokazywane respondentowi po decyzji.
  const [drawn, setDrawn] = useState<{ name: string; cards: string[] } | null>(null);
  // Scepter of Emelpar: wydaj żeton z rezerwy zamiast z puli strategicznej (decyzja gracza).
  const [useScepter, setUseScepter] = useState(false);
  // Perfect Synthesis (Naaz-Rokha): przy pustej rezerwie żeton z wybranej puli arkusza.
  const [tokenPool, setTokenPool] = useState<string | null>(null);

  const window = gameState?.pendingWindow ?? null;
  const canActAs = useCanActAs();
  // Pokazujemy TYLKO dla okna secondary z czekającym respondentem. Pozostałe typy
  // okien (walka, reakcje) mają własne panele/modale — nie ten popup.
  const isSecondary =
    !!window &&
    window.windowType === "STRATEGY_SECONDARY" &&
    !window.isComplete &&
    !!window.currentResponderId &&
    // W sieci decyduje tylko respondent; reszta ma „Waiting for X" (TurnStatusChip).
    canActAs(window.currentResponderId) &&
    // Respondent po "follow" produkuje (Warfare): okno produkcji ma pierwszeństwo.
    !window.context?.await_production;

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

  const decide = (execute: boolean, payload: Record<string, unknown> = {}) => {
    const id = window?.currentResponderId;
    if (!id || busy) return;
    if (execute && useScepter && needsToken) payload = { ...payload, scepter: true };
    if (execute && sheetNeeded && tokenPool) payload = { ...payload, token_pool: tokenPool };
    setBusy(true);
    // Karty dobierające karty akcji (Politics): pokaż respondentowi, co dobrał - różnica
    // ręki przed/po (ręka jest prywatna, więc pytamy tylko o jego własną).
    const showDraws = execute && initiative === POLITICS_INITIATIVE;
    void (async () => {
      try {
        const before = showDraws ? await fetchActionCards(gameId, id) : [];
        await strategySecondary(id, execute, payload);
        if (showDraws) {
          const after = await fetchActionCards(gameId, id);
          const pool = [...before];
          const fresh = after.filter((card) => {
            const i = pool.indexOf(card);
            if (i >= 0) {
              pool.splice(i, 1);
              return false;
            }
            return true;
          });
          setDrawn({ name: responderName, cards: fresh });
        }
      } finally {
        setBusy(false);
      }
    })();
  };

  // Karty, których „follow" wymaga wyborów (np. Leadership: planety + rozkład żetonów),
  // pokazują własny widok po kliknięciu Follow; backend sygnalizuje to ``needs_input``.
  const { data: prompt } = useStrategyPrompt(
    isSecondary ? (window?.currentResponderId ?? null) : null,
    `${initiative ?? 0}:${window?.cursor ?? 0}`,
  );
  const InputView = initiative != null ? SECONDARY_VIEWS[initiative] : undefined;
  const needsInput =
    prompt?.kind === "secondary" && prompt.options.needs_input === true && !!InputView;
  const composing = needsInput && composingCursor === (window?.cursor ?? -1);
  const shell: CardShell = {
    hue,
    initiative: initiative ?? 0,
    title: cardName,
  };

  // Koszt follow: żeton ze strategy pool (window.context.cost = 1), chyba że respondent
  // został wskazany jako „free" (wtedy secondary jest DARMOWE i OBOWIĄZKOWE).
  const isFree = String(window?.context?.free ?? "").split(",").includes(
    window?.currentResponderId ?? "\0",
  );
  // Secondary bez żetonu, ale nieobowiązkowe (Masters of Trade, Acquiescence — RULES.md 62.6/62.7).
  const noCost = String(window?.context?.no_cost ?? "")
    .split(",")
    .includes(window?.currentResponderId ?? "\0");
  const needsToken = Number(window?.context?.cost ?? 0) > 0 && !isFree && !noCost;
  const noCostName = noCost
    ? noCostSourceName(window?.context?.no_cost_why, window?.currentResponderId)
    : null;
  const poolTokens = (responder as { strategicCC?: number } | undefined)?.strategicCC;
  // Perfect Synthesis (RULES.md 62.15): żeton z rezerwy zamiast z puli strategicznej; pusta
  // rezerwa = żeton z wybranej puli arkusza.
  const fromReinforcements = window?.context?.token_from === "reinforcements";
  const reinforcementTokens = (responder as { ccReinf?: number } | undefined)?.ccReinf;
  const sheetNeeded = needsToken && fromReinforcements && (reinforcementTokens ?? 1) < 1;
  // Scepter of Emelpar: gotowy relikt pozwala wydać żeton z rezerwy zamiast z puli.
  const scepterReady =
    needsToken &&
    !fromReinforcements &&
    ((responder as { relics?: string[] } | undefined)?.relics ?? []).includes("emelpar") &&
    !((responder as { exhaustedRelics?: string[] } | undefined)?.exhaustedRelics ?? []).includes(
      "emelpar",
    );
  const cannotAfford = fromReinforcements
    ? sheetNeeded && !tokenPool
    : needsToken && (poolTokens ?? 1) < 1 && !(scepterReady && useScepter);

  // Wybór na mapie (Construction): widok wyborów w nieblokującym doku zamiast modala.
  const secondaryMode = initiative != null ? SECONDARY_MODE[initiative] : undefined;
  const inDock = composing && secondaryMode === "dock";
  // Pełnoekranowe okno wyborów (drzewo technologii) rysuje się samo - bez modala.
  const inOverlay = composing && secondaryMode === "overlay";
  const inputView =
    composing && InputView && prompt ? (
      <InputView
        key={window?.cursor}
        prompt={prompt}
        shell={shell}
        responder={(responder as PromptPlayer | undefined) ?? undefined}
        players={playerData as unknown as PromptPlayer[]}
        busy={busy}
        submit={(payload) => decide(true, payload)}
        back={() => setComposingCursor(null)}
      />
    ) : null;

  return (
    <>
    <StrategyPrimaryStepModal />
    {inDock && inputView ? (
      <PromptDock label={`${cardName} - secondary`}>{inputView}</PromptDock>
    ) : null}
    {inOverlay && inputView ? inputView : null}
    <AppModal
      floating
      opened={drawn != null}
      onClose={() => setDrawn(null)}
      title="Action cards drawn"
      size={460}
    >
      <Stack gap="md">
        <Text size="sm">
          <b>{drawn?.name}</b> drew {drawn?.cards.length ?? 0} action card(s):
        </Text>
        <DrawnActionCards cards={drawn?.cards ?? []} />
        <Group justify="flex-end">
          <Button onClick={() => setDrawn(null)}>OK</Button>
        </Group>
      </Stack>
    </AppModal>
    <AppModal
      floating
      minimizable={`${cardName} - secondary`}
      opened={isSecondary && !inDock && !inOverlay}
      // Modal wymuszony: nie zamykamy go samodzielnie — zniknie, gdy backend domknie
      // okno (po decyzji ostatniego gracza). onClose to no-op (wymagany przez typ).
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      // Krok z widokiem karty ma własny nagłówek (PromptShell: karta + plakietka Secondary).
      title={inputView ? undefined : "Strategy Card — secondary ability"}
      size={composing ? 560 : 460}
    >
      {inputView ? (
        inputView
      ) : (
      <Stack gap="md" {...PHASE_WINDOW}>
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

        {noCost && !isFree ? (
          <Text size="sm" fw={600} style={{ color: hue }}>
            {noCostName ? <b>{noCostName}: </b> : null}
            you may follow for free — no command token is spent.
          </Text>
        ) : null}

        <Text size="xs" c="dimmed">
          {isFree
            ? "The active player chose you: you must resolve this ability and it costs no command token. "
            : needsToken && fromReinforcements
              ? `Perfect Synthesis: following costs 1 command token from your reinforcements${
                  reinforcementTokens != null ? ` (you have ${reinforcementTokens})` : ""
                }${sheetNeeded ? " - none left, so spend one from your command sheet" : ""}. `
              : needsToken
                ? `Following costs 1 command token from your strategy pool${
                    poolTokens != null ? ` (you have ${poolTokens})` : ""
                  }. `
                : "Following is optional. "}
          Players respond in turn order — the player to the left of the active
          player first, then clockwise.
          {window ? ` Remaining after you: ${Math.max(window.remaining - 1, 0)}.` : ""}
        </Text>

        {sheetNeeded && (
          <Group gap="xs" role="group" aria-label="Command sheet pool">
            {(
              [
                ["tactical", "Tactic pool"],
                ["fleet", "Fleet pool"],
                ["strategic", "Strategy pool"],
              ] as const
            ).map(([pool, label]) => (
              <Button
                key={pool}
                size="xs"
                variant={tokenPool === pool ? "filled" : "default"}
                aria-pressed={tokenPool === pool}
                onClick={() => setTokenPool(pool)}
              >
                {label}
              </Button>
            ))}
          </Group>
        )}

        {scepterReady && (
          <Switch
            checked={useScepter}
            onChange={(e) => setUseScepter(e.currentTarget.checked)}
            label="Exhaust Scepter of Emelpar to spend a token from your reinforcements instead"
          />
        )}

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
            onClick={() =>
              needsInput ? setComposingCursor(window?.cursor ?? 0) : decide(true)
            }
            title={
              cannotAfford
                ? sheetNeeded
                  ? "Choose the pool to spend a command token from"
                  : "No command token in your strategy pool"
                : undefined
            }
          >
            Follow
          </Button>
        </Group>
      </Stack>
      )}
    </AppModal>
    </>
  );
}

export default SecondaryDecisionModal;

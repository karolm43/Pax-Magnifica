import { useEffect, useState, type CSSProperties } from "react";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { useParams } from "react-router-dom";
import {
  IconBolt,
  IconHandStop,
  IconPlayerPlayFilled,
  IconPlayerTrackNextFilled,
  IconChevronsRight,
  IconInfoCircle,
  IconCards,
  IconSparkles,
  IconUserStar,
  IconFlask,
  IconDiamond,
  IconTarget,
  IconCrosshair,
  IconArrowsExchange,
  IconCompass,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import {
  useBoardEditor,
  useStrategyCards,
  type StrategyCardState,
} from "@/api/useBoardEditor";
import {
  collectComponentActions,
  KIND_LABEL,
  type ComponentActionChoice,
  type ComponentActionKind,
} from "./componentActions";
import {
  getStrategyCardById,
  getStrategyCardByInitiative,
} from "@/entities/lookup/strategyCards";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { DetailsCard, type DetailsCardColor } from "@/shared/ui/DetailsCard";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { useAppStore, useSettingsStore } from "@/state/appStore";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useHudMetric } from "@/hooks/useHudMetric";
import { useDeskPlayer } from "./useDeskPlayer";
import { ReactionSettings } from "./ReactionSettings";
import { TransactionModal } from "./TransactionModal";
import { ActionCardPlayModal } from "./ActionCardPlayModal";
import { TechnologyUseModal } from "./TechnologyUseModal";
import { LegendaryUseModal } from "./LegendaryUseModal";
import { FactionComponentUseModal } from "./FactionComponentUseModal";
import { useTechnologyAbilities } from "@/api/useTechnology";
import { useForgeOptions } from "@/api/useRelics";
import { ExpeditionModal } from "@/domains/thunders-edge/ExpeditionModal";
import { ComponentInfoButton, type ComponentKind } from "@/domains/cards/components/ComponentInfo";
import styles from "./TurnControls.module.css";

/** Rodzaj źródła akcji → rodzaj komponentu do opisu pod ⓘ (zdolność frakcji/legendarna: brak). */
const INFO_KIND: Partial<Record<ComponentActionKind, ComponentKind>> = {
  leader: "leader",
  technology: "tech",
  relic: "relic",
  breakthrough: "breakthrough",
};

/* Initiative → wariant koloru DetailsCard (tooltip treści) — jak w StrategyCardTable. */
const SC_DETAILS_COLOR: Record<number, DetailsCardColor> = {
  1: "red",
  2: "orange",
  3: "yellow",
  4: "green",
  5: "teal",
  6: "cyan",
  7: "blue",
  8: "violet",
};

/* Ikona wiersza listy akcji komponentu wg rodzaju źródła (karta/zdolność/lider/…). */
const COMPONENT_KIND_ICON: Record<
  ComponentActionKind,
  typeof IconCards
> = {
  "action-card": IconCards,
  ability: IconSparkles,
  leader: IconUserStar,
  technology: IconFlask,
  relic: IconDiamond,
  legendary: IconDiamond,
  breakthrough: IconSparkles,
};

/* Initiative → barwa karty (fallback glow, gdy brak colourHexCode w danych). */
const SC_HUE: Record<number, string> = {
  1: "#ec1c24",
  2: "#f69421",
  3: "#fff200",
  4: "#39b54a",
  5: "#00a99d",
  6: "#008ed4",
  7: "#15489f",
  8: "#752b90",
};

/**
 * Sterowanie turą aktywnego gracza — PRZYPIĘTE na mapie, ODDZIELNE od ręki kart.
 *
 * Dwie osobne strefy „jak rzeczy przed graczem":
 *  - .cardZone (lewy dół): karta strategii jako DUŻY obrazek PNG, lekko przechylona
 *    (leży na stole), prostuje się i unosi na hover; zagranie = nakładka „Play"
 *    pojawiająca się na hover (NIE osobny przycisk);
 *  - .actionZone (prawy dół): elegancki panel akcji tury (faza + gracz w nagłówku,
 *    duże przyciski z ikonami i poświatą) — Pass / Component action / End turn /
 *    Next phase. „Component action" (RULES.md 31.8) otwiera modal „co zagrałeś?"
 *    (karty akcji z oknem „Action" + opcja dla reliktu/techu/zdolności); na razie
 *    tylko rejestruje akcję tury, bez mechaniki konkretnego komponentu.
 *
 * Render tylko w fazie akcji/strategii i gdy jest aktywny gracz (inaczej null).
 */
export function TurnControls() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: webData } = usePlayerData(gameId);
  const { data: cards } = useStrategyCards();
  const {
    playStrategyCard,
    passTurn,
    endTurn,
    playComponentAction,
    forgeRelic,
    nextPlayer,
    phaseStep,
    nextPhase,
    skipPhase,
    skipPlayer,
    nextRound,
    activateSystem,
  } = useBoardEditor();
  // God-Mode (Settings → Admin / testing): pokaż przycisk przeskoku fazy.
  // Gra sieciowa: God-Mode tylko dla hosta (backend i tak odrzuca innych — RULES.md 44.2).
  const { data: networkMe } = useNetworkMe();
  const skipPhasesEnabled =
    useSettingsStore((s) => s.settings.skipPhases) && (!networkMe?.network || networkMe.host);
  const [busy, setBusy] = useState(false);
  // Oba boxy (karta strategii i panel przycisków) są PRZESUWALNE; pozycje zapisują
  // się w localStorage, dwuklik na uchwycie resetuje do domyślnej.
  const cardDrag = useDraggablePanel("turnControls.cardZone.pos");
  const actionDrag = useDraggablePanel("turnControls.actionZone.pos");
  // Slot HUD „prawy dół": ręka (dół środek) kończy się przed kartą strategii.
  useHudMetric(
    cardDrag.el,
    "--hud-right-w",
    (rect) => window.innerWidth - rect.left,
    !cardDrag.isMoved,
  );
  // Slot HUD „prawy dół” od góry: centrum decyzji (prawa góra) kończy się NAD panelem akcji i
  // kartą strategii, zamiast chować pod nimi swoje przyciski.
  useHudMetric(actionDrag.el, "--hud-action-top", (rect) => rect.top, !actionDrag.isMoved);
  useHudMetric(cardDrag.el, "--hud-card-top", (rect) => rect.top, !cardDrag.isMoved);
  // Tryb aktywacji systemu (akcja taktyczna) — współdzielony ze store. Klik przycisku
  // włącza tryb „wskaż system", a klik w kafelek na mapie uruchamia aktywację (ten sam
  // potok, który odbiera panel taktyczny). Blok A: wygodne wejście z prawego dolnego rogu.
  const activateMode = useAppStore((s) => s.activateMode);
  const toggleActivateMode = useAppStore((s) => s.toggleActivateMode);
  const activateRequest = useAppStore((s) => s.activateRequest);
  const clearActivateRequest = useAppStore((s) => s.clearActivateRequest);
  // Krok potwierdzenia pasa: pas jest „jak akcja" i NIE kończy tury — gracz łatwo
  // to przeoczy, więc najpierw pytamy „na pewno?", a po pasie wołamy o oddanie tury.
  const [confirmingPass, setConfirmingPass] = useState(false);
  // Modal akcji komponentu: „co zagrałeś?". Wybór to tylko adnotacja (RULES.md 31.8).
  const [componentOpen, setComponentOpen] = useState(false);
  // Karta akcji wybrana na liście akcji komponentu - otwiera formularz zagrania (RULES.md 53).
  const [playingCard, setPlayingCard] = useState<ComponentActionChoice | null>(null);
  // Technologia wybrana do użycia (akcja „ACTION:" albo zdolność poza akcją) - RULES.md 57.
  const [usingTech, setUsingTech] = useState<{ id: string; name: string } | null>(null);
  // Karta zdolności legendarnej planety z „ACTION:" wybrana do użycia (RULES.md 60.3).
  const [usingLegendary, setUsingLegendary] = useState<{ id: string; name: string } | null>(null);
  // Lider / zdolność frakcji / przełom (RULES.md 61.3): formularz silnika + koszt użycia.
  const [usingFaction, setUsingFaction] = useState<{
    kind: "leader" | "ability" | "breakthrough" | "technology";
    id: string;
    name: string;
  } | null>(null);
  // Okno transakcji (RULES.md 47): wymiana z sąsiadem + żetony obietnic.
  const [transactionOpen, setTransactionOpen] = useState(false);
  // Ekspedycja Thunder's Edge (RULES.md 50): zajęcie plastra na koniec tury.
  const [expeditionOpen, setExpeditionOpen] = useState(false);

  // Pulpit widoczny CAŁY CZAS — pokazuje „gracza pulpitu" (aktywny → mówca →
  // pierwszy). Zwraca null tylko, gdy nie ma żadnego posadzonego gracza.
  const active = useDeskPlayer();

  // Odbiór kliknięcia w kafelek w trybie aktywacji: gdy store zgłosi pozycję
  // (``activateRequest``), aktywujemy ten system, czyścimy żądanie i wyłączamy tryb.
  // Efekt żyje TU (TurnControls jest zamontowany przez całą fazę akcji), niezależnie
  // od tego, którą zakładkę pokazuje GameStatePanel — dzięki temu przycisk „Activate
  // system" z rogu działa zawsze (Blok A). Hook wołany ZAWSZE (przed early-return).
  useEffect(() => {
    if (!activateRequest) return;
    const position = activateRequest;
    clearActivateRequest();
    if (activateMode) toggleActivateMode();
    void activateSystem(position);
  }, [
    activateRequest,
    activateMode,
    activateSystem,
    clearActivateRequest,
    toggleActivateMode,
  ]);

  if (!active) return null;

  const phase = gameState?.phase ?? "unknown";
  const isStrategy = phase === "strategy";
  // Pass / End turn mają sens tylko w fazie akcji i dla GRACZA, którego jest TURA
  // (nie dla mówcy-fallbacku między turami). Używamy ``activeTurnPlayer`` (czyja
  // tura, nie gaśnie przy passed), nie ``active.active`` — ten ostatni gaśnie dla
  // spasowanego gracza, przez co przyciski znikały, gdy gracz zagrał kartę i
  // spasował, a okno secondary wciąż trwało (RULES.md 31.4/31.6).
  const isTurnPlayer =
    gameState?.activeTurnPlayer != null &&
    active.color === gameState.activeTurnPlayer;
  const isAction =
    phase === "action" && (isTurnPlayer || active.active === true);
  // Dopóki trwa OTWARTE OKNO czasowe (np. secondary karty strategii), aktywny gracz
  // NIE może zakończyć tury — wszyscy inni muszą najpierw zdecydować (RULES.md 31.6).
  // Blokada w UI (czytelna) + twarda walidacja w backendzie (end_turn → 422).
  const windowOpen = gameState?.pendingWindow != null;
  // Status: „Next player" kończy krok gracza (/turn/phase-step). Agenda: „Pass"
  // kończy część gracza (/turn/phase-step), „Next player" tylko przewija (/turn/
  // next-player). „Next phase" u mówcy pojawia się wg ``canAdvancePhase``.
  const isStatus = phase.startsWith("status");
  // Zainicjowana faza statusu (RULES.md 41) prowadzi panel kroków (StatusPhasePanel);
  // stary przycisk „Next player" zostaje tylko dla statusu wprowadzonego God-Mode.
  const statusInSteps = isStatus && gameState?.status != null;
  const isAgenda = phase.startsWith("agenda");
  // Zainicjowana faza agendy (RULES.md 51) prowadzi okno Rady (AgendaOverlay): pasy i
  // przewijanie graczy znikają, koniec fazy odblokowuje się po obu agendach.
  const agendaInSteps = isAgenda && gameState?.agendaPhase != null;
  const isSpeaker =
    gameState?.speaker != null && active.color === gameState.speaker;
  // „Next phase" widzi ZAWSZE mówca (w każdej głównej fazie). Gdy przejście nie jest
  // jeszcze dozwolone (np. nie wszyscy wybrali/spasowali), klik zwróci 422 i panel
  // pokaże komunikat — zgodnie z decyzją „komunikat przy niedozwolonej akcji"
  // (2026-11, uwaga użytkownika). Brak twardego ukrywania przycisku.
  const showNextPhase = isAgenda || isSpeaker;
  // Czytelna etykieta fazy w nagłówku pulpitu.
  const phaseLabel = phase.startsWith("agenda")
    ? "Agenda phase"
    : phase.startsWith("status")
      ? "Status phase"
      : phase === "action"
        ? "Action phase"
        : phase === "strategy"
          ? "Strategy phase"
          : "Turn";
  const myCards = (cards ?? []).filter((c) => c.picked_by === active.discordId);
  const hasCard = myCards.length > 0;
  const played = myCards.some((c) => c.exhausted);
  const canPass = !hasCard || played;
  const activeName = getPlayerFactionDisplayName(active);
  // Czy gracz JUŻ spasował w tej fazie akcji. Pas ≠ koniec tury (RULES.md 31.5):
  // po pasie trzeba jeszcze oddać turę przez End turn.
  const hasPassed = active.passed === true;
  // Czy gracz wykonał AKCJĘ w tej turze (strategiczna/taktyczna/komponentu —
  // RULES.md 31.7). End turn jest możliwy dopiero po akcji LUB pasie.
  const tookAction = active.tookActionThisTurn === true;
  // End turn wolno dać, gdy gracz zrobił akcję albo spasował, i nie trwa okno.
  const canEndTurn = isAction && (tookAction || hasPassed) && !windowOpen;
  // End turn „woła o uwagę" (nudge), gdy jest już możliwy do kliknięcia — głównie po
  // pasie, ale też po akcji, gdy gracz może zapomnieć oddać turę.
  const nudgeEndTurn = canEndTurn;

  // Jedna zwięzła podpowiedź (najważniejsza w danym stanie) zamiast stosu chipów.
  // ``ok`` = zielony wariant („zrób następny krok"), inaczej ostrzegawczy.
  // Akcja komponentu (RULES.md 31.8) — dostępna jak każda akcja tury: w fazie akcji,
  // gdy gracz jeszcze nie działał ani nie spasował, i nie trwa okno czasowe.
  // Dopóki zostały akcje (Fleet Logistics = 2 na turę), przyciski akcji są aktywne mimo
  // tookActionThisTurn (to ono odblokowuje End turn). Brak pola = jedna akcja (stare migawki).
  const hasActionLeft = active.actionsLeft != null ? active.actionsLeft > 0 : !tookAction;
  const canComponentAction = isAction && hasActionLeft && !hasPassed && !windowOpen;
  // Ekspedycja: koniec tury (po akcji lub pasie), bez otwartego okna; wolny plaster żetonu.
  const hasFreeExpedition = Object.values(webData?.expeditions ?? {}).some(
    (slice) => slice.completedBy == null,
  );
  const canExpedition = isAction && (tookAction || hasPassed) && !windowOpen;
  // Akcja strategiczna to TEŻ jedna z akcji tury (RULES.md 30.3) — te same warunki.
  const canStrategicAction = canComponentAction;
  // Akcja TAKTYCZNA (RULES.md 31.7 / R_tactical_action) — aktywacja systemu. Dostępna
  // jak każda akcja tury: faza akcji, gracz jeszcze nie działał ani nie spasował, brak
  // otwartego okna. Trwająca akcja (activeSystem != null) → zamiast przycisku pokazujemy
  // wskaźnik „akcja w toku" (kroki są w panelu taktycznym). Blok A.
  const activeSystem = gameState?.activeSystem ?? null;
  const inTacticalAction = activeSystem != null;

  let turnHint: { ok: boolean; text: string } | null = null;
  if (isAction) {
    if (activateMode && !inTacticalAction) {
      turnHint = { ok: true, text: "Click a system on the map to activate it." };
    } else if (windowOpen) {
      turnHint = { ok: false, text: "Waiting for players to decide on the secondary." };
    } else if (canEndTurn) {
      turnHint = {
        ok: true,
        text: hasPassed
          ? "You passed — press End turn to hand over."
          : "Action done — press End turn to hand over.",
      };
    } else if (!canPass && !hasPassed) {
      turnHint = { ok: false, text: "Play your Strategy Card first to pass." };
    } else if (!tookAction && !hasPassed) {
      turnHint = { ok: false, text: "Take an action or pass, then end your turn." };
    }
  }
  const canActivate =
    isAction && hasActionLeft && !hasPassed && !windowOpen && !inTacticalAction;
  // Wszystkie KOMPONENTY Z AKCJĄ („Action") dostępne aktywnemu graczowi: karty akcji
  // z ręki + zdolności frakcji + liderzy + techy + relikty, które posiada. Dane z
  // web-data (``playerData``) + ręki — zero hardkodowania (patrz componentActions.ts).
  const activePlayerData = webData?.playerData?.find(
    (p) => p.color === active.color,
  );
  // Stół transakcji (RULES.md 47.1b): siada gracz PRZY EKRANIE (sieć: ja; lokalnie: pulpit).
  const tradingPlayerData =
    (networkMe?.network
      ? webData?.playerData?.find((p) => p.discordId === networkMe.player_id)
      : undefined) ?? activePlayerData;
  const { data: freeAbilities } = useTechnologyAbilities(
    active.discordId ?? null,
    componentOpen,
  );
  // Fragmenty reliktów (RULES.md 59.7): „Purge 3 fragments -> relic" to akcja komponentu.
  // Silnik liczy legalne zestawy (typ, dżokery Unknown, tura); pokazujemy typy, które gracz ma.
  const { data: forgeOptions } = useForgeOptions(
    active.discordId ?? null,
    componentOpen,
  );
  // Karty akcji z ręki NIE są na liście (U4/Z9): zagrywa się je przeciągnięciem z ręki.
  const componentChoices = collectComponentActions(activePlayerData, []);

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn().finally(() => setBusy(false));
  };

  return (
    <>
      {/* STREFA KARTY — karta w SLOCIE (wyznaczone miejsce przy stole). Slot ma
          stały kształt karty i jest widoczny także, gdy karty nie ma (pusty zarys). */}
      <div
        className={styles.cardZone}
        aria-label="Your Strategy Card"
        ref={cardDrag.ref}
        style={cardDrag.style}
        data-draggable-panel
        data-dragging={cardDrag.isDragging || undefined}
      >
        <div
          className={styles.dragGrip}
          onPointerDown={cardDrag.onHandlePointerDown}
          onDoubleClick={cardDrag.reset}
          title="Drag to move · double-click resets position"
        >
          <span aria-hidden="true" />
        </div>
        <div className={styles.cards}>
          {hasCard ? (
            myCards.map((card, i) => (
              <div key={card.initiative} className={styles.slot} data-filled>
                <StrategyCardImage
                  card={card}
                  index={i}
                  canPlay={canStrategicAction && !card.exhausted}
                  busy={busy}
                  onPlay={() =>
                    run(() => playStrategyCard(active.discordId, card.initiative))
                  }
                />
              </div>
            ))
          ) : (
            <div className={styles.slot}>
              <div className={styles.slotEmpty}>
                <IconBolt size={18} aria-hidden="true" />
                <span>
                  {isStrategy ? "Pick a Strategy Card" : "Strategy Card"}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* STREFA PRZYCISKÓW (prawy dół) — elegancki panel akcji tury. */}
      <div
        className={styles.actionZone}
        aria-label="Turn actions"
        ref={actionDrag.ref}
        style={actionDrag.style}
        data-draggable-panel
        data-dragging={actionDrag.isDragging || undefined}
      >
        <header
          className={styles.actionHead}
          data-grab
          onPointerDown={actionDrag.onHandlePointerDown}
          onDoubleClick={actionDrag.reset}
          title="Drag to move · double-click resets position"
        >
          {active.faction && (
            <CircularFactionIcon faction={active.faction} size={22} />
          )}
          <span className={styles.actionHeadText}>
            <small className={styles.actionPhase}>{phaseLabel}</small>
            <b className={styles.actionWho}>{activeName}</b>
          </span>
          {/* Ustawienia reakcji poza turą - wszystkie w jednym miejscu (RULES.md 54.11-54.12). */}
          <ReactionSettings player={active} quickWindows={gameState?.quickReactionWindows} />
        </header>

        <div className={styles.actionBtns}>
          {/* Faza AKCJI: Pass (po akcji strategicznej) + End turn. Pas otwiera MODAL
              potwierdzenia (bez przerzucania layoutu panelu — RULES.md 31.5). End turn
              możliwy dopiero po akcji lub pasie (RULES.md 31.7). */}
          {isAction && (
            <>
              {/* Akcja TAKTYCZNA — aktywacja systemu (główna akcja fazy akcji). Gdy akcja
                  już trwa, pokazujemy wskaźnik „w toku" (kroki w panelu taktycznym).
                  Inaczej: toggle trybu „wskaż system" (klik w kafelek aktywuje). */}
              {inTacticalAction ? (
                <div
                  className={styles.tacticalLive}
                  title="Tactical action in progress — resolve the steps in the tactical panel"
                >
                  <IconCrosshair size={16} aria-hidden="true" />
                  <span>Tactical action in progress</span>
                </div>
              ) : (
                <button
                  type="button"
                  className={styles.activate}
                  style={{ "--d": "0ms" } as CSSProperties}
                  data-on={activateMode || undefined}
                  disabled={busy || !canActivate}
                  onClick={() => toggleActivateMode()}
                  title={
                    windowOpen
                      ? "Wait — every player must decide on the secondary first"
                      : hasPassed
                        ? "You already passed this action phase"
                        : !hasActionLeft
                          ? "You already acted this turn — End turn instead"
                          : activateMode
                            ? "Now click a system on the map to activate it"
                            : "Activate a system (tactical action): click, then pick a system"
                  }
                >
                  <IconTarget size={16} aria-hidden="true" />
                  <span>
                    {activateMode ? "Pick a system on the map…" : "Activate system"}
                  </span>
                </button>
              )}
              <button
                type="button"
                className={`${styles.pass} ${styles.tile}`}
                style={{ "--d": "60ms" } as CSSProperties}
                disabled={busy || hasPassed || tookAction || !canPass}
                onClick={() => setConfirmingPass(true)}
                title={
                  hasPassed
                    ? "You already passed — hand over with End turn"
                    : tookAction
                      ? "You already acted this turn — End turn instead"
                      : canPass
                        ? "Pass, then End turn to hand over"
                        : "Play your Strategy Card before passing."
                }
              >
                <IconHandStop size={16} aria-hidden="true" />
                <span>Pass</span>
              </button>
              {/* Akcja komponentu (RULES.md 31.8) — karta akcji „Action", relikt,
                  tech, zdolność. Otwiera modal „co zagrałeś?"; na razie tylko
                  rejestruje akcję (bez mechaniki komponentu). */}
              <button
                type="button"
                className={`${styles.component} ${styles.tile}`}
                style={{ "--d": "120ms" } as CSSProperties}
                disabled={busy || !canComponentAction}
                onClick={() => setComponentOpen(true)}
                title={
                  windowOpen
                    ? "Wait — every player must decide on the secondary first"
                    : hasPassed
                      ? "You already passed this action phase"
                      : !hasActionLeft
                        ? "You already acted this turn — End turn instead"
                        : "Play a component ability (action card, relic, tech…)"
                }
              >
                <IconSparkles size={16} aria-hidden="true" />
                <span>Component</span>
              </button>
              {/* Transakcja z sąsiadem (RULES.md 47) — NIE jest akcją tury: wolno ją
                  rozstrzygnąć w dowolnym momencie tury (także po akcji/pasie i w
                  trakcie walki/okna), więc przycisk nie zależy od took_action/passed. */}
              <button
                type="button"
                className={`${styles.transaction} ${styles.tile}`}
                style={{ "--d": "150ms" } as CSSProperties}
                disabled={busy}
                onClick={() => setTransactionOpen(true)}
                title="Sit down at the trading table: a transaction with a neighbor or debt tokens with anyone"
              >
                <IconArrowsExchange size={16} aria-hidden="true" />
                <span>Transaction</span>
              </button>
              <button
                type="button"
                className={styles.endTurn}
                style={{ "--d": "180ms" } as CSSProperties}
                data-nudge={nudgeEndTurn ? "true" : undefined}
                disabled={busy || !canEndTurn}
                onClick={() => run(() => endTurn())}
                title={
                  windowOpen
                    ? "Wait — every player must decide on the secondary first"
                    : inTacticalAction
                      ? "End the tactical action and hand over (blocked while a combat or invasion is unresolved)"
                      : hasPassed
                        ? "You passed — end your turn to hand over"
                        : tookAction
                          ? "End your turn to hand over"
                          : "Take an action or pass before ending your turn"
                }
              >
                <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
                <span>End turn</span>
              </button>
              {/* Ekspedycja Thunder's Edge (RULES.md 50) - NA KONIEC tury (po akcji lub pasie),
                  jeden plaster na turę. Pod End turn; widoczna, dopóki któryś plaster jest wolny. */}
              {hasFreeExpedition && (
                <button
                  type="button"
                  className={styles.expedition}
                  style={{ "--d": "210ms" } as CSSProperties}
                  disabled={busy || !canExpedition}
                  onClick={() => setExpeditionOpen(true)}
                  title={
                    windowOpen
                      ? "Wait — every player must decide on the secondary first"
                      : tookAction || hasPassed
                        ? "Claim a slice of the expedition token (end of your turn, one per turn)"
                        : "An expedition is done at the END of your turn — take an action or pass first"
                  }
                >
                  <IconCompass size={16} aria-hidden="true" />
                  <span>Expedition</span>
                </button>
              )}
            </>
          )}

          {/* Faza STATUS: „Next player" KOŃCZY krok gracza (passed=True) i przesuwa
              dalej — po komplecie kroków mówca dostaje „Next phase". Wołamy BEZ
              player_id: backend adresuje swojego ``active_player_id`` (unikamy
              rozjazdu „gracza pulpitu" useDeskPlayer z realnym aktywnym — BUG 1). */}
          {isStatus && !statusInSteps && (
            <button
              type="button"
              className={styles.endTurn}
              style={{ "--d": "0ms" } as CSSProperties}
              disabled={busy}
              onClick={() => run(() => phaseStep())}
              title="Finish your Status step and pass to the next player"
            >
              <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
              <span>Next player</span>
            </button>
          )}

          {/* Faza AGENDA: „Pass" KOŃCZY część gracza (reakcja/głos), „Next player"
              tylko przewija wskaźnik bez kończenia kogokolwiek. Oba BEZ player_id —
              backend adresuje swojego aktywnego gracza. */}
          {isAgenda && !agendaInSteps && (
            <>
              <button
                type="button"
                className={styles.pass}
                style={{ "--d": "0ms" } as CSSProperties}
                disabled={busy}
                onClick={() => run(() => phaseStep())}
                title="Pass — decline your reaction/vote this agenda"
              >
                <IconHandStop size={16} aria-hidden="true" />
                <span>Pass</span>
              </button>
              <button
                type="button"
                className={styles.endTurn}
                style={{ "--d": "60ms" } as CSSProperties}
                disabled={busy}
                onClick={() => run(() => nextPlayer())}
                title="Pass the floor to the next player (no pass recorded)"
              >
                <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
                <span>Next player</span>
              </button>
            </>
          )}

          {/* Faza AGENDA: transakcje z KAŻDYM graczem przy każdej agendzie (RULES.md 47.5) -
              ten sam stół co w fazie akcji (też z okna Rady). */}
          {isAgenda && (
            <button
              type="button"
              className={`${styles.transaction} ${styles.tile}`}
              style={{ "--d": "90ms" } as CSSProperties}
              disabled={busy}
              onClick={() => setTransactionOpen(true)}
              title="Trade with any player: one transaction with each player during each agenda"
            >
              <IconArrowsExchange size={16} aria-hidden="true" />
              <span>Transaction</span>
            </button>
          )}

          {/* Przejście fazy OGŁASZA MÓWCA, i to tylko gdy wolno (``showNextPhase``):
              akcja/status po komplecie pasów/kroków; strategia po pełnym wyborze.
              PO AGENDZIE = nowa runda (runda +1, reset pasów, TG na niewybranych
              kartach) — wołamy /round/next zamiast /phase/next. */}
          {showNextPhase && (
            <button
              type="button"
              className={styles.nextPhase}
              style={{ "--d": isAction ? "120ms" : "60ms" } as CSSProperties}
              disabled={
                busy ||
                ((statusInSteps || agendaInSteps) &&
                  gameState?.canAdvancePhase !== true)
              }
              onClick={() =>
                run(isAgenda && !agendaInSteps ? nextRound : nextPhase)
              }
              title={
                agendaInSteps
                  ? gameState?.canAdvancePhase
                    ? "End the agenda phase and start the next round"
                    : "Resolve both agendas in the Galactic Council first"
                  : isAgenda
                  ? "End the agenda phase and start the next round"
                  : statusInSteps
                    ? gameState?.canAdvancePhase
                      ? "Return the Strategy Cards and finish the status phase"
                      : "Finish the status steps first (score objectives, redistribute tokens)"
                    : "Advance to the next phase"
              }
            >
              <IconChevronsRight size={16} aria-hidden="true" />
              <span>{isAgenda ? "Next round" : "Next phase"}</span>
            </button>
          )}

          {/* God-Mode (testy): przeskok fazy z pominięciem bram/okien/wyboru kart. */}
          {skipPhasesEnabled && (
            <button
              type="button"
              className={styles.nextPhase}
              disabled={busy}
              onClick={() => run(skipPhase)}
              title="God-Mode: skip to the next phase, ignoring passes, windows and card picks"
            >
              <IconChevronsRight size={16} aria-hidden="true" />
              <span>Skip phase</span>
            </button>
          )}

          {/* God-Mode (testy): tura następnego gracza bez akcji/pasa — szybkie
              przełączanie między graczami (tylko faza akcji). */}
          {skipPhasesEnabled && isAction && (
            <button
              type="button"
              className={styles.nextPhase}
              disabled={busy}
              onClick={() => run(skipPlayer)}
              title="God-Mode: hand the turn to the next player without taking an action or passing"
            >
              <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
              <span>Skip player</span>
            </button>
          )}
        </div>

        {/* Slot podpowiedzi ma STAŁĄ wysokość w fazie akcji - pojawienie się/zniknięcie
            tekstu nie zmienia rozmiaru panelu (koniec z „skakaniem"). */}
        {isAction && (
          <div className={styles.hintSlot}>
            {turnHint && (
              <p className={turnHint.ok ? styles.hintPassed : styles.hint}>
                <IconInfoCircle size={13} aria-hidden="true" />
                <span>{turnHint.text}</span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* MODAL potwierdzenia pasa — osobny overlay, żeby panel akcji NIE zmieniał
          rozmiaru (spójny, stabilny UI). Pas jest „jak akcja", ale nie kończy tury. */}
      <AppModal
        opened={confirmingPass}
        onClose={() => setConfirmingPass(false)}
        title="Pass this round?"
        size={420}
      >
        <Stack gap="md">
          <Text size="sm">
            Passing ends your turns for this Action Phase. You can still resolve
            other players' strategy card secondaries. You still have to hand over
            this turn with <b>End turn</b> afterwards.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button
              variant="default"
              disabled={busy}
              onClick={() => setConfirmingPass(false)}
            >
              Cancel
            </Button>
            <Button
              disabled={busy}
              leftSection={<IconHandStop size={16} />}
              onClick={() =>
                run(() => passTurn().finally(() => setConfirmingPass(false)))
              }
            >
              Yes, pass
            </Button>
          </Group>
        </Stack>
      </AppModal>

      {usingTech && active.discordId && (
        <TechnologyUseModal
          key={usingTech.id}
          techId={usingTech.id}
          techName={usingTech.name}
          playerId={active.discordId}
          onClose={() => setUsingTech(null)}
          onDone={() => setUsingTech(null)}
        />
      )}

      {usingFaction && active.discordId && (
        <FactionComponentUseModal
          key={`${usingFaction.kind}:${usingFaction.id}`}
          kind={usingFaction.kind}
          componentId={usingFaction.id}
          name={usingFaction.name}
          playerId={active.discordId}
          onClose={() => setUsingFaction(null)}
          onDone={() => setUsingFaction(null)}
        />
      )}
      {usingLegendary && active.discordId && (
        <LegendaryUseModal
          key={usingLegendary.id}
          planetId={usingLegendary.id}
          abilityName={usingLegendary.name}
          playerId={active.discordId}
          onClose={() => setUsingLegendary(null)}
          onDone={() => setUsingLegendary(null)}
        />
      )}

      {playingCard && active.discordId && (
        <ActionCardPlayModal
          key={`${playingCard.kind}:${playingCard.id}`}
          kind={playingCard.kind === "relic" ? "relic" : "card"}
          cardId={playingCard.id}
          cardName={playingCard.name}
          playerId={active.discordId}
          onClose={() => setPlayingCard(null)}
          onPlayed={() => setPlayingCard(null)}
        />
      )}

      {expeditionOpen && (
        <ExpeditionModal
          opened
          onClose={() => setExpeditionOpen(false)}
          gameId={gameId}
          playerId={active.discordId ?? null}
        />
      )}

      {/* MODAL transakcji (RULES.md 47.1b) — montowany tylko, gdy otwarty, by hooki ręki
          (usePlayerHand) nie odpytywały backendu przez cały czas. Gracz = ten przy ekranie
          (do stołu może usiąść każda strona); wpis ``playerData`` niesie stan posiadania. */}
      {transactionOpen && tradingPlayerData && (
        <TransactionModal
          opened
          onClose={() => setTransactionOpen(false)}
          gameId={gameId}
          me={tradingPlayerData}
          players={(webData?.playerData ?? []).filter(
            (p) => p.faction && p.faction !== "neutral",
          )}
        />
      )}

      {/* MODAL akcji komponentu — „co zagrałeś?". Lista = karty akcji z oknem
          „Action" z ręki + opcja dla źródeł nie-kartowych (relikt/tech/zdolność).
          Wybór to tylko ADNOTACJA (component_id); efekt = oznaczenie akcji w turze
          (mechanika konkretnego komponentu dojdzie później — RULES.md 31.8). */}
      <AppModal
        floating
        opened={componentOpen}
        onClose={() => setComponentOpen(false)}
        title="Play a component action"
        size={440}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Pick what you're playing. Components open a form where you make the choices and
            the engine applies the effect. Action cards are played by dragging them from your
            hand.
          </Text>

          <div className={styles.compList} role="list">
            {componentChoices.map((choice) => {
              const Icon = COMPONENT_KIND_ICON[choice.kind];
              const infoKind = INFO_KIND[choice.kind];
              return (
                <div key={`${choice.kind}:${choice.id}`} className={styles.compRow}>
                <button
                  type="button"
                  role="listitem"
                  className={styles.compItem}
                  disabled={busy}
                  onClick={() => {
                    // Karta akcji: formularz wyborów, efekt stosuje silnik (RULES.md 53).
                    // Relikt z „ACTION:" (RULES.md 59): ten sam formularz, relikt zostaje u gracza.
                    if (choice.kind === "action-card" || choice.kind === "relic") {
                      setComponentOpen(false);
                      setPlayingCard(choice);
                      return;
                    }
                    // Legendarna planeta (np. The Nucleus): formularz wyborów, silnik stosuje efekt.
                    if (choice.kind === "legendary") {
                      setComponentOpen(false);
                      setUsingLegendary({ id: choice.id, name: choice.name });
                      return;
                    }
                    // Lider / zdolność frakcji / przełom: formularz, koszt płaci silnik.
                    if (
                      choice.kind === "leader" ||
                      choice.kind === "ability" ||
                      choice.kind === "breakthrough"
                    ) {
                      setComponentOpen(false);
                      setUsingFaction({ kind: choice.kind, id: choice.id, name: choice.name });
                      return;
                    }
                    // Technologia: gracz wybiera cele w formularzu, silnik stosuje efekt.
                    if (choice.kind === "technology") {
                      setComponentOpen(false);
                      setUsingTech({ id: choice.id, name: choice.name });
                      return;
                    }
                    run(() =>
                      playComponentAction(active.discordId, choice.id).finally(
                        () => setComponentOpen(false),
                      ),
                    );
                  }}
                >
                  <Icon size={17} aria-hidden="true" />
                  <span className={styles.compItemName}>{choice.name}</span>
                  <small className={styles.compItemTag}>
                    {KIND_LABEL[choice.kind]}
                  </small>
                </button>
                {infoKind && (
                  <ComponentInfoButton
                    componentRef={{ kind: infoKind, id: choice.id }}
                    name={choice.name}
                  />
                )}
                </div>
              );
            })}

            {/* Fragmenty reliktów -> relikt (RULES.md 59.7). Nieaktywne z powodem w podpowiedzi,
                gdy zestaw nie jest legalny (za mało fragmentów itd.). */}
            {(forgeOptions ?? [])
              .filter((opt) => opt.owned + opt.wildcards > 0)
              .map((opt) => {
                const ready = opt.reason === null && opt.fragments.length > 0;
                return (
                  <button
                    key={`fragments:${opt.kind}`}
                    type="button"
                    role="listitem"
                    className={styles.compItem}
                    disabled={busy || !ready}
                    title={
                      opt.reason ??
                      (opt.deckEmpty
                        ? "The relic deck is empty - you purge the fragments without gaining a relic."
                        : undefined)
                    }
                    onClick={() =>
                      run(async () => {
                        try {
                          await forgeRelic(active.discordId ?? "", opt.fragments);
                        } catch {
                          // powód 422 pokazuje baner (postRaw)
                        } finally {
                          setComponentOpen(false);
                        }
                      })
                    }
                  >
                    <IconDiamond size={17} aria-hidden="true" />
                    <span className={styles.compItemName}>
                      Purge {opt.needed} {opt.kind} fragments to gain a relic
                    </span>
                    <small className={styles.compItemTag}>
                      {opt.owned}
                      {opt.wildcards > 0 ? ` + ${opt.wildcards} unknown` : ""} / {opt.needed}
                    </small>
                  </button>
                );
              })}
          </div>

          {/* Zdolności technologii BEZ akcji (np. Psychoarchaeology) - nie zużywają akcji tury. */}
          {(freeAbilities ?? []).length > 0 && (
            <>
              <Text size="xs" c="dimmed">
                Technology abilities (not an action)
              </Text>
              <div className={styles.compList} role="list">
                {(freeAbilities ?? []).map((ability) => (
                  <button
                    key={ability.tech_id}
                    type="button"
                    role="listitem"
                    className={styles.compItem}
                    disabled={busy || !ability.usable}
                    title={ability.reason || undefined}
                    onClick={() => {
                      setComponentOpen(false);
                      setUsingTech({ id: ability.tech_id, name: ability.name });
                    }}
                  >
                    <IconSparkles size={17} aria-hidden="true" />
                    <span className={styles.compItemName}>{ability.name}</span>
                    <small className={styles.compItemTag}>
                      {ability.usable ? "Free" : ability.reason}
                    </small>
                  </button>
                ))}
              </div>
            </>
          )}

          <Group justify="flex-end" gap="sm">
            <Button
              variant="default"
              disabled={busy}
              onClick={() => setComponentOpen(false)}
            >
              Cancel
            </Button>
          </Group>
        </Stack>
      </AppModal>
    </>
  );
}

/**
 * Jedna karta strategii w slocie: obrazek PNG + nakładka „Play"/„Played" na hover
 * ORAZ tooltip z treścią karty (Primary/Secondary) — ten sam wzorzec, co w fazie
 * strategii (``SmoothPopover`` + ``DetailsCard``). Hover otwiera tooltip i pokazuje
 * akcję „Play"; karta jednocześnie prostuje się i unosi ze slotu (CSS).
 */
function StrategyCardImage({
  card,
  index,
  canPlay,
  busy,
  onPlay,
}: {
  card: StrategyCardState;
  index: number;
  canPlay: boolean;
  busy: boolean;
  onPlay: () => void;
}) {
  const [failed, setFailed] = useState(false);
  const [hovered, setHovered] = useState(false);
  const def =
    getStrategyCardById(card.id) ?? getStrategyCardByInitiative(card.initiative);
  const imageURL = def?.imageURL;
  const showImage = !!imageURL && !failed;
  const name = card.name || SC_NAMES[card.initiative] || "—";
  const hue = def?.colourHexCode || SC_HUE[card.initiative] || "#888";
  const detailsColor =
    SC_DETAILS_COLOR[card.initiative] ?? ("none" as DetailsCardColor);
  const primaryText = (def?.primaryTexts ?? []).join("\n\n");
  const secondaryText = (def?.secondaryTexts ?? []).join("\n\n");

  return (
    <SmoothPopover opened={hovered} position="top" onChange={setHovered}>
      <SmoothPopover.Target>
        <div
          className={styles.card}
          data-played={card.exhausted || undefined}
          style={
            {
              "--sc-hue": hue,
              "--i": index,
            } as CSSProperties
          }
          title={name}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onFocus={() => setHovered(true)}
          onBlur={() => setHovered(false)}
        >
          <div className={styles.cardInner}>
            {showImage ? (
              <img
                className={styles.cardImage}
                src={imageURL}
                alt={name}
                draggable={false}
                loading="lazy"
                onError={() => setFailed(true)}
              />
            ) : (
              <div className={styles.cardFallback}>
                <span className={styles.disc}>{card.initiative}</span>
                <span className={styles.name}>{name}</span>
              </div>
            )}

            {/* Nakładka na hover: Play (niezagrana) albo znacznik Played. */}
            {canPlay ? (
              <button
                type="button"
                className={styles.playOverlay}
                data-no-drag
                disabled={busy}
                onClick={onPlay}
                title={`Play ${name} (primary + secondary window)`}
              >
                <IconPlayerPlayFilled size={22} aria-hidden="true" />
                <span>Play</span>
              </button>
            ) : card.exhausted ? (
              <span className={styles.playedBadge}>Played</span>
            ) : null}
          </div>
        </div>
      </SmoothPopover.Target>

      {/* Tooltip treści karty — jak w StrategyCardTable (Primary/Secondary). */}
      <SmoothPopover.Dropdown p={0}>
        <DetailsCard width={340} color={detailsColor}>
          <Stack gap="md">
            <DetailsCard.Title
              title={`${def?.initiative ?? card.initiative} ${def?.name ?? name}`}
              subtitle={`Strategy card · Initiative ${def?.initiative ?? card.initiative}`}
            />
            {primaryText && (
              <DetailsCard.Section title="Primary" content={primaryText} />
            )}
            {secondaryText && (
              <DetailsCard.Section title="Secondary" content={secondaryText} />
            )}
          </Stack>
        </DetailsCard>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

export default TurnControls;

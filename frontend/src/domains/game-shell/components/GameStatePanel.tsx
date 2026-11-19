import {
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { InvasionStepPanel } from "@/domains/invasion/InvasionStepPanel";
import { useParams } from "react-router-dom";
import { Button, Collapse, Group, Stack, Text, UnstyledButton } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import {
  IconArrowRight,
  IconArrowsMove,
  IconBolt,
  IconChevronDown,
  IconGripVertical,
  IconLayoutGrid,
  IconLock,
  IconStack2,
  IconSwords,
  IconTarget,
  IconTrophy,
} from "@tabler/icons-react";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useHudMetric } from "@/hooks/useHudMetric";
import cx from "clsx";
import { useGameState } from "@/api/useGameState";
import {
  useBoardEditor,
  useStrategyCards,
  type StrategyCardState,
} from "@/api/useBoardEditor";
import { useAppStore, useSettingsStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { MovementStepPanel } from "./MovementStepPanel";
import { SpaceCannonStepPanel } from "./SpaceCannonStepPanel";
import { DEFAULT_GAME_ID } from "@/config";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import type {
  GamePhase,
  GameState,
  GameStateCombat,
  PlayerData,
} from "@/entities/data/types";
import {
  loadStoredChoice,
  saveStoredChoice,
} from "@/utils/localStorageSettings";
import { isMobileDevice } from "@/utils/isTouchDevice";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import {
  prettifyId,
  resolveSystemName,
} from "./GameEventPanel/eventFormatting";
import { CoachSection } from "@/domains/tutorial";
import { AgendaRow } from "./GameStateAgenda";
import { getPlayerDisplayName, playerNameForColor } from "./gameStatePlayers";
import styles from "./GameStatePanel.module.css";

type PhaseStep = "strategy" | "action" | "status" | "agenda";

type PhaseConfig = {
  label: string;
  /** Signal triplet (space-separated) the plate's top line and dot key to. */
  tone: string;
  step: PhaseStep | null;
};

const TONE = {
  neutral: "var(--ds-hair-rgb)",
  strategy: "var(--ds-sig-break)",
  action: "var(--ds-sig-bio)",
  status: "var(--ds-sig-warn)",
  agenda: "var(--ds-sig-law)",
  combat: "var(--ds-sig-danger)",
  finished: "var(--ds-sig-relic)",
};

const PHASE_CONFIGS: Record<GamePhase, PhaseConfig> = {
  unknown: { label: "Unknown phase", tone: TONE.neutral, step: null },
  "setup.draft": { label: "Setup · Draft", tone: TONE.neutral, step: null },
  "setup.players": { label: "Setup · Players", tone: TONE.neutral, step: null },
  strategy: { label: "Strategy phase", tone: TONE.strategy, step: "strategy" },
  action: { label: "Action phase", tone: TONE.action, step: "action" },
  "status.scoring": {
    label: "Status · Scoring",
    tone: TONE.status,
    step: "status",
  },
  "status.homework": {
    label: "Status · Homework",
    tone: TONE.status,
    step: "status",
  },
  "agenda.readyToFlip": {
    label: "Agenda · Ready",
    tone: TONE.agenda,
    step: "agenda",
  },
  "agenda.whens": {
    label: "Agenda · Whens",
    tone: TONE.agenda,
    step: "agenda",
  },
  "agenda.afters": {
    label: "Agenda · Afters",
    tone: TONE.agenda,
    step: "agenda",
  },
  "agenda.voting": {
    label: "Agenda · Voting",
    tone: TONE.agenda,
    step: "agenda",
  },
  "agenda.resolving": {
    label: "Agenda · Resolving",
    tone: TONE.agenda,
    step: "agenda",
  },
  finished: { label: "Game over", tone: TONE.finished, step: null },
};

const PHASE_STEPS: { step: PhaseStep; label: string }[] = [
  { step: "strategy", label: "Strategy" },
  { step: "action", label: "Action" },
  { step: "status", label: "Status" },
  { step: "agenda", label: "Agenda" },
];

/* Strategy card initiative → its signal triplet (comma-separated). */
const SC_TONE: Record<number, string> = {
  1: "var(--gd-red)",
  2: "var(--gd-orange)",
  3: "var(--gd-yellow)",
  4: "var(--gd-green)",
  5: "var(--gd-teal)",
  6: "var(--gd-cyan)",
  7: "var(--gd-blue)",
  8: "var(--gd-purple)",
};

type SeatStatus = "acting" | "passed" | "waiting" | "picked" | "picking";

type Seat = {
  player: PlayerData;
  name: string;
  initiative: number | null;
  status: SeatStatus;
};

/** The player's colour as a comma triplet, for rgba(var(--pc), a). */
function playerTone(color: string | null | undefined): string | undefined {
  if (!color) return undefined;
  const rgb = resolvePrimaryRgb(color);
  return rgb ? `${rgb.red}, ${rgb.green}, ${rgb.blue}` : undefined;
}

function toneStyle(vars: Record<string, string | undefined>): CSSProperties {
  const entries = Object.entries(vars).filter(([, v]) => v !== undefined);
  return Object.fromEntries(entries) as CSSProperties;
}

function lowestInitiative(player: PlayerData): number | null {
  if (!player.scs?.length) return null;
  return Math.min(...player.scs);
}

function seatStatus(player: PlayerData, phase: GamePhase): SeatStatus {
  if (player.active) return phase === "strategy" ? "picking" : "acting";
  if (phase === "strategy") return player.scs?.length ? "picked" : "waiting";
  return player.passed ? "passed" : "waiting";
}

/**
 * Kolejność miejsc (speaker order) jako lista kolorów, rotowana tak, by zaczynać
 * od mówcy. Używana w fazie strategii — wybór idzie zegarowo od mówcy (RULES.md 24).
 * Gdy backend nie podał seatingOrder, zwraca pustą listę (fallback na inicjatywę).
 */
function speakerOrderColors(gameState: GameState): string[] {
  const order = gameState.seatingOrder ?? [];
  const speaker = gameState.speaker ?? null;
  if (order.length === 0) return [];
  if (!speaker || !order.includes(speaker)) return order;
  const idx = order.indexOf(speaker);
  return [...order.slice(idx), ...order.slice(0, idx)];
}

function isSeated(player: PlayerData): boolean {
  if (!player.faction || player.faction === "neutral") return false;
  const name = getPlayerDisplayName(player, player.color).toLowerCase();
  return !name.endsWith(".deck") && !name.endsWith('.deck"');
}

/**
 * Miejsca graczy w kolejności zależnej od fazy:
 * - faza strategii: SPEAKER ORDER (mówca pierwszy, zegarowo) — tak idzie wybór kart;
 * - pozostałe fazy: INICJATYWA kart (najniższy numer pierwszy).
 * Gdy brak speaker order (``seatColors`` puste), wszędzie używamy inicjatywy.
 */
function buildSeats(
  playerData: PlayerData[],
  phase: GamePhase,
  seatColors: string[],
): Seat[] {
  const seats = playerData.filter(isSeated).map((player) => ({
    player,
    name: getPlayerDisplayName(player, player.color),
    initiative: lowestInitiative(player),
    status: seatStatus(player, phase),
  }));

  if (phase === "strategy" && seatColors.length > 0) {
    const rank = new Map(seatColors.map((color, i) => [color, i]));
    return seats.sort(
      (a, b) =>
        (rank.get(a.player.color ?? "") ?? 99) -
        (rank.get(b.player.color ?? "") ?? 99),
    );
  }
  return seats.sort((a, b) => (a.initiative ?? 99) - (b.initiative ?? 99));
}

function systemLabel(
  position: string | null,
  tiles: Record<string, { systemId: string }> | undefined,
): string | null {
  if (!position) return null;
  const systemId = tiles?.[position]?.systemId;
  const name = systemId
    ? resolveSystemName(position, { [position]: systemId })
    : position;
  return name === position ? position : `${position} ${name}`;
}

function nowPhrase(phase: GamePhase, system: string | null): string {
  if (phase === "action") {
    return system ? `Tactical action · ${system}` : "Taking a turn";
  }
  if (phase === "strategy") return "Picking a strategy card";
  if (phase === "agenda.voting") return "Casting votes";
  if (phase.startsWith("agenda")) return "Agenda phase";
  if (phase.startsWith("status")) return "Status phase";
  return "On the clock";
}

const PANEL_OPEN_KEY = "ti4_game_state_panel_open";
const PANEL_POS_KEY = "ti4_game_state_panel_pos";

/**
 * Whether the plate is expanded, remembered across games and reloads. The
 * plate floats over the board's top-left corner, so leaving it open is the
 * player's choice; a phone starts collapsed.
 */
function useGameStatePanelOpen(): [boolean, (next: boolean) => void] {
  const [isOpen, setIsOpen] = useState(() => {
    const stored = loadStoredChoice(PANEL_OPEN_KEY, ["true", "false"]);
    if (stored === null) return !isMobileDevice();
    return stored === "true";
  });

  const set = (next: boolean) => {
    setIsOpen(next);
    saveStoredChoice(PANEL_OPEN_KEY, String(next), "game state panel state");
  };

  return [isOpen, set];
}

const DETAILS_ID = "game-state-panel-details";

function PlateHeader({
  label,
  meta,
  isOpen,
  onToggle,
  onHandlePointerDown,
  onResetPosition,
}: {
  label: string;
  meta: ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  onHandlePointerDown: (event: ReactPointerEvent) => void;
  onResetPosition: () => void;
}) {
  const action = isOpen ? "Collapse game state" : "Expand game state";
  return (
    // Nagłówek = uchwyt przeciągania panelu (pointer-down zaczyna drag). Klik w
    // przycisk zwijania [data-no-drag] nie rusza panelu. Dwuklik = reset pozycji.
    <div
      className={styles.header}
      onPointerDown={onHandlePointerDown}
      onDoubleClick={onResetPosition}
      title="Drag to move the panel · double-click resets its position"
    >
      <span className={styles.dragGrip} aria-hidden="true">
        <IconGripVertical size={13} />
      </span>
      <span className={styles.phaseDot} aria-hidden="true" />
      <span className={styles.phaseLabel}>{label}</span>
      <span className={styles.headerMeta}>{meta}</span>
      <UnstyledButton
        data-no-drag
        className={styles.collapseBtn}
        aria-controls={DETAILS_ID}
        aria-expanded={isOpen}
        aria-label={action}
        title={action}
        onClick={onToggle}
      >
        <IconChevronDown
          aria-hidden="true"
          size={13}
          className={cx(styles.chevron, isOpen && styles.chevronOpen)}
        />
      </UnstyledButton>
    </div>
  );
}

function PhaseTrack({ step }: { step: PhaseStep | null }) {
  if (!step) return null;
  const current = PHASE_STEPS.findIndex((s) => s.step === step);
  return (
    <div className={styles.track} aria-label="Phase">
      {PHASE_STEPS.map((s, index) => {
        const state =
          index < current ? "done" : index === current ? "now" : undefined;
        return (
          <span
            key={s.step}
            className={styles.trackStep}
            data-s={state}
            aria-current={state === "now" ? "step" : undefined}
          >
            {s.label}
          </span>
        );
      })}
    </div>
  );
}

function FactionMark({
  player,
  size,
}: {
  player: PlayerData | undefined;
  size: number;
}) {
  if (!player?.faction) return <span style={{ width: size, height: size }} />;
  return (
    <CircularFactionIcon
      faction={player.faction}
      size={size}
      factionImageOverride={player.factionImage}
      factionImageTypeOverride={player.factionImageType}
    />
  );
}

function NowCallout({
  player,
  name,
  detail,
  icon,
}: {
  player: PlayerData | undefined;
  name: string;
  detail: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div
      className={styles.now}
      style={toneStyle({ "--pc": playerTone(player?.color) })}
    >
      {icon ?? <FactionMark player={player} size={26} />}
      <span className={styles.nowText}>
        <b className={styles.nowName}>{name}</b>
        <small className={styles.nowDetail}>{detail}</small>
      </span>
    </div>
  );
}

function ScDisc({ initiative }: { initiative: number | null }) {
  if (initiative === null) {
    return <span className={cx(styles.disc, styles.discEmpty)}>–</span>;
  }
  return (
    <span
      className={styles.disc}
      style={toneStyle({ "--scc": SC_TONE[initiative] })}
    >
      {initiative}
    </span>
  );
}

/** Etykiety statusu miejsca po polsku (planszówkowy, czytelny ton). */
const SEAT_STATUS_LABEL: Record<SeatStatus, string> = {
  acting: "Active",
  picking: "Picking",
  passed: "passed",
  picked: "picked",
  waiting: "Waiting",
};

function TurnOrder({
  seats,
  activeColor,
  phase,
}: {
  seats: Seat[];
  activeColor: string | null;
  phase: GamePhase;
}) {
  if (seats.length === 0) return null;
  const orderLabel =
    phase === "strategy" ? "Pick order (from Speaker)" : "Turn order (initiative)";
  return (
    <div className={styles.section}>
      <span className={styles.label}>{orderLabel}</span>
      <div className={styles.order} role="list" aria-label={orderLabel}>
        {seats.map((seat) => {
          const isActive = seat.player.color === activeColor;
          return (
            <div
              key={seat.player.color}
              role="listitem"
              className={styles.seat}
              data-s={seat.status}
              data-active={isActive || undefined}
              style={toneStyle({ "--pc": playerTone(seat.player.color) })}
            >
              <ScDisc initiative={seat.initiative} />
              <FactionMark player={seat.player} size={18} />
              <span className={styles.seatName}>{seat.name}</span>
              <span className={styles.seatStatus}>
                {SEAT_STATUS_LABEL[seat.status]}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Strategy cards still being followed: who has yet to resolve the secondary
 * of each played card.
 */
function FollowQueue({ seats }: { seats: Seat[] }) {
  const pending = new Map<number, Seat[]>();
  for (const seat of seats) {
    for (const sc of seat.player.unfollowedSCs ?? []) {
      pending.set(sc, [...(pending.get(sc) ?? []), seat]);
    }
  }
  if (pending.size === 0) return null;

  return (
    <>
      {[...pending.entries()].map(([sc, waiting]) => (
        <div key={sc} className={styles.follow}>
          <span className={styles.label}>
            Following {sc}
            {SC_NAMES[sc] ? ` · ${prettifyId(SC_NAMES[sc].toLowerCase())}` : ""}
          </span>
          <span className={styles.followChips}>
            {waiting.map((seat) => (
              <span key={seat.player.color} title={seat.name}>
                <FactionMark player={seat.player} size={16} />
              </span>
            ))}
          </span>
          <span className={styles.followCount}>{waiting.length} left</span>
        </div>
      ))}
    </>
  );
}

function CombatSection({
  combat,
  playerData,
  location,
}: {
  combat: GameStateCombat;
  playerData: PlayerData[];
  location: string | null;
}) {
  const sides = combat.participantColors;
  return (
    <div className={styles.section}>
      <span className={styles.label}>
        <IconSwords size={11} aria-hidden="true" />
        Combat{location ? ` · ${location}` : ""}
        {combat.unitHolder ? ` · ${combat.unitHolder}` : ""}
        {combat.round !== null ? ` · round ${combat.round}` : ""}
      </span>
      {sides.length > 0 && (
        <div className={styles.sides}>
          {sides.map((color, index) => {
            const player = playerData.find((p) => p.color === color);
            return (
              <span
                key={color}
                className={styles.side}
                data-align={index === 0 ? "start" : "end"}
                style={toneStyle({ "--pc": playerTone(color) })}
              >
                <FactionMark player={player} size={18} />
                <span>{playerNameForColor(playerData, color)}</span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

function WinnerCallout({
  winner,
  playerData,
}: {
  winner: string;
  playerData: PlayerData[];
}) {
  const player = playerData.find((p) => p.color === winner);
  return (
    <NowCallout
      player={player}
      name={`${playerNameForColor(playerData, winner)} wins`}
      detail="Victory points reached"
      icon={
        <span className={styles.trophy}>
          <IconTrophy size={16} aria-hidden="true" />
        </span>
      }
    />
  );
}

type Locations = { system: string | null; combat: string | null };

/**
 * Tryb renderowania wnętrza panelu stanu:
 * - ``"info"`` — pływający panel „Game state": TYLKO warstwa informacyjna (kto gra,
 *   faza, kolejka, pomoc przy wyborze kart jako PODGLĄD). Zero klikalnych akcji —
 *   przeniesione w inne miejsca (faza akcji, sterowanie turą/rundą).
 * - ``"full"`` — kontrolki akcji (zakładka gracza): pełny zestaw z przyciskami
 *   (okno czasowe, wybór/zagranie kart, faza akcji, End turn/Pass/Next phase).
 *
 * Żaden komponent nie jest usuwany — w trybie ``info`` renderujemy jego
 * informacyjny wariant, a klikalne elementy pomijamy.
 */
type PanelVariant = "info" | "full";

function PlateBody({
  gameState,
  playerData,
  locations,
  variant = "full",
}: {
  gameState: GameState;
  playerData: PlayerData[];
  locations: Locations;
  variant?: PanelVariant;
}) {
  const { phase, activePlayer, winner, activeCombat } = gameState;
  if (phase === "finished" && winner) {
    return <WinnerCallout winner={winner} playerData={playerData} />;
  }

  const isInfo = variant === "info";
  const seatColors = speakerOrderColors(gameState);
  const seats = buildSeats(playerData, phase, seatColors);
  // Gracz, którego jest TURA: preferujemy ``activeTurnPlayer`` (nie gaśnie przy
  // passed), spadając na ``activePlayer`` (highlight). Dzięki temu po pasie panel
  // wciąż wie, czyja tura — End turn/Pass i status karty nie znikają (RULES.md 31.4).
  const turnColor = gameState.activeTurnPlayer ?? activePlayer;
  const active = playerData.find((p) => p.color === turnColor);
  const isAgenda = phase.startsWith("agenda");
  // Pływający panel fazy (info) jest ZWIĘZŁY (decyzja użytkownika): w fazie strategii
  // kolejność wyboru i karty pokazuje stół kart strategii na środku ekranu
  // (StrategyCardTable), więc panel ich nie dubluje. Pełny wariant (zakładka) bez zmian.
  const showOrder = phase === "action" || (phase === "strategy" && !isInfo);

  // Status karty strategii aktywnego gracza (faza akcji): czy ma kartę i czy
  // już ją zagrał. Steruje bramką przycisku „Pass" (nie można pasować przed
  // akcją strategiczną — RULES.md 31.2 / R_action_phase) i banerem statusu.
  const strategyStatus = usePlayerStrategyStatus(active);

  return (
    <>
      {/* Odrzucone akcje (422) pokazuje teraz PANEL KOMUNIKATÓW u góry ekranu
          (PhaseNoticePanel) — jedno, spójne miejsce. Dawny lokalny NoticeBanner
          usunięty, by nie dublować komunikatu (DECYZJA 2026-11). */}
      {gameState.pendingWindow && (
        <WindowSection
          window={gameState.pendingWindow}
          playerData={playerData}
          variant={variant}
        />
      )}
      {activePlayer && (
        <NowCallout
          player={active}
          name={playerNameForColor(playerData, activePlayer)}
          detail={nowPhrase(phase, locations.system)}
        />
      )}
      {activeCombat && (
        <CombatSection
          combat={activeCombat}
          playerData={playerData}
          location={locations.combat}
        />
      )}
      {showOrder && (
        <TurnOrder seats={seats} activeColor={activePlayer} phase={phase} />
      )}
      {phase === "strategy" && !isInfo && (
        <StrategyCardPicker
          seats={seats}
          activeColor={activePlayer}
          pickCount={gameState.strategyPickCount ?? null}
        />
      )}
      {/* Faza akcji = same klikalne akcje → tylko w trybie pełnym (osobne miejsce). */}
      {phase === "action" && !isInfo && (
        <>
          {/* Wyraźny status karty strategii aktywnego gracza: jaką kartę ma i
              czy ją zagrał. Odpowiada na „chcę widzieć jaką kartę wybrałem". */}
          <StrategyCardStatus player={active} status={strategyStatus} />
          <ActionPhasePanel
            seats={seats}
            activeSystem={gameState.activeSystem}
            tacticalStep={gameState.tacticalStep ?? null}
            systemLabel={locations.system}
            activePlayerColor={gameState.activePlayer}
          />
        </>
      )}
      {isAgenda && (
        <AgendaRow
          agenda={gameState.agenda}
          phase={phase}
          activePlayer={activePlayer}
          playerData={playerData}
        />
      )}
      {/* Sterowanie turą/fazą/rundą = klikalne akcje → tylko w trybie pełnym. */}
      {!isInfo && (
        <PhaseControls
          gameState={gameState}
          activePlayer={active}
          canPass={strategyStatus.canPass}
          passBlockReason={strategyStatus.passBlockReason}
        />
      )}
    </>
  );
}

/** Czytelne etykiety typów okien czasowych (RULES.md 29.2). */
const WINDOW_LABELS: Record<string, string> = {
  STRATEGY_SECONDARY: "Strategy Card secondary",
  COMBAT_ASSIGN_HITS: "Assign hits in combat",
  COMBAT_RETREAT: "Announce retreats",
  CAPACITY: "Capacity exceeded",
  FLEET_POOL: "Fleet pool exceeded",
  SPACE_CANNON: "Space Cannon",
  REACTION: "Reaction window",
};

/*
 * Okna rozstrzygane WŁASNYM oknem/panelem (walka, Space Cannon, pojemność, pula floty,
 * oferty): ogólnej odpowiedzi w oknie nie ma (backend jej nie przyjmuje — omijała obowiązkowe
 * decyzje). Panel pokazuje, GDZIE rozstrzygnąć okno; God-Mode dostaje wentyl „Close window”.
 */
const WINDOW_RESOLVED_ELSEWHERE: Record<string, string> = {
  COMBAT_ASSIGN_HITS: "Assign the hits in the battle window.",
  COMBAT_RETREAT: "Announce the retreat in the battle window.",
  CAPACITY: "Remove the excess units in the capacity window.",
  FLEET_POOL: "Return the excess ships in the fleet pool window.",
  SPACE_CANNON: "Fire or pass in the Space Cannon step panel.",
  REACTION: "Decide on the pending offers in the offers window.",
};

/**
 * Panel otwartego OKNA CZASOWEGO (timing window, Etap E8). Pokazuje wyraźnie, czyja
 * teraz reakcja (kolejka graczy pytanych po kolei — RULES.md 29.2) i daje przyciski
 * odpowiedzi. ``currentResponder`` to KOLOR gracza (jak ``activePlayer``), więc
 * dopasowujemy go do ``playerData`` po kolorze; odpowiedź adresujemy stabilnym
 * ``currentResponderId`` (player_id). W T2 decyzje to „Wykonaj"/„Pas" (etykiety) —
 * efekty konkretnych okien (secondary zużywa żeton, assign-hits usuwa jednostki)
 * dojdą od T3.
 */
function WindowSection({
  window,
  playerData,
  variant = "full",
}: {
  window: NonNullable<GameState["pendingWindow"]>;
  playerData: PlayerData[];
  variant?: PanelVariant;
}) {
  const { strategySecondary, closeWindow } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  // God-Mode (Settings → Admin / testing): odsłania wentyl „Close window" dla okien,
  // które mają własny panel rozstrzygania.
  const godMode = useSettingsStore((s) => s.settings.skipPhases);

  const isInfo = variant === "info";
  const label = WINDOW_LABELS[window.windowType] ?? window.windowType;
  const elsewhere = WINDOW_RESOLVED_ELSEWHERE[window.windowType] ?? null;
  // Przyciski odpowiedzi tylko dla secondary karty strategii (jedyne okno rozstrzygane w tym
  // panelu); okno nieznanego typu pokazuje tylko stan kolejki.
  const isSecondary = window.windowType === "STRATEGY_SECONDARY";
  const showGenericControls = !isInfo && isSecondary;
  const showCloseVent = !isInfo && (elsewhere == null || godMode);
  const responderColor = window.currentResponder;
  const responder = playerData.find((p) => p.color === responderColor);
  const responderName = responderColor
    ? playerNameForColor(playerData, responderColor)
    : null;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  // Secondary karty strategii: własny endpoint (efekt + przesunięcie kolejki, RULES.md 31.6).
  const respond = (execute: boolean) => {
    const id = window.currentResponderId;
    if (id) void run(() => strategySecondary(id, execute));
  };

  return (
    <div className={styles.section}>
      <span className={styles.label}>{label}</span>
      {window.isComplete || !window.currentResponderId ? (
        <>
          <span className={styles.label}>
            {isInfo
              ? "Everyone has responded"
              : "Everyone has responded — close the window"}
          </span>
          {/* Zamknięcie okna = klikalna akcja → tylko w trybie pełnym. Okna z własnym
              panelem zamykają się same po rozstrzygnięciu; ręczny wentyl tylko w God-Mode. */}
          {showCloseVent && (
            <div className={styles.controls}>
              <button
                type="button"
                className={styles.scPickBtn}
                disabled={busy}
                onClick={() => void run(() => closeWindow())}
              >
                Close window
              </button>
            </div>
          )}
        </>
      ) : (
        <>
          {/* Kto teraz reaguje — baner spójny z pickerem fazy strategii. */}
          <div
            className={styles.pickerNow}
            style={toneStyle({ "--pc": playerTone(responderColor) })}
          >
            {responder ? <FactionMark player={responder} size={22} /> : null}
            <span className={styles.pickerText}>
              <small className={styles.pickerLabel}>Responding</small>
              <b className={styles.pickerName}>
                {responderName ?? window.currentResponderId}
              </b>
            </span>
          </div>
          <span className={styles.label}>
            Remaining in queue: {window.remaining}
          </span>
          {/* Okno z własnym panelem: tu tylko wskazówka, gdzie je rozstrzygnąć. */}
          {elsewhere && !godMode && (
            <span className={styles.label}>{elsewhere}</span>
          )}
          {/* Odpowiedź w oknie = klikalne akcje → tylko w trybie pełnym (i tylko dla okien
              bez własnego panelu, chyba że God-Mode). */}
          {showGenericControls && (
            <div className={styles.controls}>
              <button
                type="button"
                className={styles.scPickBtn}
                disabled={busy}
                onClick={() => respond(true)}
                title="Follow — resolve the secondary ability"
              >
                Follow
              </button>
              <button
                type="button"
                className={styles.scPickBtn}
                disabled={busy}
                onClick={() => respond(false)}
                title="Decline the secondary"
              >
                Don't follow
              </button>
            </div>
          )}
          {/* God-Mode: wentyl hosta dla okna z własnym panelem (omija decyzję). */}
          {elsewhere && godMode && !isInfo && (
            <div className={styles.controls}>
              <button
                type="button"
                className={styles.scPickBtn}
                disabled={busy}
                onClick={() => void run(() => closeWindow())}
                title="God-Mode: close this window without resolving it"
              >
                Close window
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Wybór kart strategii (faza strategii, Etap E2/przebudowa tur). Planszówkowy
 * przepływ (RULES.md 24): wybór idzie w SPEAKER ORDER (od mówcy, zegarowo), jeden
 * gracz naraz. Panel pokazuje wyraźnie, KTO teraz wybiera, a karty są dużymi,
 * klikalnymi wierszami — kliknięcie przydziela kartę aktywnemu graczowi i tura
 * wyboru przechodzi sama do następnego. Operator może nadpisać mówcę (asystent,
 * nie sędzia); już wybrane karty pokazują właściciela.
 */
function StrategyCardPicker({
  seats,
  activeColor,
  pickCount,
}: {
  seats: Seat[];
  activeColor: string | null;
  /**
   * Liczba kart strategii na gracza (``Pick_Count``) z ``gameState``; ``null``, gdy
   * nieznana (liczba graczy spoza 3..8). Decyduje, kiedy wybór jest kompletny.
   */
  pickCount: number | null;
}) {
  const { data: cards } = useStrategyCards();
  const { pickStrategyCard, setSpeaker } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  if (!cards || cards.length === 0) return null;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  // Gracz, którego teraz kolej wybierać (aktywny w fazie strategii).
  const picker = seats.find((s) => s.player.color === activeColor);
  // Wybór kompletny dopiero, gdy KAŻDY gracz ma Pick_Count kart (druga runda przy
  // 3–4 graczach). Gdy pickCount nieznane (liczba graczy spoza 3..8), nie twierdzimy
  // błędnie „wszyscy wybrali" — bezpieczny fallback do false. RULES.md 13.
  const allPicked =
    pickCount !== null &&
    seats.every((s) => (s.player.scs?.length ?? 0) >= pickCount);

  return (
    <div className={styles.section}>
      {/* Kto teraz wybiera — wyraźny baner planszówkowy. */}
      {picker ? (
        <div
          className={styles.pickerNow}
          style={toneStyle({ "--pc": playerTone(picker.player.color) })}
        >
          <FactionMark player={picker.player} size={22} />
          <span className={styles.pickerText}>
            <small className={styles.pickerLabel}>Picking a card</small>
            <b className={styles.pickerName}>{picker.name}</b>
          </span>
        </div>
      ) : allPicked ? (
        <span className={styles.label}>
          Everyone has picked — move on to the Action Phase
        </span>
      ) : (
        <span className={styles.label}>Strategy Card selection</span>
      )}

      <div className={styles.scList}>
        {cards.map((card) => {
          const owner = seats.find(
            (s) => s.player.discordId === card.picked_by,
          );
          const canPick = !owner && !!picker;
          return (
            <button
              key={card.initiative}
              type="button"
              className={styles.scCard}
              data-picked={!!owner || undefined}
              disabled={busy || !canPick}
              onClick={() =>
                canPick &&
                void run(() =>
                  pickStrategyCard(picker.player.discordId, card.initiative),
                )
              }
              title={
                owner
                  ? `Picked by: ${getPlayerDisplayName(owner.player, owner.player.color)}`
                  : picker
                    ? `Pick for: ${picker.name}`
                    : card.name
              }
            >
              <span
                className={styles.disc}
                style={toneStyle({ "--scc": SC_TONE[card.initiative] })}
              >
                {card.initiative}
              </span>
              <span className={styles.scName}>{card.name}</span>
              {card.trade_goods > 0 && (
                <span className={styles.scTg} title="Trade Goods on the card">
                  +{card.trade_goods} TG
                </span>
              )}
              <span className={styles.scActions}>
                {owner && <FactionMark player={owner.player} size={18} />}
              </span>
            </button>
          );
        })}
      </div>

      {/* Zmiana mówcy (kto zaczyna wybór) - tylko w pełnym wariancie (zakładka gracza). */}
      <div className={styles.speakerRow}>
        <span className={styles.label}>Speaker</span>
        <div className={styles.speakerChips}>
          {seats.map((seat) => (
            <button
              key={seat.player.discordId}
              type="button"
              className={styles.scPickBtn}
              data-active={seat.player.isSpeaker || undefined}
              disabled={busy}
              onClick={() =>
                void run(() => setSpeaker(seat.player.discordId))
              }
              title={`Set Speaker: ${seat.name}`}
            >
              <FactionMark player={seat.player} size={16} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Krok PRODUCTION w panelu pomocy: właściwa produkcja dzieje się w dużym oknie
 * (`ProductionOverlay`, RULES.md 33.3), które otwiera się DOPIERO po kliknięciu „Open
 * production" (tu albo w pływającym przycisku na mapie) - wejście w krok go nie pokazuje.
 */
function ProductionStepPanel() {
  const setHidden = useAppStore((s) => s.setProductionHidden);
  return (
    <div className={styles.stepBody}>
      <span className={styles.prodNote}>
        Build units with the PRODUCTION of your units in this system.
      </span>
      <button
        type="button"
        className={cx(styles.ctlBtn, styles.ctlPrimary)}
        onClick={() => setHidden(false)}
      >
        <IconStack2 size={13} /> Open production
      </button>
    </div>
  );
}

/* Statki (asyncId) — kto ma flotę w systemie (walka kosmiczna) — i siły naziemne
   (walka naziemna). Spójne z backendowym PLACEMENT_BY_BASE_TYPE. */
const SHIP_ASYNC_IDS = new Set(["ff", "dd", "ca", "cv", "dn", "fs", "ws"]);

/** Kroki akcji taktycznej + etykiety i ikony (RULES.md 19). */
const TACTICAL_STEPS: {
  step: string;
  label: string;
  short: string;
}[] = [
  { step: "MOVEMENT", label: "Movement", short: "Move" },
  { step: "SPACE_CANNON", label: "Space Cannon", short: "Cannon" },
  { step: "SPACE_COMBAT", label: "Space Combat", short: "Combat" },
  { step: "INVASION", label: "Invasion", short: "Invasion" },
  { step: "PRODUCTION", label: "Production", short: "Production" },
];

/**
 * Panel akcji taktycznej (E3). Prowadzi gracza przez kroki (aktywacja → ruch →
 * działa → walka → inwazja → produkcja) BEZ walidacji reguł — gracze grają
 * fizycznie i wprowadzają wynik. Kroki są klikalnymi „pigułkami" (skok do kroku),
 * z wyróżnionym bieżącym. Krok produkcji otwiera pełny edytor stawiania jednostek.
 *
 * Eksportowany, bo poza osadzeniem w panelu fazy (``ActionPhasePanel``) jest też
 * reużywany w pływającym doku na map view (``TacticalActionDock``) — żeby panel
 * kroków był WIDOCZNY i POMOCNY na mapie przez całą akcję taktyczną (Blok A/UX).
 */
export function TacticalActionPanel({
  activeSystem,
  tacticalStep,
  systemLabel,
  activePlayerColor,
}: {
  activeSystem: string | null;
  tacticalStep: string | null;
  systemLabel: string | null;
  activePlayerColor: string | null;
}) {
  const { tacticalNextStep, endTactical, battleStart } = useBoardEditor();
  const activateMode = useAppStore((s) => s.activateMode);
  const toggleActivateMode = useAppStore((s) => s.toggleActivateMode);
  const setBattleHidden = useAppStore((s) => s.setBattleHidden);
  const params = useParams<{ mapid: string }>();
  const { data: liveGameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  // Trwająca walka (RULES.md 39) — okno pola bitwy pokazuje się samo; tu tylko powrót.
  const inCombat = liveGameState?.activeCombat != null;
  const gameData = useGameData();
  const [busy, setBusy] = useState(false);

  const activeTile = activeSystem ? gameData?.tiles?.[activeSystem] : undefined;

  // Czy w aktywnym systemie STATKI ma co najmniej dwóch graczy (walka obowiązkowa —
  // RULES.md 39 W2). Siły naziemne w przestrzeni (ładunek) nie liczą się jako statki.
  const hasSpaceCombat = (() => {
    if (!activeTile) return false;
    const factionsWithShips = Object.values(
      activeTile.unitsByFaction ?? {},
    ).filter((entities) =>
      entities.some(
        (e) => e.entityType === "unit" && e.count > 0 && SHIP_ASYNC_IDS.has(e.entityId),
      ),
    );
    return factionsWithShips.length >= 2;
  })();

  // Uwaga: odbiór kliknięcia w kafelek w trybie aktywacji (``activateRequest``) żyje
  // teraz w ``TurnControls`` (zamontowany przez całą fazę akcji), żeby przycisk
  // „Activate system" z rogu działał niezależnie od aktywnej zakładki panelu (Blok A).

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  // Brak aktywnego systemu: duży przycisk-start aktywacji (klik → wskaż kafelek).
  if (!activeSystem) {
    return (
      <button
        type="button"
        className={cx(styles.bigAction, activateMode && styles.bigActionOn)}
        onClick={toggleActivateMode}
        title="Click, then pick a system on the map to activate it"
      >
        <IconTarget size={16} aria-hidden="true" />
        <span>
          {activateMode ? "Pick a system on the map…" : "Activate system"}
        </span>
      </button>
    );
  }

  const currentIndex = TACTICAL_STEPS.findIndex((x) => x.step === tacticalStep);
  const isLast = currentIndex >= TACTICAL_STEPS.length - 1;

  // Blokady wyjścia z kroku / zakończenia akcji — lustro twardych reguł backendu
  // (core/tactical._check_can_leave): trwająca walka, okno Space Cannon / pojemności /
  // puli floty, niedokończona inwazja, obowiązkowa walka kosmiczna. Backend i tak
  // odrzuci (422); tu dajemy czytelny powód i wyszarzamy przyciski.
  const windowType = liveGameState?.pendingWindow?.windowType ?? null;
  const invasionOpen =
    tacticalStep === "INVASION" &&
    liveGameState?.activeInvasion != null &&
    liveGameState.activeInvasion.phase !== "ESTABLISH";
  const spaceCombatIndex = TACTICAL_STEPS.findIndex(
    (x) => x.step === "SPACE_COMBAT",
  );
  const commonBlock: string | null = inCombat
    ? "Combat in progress - finish it first."
    : windowType === "SPACE_CANNON"
      ? "Space Cannon is being resolved."
      : windowType === "CAPACITY"
        ? "Units exceed capacity - remove the excess."
        : windowType === "FLEET_POOL"
          ? "Ships exceed the fleet pool - remove the excess."
          : invasionOpen
            ? "Invasion in progress - finish it first."
            : null;
  const combatOwed = hasSpaceCombat && currentIndex <= spaceCombatIndex;
  const combatReason = "Space combat is mandatory - resolve it first.";
  const nextBlock =
    commonBlock ??
    (hasSpaceCombat && tacticalStep === "SPACE_COMBAT" ? combatReason : null);
  const endBlock = commonBlock ?? (combatOwed ? combatReason : null);
  const blockReason = nextBlock ?? endBlock;

  return (
    <div className={styles.tactical}>
      <div className={styles.tacticalHead}>
        <IconTarget size={14} aria-hidden="true" />
        <span className={styles.tacticalSystem} title={systemLabel ?? activeSystem}>
          {systemLabel ?? activeSystem}
        </span>
      </div>

      {/* Kroki jako WSKAŹNIK postępu (nie przełącznik) — pokazują gdzie jesteśmy,
          ale NIE pozwalają swobodnie skakać w przód/w tył (akcja taktyczna idzie
          po kolei; skakanie psuło przepływ). Postęp prowadzi wyłącznie „Next step". */}
      <ol className={styles.stepPills} aria-label="Tactical action step">
        {TACTICAL_STEPS.map((s, index) => {
          const state =
            index < currentIndex
              ? "done"
              : index === currentIndex
                ? "now"
                : undefined;
          return (
            <li
              key={s.step}
              className={styles.stepPill}
              data-s={state}
              aria-current={state === "now" ? "step" : undefined}
              title={s.label}
            >
              <span className={styles.stepIndex}>{index + 1}</span>
              <span className={styles.stepName}>{s.short}</span>
            </li>
          );
        })}
      </ol>

      {/* Zawartość bieżącego kroku — JEDYNA przewijana część panelu. */}
      <div className={styles.tacticalScroll}>
      {tacticalStep === "MOVEMENT" && (
        <div className={styles.stepBody}>
          <MovementStepPanel
            activeSystem={activeSystem}
            activePlayerColor={activePlayerColor}
          />
        </div>
      )}

      {tacticalStep === "SPACE_CANNON" && (
        <div className={styles.stepBody}>
          <SpaceCannonStepPanel />
        </div>
      )}

      {tacticalStep === "SPACE_COMBAT" && (
        <div className={styles.stepBody}>
          {inCombat ? (
            <button
              type="button"
              className={cx(styles.ctlBtn, styles.ctlPrimary)}
              onClick={() => setBattleHidden(false)}
            >
              <IconSwords size={13} /> Return to battle
            </button>
          ) : hasSpaceCombat ? (
            <>
              <span className={styles.prodNote}>
                Two fleets share this system — space combat is mandatory.
              </span>
              <button
                type="button"
                className={cx(styles.ctlBtn, styles.ctlPrimary)}
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    setBattleHidden(false);
                    await battleStart(null);
                  })
                }
              >
                <IconSwords size={13} /> Start space combat
              </button>
            </>
          ) : (
            <span className={styles.prodNote}>
              No opposing fleet — space combat not needed.
            </span>
          )}
        </div>
      )}

      {tacticalStep === "INVASION" && (
        <div className={styles.stepBody}>
          <InvasionStepPanel />
        </div>
      )}

      {tacticalStep === "PRODUCTION" && <ProductionStepPanel />}
      </div>

      {/* STOPKA przypięta do dołu panelu (nie przesuwa się wraz z zawartością kroku).
          „Next step"/„End action" wymagają DRUGIEGO kliknięcia (kroków nie da się
          cofnąć); przy blokadzie reguł są wyszarzone z podanym powodem. */}
      <footer className={styles.tacticalFoot}>
        {blockReason && (
          <p className={styles.blockNote} role="status">
            <IconLock size={12} aria-hidden="true" /> {blockReason}
          </p>
        )}
        <div className={styles.footBtns}>
          <button
            type="button"
            className={styles.endAction}
            disabled={busy || endBlock !== null}
            onClick={() => void run(endTactical)}
            title={endBlock ?? "End the tactical action now"}
          >
            End action
          </button>
          <button
            type="button"
            className={styles.nextStep}
            disabled={busy || nextBlock !== null}
            onClick={() => void run(tacticalNextStep)}
            title={
              nextBlock ??
              (isLast
                ? "Finish the tactical action"
                : "Advance to the next step (empty steps are skipped)")
            }
          >
            {isLast ? "Finish action" : "Next step"}
            <IconArrowRight size={14} aria-hidden="true" />
          </button>
        </div>
      </footer>
    </div>
  );
}

/**
 * Status karty strategii aktywnego gracza w fazie akcji: które karty ma (numery
 * inicjatywy + nazwy), czy zagrał już przynajmniej jedną (``exhausted``) oraz czy
 * wolno mu spasować. Reguła: nie można spasować przed wykonaniem akcji
 * strategicznej (RULES.md 31.2 / R_action_phase) — tę bramkę egzekwuje backend
 * (422), a tu odwzorowujemy ją proaktywnie, by gracz dostał natychmiastowy sygnał
 * zamiast baneru błędu. Gdy gracz nie ma karty strategii (stan brzegowy), pas jest
 * dozwolony. Hook, bo czyta pulę kart strategii (``useStrategyCards``).
 */
type PlayerStrategyStatus = {
  cards: StrategyCardState[];
  hasCard: boolean;
  played: boolean;
  canPass: boolean;
  passBlockReason: string | null;
};

function usePlayerStrategyStatus(
  player: PlayerData | undefined,
): PlayerStrategyStatus {
  const { data: cards } = useStrategyCards();
  const mine = (cards ?? []).filter((c) => c.picked_by === player?.discordId);
  const hasCard = mine.length > 0;
  // Zagrana = którakolwiek karta gracza jest wyczerpana (zagrano primary).
  const played = mine.some((c) => c.exhausted);
  // Pas dozwolony, gdy gracz nie ma karty (brzegowo) albo już zagrał.
  const canPass = !hasCard || played;
  const passBlockReason = canPass
    ? null
    : "Play your Strategy Card before passing.";
  return { cards: mine, hasCard, played, canPass, passBlockReason };
}

/**
 * Baner statusu karty strategii aktywnego gracza (faza akcji). Pokazuje WYRAŹNIE,
 * jaką kartę gracz wybrał w fazie strategii i czy już ją zagrał w tej turze —
 * z odznaką stanu (dysk inicjatywy w barwie karty + „Played"/„Not played yet").
 * To czysty wskaźnik; zagranie karty dzieje się w zakładce „Strategic" niżej.
 */
function StrategyCardStatus({
  player,
  status,
}: {
  player: PlayerData | undefined;
  status: PlayerStrategyStatus;
}) {
  if (!player || !status.hasCard) return null;
  return (
    <div className={styles.scStatus}>
      <span className={styles.label}>
        <IconBolt size={11} aria-hidden="true" />
        Your Strategy Card
      </span>
      <div className={styles.scStatusCards}>
        {status.cards.map((card) => (
          <div
            key={card.initiative}
            className={styles.scStatusCard}
            data-played={card.exhausted || undefined}
          >
            <span
              className={styles.disc}
              style={toneStyle({ "--scc": SC_TONE[card.initiative] })}
            >
              {card.initiative}
            </span>
            <span className={styles.scStatusName}>{card.name}</span>
            <span
              className={styles.scStatusBadge}
              data-played={card.exhausted || undefined}
            >
              {card.exhausted ? "Played" : "Not played"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Trzy rodzaje akcji w fazie akcji TI4 (RULES.md 19). */
type ActionKind = "tactical" | "strategy" | "component";

const ACTION_KINDS: {
  kind: ActionKind;
  label: string;
  hint: string;
  icon: ReactNode;
}[] = [
  {
    kind: "tactical",
    label: "Tactical",
    hint: "Activate a system: movement, combat, invasion, production.",
    icon: <IconTarget size={15} aria-hidden="true" />,
  },
  {
    kind: "strategy",
    label: "Strategic",
    hint: "Resolve a Strategy Card (other players' secondary abilities).",
    icon: <IconBolt size={15} aria-hidden="true" />,
  },
  {
    kind: "component",
    label: "Component",
    hint: "Play an Action Card, or use a leader, technology or relic.",
    icon: <IconLayoutGrid size={15} aria-hidden="true" />,
  },
];

/**
 * Panel fazy akcji: planszówkowy wybór RODZAJU akcji (taktyczna / strategiczna /
 * komponentowa — trzy jedyne opcje w turze TI4), a pod spodem szczegóły wybranego
 * rodzaju. Gdy trwa akcja taktyczna (aktywny system), od razu pokazujemy jej
 * kroki. Asystent — nie wymusza wyboru, pozwala przełączać rodzaj.
 */
function ActionPhasePanel({
  seats,
  activeSystem,
  tacticalStep,
  systemLabel,
  activePlayerColor,
}: {
  seats: Seat[];
  activeSystem: string | null;
  tacticalStep: string | null;
  systemLabel: string | null;
  activePlayerColor: string | null;
}) {
  // Trwająca akcja taktyczna wymusza zakładkę „taktyczna" (jest aktywny system).
  const [kind, setKind] = useState<ActionKind>("tactical");
  const effectiveKind: ActionKind = activeSystem ? "tactical" : kind;

  return (
    <div className={styles.section}>
      <span className={styles.label}>
        <IconArrowsMove size={11} aria-hidden="true" />
        Action type
      </span>

      {/* Trzy rodzaje akcji jako segmentowany wybór. */}
      <div className={styles.actionKinds} role="tablist" aria-label="Action type">
        {ACTION_KINDS.map((a) => (
          <button
            key={a.kind}
            type="button"
            role="tab"
            className={styles.actionKind}
            data-active={a.kind === effectiveKind || undefined}
            aria-selected={a.kind === effectiveKind}
            // Trwa akcja taktyczna → inne rodzaje zablokowane (najpierw zakończ).
            disabled={!!activeSystem && a.kind !== "tactical"}
            onClick={() => setKind(a.kind)}
            title={a.hint}
          >
            {a.icon}
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      {effectiveKind === "tactical" && (
        <TacticalActionPanel
          activeSystem={activeSystem}
          tacticalStep={tacticalStep}
          systemLabel={systemLabel}
          activePlayerColor={activePlayerColor}
        />
      )}

      {effectiveKind === "strategy" && (
        <div className={styles.kindBody}>
          <FollowQueue seats={seats} />
          <StrategicActionControl activePlayerColor={activePlayerColor} seats={seats} />
        </div>
      )}

      {effectiveKind === "component" && (
        <div className={styles.kindBody}>
          <span className={styles.prodNote}>
            A Component Action means using a component marked "ACTION" (Action
            Card, leader, action technology, relic). Resolve it at the table and
            record the effect on the board. Dedicated pickers will arrive in
            stage E4.
          </span>
          <span className={styles.prodNote}>
            Exhaust planets, technologies and leaders by right-clicking the
            component in the player panel (the "Exhaust / Ready" menu).
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Akcja strategiczna (faza akcji): aktywny gracz ZAGRYWA swoją kartę strategii —
 * rozstrzyga primary i otwiera okno secondary dla pozostałych (RULES.md 30). To
 * realny przycisk (wcześniej była tylko notka „rozlicz przy stole"). Kartę można
 * zagrać raz; po zagraniu pokazujemy, że czeka na secondary (panel okna u góry).
 */
function StrategicActionControl({
  activePlayerColor,
  seats,
}: {
  activePlayerColor: string | null;
  seats: Seat[];
}) {
  const { playStrategyCard } = useBoardEditor();
  const { data: cards } = useStrategyCards();
  const [busy, setBusy] = useState(false);

  const active = seats.find((s) => s.player.color === activePlayerColor);
  // Numery kart aktywnego gracza (z jego scs) jeszcze NIE zagrane (nie exhausted).
  const myCards = (cards ?? []).filter((c) => c.picked_by === active?.player.discordId);

  if (!active) {
    return (
      <span className={styles.prodNote}>
        No active player — cannot play a Strategy Card.
      </span>
    );
  }
  if (myCards.length === 0) {
    return (
      <span className={styles.prodNote}>
        {active.name} has no Strategy Card to play.
      </span>
    );
  }

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.scList}>
      {myCards.map((card) => (
        <button
          key={card.initiative}
          type="button"
          className={styles.scCard}
          data-picked={card.exhausted || undefined}
          disabled={busy || card.exhausted}
          onClick={() =>
            void run(() =>
              playStrategyCard(active.player.discordId, card.initiative),
            )
          }
          title={
            card.exhausted
              ? `${card.name} already played (awaiting secondary)`
              : `Play ${card.name} (primary + secondary window)`
          }
        >
          <span
            className={styles.disc}
            style={toneStyle({ "--scc": SC_TONE[card.initiative] })}
          >
            {card.initiative}
          </span>
          <span className={styles.scName}>
            {card.exhausted ? `${card.name} — played` : `Play: ${card.name}`}
          </span>
        </button>
      ))}
    </div>
  );
}

/**
 * Sterowanie przepływem gry (God-Mode / krokowa rozgrywka): zakończ turę, pas,
 * następna faza, nowa runda. Wywołuje endpointy przepływu (commit → historia).
 */
function PhaseControls({
  gameState,
  activePlayer,
  canPass = true,
  passBlockReason = null,
}: {
  gameState: GameState;
  /** „Gracz pulpitu" (PlayerData) — jego kolor porównujemy z mówcą. */
  activePlayer?: PlayerData | null;
  /** Czy aktywny gracz może spasować (po akcji strategicznej — RULES.md 31.2). */
  canPass?: boolean;
  /** Powód blokady pasa (tooltip), gdy ``canPass`` === false. */
  passBlockReason?: string | null;
}) {
  const { endTurn, passTurn, nextPlayer, phaseStep, nextPhase, nextRound } =
    useBoardEditor();
  const [busy, setBusy] = useState(false);
  // Potwierdzenie pasa (pas ≠ koniec tury — RULES.md 31.5).
  const [confirmingPass, setConfirmingPass] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  const phase = gameState.phase;
  const isAction = phase === "action";
  const isStatus = phase.startsWith("status");
  // Zainicjowana faza statusu (RULES.md 41) jest prowadzona panelem kroków; stary
  // przycisk „Next player" zostaje tylko dla statusu wprowadzonego God-Mode.
  const statusInSteps = isStatus && gameState.status != null;
  const isAgenda = phase.startsWith("agenda");
  // Zainicjowana faza agendy (RULES.md 51) prowadzi okno Rady (AgendaOverlay).
  const agendaInSteps = isAgenda && gameState.agendaPhase != null;
  // Otwarte okno czasowe (secondary itp.) blokuje End turn (RULES.md 31.6).
  const windowOpen = gameState.pendingWindow != null;
  // Czy aktywny gracz już spasował / wykonał akcję w tej turze (RULES.md 31.5/31.7).
  const hasPassed = activePlayer?.passed === true;
  const tookAction = activePlayer?.tookActionThisTurn === true;
  // End turn możliwy dopiero po akcji lub pasie i gdy nie trwa okno czasowe.
  const canEndTurn = isAction && (tookAction || hasPassed) && !windowOpen;
  const nudgeEndTurn = canEndTurn;
  // „Next phase" widzi ZAWSZE mówca; gdy przejście nie jest dozwolone, klik zwróci
  // 422 i panel komunikatów to pokaże (DECYZJA 2026-11). Bez twardego ukrywania.
  const isSpeaker =
    gameState.speaker != null && activePlayer?.color === gameState.speaker;
  const showNextPhase = isSpeaker;

  return (
    <div className={styles.controls}>
      {/* Faza akcji: główna akcja to „Zakończ turę" (duży, wyróżniony). Pas już
          NIE oddaje tury — oznacza gracza spasowanym, turę kończy End turn. */}
      {isAction && (
        <>
          <button
            type="button"
            className={cx(styles.ctlBtn, styles.ctlPrimary)}
            data-nudge={nudgeEndTurn ? "true" : undefined}
            disabled={busy || !canEndTurn}
            onClick={() => void run(() => endTurn())}
            title={
              windowOpen
                ? "Wait — every player must decide on the secondary first"
                : gameState.activeSystem != null
                  ? "End the tactical action and hand over (blocked while a combat or invasion is unresolved)"
                  : hasPassed
                    ? "You passed — end your turn to hand over"
                    : tookAction
                      ? "End your turn to hand over"
                      : "Take an action or pass before ending your turn"
            }
          >
            End turn
          </button>
          <button
            type="button"
            className={styles.ctlBtn}
            disabled={busy || hasPassed || tookAction || !canPass}
            onClick={() => setConfirmingPass(true)}
            title={
              hasPassed
                ? "You already passed — hand over with End turn"
                : tookAction
                  ? "You already acted this turn — End turn instead"
                  : canPass
                    ? "Pass — then End turn to hand over"
                    : (passBlockReason ?? "You cannot pass yet.")
            }
          >
            Pass
          </button>
          {/* Dlaczego pas jest zablokowany — czytelna podpowiedź przy przycisku. */}
          {!canPass && !hasPassed && passBlockReason && (
            <span className={styles.passHint}>{passBlockReason}</span>
          )}
          {/* Trzeba najpierw wykonać akcję albo spasować (RULES.md 31.7). */}
          {!tookAction && !hasPassed && !windowOpen && (
            <span className={styles.passHint}>
              Take an action or pass, then End turn.
            </span>
          )}
          {/* Po akcji/pasie: przypomnienie, że tura wciąż trzeba oddać. */}
          {canEndTurn && (
            <span className={styles.passedHint}>
              {hasPassed
                ? "You passed — now press End turn to hand over."
                : "Action done — press End turn to hand over."}
            </span>
          )}
          <AppModal
            opened={confirmingPass}
            onClose={() => setConfirmingPass(false)}
            title="Pass this round?"
            size={420}
          >
            <Stack gap="md">
              <Text size="sm">
                Passing ends your turns for this Action Phase. You still have to
                hand over this turn with <b>End turn</b> afterwards.
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
                  onClick={() =>
                    void run(() =>
                      passTurn().finally(() => setConfirmingPass(false)),
                    )
                  }
                >
                  Yes, pass
                </Button>
              </Group>
            </Stack>
          </AppModal>
        </>
      )}
      {/* Faza statusu: „Next player" KOŃCZY krok gracza i przesuwa dalej. Wołamy
          BEZ player_id — backend adresuje swojego aktywnego gracza (BUG 1). */}
      {isStatus && !statusInSteps && (
        <button
          type="button"
          className={cx(styles.ctlBtn, styles.ctlPrimary)}
          disabled={busy}
          onClick={() => void run(() => phaseStep())}
          title="Finish your Status step and pass to the next player"
        >
          Next player
        </button>
      )}
      {/* Faza agendy: „Pass" kończy część gracza, „Next player" tylko przewija.
          Oba BEZ player_id — backend adresuje swojego aktywnego gracza. */}
      {isAgenda && !agendaInSteps && (
        <>
          <button
            type="button"
            className={styles.ctlBtn}
            disabled={busy}
            onClick={() => void run(() => phaseStep())}
            title="Pass — decline your reaction/vote this agenda"
          >
            Pass
          </button>
          <button
            type="button"
            className={styles.ctlBtn}
            disabled={busy}
            onClick={() => void run(() => nextPlayer())}
            title="Pass the floor to the next player (no pass recorded)"
          >
            Next player
          </button>
        </>
      )}
      {/* Drobne sterowanie fazami (operator) — osobny, cichszy rząd. Przejście
          fazy ogłasza MÓWCA i tylko gdy wolno (``showNextPhase``). Po agendzie
          mówca startuje nową rundę. */}
      <div className={styles.controlsMinor}>
        {!isAgenda && showNextPhase && (
          <button
            type="button"
            className={styles.ctlBtnGhost}
            disabled={busy || (statusInSteps && gameState.canAdvancePhase !== true)}
            onClick={() => void run(nextPhase)}
          >
            Next phase
          </button>
        )}
        {isAgenda && isSpeaker && (
          <button
            type="button"
            className={styles.ctlBtnGhost}
            disabled={busy || (agendaInSteps && gameState.canAdvancePhase !== true)}
            onClick={() => void run(agendaInSteps ? nextPhase : nextRound)}
          >
            New round
          </button>
        )}
      </div>
    </div>
  );
}

function headerMeta(
  round: number | undefined,
  gameState: GameState,
  playerData: PlayerData[],
  isOpen: boolean,
): string {
  const parts: string[] = [];
  if (round) parts.push(`R${round}`);
  if (!isOpen && gameState.activePlayer) {
    parts.push(playerNameForColor(playerData, gameState.activePlayer));
  }
  return parts.join(" · ");
}

/**
 * The game-state plate: whose move it is and what they are doing. A phase
 * track sits on top, the current actor is called out in a faint wash of their
 * colour, and the body follows the phase. Collapsed, it is one line.
 */
function GameStatePanelContent({
  gameState,
  playerData,
  round,
  locations,
}: {
  gameState: GameState;
  playerData: PlayerData[];
  round: number | undefined;
  locations: Locations;
}) {
  const [isOpen, setIsOpen] = useGameStatePanelOpen();
  const drag = useDraggablePanel(PANEL_POS_KEY);
  // Na telefonie panel dokuje się paskiem nad planszą (CSS), więc nie pozwalamy
  // mu „pływać" — przesuwanie ma sens tylko na desktopie z wolną przestrzenią.
  const dragEnabled = !isMobileDevice();
  // Slot HUD „lewa góra": dok akcji taktycznej (lewy dół) kończy się pod tym panelem.
  useHudMetric(
    drag.el,
    "--hud-gsp-bottom",
    (rect) => rect.bottom,
    dragEnabled && !drag.isMoved,
  );
  const { phase, activeCombat } = gameState;
  const config = PHASE_CONFIGS[phase];
  const tone = activeCombat ? TONE.combat : config.tone;
  const label = activeCombat ? "Combat" : config.label;

  return (
    <section
      className={styles.panel}
      style={{
        ...toneStyle({ "--ph": tone }),
        ...(dragEnabled ? drag.style : {}),
      }}
      aria-label="Game state"
      ref={drag.ref}
      data-open={isOpen || undefined}
      data-dragging={(dragEnabled && drag.isDragging) || undefined}
      data-draggable-panel
    >
      <PlateHeader
        label={label}
        meta={headerMeta(round, gameState, playerData, isOpen)}
        isOpen={isOpen}
        onToggle={() => setIsOpen(!isOpen)}
        onHandlePointerDown={dragEnabled ? drag.onHandlePointerDown : () => {}}
        onResetPosition={dragEnabled ? drag.reset : () => {}}
      />
      <Collapse in={isOpen} id={DETAILS_ID} transitionDuration={160}>
        <PhaseTrack step={config.step} />
        {/* Pływający panel „Game state" = TYLKO status/informacja (bez klikalnych
            akcji). Funkcjonalność (faza akcji, sterowanie turą/rundą) żyje w innych
            miejscach — tu jej nie renderujemy (``variant="info"``). */}
        <PlateBody
          gameState={gameState}
          playerData={playerData}
          locations={locations}
          variant="info"
        />
      </Collapse>
      {/* „What now?” samouczka = część tego panelu (dawniej osobne okno w lewym dole,
          nachodziło na panel i czat). Widoczna także przy zwiniętym panelu fazy. */}
      <CoachSection />
    </section>
  );
}

export function GameStatePanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const playerData = gameData?.playerData ?? [];

  if (!gameState?.phase || gameState.phase === "unknown") return null;

  return (
    <GameStatePanelContent
      gameState={gameState}
      playerData={playerData}
      round={gameData?.gameRound}
      locations={{
        system: systemLabel(gameState.activeSystem, gameData?.tiles),
        combat: systemLabel(
          gameState.activeCombat?.system ?? null,
          gameData?.tiles,
        ),
      }}
    />
  );
}

/**
 * Same kontrolki akcji co w ``GameStatePanel`` (okno czasowe + panel fazy/akcji
 * taktycznej + baner odrzuconej akcji), ale BEZ pływającej/przeciąganej obudowy —
 * do osadzenia w zakładce (``Player_Tab``, zadanie 13.2). Reużywa ten sam
 * ``PlateBody`` (jedno źródło logiki akcji) i te same hooki danych web-data,
 * więc panel i zakładka zawsze pokazują ten sam stan gry.
 *
 * Akcje sterowane są przez ``pendingWindow``/``tacticalStep`` z ``gameState``
 * (R12.2). Akcja nielegalna → endpoint zwraca 422 → ``PhaseNoticePanel`` (u góry
 * ekranu) pokazuje komunikat; stan gry pozostaje bez zmian (R12.3 —
 * egzekwowane po stronie core/API). Zwraca ``null``, gdy brak sensownej fazy.
 */
export function GameStateActionControls() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const playerData = gameData?.playerData ?? [];

  if (!gameState?.phase || gameState.phase === "unknown") return null;

  return (
    <PlateBody
      gameState={gameState}
      playerData={playerData}
      locations={{
        system: systemLabel(gameState.activeSystem, gameData?.tiles),
        combat: systemLabel(
          gameState.activeCombat?.system ?? null,
          gameData?.tiles,
        ),
      }}
      variant="full"
    />
  );
}

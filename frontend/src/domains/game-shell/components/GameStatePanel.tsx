import {
  useEffect,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { useParams } from "react-router-dom";
import { Collapse, UnstyledButton } from "@/ds";
import {
  IconArrowsMove,
  IconBolt,
  IconChevronDown,
  IconGripVertical,
  IconLayoutGrid,
  IconMinus,
  IconPlus,
  IconStack2,
  IconSwords,
  IconTarget,
  IconTrophy,
} from "@tabler/icons-react";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { getColorAlias } from "@/entities/lookup/colors";
import { Unit } from "@/shared/ui/Unit";
import cx from "clsx";
import { useGameState } from "@/api/useGameState";
import {
  useBoardEditor,
  useProductionHelp,
  useStrategyCards,
} from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
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
      title="Przeciągnij, aby przesunąć panel · dwuklik resetuje pozycję"
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
  acting: "rusza",
  picking: "wybiera",
  passed: "spasował",
  picked: "wybrał",
  waiting: "czeka",
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
    phase === "strategy" ? "Kolejność wyboru (od mówcy)" : "Kolejność tur (inicjatywa)";
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

function PlateBody({
  gameState,
  playerData,
  locations,
}: {
  gameState: GameState;
  playerData: PlayerData[];
  locations: Locations;
}) {
  const { phase, activePlayer, winner, activeCombat } = gameState;
  if (phase === "finished" && winner) {
    return <WinnerCallout winner={winner} playerData={playerData} />;
  }

  const seatColors = speakerOrderColors(gameState);
  const seats = buildSeats(playerData, phase, seatColors);
  const active = playerData.find((p) => p.color === activePlayer);
  const isAgenda = phase.startsWith("agenda");
  const showOrder = phase === "action" || phase === "strategy";

  return (
    <>
      <NoticeBanner />
      {gameState.pendingWindow && (
        <WindowSection
          window={gameState.pendingWindow}
          playerData={playerData}
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
      {phase === "strategy" && (
        <StrategyCardPicker seats={seats} activeColor={activePlayer} />
      )}
      {phase === "action" && (
        <ActionPhasePanel
          seats={seats}
          activeSystem={gameState.activeSystem}
          tacticalStep={gameState.tacticalStep ?? null}
          systemLabel={locations.system}
          activePlayerColor={gameState.activePlayer}
        />
      )}
      {isAgenda && (
        <AgendaRow
          agenda={gameState.agenda}
          phase={phase}
          activePlayer={activePlayer}
          playerData={playerData}
        />
      )}
      <PhaseControls phase={phase} activePlayerId={active?.discordId ?? null} />
    </>
  );
}

/**
 * Przelotny baner komunikatu (odrzucona akcja walidacji: „system już aktywowany",
 * „za mało zasobów" itp.). Czyta ``notice`` ze store (ustawiane przez useBoardEditor
 * przy 422). Gracz zamyka go krzyżykiem; kolejna akcja go nadpisuje.
 */
function NoticeBanner() {
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);
  if (!notice) return null;
  return (
    <div className={styles.notice} data-kind={notice.kind} role="alert">
      <span className={styles.noticeText}>{notice.text}</span>
      <button
        type="button"
        className={styles.noticeClose}
        onClick={clearNotice}
        aria-label="Zamknij komunikat"
        title="Zamknij"
      >
        ×
      </button>
    </div>
  );
}

/** Czytelne etykiety typów okien czasowych (RULES.md 29.2). */
const WINDOW_LABELS: Record<string, string> = {
  STRATEGY_SECONDARY: "Secondary karty strategii",
  COMBAT_ASSIGN_HITS: "Przypisanie strat w walce",
  SPACE_CANNON: "Space Cannon (ostrzał)",
  REACTION: "Okno reakcji",
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
}: {
  window: NonNullable<GameState["pendingWindow"]>;
  playerData: PlayerData[];
}) {
  const { respondWindow, strategySecondary, closeWindow } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const label = WINDOW_LABELS[window.windowType] ?? window.windowType;
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

  // Odpowiedź routowana po TYPIE okna: secondary karty strategii ma własny endpoint
  // (wykonuje efekt + przesuwa kolejkę); pozostałe okna w T3 to generyczny respond
  // (sama mechanika kolejki). Kolejne typy dokładaj tu gałęzią.
  const respond = (execute: boolean) => {
    const id = window.currentResponderId;
    if (!id) return;
    if (window.windowType === "STRATEGY_SECONDARY") {
      void run(() => strategySecondary(id, execute));
    } else {
      void run(() => respondWindow(id, execute ? "execute" : "pass"));
    }
  };

  return (
    <div className={styles.section}>
      <span className={styles.label}>{label}</span>
      {window.isComplete || !window.currentResponderId ? (
        <>
          <span className={styles.label}>
            Wszyscy odpowiedzieli — zamknij okno
          </span>
          <div className={styles.controls}>
            <button
              type="button"
              className={styles.scPickBtn}
              disabled={busy}
              onClick={() => void run(() => closeWindow())}
            >
              Zamknij okno
            </button>
          </div>
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
              <small className={styles.pickerLabel}>Reaguje</small>
              <b className={styles.pickerName}>
                {responderName ?? window.currentResponderId}
              </b>
            </span>
          </div>
          <span className={styles.label}>
            Pozostało w kolejce: {window.remaining}
          </span>
          <div className={styles.controls}>
            <button
              type="button"
              className={styles.scPickBtn}
              disabled={busy}
              onClick={() => respond(true)}
              title="Wykonaj akcję w tym oknie"
            >
              Wykonaj
            </button>
            <button
              type="button"
              className={styles.scPickBtn}
              disabled={busy}
              onClick={() => respond(false)}
              title="Zrezygnuj (pas)"
            >
              Pas
            </button>
          </div>
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
}: {
  seats: Seat[];
  activeColor: string | null;
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
  const allPicked = seats.every((s) => s.player.scs?.length);

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
            <small className={styles.pickerLabel}>Wybiera kartę</small>
            <b className={styles.pickerName}>{picker.name}</b>
          </span>
        </div>
      ) : allPicked ? (
        <span className={styles.label}>
          Wszyscy wybrali — przejdź do fazy akcji
        </span>
      ) : (
        <span className={styles.label}>Wybór kart strategii</span>
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
                  ? `Wybrana: ${getPlayerDisplayName(owner.player, owner.player.color)}`
                  : picker
                    ? `Wybierz dla: ${picker.name}`
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
                <span className={styles.scTg} title="Trade goods na karcie">
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

      {/* Zmiana mówcy (kto zaczyna wybór) — operator, gdy trzeba. */}
      <div className={styles.speakerRow}>
        <span className={styles.label}>Mówca</span>
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
              title={`Ustaw mówcę: ${seat.name}`}
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
 * Panel produkcji (krok PRODUCTION) — pełnoprawny edytor stawiania jednostek.
 * W TI4 produkcja DODAJE nowe jednostki na planszę: statki do przestrzeni
 * aktywnego systemu, siły naziemne/struktury na wybraną planetę. Panel pokazuje
 * dostępne zasoby (podpowiedź) i pozwala +/− każdą jednostkę przez God-Mode
 * (``editUnit``). NIE waliduje limitu zasobów — gracz pilnuje kosztu sam
 * (asystent, nie sędzia). Reguła umiejscowienia: RULES.md 26.
 */
function ProductionPanel({
  activeSystem,
  activePlayerColor,
  planets,
}: {
  activeSystem: string;
  activePlayerColor: string | null;
  planets: string[];
}) {
  const gameData = useGameData();
  const { editUnit, produce } = useBoardEditor();
  const player = gameData?.playerData?.find(
    (p) => p.color === activePlayerColor,
  );
  const faction = player?.faction ?? null;
  const colorAlias = getColorAlias(player?.color);
  const { data } = useProductionHelp(faction);

  // Strefa docelowa dla sił naziemnych/struktur: wybrana planeta (domyślnie
  // pierwsza w systemie). Statki zawsze trafiają do „space".
  const [planet, setPlanet] = useState<string | null>(planets[0] ?? null);
  const [busy, setBusy] = useState(false);

  if (!faction || !data) {
    return (
      <span className={styles.prodNote}>
        Brak aktywnego gracza z frakcją — nie można produkować.
      </span>
    );
  }

  // Dodawanie jednostek idzie przez WALIDOWANY endpoint produkcji (koszt/limit/
  // blokada — RULES.md 33.2); odrzucenie pokazuje baner (notice). Usuwanie to
  // korekta God-Mode (nie jest akcją reguł). ``baseType`` z asyncId przez katalog.
  const addUnit = (baseType: string, zone: string) => {
    if (busy) return;
    setBusy(true);
    void produce(faction, [{ baseType, count: 1, zone }]).finally(() =>
      setBusy(false),
    );
  };

  const removeUnit = (asyncId: string, zone: string, count: number) => {
    if (busy) return;
    setBusy(true);
    void editUnit({ position: activeSystem, zone, faction, asyncId, delta: -count })
      .finally(() => setBusy(false));
  };

  const ships = data.units.filter((u) => u.placement === "space");
  const ground = data.units.filter((u) => u.placement === "planet");

  return (
    <div className={styles.production}>
      <div className={styles.prodHead}>
        <span className={styles.label}>
          <IconStack2 size={11} aria-hidden="true" />
          Produkcja
        </span>
        <span className={styles.prodRes} title="Zasoby z kontrolowanych planet">
          {data.availableResources} zasobów
        </span>
      </div>

      {/* Statki → przestrzeń aktywnego systemu. */}
      <span className={styles.prodZoneLabel}>Statki · przestrzeń</span>
      <div className={styles.unitGrid}>
        {ships.map((u) => (
          <ProductionUnitTile
            key={u.asyncId}
            unit={u}
            colorAlias={colorAlias}
            faction={faction}
            busy={busy}
            onAdd={() => addUnit(u.baseType, "space")}
            onRemove={() => removeUnit(u.asyncId, "space", u.unitsPerCost)}
          />
        ))}
      </div>

      {/* Siły naziemne / struktury → wybrana planeta. */}
      {ground.length > 0 && (
        <>
          <div className={styles.prodZoneRow}>
            <span className={styles.prodZoneLabel}>Naziemne · planeta</span>
            {planets.length > 0 ? (
              <div className={styles.planetTabs}>
                {planets.map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={styles.planetTab}
                    data-active={p === planet || undefined}
                    onClick={() => setPlanet(p)}
                  >
                    {p}
                  </button>
                ))}
              </div>
            ) : (
              <span className={styles.prodNote}>Brak planet w systemie</span>
            )}
          </div>
          {planet && (
            <div className={styles.unitGrid}>
              {ground.map((u) => (
                <ProductionUnitTile
                  key={u.asyncId}
                  unit={u}
                  colorAlias={colorAlias}
                  faction={faction}
                  busy={busy}
                  onAdd={() => addUnit(u.baseType, planet)}
                  onRemove={() => removeUnit(u.asyncId, planet, u.unitsPerCost)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** Kafelek jednej produkowalnej jednostki: ikona, koszt, +/− (stawia na planszę). */
function ProductionUnitTile({
  unit,
  colorAlias,
  faction,
  busy,
  onAdd,
  onRemove,
}: {
  unit: {
    asyncId: string;
    name: string;
    cost: number;
    unitsPerCost: number;
  };
  colorAlias: string;
  faction: string;
  busy: boolean;
  onAdd: () => void;
  onRemove: () => void;
}) {
  const perCost = unit.unitsPerCost > 1 ? `×${unit.unitsPerCost}` : "";
  return (
    <div className={styles.unitTile} title={unit.name}>
      <div className={styles.unitTileIcon}>
        <Unit
          unitType={unit.asyncId}
          colorAlias={colorAlias}
          faction={faction}
          scaleSprite
        />
      </div>
      <span className={styles.unitTileName}>{unit.name}</span>
      <span className={styles.unitTileCost} title="Koszt · ile sztuk za koszt">
        {unit.cost}
        {perCost}
      </span>
      <div className={styles.unitTileBtns}>
        <button
          type="button"
          className={styles.unitStep}
          disabled={busy}
          onClick={onRemove}
          aria-label={`Usuń ${unit.name}`}
          title="Usuń z planszy"
        >
          <IconMinus size={13} />
        </button>
        <button
          type="button"
          className={cx(styles.unitStep, styles.unitStepAdd)}
          disabled={busy}
          onClick={onAdd}
          aria-label={`Wyprodukuj ${unit.name}`}
          title="Wyprodukuj (postaw na planszy)"
        >
          <IconPlus size={13} />
        </button>
      </div>
    </div>
  );
}

/** Kroki akcji taktycznej + etykiety i ikony (RULES.md 19). */
const TACTICAL_STEPS: {
  step: string;
  label: string;
  short: string;
}[] = [
  { step: "MOVEMENT", label: "Ruch", short: "Ruch" },
  { step: "SPACE_CANNON", label: "Działa kosmiczne", short: "Działa" },
  { step: "SPACE_COMBAT", label: "Walka kosmiczna", short: "Walka" },
  { step: "INVASION", label: "Inwazja", short: "Inwazja" },
  { step: "PRODUCTION", label: "Produkcja", short: "Produkcja" },
];

/**
 * Panel akcji taktycznej (E3). Prowadzi gracza przez kroki (aktywacja → ruch →
 * działa → walka → inwazja → produkcja) BEZ walidacji reguł — gracze grają
 * fizycznie i wprowadzają wynik. Kroki są klikalnymi „pigułkami" (skok do kroku),
 * z wyróżnionym bieżącym. Krok produkcji otwiera pełny edytor stawiania jednostek.
 */
function TacticalActionPanel({
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
  const { activateSystem, tacticalSetStep, tacticalNextStep, endTactical } =
    useBoardEditor();
  const activateMode = useAppStore((s) => s.activateMode);
  const toggleActivateMode = useAppStore((s) => s.toggleActivateMode);
  const activateRequest = useAppStore((s) => s.activateRequest);
  const clearActivateRequest = useAppStore((s) => s.clearActivateRequest);
  const openCombat = useAppStore((s) => s.openCombat);
  const gameData = useGameData();
  const [busy, setBusy] = useState(false);

  const activeTile = activeSystem ? gameData?.tiles?.[activeSystem] : undefined;

  // Czy w aktywnym systemie są statki co najmniej dwóch graczy (jest walka?).
  const hasSpaceCombat = (() => {
    if (!activeTile) return false;
    const factionsWithShips = Object.values(
      activeTile.unitsByFaction ?? {},
    ).filter((entities) =>
      entities.some((e) => e.entityType === "unit" && e.count > 0),
    );
    return factionsWithShips.length >= 2;
  })();

  // Planety aktywnego systemu (inwazja / produkcja naziemna) — id z danych kafelka.
  const activePlanets = activeTile ? Object.keys(activeTile.planets ?? {}) : [];

  // Gdy w trybie aktywacji klik w kafelek zgłosił pozycję — aktywuj system,
  // wyłącz tryb i wyczyść żądanie (jednorazowa aktywacja na klik).
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
        title="Kliknij, potem wskaż system na mapie, aby go aktywować"
      >
        <IconTarget size={16} aria-hidden="true" />
        <span>
          {activateMode ? "Wskaż system na mapie…" : "Aktywuj system"}
        </span>
      </button>
    );
  }

  const currentIndex = TACTICAL_STEPS.findIndex((x) => x.step === tacticalStep);

  return (
    <div className={styles.tactical}>
      <div className={styles.tacticalHead}>
        <span className={styles.tacticalSystem}>
          {systemLabel ?? activeSystem}
        </span>
        <button
          type="button"
          className={styles.endAction}
          disabled={busy}
          onClick={() => void run(endTactical)}
          title="Zakończ bieżącą akcję taktyczną"
        >
          Zakończ akcję
        </button>
      </div>

      {/* Kroki jako klikalne pigułki — skok do dowolnego kroku (asystent). */}
      <div className={styles.stepPills} aria-label="Krok akcji taktycznej">
        {TACTICAL_STEPS.map((s, index) => {
          const state =
            index < currentIndex
              ? "done"
              : index === currentIndex
                ? "now"
                : undefined;
          return (
            <button
              key={s.step}
              type="button"
              className={styles.stepPill}
              data-s={state}
              disabled={busy}
              aria-current={state === "now" ? "step" : undefined}
              onClick={() => void run(() => tacticalSetStep(s.step))}
              title={`Przejdź do kroku: ${s.label}`}
            >
              <span className={styles.stepIndex}>{index + 1}</span>
              <span className={styles.stepName}>{s.short}</span>
            </button>
          );
        })}
      </div>

      {/* Zawartość bieżącego kroku. */}
      {tacticalStep === "SPACE_COMBAT" && (
        <div className={styles.stepBody}>
          {hasSpaceCombat ? (
            <button
              type="button"
              className={cx(styles.ctlBtn, styles.ctlPrimary)}
              onClick={() => openCombat(activeSystem, null)}
            >
              <IconSwords size={13} /> Otwórz okno walki kosmicznej
            </button>
          ) : (
            <span className={styles.prodNote}>
              Brak drugiej floty — walka kosmiczna niepotrzebna.
            </span>
          )}
        </div>
      )}

      {tacticalStep === "INVASION" && (
        <div className={styles.stepBody}>
          {activePlanets.length > 0 ? (
            <>
              <span className={styles.prodNote}>Walka naziemna na planecie:</span>
              <div className={styles.planetTabs}>
                {activePlanets.map((planet) => (
                  <button
                    key={planet}
                    type="button"
                    className={styles.planetTab}
                    onClick={() => openCombat(activeSystem, planet)}
                    title={`Okno walki naziemnej na ${planet}`}
                  >
                    {planet}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <span className={styles.prodNote}>Brak planet w systemie.</span>
          )}
        </div>
      )}

      {tacticalStep === "PRODUCTION" && (
        <ProductionPanel
          activeSystem={activeSystem}
          activePlayerColor={activePlayerColor}
          planets={activePlanets}
        />
      )}

      {/* Nawigacja kroków — „następny krok" zawsze dostępny. */}
      <button
        type="button"
        className={styles.nextStep}
        disabled={busy}
        onClick={() => void run(tacticalNextStep)}
        title="Przejdź do następnego kroku (po produkcji kończy akcję)"
      >
        Następny krok →
      </button>
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
    label: "Taktyczna",
    hint: "Aktywuj system: ruch, walka, inwazja, produkcja.",
    icon: <IconTarget size={15} aria-hidden="true" />,
  },
  {
    kind: "strategy",
    label: "Strategiczna",
    hint: "Rozlicz kartę strategii (secondary pozostałych graczy).",
    icon: <IconBolt size={15} aria-hidden="true" />,
  },
  {
    kind: "component",
    label: "Komponentowa",
    hint: "Zagraj kartę akcji, aktywuj lidera, technologię lub relikt.",
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
        Rodzaj akcji
      </span>

      {/* Trzy rodzaje akcji jako segmentowany wybór. */}
      <div className={styles.actionKinds} role="tablist" aria-label="Rodzaj akcji">
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
            Akcja komponentowa = zagranie karty z napisem „ACTION" (karta akcji,
            lider, technologia-akcja, relikt). Rozegraj ją przy stole, a efekt
            nanieś na planszę. Dedykowane pickery pojawią się w etapie E4.
          </span>
          <span className={styles.prodNote}>
            Wyczerpywanie planet, technologii i liderów robisz prawym przyciskiem
            myszy na komponencie w panelu gracza (menu „Wyczerp / Odśwież").
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
        Brak aktywnego gracza — nie można zagrać karty strategii.
      </span>
    );
  }
  if (myCards.length === 0) {
    return (
      <span className={styles.prodNote}>
        {active.name} nie ma karty strategii do zagrania.
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
              ? `${card.name} już zagrana (czeka na secondary)`
              : `Zagraj ${card.name} (primary + okno secondary)`
          }
        >
          <span
            className={styles.disc}
            style={toneStyle({ "--scc": SC_TONE[card.initiative] })}
          >
            {card.initiative}
          </span>
          <span className={styles.scName}>
            {card.exhausted ? `${card.name} — zagrana` : `Zagraj: ${card.name}`}
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
  phase,
  activePlayerId,
}: {
  phase: GamePhase;
  activePlayerId: string | null;
}) {
  const { endTurn, passTurn, nextPhase, nextRound } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  const isAction = phase === "action";
  const isAgenda = phase.startsWith("agenda");

  return (
    <div className={styles.controls}>
      {/* Faza akcji: główna akcja to „Zakończ turę" (duży, wyróżniony). */}
      {isAction && (
        <>
          <button
            type="button"
            className={cx(styles.ctlBtn, styles.ctlPrimary)}
            disabled={busy}
            onClick={() => void run(() => endTurn(activePlayerId ?? undefined))}
          >
            Zakończ turę
          </button>
          <button
            type="button"
            className={styles.ctlBtn}
            disabled={busy}
            onClick={() => void run(() => passTurn(activePlayerId ?? undefined))}
            title="Pasuj — pomijany do końca fazy akcji"
          >
            Pas
          </button>
        </>
      )}
      {/* Drobne sterowanie fazami (operator) — osobny, cichszy rząd. */}
      <div className={styles.controlsMinor}>
        {!isAgenda && (
          <button
            type="button"
            className={styles.ctlBtnGhost}
            disabled={busy}
            onClick={() => void run(nextPhase)}
          >
            Następna faza
          </button>
        )}
        <button
          type="button"
          className={styles.ctlBtnGhost}
          disabled={busy}
          onClick={() => void run(nextRound)}
        >
          Nowa runda
        </button>
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
        <PlateBody
          gameState={gameState}
          playerData={playerData}
          locations={locations}
        />
      </Collapse>
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

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { Collapse, UnstyledButton } from "@/ds";
import { IconChevronDown, IconSwords, IconTrophy } from "@tabler/icons-react";
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
}: {
  label: string;
  meta: ReactNode;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const action = isOpen ? "Collapse game state" : "Expand game state";
  return (
    <UnstyledButton
      className={styles.header}
      aria-controls={DETAILS_ID}
      aria-expanded={isOpen}
      aria-label={action}
      title={action}
      onClick={onToggle}
    >
      <span className={styles.phaseDot} aria-hidden="true" />
      <span className={styles.phaseLabel}>{label}</span>
      <span className={styles.headerMeta}>{meta}</span>
      <IconChevronDown
        aria-hidden="true"
        size={13}
        className={cx(styles.chevron, isOpen && styles.chevronOpen)}
      />
    </UnstyledButton>
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
      {phase === "action" && <FollowQueue seats={seats} />}
      {phase === "action" && (
        <TacticalActionPanel
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
      <PhaseControls phase={phase} />
    </>
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
 * Pomoc produkcji (krok PRODUCTION): dostępne zasoby aktywnego gracza + koszty
 * jego jednostek. Tylko podpowiedź — stawianie jednostek robi edytor planszy.
 */
function ProductionHelpRow({
  activePlayerColor,
}: {
  activePlayerColor: string | null;
}) {
  const gameData = useGameData();
  const player = gameData?.playerData?.find(
    (p) => p.color === activePlayerColor,
  );
  const faction = player?.faction ?? null;
  const { data } = useProductionHelp(faction);
  if (!data) return null;
  return (
    <div className={styles.controls}>
      <span className={styles.label} style={{ flex: 1 }}>
        Produkcja · zasoby: {data.availableResources}
      </span>
      {data.units.slice(0, 6).map((u) => (
        <span key={u.asyncId} className={styles.label} title={u.name}>
          {u.asyncId.toUpperCase()} {u.cost}
          {u.unitsPerCost > 1 ? `/${u.unitsPerCost}` : ""}
        </span>
      ))}
    </div>
  );
}

/** Kolejność kroków akcji taktycznej + ich etykiety (RULES.md 19). */
const TACTICAL_STEPS: { step: string; label: string }[] = [
  { step: "MOVEMENT", label: "Ruch" },
  { step: "SPACE_CANNON", label: "Działa kosmiczne" },
  { step: "SPACE_COMBAT", label: "Walka kosmiczna" },
  { step: "INVASION", label: "Inwazja" },
  { step: "PRODUCTION", label: "Produkcja" },
];

/**
 * Panel akcji taktycznej (E3). Prowadzi gracza przez kroki (aktywacja → ruch →
 * działa → walka → inwazja → produkcja) BEZ walidacji reguł — gracze grają
 * fizycznie i wprowadzają wynik. Gdy brak aktywnego systemu: przycisk włączający
 * tryb aktywacji (klik w kafelek). Gdy akcja trwa: bieżący krok + „Następny krok"
 * / „Zakończ akcję".
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
  const { activateSystem, tacticalNextStep, endTactical } = useBoardEditor();
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
    const factionsWithShips = Object.values(activeTile.unitsByFaction ?? {}).filter(
      (entities) =>
        entities.some((e) => e.entityType === "unit" && e.count > 0),
    );
    return factionsWithShips.length >= 2;
  })();

  // Planety aktywnego systemu (do kroku inwazji) — id planet z danych kafelka.
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

  const stepLabel =
    TACTICAL_STEPS.find((s) => s.step === tacticalStep)?.label ?? tacticalStep;

  return (
    <div className={styles.section}>
      <span className={styles.label}>
        <IconSwords size={11} aria-hidden="true" />
        Akcja taktyczna
      </span>
      {activeSystem ? (
        <>
          <div className={styles.track} aria-label="Krok taktyczny">
            {TACTICAL_STEPS.map((s) => {
              const current = TACTICAL_STEPS.findIndex(
                (x) => x.step === tacticalStep,
              );
              const index = TACTICAL_STEPS.findIndex((x) => x.step === s.step);
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
          <div className={styles.controls}>
            <span className={styles.label} style={{ flex: 1 }}>
              {systemLabel ?? activeSystem}
              {stepLabel ? ` · ${stepLabel}` : ""}
            </span>
            {hasSpaceCombat && (
              <button
                type="button"
                className={styles.ctlBtn}
                data-active
                onClick={() => openCombat(activeSystem, null)}
                title="Otwórz okno walki kosmicznej (asystent trafień)"
              >
                Walka
              </button>
            )}
            <button
              type="button"
              className={styles.ctlBtn}
              disabled={busy}
              onClick={() => void run(tacticalNextStep)}
            >
              Następny krok
            </button>
            <button
              type="button"
              className={styles.ctlBtn}
              disabled={busy}
              onClick={() => void run(endTactical)}
            >
              Zakończ akcję
            </button>
          </div>
          {tacticalStep === "INVASION" && activePlanets.length > 0 && (
            <div className={styles.controls}>
              <span className={styles.label} style={{ flex: 1 }}>
                Inwazja — walka naziemna:
              </span>
              {activePlanets.map((planet) => (
                <button
                  key={planet}
                  type="button"
                  className={styles.ctlBtn}
                  onClick={() => openCombat(activeSystem, planet)}
                  title={`Okno walki naziemnej na ${planet}`}
                >
                  {planet}
                </button>
              ))}
            </div>
          )}
          {tacticalStep === "PRODUCTION" && (
            <ProductionHelpRow activePlayerColor={activePlayerColor} />
          )}
        </>
      ) : (
        <div className={styles.controls}>
          <button
            type="button"
            className={styles.ctlBtn}
            data-active={activateMode || undefined}
            onClick={toggleActivateMode}
            title="Kliknij, potem wskaż system na mapie do aktywacji"
          >
            {activateMode ? "Wskaż system na mapie…" : "Aktywuj system"}
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Sterowanie przepływem gry (God-Mode / krokowa rozgrywka): zakończ turę, pas,
 * następna faza, nowa runda. Wywołuje endpointy przepływu (commit → historia).
 */
function PhaseControls({ phase }: { phase: GamePhase }) {
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
            onClick={() => void run(endTurn)}
          >
            Zakończ turę
          </button>
          <button
            type="button"
            className={styles.ctlBtn}
            disabled={busy}
            onClick={() => void run(passTurn)}
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
  const { phase, activeCombat } = gameState;
  const config = PHASE_CONFIGS[phase];
  const tone = activeCombat ? TONE.combat : config.tone;
  const label = activeCombat ? "Combat" : config.label;

  return (
    <section
      className={styles.panel}
      style={toneStyle({ "--ph": tone })}
      aria-label="Game state"
      data-open={isOpen || undefined}
    >
      <PlateHeader
        label={label}
        meta={headerMeta(round, gameState, playerData, isOpen)}
        isOpen={isOpen}
        onToggle={() => setIsOpen(!isOpen)}
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

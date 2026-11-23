import { useParams } from "react-router-dom";
import { IconBook2, IconChevronDown, IconCompass } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useStrategyCards } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import { coachHint, type CoachContext } from "./coachHint";
import { useTutorialStore } from "./tutorialStore";
import styles from "./CoachSection.module.css";

function seated(players: PlayerData[]): PlayerData[] {
  return players.filter((p) => p.faction && p.faction !== "neutral" && p.discordId);
}

/**
 * Gracz PRZY EKRANIE: w sieci moje miejsce (token); lokalnie i w trybie testowym (host bez
 * miejsca steruje każdym graczem) gracz z turą, jeśli jest człowiekiem, inaczej pierwszy
 * człowiek przy stole (solo z botami).
 */
function viewer(
  players: PlayerData[],
  turn: PlayerData | undefined,
  me: { network?: boolean; host?: boolean; player_id?: string | null } | undefined,
): PlayerData | undefined {
  // Tryb testowy jak lokalny - inaczej coach mówił „Watch the map” w turze gracza (plan U5/Z13).
  const testMode = me?.network === true && me.host === true && !me.player_id;
  if (me?.network && !testMode) return players.find((p) => p.discordId === me.player_id);
  if (turn && turn.controlType !== "BOT") return turn;
  return players.find((p) => p.controlType !== "BOT");
}

function useCoachContext(): CoachContext | null {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const { data: me } = useNetworkMe();
  const { data: cards } = useStrategyCards();
  if (!gameState) return null;
  const players = seated(gameData?.playerData ?? []);
  if (players.length === 0) return null;
  const turn = gameState.activeTurnPlayer
    ? players.find((p) => p.color === gameState.activeTurnPlayer)
    : undefined;
  const mine = viewer(players, turn, me);
  const myCards = (cards ?? []).filter((c) => mine && c.picked_by === mine.discordId);
  const window = gameState.pendingWindow;
  return {
    phase: gameState.phase ?? "unknown",
    setupPending: gameState.setup != null,
    winner: gameState.winnerId != null || gameState.phase === "finished",
    turnName: turn ? getPlayerFactionDisplayName(turn) : null,
    myTurn: turn != null && mine != null && turn.color === mine.color,
    turnIsBot: turn?.controlType === "BOT",
    myCardPicked: myCards.length > 0,
    myCardPlayed: myCards.some((c) => c.exhausted),
    passed: mine?.passed === true,
    tookAction: mine?.tookActionThisTurn === true,
    activeSystem: gameState.activeSystem ?? null,
    tacticalStep: gameState.tacticalStep ?? null,
    inCombat: gameState.activeCombat != null,
    windowOpen: window != null && !window.isComplete,
    myDecision: window != null && mine != null && window.currentResponderId === mine.discordId,
    isSpeaker: mine != null && gameState.speaker === mine.color,
    canAdvancePhase: gameState.canAdvancePhase === true,
  };
}

/**
 * Sekcja „What now?” samouczka — część panelu fazy (GameStatePanel, lewa góra): jedna
 * krótka podpowiedź, co zrobić w bieżącej fazie/kroku, i „Learn more” do właściwego
 * rozdziału How to play. Dawniej osobne pływające okno w lewym dole — nachodziło na panel
 * fazy i ikonę czatu, więc (decyzja użytkownika: mniej okien) żyje w jednym panelu z fazą.
 * Nagłówek zwija sekcję do jednej linii (wybór zapamiętany w `tutorialStore`).
 */
export function CoachSection() {
  const context = useCoachContext();
  const coachOpen = useTutorialStore((s) => s.coachOpen);
  const setCoachOpen = useTutorialStore((s) => s.setCoachOpen);
  const openGuide = useTutorialStore((s) => s.openGuide);
  if (!context) return null;
  const hint = coachHint(context);
  const toggle = coachOpen ? "Hide hints" : "Show hints: what to do now";

  return (
    <section
      className={styles.section}
      aria-label="What now?"
      aria-live="polite"
      data-act={hint.act || undefined}
    >
      <button
        type="button"
        className={styles.head}
        aria-expanded={coachOpen}
        aria-label={toggle}
        title={toggle}
        onClick={() => setCoachOpen(!coachOpen)}
      >
        <IconCompass size={14} aria-hidden="true" className={styles.compass} />
        <span className={styles.kicker}>What now?</span>
        {!coachOpen && <span className={styles.peek}>{hint.title}</span>}
        <IconChevronDown
          size={13}
          aria-hidden="true"
          className={styles.chevron}
          data-open={coachOpen || undefined}
        />
      </button>
      {coachOpen && (
        <div className={styles.body}>
          <b className={styles.title}>{hint.title}</b>
          <ul className={styles.lines}>
            {hint.lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <button type="button" className={styles.more} onClick={() => openGuide(hint.chapter)}>
            <IconBook2 size={14} aria-hidden="true" /> Learn more
          </button>
        </div>
      )}
    </section>
  );
}

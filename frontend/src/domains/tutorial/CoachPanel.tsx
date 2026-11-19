import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { IconBook2, IconMinus, IconCompass } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useStrategyCards } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import type { PlayerData } from "@/entities/data/types";
import { coachHint, type CoachContext } from "./coachHint";
import { useTutorialStore } from "./tutorialStore";
import styles from "./CoachPanel.module.css";

function seated(players: PlayerData[]): PlayerData[] {
  return players.filter((p) => p.faction && p.faction !== "neutral" && p.discordId);
}

/**
 * Gracz PRZY EKRANIE: w sieci moje miejsce (token); lokalnie gracz z turą, jeśli jest
 * człowiekiem, inaczej pierwszy człowiek przy stole (solo z botami).
 */
function viewer(
  players: PlayerData[],
  turn: PlayerData | undefined,
  me: { network?: boolean; player_id?: string | null } | undefined,
): PlayerData | undefined {
  if (me?.network) return players.find((p) => p.discordId === me.player_id);
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
 * Panel „What now?” samouczka (lewy dół, nad ikoną czatu): jedna krótka podpowiedź, co
 * zrobić w bieżącej fazie/kroku, i „Learn more” do właściwego rozdziału How to play.
 * Zwija się do ikony (wybór zapamiętany), przesuwany jak inne panele (`useDraggablePanel`).
 */
export function CoachPanel() {
  const context = useCoachContext();
  const coachOpen = useTutorialStore((s) => s.coachOpen);
  const setCoachOpen = useTutorialStore((s) => s.setCoachOpen);
  const openGuide = useTutorialStore((s) => s.openGuide);
  const drag = useDraggablePanel("panel:coach");
  if (!context) return null;
  const hint = coachHint(context);

  if (!coachOpen) {
    return createPortal(
      <button
        type="button"
        className={styles.launcher}
        data-act={hint.act || undefined}
        onClick={() => setCoachOpen(true)}
        aria-label="Show hints: what to do now"
        title="What now?"
      >
        <IconCompass size={18} aria-hidden="true" />
      </button>,
      document.body,
    );
  }

  return createPortal(
    <section
      className={styles.panel}
      aria-label="What now?"
      aria-live="polite"
      data-act={hint.act || undefined}
      ref={drag.ref}
      style={drag.style}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
    >
      <header
        className={styles.head}
        data-grab
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move · double-click resets position"
      >
        <IconCompass size={15} aria-hidden="true" />
        <span className={styles.kicker}>What now?</span>
        <button
          type="button"
          className={styles.close}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => setCoachOpen(false)}
          aria-label="Hide hints"
          title="Hide hints"
        >
          <IconMinus size={15} aria-hidden="true" />
        </button>
      </header>
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
    </section>,
    document.body,
  );
}

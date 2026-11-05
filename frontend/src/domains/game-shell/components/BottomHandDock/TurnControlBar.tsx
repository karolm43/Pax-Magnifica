import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { IconBolt } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor, useStrategyCards } from "@/api/useBoardEditor";
import type { PlayerData } from "@/entities/data/types";
import styles from "./TurnControlBar.module.css";

/* Numer inicjatywy → barwa karty strategii (spójne z panelem stanu gry). */
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

/**
 * Pasek sterowania turą aktywnego gracza — PRZYPIĘTY na mapie (w BottomHandDock),
 * żeby „Pass" i wybrana karta strategii były widoczne wprost na głównym ekranie
 * (bez wchodzenia w zakładkę gracza). Pokazuje:
 *  - wybraną kartę strategii aktywnego gracza (numer + nazwa + „Played"/„Not played"),
 *  - akcje tury: Play (zagranie karty), Pass (bramka: nie można pasować przed
 *    akcją strategiczną — RULES.md 31.2), End turn, Next phase.
 *
 * Renderuje się tylko w FAZIE AKCJI (``action``). W innych fazach zwraca null —
 * sterowanie fazami strategii/statusu/agendy ma własne miejsca.
 */
export function TurnControlBar({ active }: { active: PlayerData }) {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: cards } = useStrategyCards();
  const { playStrategyCard, passTurn, endTurn, nextPhase } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const phase = gameState?.phase ?? "unknown";
  const isAction = phase === "action";

  const myCards = (cards ?? []).filter((c) => c.picked_by === active.discordId);
  const hasCard = myCards.length > 0;
  const played = myCards.some((c) => c.exhausted);
  const canPass = !hasCard || played;
  // Karta jeszcze niezagrana (do przycisku „Play").
  const unplayed = myCards.find((c) => !c.exhausted) ?? null;

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn().finally(() => setBusy(false));
  };

  return (
    <div className={styles.bar}>
      {/* Status karty strategii aktywnego gracza (widoczny zawsze, gdy ma kartę). */}
      <div className={styles.sc}>
        <IconBolt size={13} aria-hidden="true" className={styles.scIcon} />
        {hasCard ? (
          myCards.map((card) => (
            <span
              key={card.initiative}
              className={styles.scCard}
              data-played={card.exhausted || undefined}
              style={{ "--scc": SC_TONE[card.initiative] } as CSSProperties}
            >
              <b className={styles.scDisc}>{card.initiative}</b>
              <span className={styles.scName}>{card.name}</span>
              {isAction && (
                <small className={styles.scState}>
                  {card.exhausted ? "Played" : "Not played"}
                </small>
              )}
            </span>
          ))
        ) : (
          <span className={styles.scEmpty}>No Strategy Card</span>
        )}
      </div>

      {/* Akcje tury — Play/Pass/End turn tylko w fazie akcji; Next phase zawsze. */}
      <div className={styles.actions}>
        {isAction && unplayed && (
          <button
            type="button"
            className={styles.play}
            disabled={busy}
            onClick={() =>
              run(() => playStrategyCard(active.discordId, unplayed.initiative))
            }
            title={`Play ${unplayed.name} (primary + secondary window)`}
          >
            Play {unplayed.name}
          </button>
        )}
        {isAction && (
          <>
            <button
              type="button"
              className={styles.btn}
              disabled={busy || !canPass}
              onClick={() => run(() => passTurn(active.discordId))}
              title={
                canPass
                  ? "Pass — skipped for the rest of the Action Phase"
                  : "Play your Strategy Card before passing."
              }
            >
              Pass
            </button>
            <button
              type="button"
              className={styles.endTurn}
              disabled={busy}
              onClick={() => run(() => endTurn(active.discordId))}
              title="End your turn"
            >
              End turn
            </button>
          </>
        )}
        <button
          type="button"
          className={styles.ghost}
          disabled={busy}
          onClick={() => run(nextPhase)}
          title="Advance to the next phase"
        >
          Next phase
        </button>
      </div>
    </div>
  );
}

export default TurnControlBar;

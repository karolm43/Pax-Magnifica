import { useState } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import {
  useBoardEditor,
  useStrategyCards,
  type StrategyCardState,
} from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import {
  getStrategyCardById,
  getStrategyCardByInitiative,
} from "@/entities/lookup/strategyCards";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import type { PlayerData } from "@/entities/data/types";
import styles from "./TurnControls.module.css";

/**
 * Sterowanie turą aktywnego gracza — PRZYPIĘTE na mapie, ODDZIELNE od ręki kart.
 *
 * Pokazuje wybraną kartę strategii aktywnego gracza jako OBRAZEK karty (ta sama
 * grafika co w fazie strategii, ``getStrategyCardById(id).imageURL``). Zagranie
 * karty NIE jest osobnym przyciskiem — to nakładka „Play", która pojawia się PO
 * NAJECHANIU na kartę (tylko w fazie akcji, gdy jeszcze niezagrana). Zagrana karta
 * ma nakładkę-znacznik „Played".
 *
 * Obok karty: osobne przyciski tury — Pass (bramka: nie można pasować przed akcją
 * strategiczną, RULES.md 31.2), End turn (faza akcji) oraz Next phase (zawsze).
 *
 * Renderuje się, gdy jest aktywny gracz i (ma kartę strategii ALBO trwa faza, w
 * której sterowanie turą ma sens). Zwraca null poza fazami gry.
 */
export function TurnControls() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: cards } = useStrategyCards();
  const gameData = useGameData();
  const { playStrategyCard, passTurn, endTurn, nextPhase } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const phase = gameState?.phase ?? "unknown";
  // Sterowanie turą ma sens tylko w fazie akcji i strategii (Next phase).
  if (phase !== "action" && phase !== "strategy") return null;

  const players: PlayerData[] = gameData?.playerData ?? [];
  const active = players.find((p) => p.active);
  if (!active) return null;

  const isAction = phase === "action";
  const myCards = (cards ?? []).filter((c) => c.picked_by === active.discordId);
  const hasCard = myCards.length > 0;
  const played = myCards.some((c) => c.exhausted);
  const canPass = !hasCard || played;

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn().finally(() => setBusy(false));
  };

  return (
    <>
      {/* STREFA KARTY (lewy dół) — karta strategii jak leżąca przed graczem.
          Duży obrazek PNG; „Play" pojawia się na hover (nie jest osobnym
          przyciskiem). */}
      <div className={styles.cardZone} aria-label="Your Strategy Card">
        <div className={styles.cards}>
          {hasCard ? (
            myCards.map((card) => (
              <StrategyCardImage
                key={card.initiative}
                card={card}
                canPlay={isAction && !card.exhausted}
                busy={busy}
                onPlay={() =>
                  run(() => playStrategyCard(active.discordId, card.initiative))
                }
              />
            ))
          ) : (
            <span className={styles.noCard}>No Strategy Card</span>
          )}
        </div>
      </div>

      {/* STREFA PRZYCISKÓW (prawy dół) — osobny, wyraźny panel akcji tury.
          Celowo z dala od karty i od ręki. */}
      <div className={styles.actionZone} aria-label="Turn actions">
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
    </>
  );
}

/** Jedna karta strategii jako obrazek + nakładka „Play"/„Played" na hover. */
function StrategyCardImage({
  card,
  canPlay,
  busy,
  onPlay,
}: {
  card: StrategyCardState;
  canPlay: boolean;
  busy: boolean;
  onPlay: () => void;
}) {
  const [failed, setFailed] = useState(false);
  const def =
    getStrategyCardById(card.id) ?? getStrategyCardByInitiative(card.initiative);
  const imageURL = def?.imageURL;
  const showImage = !!imageURL && !failed;
  const name = card.name || SC_NAMES[card.initiative] || "—";

  return (
    <div
      className={styles.card}
      data-played={card.exhausted || undefined}
      title={name}
    >
      {showImage ? (
        <img
          className={styles.cardImage}
          src={imageURL}
          alt={name}
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
          disabled={busy}
          onClick={onPlay}
          title={`Play ${name} (primary + secondary window)`}
        >
          Play
        </button>
      ) : card.exhausted ? (
        <span className={styles.playedBadge}>Played</span>
      ) : null}
    </div>
  );
}

export default TurnControls;

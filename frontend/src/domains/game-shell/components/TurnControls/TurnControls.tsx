import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import {
  IconBolt,
  IconHandStop,
  IconPlayerPlayFilled,
  IconPlayerTrackNextFilled,
  IconChevronsRight,
} from "@tabler/icons-react";
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
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import styles from "./TurnControls.module.css";

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
 *    duże przyciski z ikonami i poświatą) — Pass / End turn / Next phase.
 *
 * Render tylko w fazie akcji/strategii i gdy jest aktywny gracz (inaczej null).
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
  if (phase !== "action" && phase !== "strategy") return null;

  const players: PlayerData[] = gameData?.playerData ?? [];
  const active = players.find((p) => p.active);
  if (!active) return null;

  const isAction = phase === "action";
  const myCards = (cards ?? []).filter((c) => c.picked_by === active.discordId);
  const hasCard = myCards.length > 0;
  const played = myCards.some((c) => c.exhausted);
  const canPass = !hasCard || played;
  const activeName = getPlayerFactionDisplayName(active);

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn().finally(() => setBusy(false));
  };

  return (
    <>
      {/* STREFA KARTY (lewy dół) — karta leżąca przed graczem. */}
      <div className={styles.cardZone} aria-label="Your Strategy Card">
        {hasCard ? (
          <div className={styles.cards}>
            {myCards.map((card, i) => (
              <StrategyCardImage
                key={card.initiative}
                card={card}
                index={i}
                canPlay={isAction && !card.exhausted}
                busy={busy}
                onPlay={() =>
                  run(() => playStrategyCard(active.discordId, card.initiative))
                }
              />
            ))}
          </div>
        ) : (
          <div className={styles.noCard}>
            <IconBolt size={15} aria-hidden="true" />
            <span>
              {isAction ? "No Strategy Card" : "Pick a Strategy Card"}
            </span>
          </div>
        )}
      </div>

      {/* STREFA PRZYCISKÓW (prawy dół) — elegancki panel akcji tury. */}
      <div className={styles.actionZone} aria-label="Turn actions">
        <header className={styles.actionHead}>
          {active.faction && (
            <CircularFactionIcon faction={active.faction} size={22} />
          )}
          <span className={styles.actionHeadText}>
            <small className={styles.actionPhase}>
              {isAction ? "Action phase" : "Strategy phase"}
            </small>
            <b className={styles.actionWho}>{activeName}</b>
          </span>
        </header>

        <div className={styles.actionBtns}>
          {isAction && (
            <>
              <button
                type="button"
                className={styles.pass}
                style={{ "--d": "0ms" } as CSSProperties}
                disabled={busy || !canPass}
                onClick={() => run(() => passTurn(active.discordId))}
                title={
                  canPass
                    ? "Pass — skipped for the rest of the Action Phase"
                    : "Play your Strategy Card before passing."
                }
              >
                <IconHandStop size={16} aria-hidden="true" />
                <span>Pass</span>
              </button>
              <button
                type="button"
                className={styles.endTurn}
                style={{ "--d": "60ms" } as CSSProperties}
                disabled={busy}
                onClick={() => run(() => endTurn(active.discordId))}
                title="End your turn"
              >
                <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
                <span>End turn</span>
              </button>
            </>
          )}
          <button
            type="button"
            className={styles.nextPhase}
            style={{ "--d": isAction ? "120ms" : "0ms" } as CSSProperties}
            disabled={busy}
            onClick={() => run(nextPhase)}
            title="Advance to the next phase"
          >
            <IconChevronsRight size={16} aria-hidden="true" />
            <span>Next phase</span>
          </button>
        </div>

        {/* Podpowiedź, gdy Pass zablokowany (zanim zagrasz kartę). */}
        {isAction && !canPass && (
          <p className={styles.hint}>Play your Strategy Card first to pass.</p>
        )}
      </div>
    </>
  );
}

/** Jedna karta strategii jako obrazek + nakładka „Play"/„Played" na hover. */
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
  const def =
    getStrategyCardById(card.id) ?? getStrategyCardByInitiative(card.initiative);
  const imageURL = def?.imageURL;
  const showImage = !!imageURL && !failed;
  const name = card.name || SC_NAMES[card.initiative] || "—";
  const hue = def?.colourHexCode || SC_HUE[card.initiative] || "#888";

  return (
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
    >
      <div className={styles.cardInner}>
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
            <IconPlayerPlayFilled size={22} aria-hidden="true" />
            <span>Play</span>
          </button>
        ) : card.exhausted ? (
          <span className={styles.playedBadge}>Played</span>
        ) : null}
      </div>
    </div>
  );
}

export default TurnControls;

import { useEffect, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { IconArrowRight, IconCheck, IconCompass } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { getTileById } from "@/entities/lookup/systems";
import { getPlanetData } from "@/entities/lookup/planets";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import {
  useExploration,
  useExplorationActions,
  type ExploreCard,
  type ExploreOption,
  type ExplorationView,
} from "./useExploration";
import styles from "./ExplorationOverlay.module.css";

const DECK_LABEL: Record<string, string> = {
  cultural: "Cultural",
  hazardous: "Hazardous",
  industrial: "Industrial",
};

const FATE_LABEL: Record<string, string> = {
  discarded: "discarded",
  attached: "attached to the planet",
  kept: "kept in your play area",
  purged: "purged",
};

const planetName = (id: string) => getPlanetData(id)?.name ?? id;

/** Karta eksploracji: kolor talii, nazwa, treść i cytat (karta jest jawna dla wszystkich). */
function CardFace({ card, planet }: { card: ExploreCard; planet?: string }) {
  return (
    <article className={styles.card} data-deck={card.deck.toLowerCase()}>
      <header className={styles.cardHead}>
        <span className={styles.deckTag}>
          {DECK_LABEL[card.deck] ?? card.deck} · {card.resolution}
        </span>
        {planet && <span className={styles.cardPlanet}>{planetName(planet)}</span>}
      </header>
      <h3 className={styles.cardName}>{card.name}</h3>
      <p className={styles.cardText}>{card.text}</p>
      {card.flavorText && <p className={styles.flavor}>{card.flavorText}</p>}
    </article>
  );
}

function ExplorationWindow({ view }: { view: ExplorationView }) {
  const gameData = useGameData();
  const look = usePlayerLook();
  const actions = useExplorationActions();
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  // Opcja czekająca na parametr (np. wybór puli żetonu).
  const [pending, setPending] = useState<ExploreOption | null>(null);

  const player = view.player ? look(view.player) : null;
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName = tile
    ? (getTileById(tile.systemId)?.name ?? view.position)
    : view.position;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
      setPending(null);
    } catch {
      // Powód (422) pokazuje panel komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  if (hidden) {
    return createPortal(
      <button
        type="button"
        className={styles.restore}
        onClick={() => setHidden(false)}
      >
        <IconCompass size={16} aria-hidden="true" /> Exploration - show
      </button>,
      document.body,
    );
  }

  const current = view.current;
  const nextUp = view.queue.length;
  const choose = (option: ExploreOption) => {
    if (option.params.length > 0) setPending(option);
    else void run(() => actions.resolve(option.id));
  };

  return createPortal(
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label={`Exploration of ${systemName ?? ""}`}
      style={{ "--att-rgb": player?.rgb ?? "148 163 184" } as CSSProperties}
    >
      <div className={styles.panel}>
        <header className={styles.topBar}>
          <span className={styles.title}>
            <IconCompass size={20} aria-hidden="true" /> Exploration
            <small>{systemName}</small>
          </span>
          {view.player && (
            <span className={styles.who}>
              <CircularFactionIcon faction={view.player} size={22} />
              {player?.name}
            </span>
          )}
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => setHidden(true)}
          >
            Hide
          </button>
        </header>

        {nextUp > 0 && (
          <section className={styles.queue} aria-label="Exploration order">
            <h4>
              {current
                ? "Next in line"
                : nextUp > 1
                  ? "Choose which planet to explore first"
                  : "Explore this planet"}
            </h4>
            <ol>
              {view.queue.map((q, index) => (
                <li key={q.planet} className={styles.queueItem}>
                  <b className={styles.order}>
                    {current ? index + 2 : index + 1}
                  </b>
                  <span className={styles.queueName}>{planetName(q.planet)}</span>
                  <span className={styles.traits}>
                    {q.traits.map((t) => DECK_LABEL[t] ?? t).join(" / ")}
                  </span>
                  {!current &&
                    q.traits.map((trait) => (
                      <button
                        key={trait}
                        type="button"
                        className={styles.primaryBtn}
                        disabled={busy}
                        onClick={() =>
                          void run(() =>
                            actions.draw(
                              q.planet,
                              q.traits.length > 1 ? trait : undefined,
                            ),
                          )
                        }
                      >
                        Draw{q.traits.length > 1 ? ` ${DECK_LABEL[trait]}` : ""}
                      </button>
                    ))}
                </li>
              ))}
            </ol>
          </section>
        )}

        {current && (
          <section className={styles.stage}>
            <CardFace card={current.card} planet={current.planet} />
            <div className={styles.options}>
              <h4>How do you resolve it?</h4>
              {pending ? (
                <>
                  <p className={styles.hint}>{pending.label}</p>
                  <div className={styles.paramRow}>
                    {pending.params.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        className={styles.primaryBtn}
                        disabled={busy}
                        onClick={() =>
                          void run(() => actions.resolve(pending.id, p.id))
                        }
                      >
                        {p.label}
                      </button>
                    ))}
                    <button
                      type="button"
                      className={styles.ghostBtn}
                      onClick={() => setPending(null)}
                    >
                      Back
                    </button>
                  </div>
                </>
              ) : (
                current.options.map((o) => (
                  <div key={o.id} className={styles.optionRow}>
                    <button
                      type="button"
                      className={
                        o.id === "skip" ? styles.ghostBtn : styles.primaryBtn
                      }
                      disabled={busy || !o.enabled}
                      onClick={() => choose(o)}
                    >
                      {o.label}
                    </button>
                    {!o.enabled && o.reason && (
                      <span className={styles.reason}>{o.reason}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        )}

        {view.log.length > 0 && (
          <section className={styles.log} aria-label="Resolved explorations">
            <h4>Resolved</h4>
            <ul>
              {view.log.map((entry, i) => (
                <li key={`${entry.card.cardId}-${i}`} data-deck={entry.deck}>
                  <b>{planetName(entry.planet)}</b>
                  <span>
                    {entry.card.name} - {entry.summary}
                  </span>
                  <small>{FATE_LABEL[entry.fate] ?? entry.fate}</small>
                </li>
              ))}
            </ul>
          </section>
        )}

        {view.done && (
          <footer className={styles.footer}>
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={busy}
              onClick={() => void run(actions.finish)}
            >
              <IconCheck size={14} aria-hidden="true" /> Done exploring{" "}
              <IconArrowRight size={14} aria-hidden="true" />
            </button>
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}

/**
 * Okno EKSPLORACJI (RULES.md 46) - pojawia się samo po Establish Control, gdy gracz przejął
 * planetę niczyją (``gameState.activeExploration``). Karta jest dobierana automatycznie, gdy nie
 * ma wyboru (jedna planeta, jedna cecha); przy kilku planetach gracz ustala kolejność, przy
 * kilku cechach - talię. Każda karta jest rozstrzygana w całości, zanim padnie następna.
 */
export function ExplorationOverlay() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const queryClient = useQueryClient();
  const active = gameState?.activeExploration != null;
  const { data: view } = useExploration(active);

  // Każda zmiana stanu gry odświeża widok eksploracji.
  useEffect(() => {
    if (active) void queryClient.invalidateQueries({ queryKey: ["exploration"] });
  }, [gameState, active, queryClient]);

  if (!active || !view?.active) return null;
  return <ExplorationWindow key={view.position} view={view} />;
}

export default ExplorationOverlay;

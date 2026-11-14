import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { IconBolt, IconChevronUp, IconMinus, IconX } from "@tabler/icons-react";
import { fetchJson } from "@/api/fetchJson";
import { useActivityFeed } from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import type { FactionComponentKind } from "@/api/useFactionComponents";
import { DEFAULT_GAME_ID } from "@/config";
import { FactionComponentUseModal } from "@/domains/game-shell/components/TurnControls/FactionComponentUseModal";
import { ActionCardPlayModal } from "@/domains/game-shell/components/TurnControls/ActionCardPlayModal";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { HandReactionRows, type HandPlay } from "./HandReactionPrompts";
import { TransactionOfferPrompt } from "./TransactionOfferPrompt";
import { humanHandOwners } from "./handReactions";
import { OfferCard, useDecisionOffers } from "./OffersModal";
import { isResearchOffer } from "./ResearchOfferOverlay";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import styles from "./AbilityPrompts.module.css";

/*
 * „Available now” (RULES.md 62.0): zdolności typu „During X: you may…” (bohater Sardakk po ruchu,
 * G'hom Sek'kus przy lądowaniu, Munitions Reserves po rzucie, Doctor Sucaban przy badaniu…) nie
 * są reakcją na zdarzenie, więc silnik nie tworzy dla nich oferty. Ta karta pokazuje je SAMA,
 * gdy tylko robią się użyteczne - gracz nie musi ich szukać w menu lidera.
 */

export type AvailableNow = {
  player_id: string;
  kind: FactionComponentKind;
  component_id: string;
  name: string;
  text: string;
};

const KIND_LABEL: Record<FactionComponentKind, string> = {
  leader: "Leader",
  ability: "Faction ability",
  breakthrough: "Breakthrough",
};

export const promptKey = (row: AvailableNow): string =>
  `${row.player_id}:${row.kind}:${row.component_id}`;

/**
 * Odrzucone „Not now” wracają dopiero, gdy zdolność przestanie być dostępna i znów się pojawi
 * (nowe okno), zamiast wyskakiwać przy każdej zmianie stanu.
 */
export function pruneDismissed(dismissed: Set<string>, available: AvailableNow[]): Set<string> {
  const live = new Set(available.map(promptKey));
  const kept = [...dismissed].filter((key) => live.has(key));
  return kept.length === dismissed.size ? dismissed : new Set(kept);
}

/**
 * CENTRUM DECYZJI - jedno miejsce na wszystko, co gracz może / musi zrobić TERAZ (prawy dół,
 * przeciągalne, zwijane do pastylki): bieżąca decyzja (oferta, wybór celu), propozycja transakcji,
 * karty z ręki z otwartym oknem i zdolności „Available now”. Wszystko jako karty o jednym
 * wyglądzie, w jednej kolumnie (wcześniej trzy osobne pływające okna w dwóch rogach ekranu).
 */
export function DecisionCenter() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const { data, refetch } = useQuery({
    queryKey: ["factionComponentAvailableNow"],
    staleTime: 0,
    queryFn: async () =>
      (
        await fetchJson<{ components: AvailableNow[] }>(
          "/bot/faction-component/available-now",
          "available abilities",
        )
      ).components,
  });
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [using, setUsing] = useState<AvailableNow | null>(null);
  const [playing, setPlaying] = useState<HandPlay | null>(null);
  const [minimized, setMinimized] = useState(false);
  const drag = useDraggablePanel("decisionCenter.pos.v1");
  const offer = useDecisionOffers();
  const research = offer.first !== null && isResearchOffer(offer.first);
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: me } = useNetworkMe();

  // Każda zmiana stanu gry może otworzyć albo zamknąć okno zdolności.
  useEffect(() => {
    void refetch();
  }, [gameState, refetch]);

  const available = useMemo(() => data ?? [], [data]);
  useEffect(() => {
    setDismissed((cur) => pruneDismissed(cur, available));
  }, [available]);

  const visible = available.filter((row) => !dismissed.has(promptKey(row)));
  const { data: feed } = useActivityFeed();
  // Lokalnie (kilku ludzi przy jednym ekranie) podpisujemy, czyja to zdolność.
  const severalHumans = new Set(available.map((r) => r.player_id)).size > 1 ||
    Object.values(feed?.players ?? {}).filter((p) => !p.is_bot).length > 1;
  const playerName = (id: string) => feed?.players[id]?.display_name ?? id;
  // Okna reakcji kart z ręki: ręce ludzi przy tym ekranie (sieć: tylko moja).
  const handOwners = humanHandOwners(me, feed?.players);
  const severalHands = handOwners.length > 1;

  return (
    <>
      {/* Decyzja badania = pełne okno badania (poza kolumną). */}
      {offer.first && research && <OfferCard offer={offer.first} queued={offer.queued} />}
      {minimized && !using && !playing &&
        createPortal(
          <button
            type="button"
            className={styles.pill}
            onClick={() => setMinimized(false)}
            title="Show decisions"
          >
            <IconChevronUp size={15} aria-hidden="true" />
            <span>Decisions</span>
          </button>,
          document.body,
        )}
      {/* Kolumna chowa się na czas formularza, który z niej otwarto (nie zasłania wyborów). */}
      {!using && !playing && !minimized &&
        createPortal(
          <div
            className={styles.stack}
            aria-label="Decisions"
            data-draggable-panel
            data-dragging={drag.isDragging || undefined}
            style={drag.style}
          >
            <div
              className={styles.bar}
              onPointerDown={drag.onHandlePointerDown}
              onDoubleClick={drag.reset}
              title="Drag to move · double-click resets position"
            >
              <span className={styles.barTitle}>Decisions</span>
              <button
                type="button"
                className={styles.iconBtn}
                data-no-drag
                onClick={() => setMinimized(true)}
                aria-label="Minimize decisions to see the board"
                title="Minimize to see the board"
              >
                <IconMinus size={14} aria-hidden="true" />
              </button>
            </div>
            <div className={styles.body}>
            {offer.first && !research && (
              <OfferCard offer={offer.first} queued={offer.queued} />
            )}
            <TransactionOfferPrompt
              gameState={gameState}
              handOwners={handOwners}
              nameOf={playerName}
            />
            {handOwners.map((id) => (
              <HandReactionRows
                key={id}
                gameId={gameId}
                playerId={id}
                playerLabel={severalHands ? playerName(id) : null}
                onPlay={setPlaying}
              />
            ))}
            {visible.map((row) => (
              <section key={promptKey(row)} className={styles.card} aria-label={`Available now: ${row.name}`}>
                <header className={styles.head}>
                  <IconBolt size={16} aria-hidden="true" className={styles.icon} />
                  <span className={styles.titleBox}>
                    <small className={styles.kind}>
                      Available now · {KIND_LABEL[row.kind]}
                      {severalHumans ? ` · ${playerName(row.player_id)}` : ""}
                    </small>
                    <b className={styles.title}>{row.name}</b>
                  </span>
                  <button
                    type="button"
                    className={styles.iconBtn}
                    aria-label={`Not now: ${row.name}`}
                    onClick={() => setDismissed((cur) => new Set(cur).add(promptKey(row)))}
                  >
                    <IconX size={14} aria-hidden="true" />
                  </button>
                </header>
                <p className={styles.text}>{row.text}</p>
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.ghost}
                    onClick={() => setDismissed((cur) => new Set(cur).add(promptKey(row)))}
                  >
                    Not now
                  </button>
                  <button type="button" className={styles.primary} onClick={() => setUsing(row)}>
                    Use {row.name}
                  </button>
                </div>
              </section>
            ))}
            </div>
          </div>,
          document.body,
        )}
      {playing && (
        <ActionCardPlayModal
          key={`${playing.tab}-${playing.id}`}
          kind={playing.tab === "notes" ? "note" : "card"}
          cardId={playing.id}
          cardName={playing.name}
          playerId={playing.playerId}
          onClose={() => setPlaying(null)}
          onPlayed={() => setPlaying(null)}
        />
      )}
      {using && (
        <FactionComponentUseModal
          kind={using.kind}
          componentId={using.component_id}
          name={using.name}
          playerId={using.player_id}
          onClose={() => setUsing(null)}
          onDone={() => {
            setUsing(null);
            void refetch();
          }}
        />
      )}
    </>
  );
}

export default DecisionCenter;

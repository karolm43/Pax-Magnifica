import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { IconDice5, IconTarget } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { PromptDock } from "@/domains/strategy/PromptDock";
import { Hint } from "@/domains/strategy/PromptParts";
import { useMapPick } from "@/domains/strategy/mapPick";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import {
  useThundersEdge,
  useThundersEdgeActions,
  type ThundersEdgeView,
} from "./useThundersEdge";
import styles from "./ThundersEdge.module.css";

const COLOR_LABEL: Record<string, string> = {
  BIOTIC: "Biotic",
  CYBERNETIC: "Cybernetic",
  PROPULSION: "Propulsion",
  WARFARE: "Warfare",
};

const HUE = "#a78bfa";

/** Wynik rzutu na The Fracture: kostka d10 z animacją (rzut jest silnikowy - UI tylko pokazuje). */
function RollBanner({ view, onDismiss }: { view: ThundersEdgeView; onDismiss: () => void }) {
  const look = usePlayerLook();
  const roll = view.lastRoll;
  if (!roll) return null;
  const who = view.players[roll.playerId] ?? roll.playerId;
  return createPortal(
    <div className={styles.rollBanner} data-success={roll.success || undefined} role="status">
      <span className={styles.die} key={roll.seq} aria-hidden="true">
        {roll.result}
      </span>
      <span className={styles.rollText}>
        <b>
          <IconDice5 size={16} aria-hidden="true" /> {look(who).name} rolled {roll.result}
        </b>
        {roll.success ? (
          <small>The Fracture enters play!</small>
        ) : (
          <small>The Fracture needs a 1 or a 10. Better luck next time.</small>
        )}
      </span>
      <button type="button" className={styles.dismiss} onClick={onDismiss}>
        OK
      </button>
    </div>,
    document.body,
  );
}

/** Dok wyboru systemów na żetony ingress (klik w podświetlony system na mapie). */
function IngressDock({ view }: { view: ThundersEdgeView }) {
  const actions = useThundersEdgeActions();
  const look = usePlayerLook();
  const [picked, setPicked] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const choice = view.pendingIngress.find((c) => c.color === picked) ?? view.pendingIngress[0];

  useMapPick(
    "system",
    choice?.candidates ?? [],
    (position) => {
      if (busy || !choice) return;
      setBusy(true);
      void actions.placeIngress(choice.color, position).finally(() => setBusy(false));
    },
    { hue: HUE, enabled: !busy },
  );

  const owner = view.fractureEnteredBy ? view.players[view.fractureEnteredBy] : null;
  return (
    <PromptDock label="Ingress tokens">
      <Hint>
        <IconTarget size={14} aria-hidden="true" /> <b>The Fracture is in play.</b>{" "}
        {owner && (
          <>
            <CircularFactionIcon faction={owner} size={16} /> {look(owner).name}{" "}
          </>
        )}
        places ingress tokens: click a <b>highlighted system</b> with a{" "}
        <b>{choice ? COLOR_LABEL[choice.color] : ""}</b> technology specialty (
        {choice?.remaining ?? 0} left). A system can hold only one ingress token.
      </Hint>
      {view.pendingIngress.length > 1 && (
        <div className={styles.cards}>
          {view.pendingIngress.map((c) => (
            <button
              key={c.color}
              type="button"
              className={styles.cardPick}
              data-on={c.color === choice?.color || undefined}
              onClick={() => setPicked(c.color)}
            >
              {COLOR_LABEL[c.color] ?? c.color} · {c.remaining} left
            </button>
          ))}
        </div>
      )}
    </PromptDock>
  );
}

/** Dok położenia Thunder's Edge (pusty system na mapie) + wybór piechoty przy remisie. */
function PlacementDock({ view }: { view: ThundersEdgeView }) {
  const actions = useThundersEdgeActions();
  const look = usePlayerLook();
  const leaders = view.placementLeaders;
  const [infantry, setInfantry] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const infantryPlayer =
    leaders.length === 1 ? leaders[0] : (infantry ?? view.placementPlayer ?? leaders[0]);

  useMapPick(
    "system",
    view.placementTargets,
    (position) => {
      if (busy) return;
      setBusy(true);
      void actions
        .placeThundersEdge(position, infantryPlayer)
        .finally(() => setBusy(false));
    },
    { hue: HUE, enabled: !busy },
  );

  const placer = view.placementPlayer ? view.players[view.placementPlayer] : null;
  const count = infantryPlayer ? (view.placementCounts[infantryPlayer] ?? 0) : 0;
  return (
    <PromptDock label="Thunder's Edge">
      <Hint>
        <IconTarget size={14} aria-hidden="true" />{" "}
        {placer && (
          <>
            <CircularFactionIcon faction={placer} size={16} /> <b>{look(placer).name}</b>
          </>
        )}{" "}
        claimed the last slice. <b>Click an empty system</b> (no planet, supernova or printed
        wormhole, outside The Fracture) to place <b>Thunder&apos;s Edge</b>. Then{" "}
        <b>{count}</b> infantry go on it and their owner takes control.
      </Hint>
      {leaders.length > 1 && (
        <>
          <Hint>Tie for the most slices - who places the infantry?</Hint>
          <div className={styles.cards}>
            {leaders.map((id) => {
              const key = view.players[id] ?? id;
              return (
                <button
                  key={id}
                  type="button"
                  className={styles.cardPick}
                  data-on={id === infantryPlayer || undefined}
                  onClick={() => setInfantry(id)}
                >
                  <CircularFactionIcon faction={key} size={16} /> {look(key).name} ·{" "}
                  {view.placementCounts[id]} slices
                </button>
              );
            })}
          </div>
        </>
      )}
    </PromptDock>
  );
}

/**
 * Okna modułu Thunder's Edge (RULES.md 50), montowane stale na stronie gry:
 *  - baner z wynikiem rzutu na The Fracture (kostka d10, tylko dla NOWEGO rzutu),
 *  - dok żetonów ingress (po wejściu The Fracture do gry),
 *  - dok położenia Thunder's Edge (po szóstym plastrze ekspedycji).
 * Wybór systemów odbywa się klikiem w mapę (`mapPick`), okna można zminimalizować.
 */
export function ThundersEdgeOverlay() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const signal = gameState?.thundersEdge;
  const active = Boolean(signal && (signal.pendingIngress || signal.pendingPlacement));
  const { data: view } = useThundersEdge(active);

  // Baner rzutu pokazujemy tylko dla rzutu, który pojawił się PO załadowaniu strony.
  const seenSeq = useRef<number | null | undefined>(undefined);
  const [bannerSeq, setBannerSeq] = useState<number | null>(null);
  const lastSeq = signal?.lastRoll?.seq ?? null;
  useEffect(() => {
    if (signal === undefined) return;
    if (seenSeq.current === undefined) {
      seenSeq.current = lastSeq; // pierwszy odczyt: stary rzut nie jest nowością
      return;
    }
    if (lastSeq !== null && lastSeq !== seenSeq.current) setBannerSeq(lastSeq);
    seenSeq.current = lastSeq;
  }, [signal, lastSeq]);

  const { data: rollView } = useThundersEdge(bannerSeq !== null);

  return (
    <>
      {bannerSeq !== null && rollView?.lastRoll && (
        <RollBanner view={rollView} onDismiss={() => setBannerSeq(null)} />
      )}
      {active && view && view.pendingIngress.length > 0 && <IngressDock view={view} />}
      {active && view && view.placementPlayer !== null && <PlacementDock view={view} />}
    </>
  );
}

import { useState } from "react";
import { useParams } from "react-router-dom";
import { IconTarget } from "@tabler/icons-react";
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
 *  - (rzut na The Fracture pokazuje wspólna scena kości: `domains/dice/TableRollWatcher`),
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

  return (
    <>
      {active && view && view.pendingIngress.length > 0 && <IngressDock view={view} />}
      {active && view && view.placementPlayer !== null && <PlacementDock view={view} />}
    </>
  );
}

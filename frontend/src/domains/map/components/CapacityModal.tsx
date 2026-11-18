import { type CSSProperties } from "react";
import { useAfterDice } from "@/domains/dice/diceGate";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useCapacity } from "@/api/useBoardEditor";
import { getTileById } from "@/entities/lookup/systems";
import { excessFor, remainingCargo, removalStatus } from "./capacityMath";
import { RemovalWindowModal } from "./RemovalWindowModal";
import styles from "./CapacityModal.module.css";

/**
 * Okno LIMITU POJEMNOŚCI (RULES.md 39.6) — „masz w przestrzeni więcej ładunku, niż zmieszczą
 * twoje statki".
 *
 * Silnik otwiera okno ``CAPACITY`` po wyłonieniu zwycięzcy walki kosmicznej, po każdym efekcie
 * stawiającym jednostki (``core/limits``) i przed przejściem kroku akcji. Układ okna jest
 * WSPÓLNY z pulą floty (``RemovalWindowModal``); tu zostaje tylko to, co dotyczy pojemności:
 * pasek ładowni na żywo (miejsca statków, przydział doku dla myśliwców, przepełnienie).
 * Poprawność liczy ``capacityMath`` (ta sama formuła co backend).
 */
export function CapacityModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { capacityResolve } = useBoardEditor();
  const window = gameState?.pendingWindow ?? null;
  const pending =
    !!window && window.windowType === "CAPACITY" && !window.isComplete;
  const { data: view } = useCapacity(pending);
  // Nadwyżka po walce (np. zniszczony nosiciel) czeka, aż kości wylądują (``diceGate``).
  const ready = useAfterDice(pending && view?.active ? `${view.playerId}@${view.position}` : "");

  if (!pending || !view?.active || !ready) return null;

  const player = gameData?.playerData?.find((p) => p.faction === view.player);
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName =
    (tile ? getTileById(tile.systemId)?.name : undefined) ??
    view.position ??
    "";
  const viewKey = `${view.playerId}@${view.position}:${view.used}`;
  // Fighter II: myśliwce ponad capacity idą do fleet pool, więc nie zapełniają ładowni.
  const toFleet = view.fightersToFleet === true;
  const costOf = (bt: string) =>
    view.cargo.find((c) => c.baseType === bt)?.cost ?? 1;

  // Pasek ładowni: miejsca doku (tylko myśliwce) + miejsca statków; wypełnienie = co zostaje.
  const hold = (remove: Record<string, number>) => {
    const left = remainingCargo(view, remove);
    const fighterLoad = costOf("fighter") * (left.fighter ?? 0);
    const dockUsed = toFleet ? 0 : Math.min(fighterLoad, view.fighterOnly);
    const shipLoad =
      Object.entries(left)
        .filter(([bt]) => !(toFleet && bt === "fighter"))
        .reduce((s, [bt, n]) => s + costOf(bt) * n, 0) - dockUsed;
    const shipUsed = Math.min(shipLoad, view.general);
    const overflow = Math.max(0, shipLoad - view.general);
    const cells = [
      ...Array.from({ length: view.fighterOnly }, (_, i) => ({
        kind: "dock" as const,
        full: i < dockUsed,
      })),
      ...Array.from({ length: view.general }, (_, i) => ({
        kind: "ship" as const,
        full: i < shipUsed,
      })),
      ...Array.from({ length: overflow }, () => ({
        kind: "over" as const,
        full: true,
      })),
    ];
    return (
      <div className={styles.hold} aria-label="Cargo hold">
        <div className={styles.holdHead}>
          <span>Hold</span>
          <span>
            {shipUsed + dockUsed + overflow} / {view.general + view.fighterOnly}
            {view.fighterOnly > 0 && (
              <small> · {view.fighterOnly} dock slots for fighters</small>
            )}
          </span>
        </div>
        <div className={styles.cells} data-over={overflow > 0 || undefined}>
          {cells.length === 0 && (
            <span className={styles.noCells}>No capacity</span>
          )}
          {cells.map((cell, i) => (
            <span
              key={i}
              className={styles.cell}
              data-kind={cell.kind}
              data-full={cell.full || undefined}
              style={{ "--i": i } as CSSProperties}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <RemovalWindowModal
      title="Capacity exceeded"
      viewKey={viewKey}
      player={player}
      fallbackName={view.player ?? ""}
      systemName={systemName}
      position={view.position}
      intro={
        <>
          Your ships can't carry all fighters and ground forces in this system's
          space. Choose which units return to your reinforcements. Ground forces
          on planets don't count.
          {toFleet
            ? " With Fighter II, fighters beyond your capacity are not removed here - they count against your fleet pool."
            : ""}
        </>
      }
      extra={hold}
      items={view.cargo}
      locationNoun="in space"
      unitNoun="unit"
      suggestion={view.suggestion}
      evaluate={(remove) => {
        const left = remainingCargo(view, remove);
        const removedTotal = Object.values(remove).reduce((a, b) => a + b, 0);
        return {
          status: removalStatus(view, remove),
          overText: `Still over capacity by ${excessFor(view, left)} — remove more.`,
          exactText: `Fits. ${removedTotal} unit${removedTotal === 1 ? "" : "s"} return to reinforcements.`,
        };
      }}
      remaining={view.remaining}
      checkNoun="capacity"
      onConfirm={(remove) =>
        view.player
          ? capacityResolve(view.player, remove)
          : Promise.resolve()
      }
    />
  );
}

export default CapacityModal;

import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useFleetPool } from "@/api/useBoardEditor";
import { getTileById } from "@/entities/lookup/systems";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { RemovalWindowModal } from "./RemovalWindowModal";

/**
 * Okno FLEET POOL (RULES.md 42) - „masz w systemie więcej statków niż żetonów w puli floty".
 *
 * Reguła pozwala ruszyć / wyprodukować / postawić statki ponad pulę, ale nadwyżkę trzeba zaraz
 * zwrócić do rezerwy. Silnik otwiera okno ``FLEET_POOL`` po KAŻDYM efekcie, który ją powoduje
 * (``core/limits``), oraz przy próbie przejścia do kolejnego kroku akcji. Układ okna jest
 * WSPÓLNY z pojemnością (``RemovalWindowModal``). Myśliwce i siły naziemne nie liczą się do
 * puli (wyjątek: Fighter II).
 */
export function FleetPoolModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { fleetPoolResolve } = useBoardEditor();
  const window = gameState?.pendingWindow ?? null;
  const pending =
    !!window && window.windowType === "FLEET_POOL" && !window.isComplete;
  const { data: view } = useFleetPool(pending);

  if (!pending || !view?.active) return null;

  const player = gameData?.playerData?.find((p) => p.faction === view.player);
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName =
    (tile ? getTileById(tile.systemId)?.name : undefined) ??
    view.position ??
    "";

  return (
    <RemovalWindowModal
      title="Fleet pool exceeded"
      viewKey={`${view.playerId}@${view.position}:${view.total}`}
      player={player}
      fallbackName={view.player ?? ""}
      systemName={systemName}
      position={view.position}
      intro={
        <>
          Your fleet pool allows <b>{view.pool}</b> non-fighter ship
          {view.pool === 1 ? "" : "s"} in a system, but you have{" "}
          <b>{view.total}</b> here. Choose <b>{view.excess}</b> to return to
          your reinforcements.{" "}
          {player?.techs?.includes("ff2")
            ? "With Fighter II, fighters in excess of your capacity count against the pool; other fighters, ground forces and units on planets don't."
            : "Fighters, ground forces and units on planets don't count."}
        </>
      }
      extra={() => <ActiveTechs context="fleet" faction={player?.faction} />}
      items={view.ships}
      locationNoun="in system"
      unitNoun="ship"
      suggestion={view.suggestion}
      evaluate={(remove) => {
        const removedTotal = Object.values(remove).reduce((a, b) => a + b, 0);
        const status =
          removedTotal < view.excess
            ? "over"
            : removedTotal > view.excess
              ? "tooMany"
              : "exact";
        const missing = view.excess - removedTotal;
        return {
          status,
          overText: `Remove ${missing} more ship${missing === 1 ? "" : "s"}.`,
          exactText: `Fits the pool. ${removedTotal} ship${removedTotal === 1 ? "" : "s"} return to reinforcements.`,
        };
      }}
      remaining={view.remaining}
      checkNoun="the fleet pool"
      onConfirm={(remove) =>
        view.player
          ? fleetPoolResolve(view.player, remove)
          : Promise.resolve()
      }
    />
  );
}

export default FleetPoolModal;

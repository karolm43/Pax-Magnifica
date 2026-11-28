import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { IconClick, IconRoute } from "@tabler/icons-react";
import { SegmentedControl, Switch } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useMoveRange } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { FleetPoolWarning } from "@/domains/map/components/FleetPoolWarning";
import { MoveRouteBox } from "@/domains/movement/MoveRouteBox";
import { FlightPlanList } from "@/domains/movement/FlightPlanList";
import { useFlightPlan } from "@/domains/movement/useFlightPlan";
import { movesSeparately, type SeparateOrder } from "@/domains/movement/flightPlan";
import { asyncOfBase } from "@/domains/movement/routeTypes";
import { lookupUnit } from "@/entities/lookup/units";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import styles from "./GameStatePanel.module.css";

/**
 * MOVEMENT step of the tactical action - the flight plan (RULES.md 32.4: the active player
 * declares every moving ship first, then they arrive together).
 *
 * Clicking a glowing system on the map (or dragging / Ctrl+clicking units) opens that system's
 * leg in the editor right here; "Add to flight plan" stages it and the next glowing system can
 * be picked. Every staged route stays on the map. Below, the combined result (fleet pool and
 * capacity in the active system once EVERYTHING arrives). The window's primary button flies
 * the whole plan with one request (all legs or nothing); Undo then reverts it in one click.
 * One-ship move bonuses stay separate switches (the player's consent); the plan shows which
 * leg spends each of them. Range, blockades and capacity are enforced by the backend.
 */
export function MovementStepPanel({
  activeSystem,
  activePlayerColor,
}: {
  activeSystem: string;
  activePlayerColor: string | null;
}) {
  const gameData = useGameData();
  const look = usePlayerLook();
  const setMoveRangeSources = useAppStore((s) => s.setMoveRangeSources);
  const gravityDrive = useAppStore((s) => s.gravityDrive);
  const setGravityDrive = useAppStore((s) => s.setGravityDrive);
  const draftOpen = useAppStore((s) => s.moveDraft !== null);
  const movePlan = useAppStore((s) => s.movePlan);
  const clearMovePlan = useAppStore((s) => s.clearMovePlan);
  const routeParams = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(routeParams.mapid ?? DEFAULT_GAME_ID);
  const flight = useFlightPlan();

  const player = gameData?.playerData?.find((p) => p.color === activePlayerColor);
  const faction = player?.faction ?? null;

  // Gravity Drive (RULES.md 55.6): a switch only for the owner, while the bonus is unused this
  // action - the PLAYER decides, the engine never turns it on by itself.
  const gravityDriveReady =
    (player?.techs ?? []).includes("gd") && gameState?.gravityDriveUsed !== true;
  const useGd = gravityDrive && gravityDriveReady;
  useEffect(() => {
    if (!gravityDriveReady && gravityDrive) setGravityDrive(false);
  }, [gravityDriveReady, gravityDrive, setGravityDrive]);
  // Ionian Fuel Refinery (Tempesta, RULES.md 60): its own switch after exhausting the card.
  const tempesta = useAppStore((s) => s.tempesta);
  const setTempesta = useAppStore((s) => s.setTempesta);
  const tempestaReady =
    gameState?.extraMoveBoostActive === true && gameState?.tempestaUsed !== true;
  const useTempesta = tempesta && tempestaReady;
  useEffect(() => {
    if (!tempestaReady && tempesta) setTempesta(false);
  }, [tempestaReady, tempesta, setTempesta]);
  // Imperator (Winnu, RULES.md 62.7): a separate "+1 for one ship" - may go to another ship.
  const imperator = useAppStore((s) => s.imperator);
  const setImperator = useAppStore((s) => s.setImperator);
  const imperatorReady =
    gameState?.imperatorBoostActive === true && gameState?.imperatorUsed !== true;
  const useImperator = imperator && imperatorReady;
  useEffect(() => {
    if (!imperatorReady && imperator) setImperator(false);
  }, [imperatorReady, imperator, setImperator]);
  const { data: moveRange } = useMoveRange(
    faction,
    Boolean(activeSystem),
    useGd,
    useTempesta,
    useImperator,
  );
  useEffect(() => {
    setMoveRangeSources(new Set(Object.keys(moveRange?.sources ?? {})));
    return () => setMoveRangeSources(new Set());
  }, [moveRange, setMoveRangeSources]);

  // Leaving the step (or another activation) drops a plan that was never flown.
  useEffect(() => () => clearMovePlan(), [activeSystem, clearMovePlan]);

  if (!faction) {
    return (
      <span className={styles.prodNote}>
        No active player with a faction — cannot move.
      </span>
    );
  }

  const sources = Object.keys(moveRange?.sources ?? {});
  const { incoming } = flight;
  // A ship that "may move before or after your other ships" (Hil Colish, RULES.md 62.19).
  const separateShip = flight.legs
    .filter(movesSeparately)
    .flatMap((leg) => leg.route.ships.filter((ship) => ship.movesSeparately))[0];
  const separateName = separateShip
    ? (lookupUnit(asyncOfBase(separateShip.baseType), faction, player)?.name ?? separateShip.baseType)
    : null;
  const onlySeparate =
    separateName !== null && flight.legs.length > 0 && flight.legs.every(movesSeparately);
  return (
    <div className={styles.movement}>
      {/* Technologies that affect movement (Antimass, Light/Wave, Gravity Drive...). */}
      <ActiveTechs context="movement" color={activePlayerColor} />

      {gravityDriveReady && (
        <Switch
          label="Use Gravity Drive"
          description="+1 move for ONE ship this action - the flight plan shows which leg uses it."
          checked={gravityDrive}
          onChange={(event) => setGravityDrive(event.currentTarget.checked)}
        />
      )}
      {tempestaReady && (
        <Switch
          label="Use Ionian Fuel Refinery"
          description="+1 move for ONE ship this action - the flight plan shows which leg uses it."
          checked={tempesta}
          onChange={(event) => setTempesta(event.currentTarget.checked)}
        />
      )}
      {imperatorReady && (
        <Switch
          label="Use Imperator"
          description="+1 move for ONE ship this action (can be a different ship than Gravity Drive)."
          checked={imperator}
          onChange={(event) => setImperator(event.currentTarget.checked)}
        />
      )}
      {gameState?.imperatorBoostActive === true && gameState?.imperatorUsed === true && (
        <span className={styles.prodZoneLabel}>Imperator used this action</span>
      )}
      {gameState?.extraMoveBoostActive === true && gameState?.tempestaUsed === true && (
        <span className={styles.prodZoneLabel}>Ionian Fuel Refinery used this action</span>
      )}
      {(player?.techs ?? []).includes("gd") && gameState?.gravityDriveUsed === true && (
        <span className={styles.prodZoneLabel}>Gravity Drive used this action</span>
      )}

      {/* The leg being picked: opened by clicking a glowing system on the map. */}
      <MoveRouteBox
        faction={faction}
        player={player}
        sources={sources}
        hue={`rgb(${look(faction).rgb})`}
        gravityDrive={useGd}
        tempesta={useTempesta}
        imperator={useImperator}
        embedded
      />
      {!draftOpen && (
        <p className={styles.moveHint}>
          <IconClick size={14} aria-hidden="true" />
          <span>
            {sources.length === 0
              ? "No ships can reach this system - continue with the next step."
              : movePlan.length === 0
                ? "Click a glowing system on the map to pick ships flying from it (or drag units onto this system)."
                : "Click another glowing system to add ships from it, or fly the plan."}
          </span>
        </p>
      )}

      {movePlan.length > 0 && (
        <section className={styles.planSection} aria-label="Staged legs">
          <span className={styles.prodZoneLabel}>
            <IconRoute size={11} aria-hidden="true" /> Flight plan · {movePlan.length} leg
            {movePlan.length === 1 ? "" : "s"}
          </span>
          <FlightPlanList legs={movePlan} />
        </section>
      )}

      {separateName && flight.separateOrderAsked && (
        <div className={styles.planSection} role="group" aria-label={`When ${separateName} moves`}>
          <span className={styles.prodZoneLabel}>{separateName} moves</span>
          <SegmentedControl
            aria-label={`When ${separateName} moves`}
            size="xs"
            fullWidth
            data={[
              { value: "before", label: "Before the others" },
              { value: "after", label: "After the others" },
            ]}
            value={flight.separateOrder ?? undefined}
            onChange={(value) => flight.setSeparateOrder(value as SeparateOrder)}
          />
          <small className={styles.moveHint}>
            {flight.separateOrder === "before"
              ? `${separateName} flies first, then the other legs - with its delta wormhole already in its new system.`
              : flight.separateOrder === "after"
                ? `The other legs fly first - they may still use the delta wormhole where ${separateName} starts.`
                : `Choose when ${separateName} moves.`}
          </small>
        </div>
      )}
      {onlySeparate && (
        <p className={styles.moveHint}>
          <IconRoute size={14} aria-hidden="true" />
          <span>
            {separateName} may move before your other ships: fly it on its own now, then plan the
            rest - their routes will see its delta wormhole in its new system.
          </span>
        </p>
      )}

      {/* Combined result once the WHOLE plan arrives (RULES.md 42: the pool may be exceeded,
          but the excess is removed right after). */}
      <FleetPoolWarning
        extra={incoming.nonFighterShips}
        extraFighters={incoming.fighters}
        extraCapacity={incoming.capacity}
        extraGround={incoming.groundForces}
      />
    </div>
  );
}

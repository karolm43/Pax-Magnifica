import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import cx from "clsx";
import {
  IconArrowBackUp,
  IconArrowRight,
  IconBuildingFactory2,
  IconCheck,
  IconLock,
  IconMinimize,
  IconRocket,
  IconSwords,
  IconTarget,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { getPlanetData } from "@/entities/lookup/planets";
import { getTileById } from "@/entities/lookup/systems";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { InvasionStepPanel } from "@/domains/invasion/InvasionStepPanel";
import { useFlightPlan } from "@/domains/movement/useFlightPlan";
import { MovementStepPanel } from "../MovementStepPanel";
import { SpaceCannonStepPanel } from "../SpaceCannonStepPanel";
import {
  STATUS_LABEL,
  TACTICAL_STEPS,
  lockReason,
  primaryAction,
  stepPrompt,
  stepStatuses,
  type StepContext,
} from "./tacticalSteps";
import styles from "./TacticalActionWindow.module.css";

/* Ships (asyncId) - who has a fleet in the system (space combat, RULES.md 39 W2). */
const SHIP_ASYNC_IDS = new Set(["ff", "dd", "ca", "cv", "dn", "fs", "ws"]);

/** Planets of the active system: name, resources / influence and the controller's icon. */
function PlanetSummary({ position }: { position: string }) {
  const gameData = useGameData();
  const tile = gameData?.tiles?.[position];
  const planets = Object.entries(tile?.planets ?? {});
  if (planets.length === 0) return null;
  return (
    <ul className={styles.planets} aria-label="Planets in the system">
      {planets.map(([id, planet]) => {
        const data = getPlanetData(id);
        const resources = planet.resources ?? data?.resources;
        const influence = planet.influence ?? data?.influence;
        return (
          <li key={id} className={styles.planet}>
            {planet.controlledBy && (
              <CircularFactionIcon faction={planet.controlledBy} size={14} />
            )}
            <b>{data?.name ?? id}</b>
            {resources != null && influence != null && (
              <small>
                {resources}/{influence}
              </small>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** PRODUCTION step body: the production window opens on step entry; this brings it back. */
function ProductionStepBody() {
  const hidden = useAppStore((s) => s.productionHidden);
  const setHidden = useAppStore((s) => s.setProductionHidden);
  return (
    <div className={styles.stepBody}>
      <button
        type="button"
        className={styles.secondary}
        disabled={!hidden}
        onClick={() => setHidden(false)}
      >
        <IconBuildingFactory2 size={14} aria-hidden="true" />
        {hidden ? "Return to production" : "Production window is open"}
      </button>
    </div>
  );
}

/**
 * Guided tactical action (RULES.md 19, 19.1): the active system with its planets, a 5-step
 * progress bar (Done / Active / Skipped / Upcoming), a one-line prompt for the current step,
 * the step's own controls, and a sticky footer with ONE context-aware primary action (Fly the
 * flight plan, Next step, Return to battle, Finish action), Undo and Minimize on the left and
 * the rule lock - phrased as what to do - right above it. Big step windows (battle, invasion,
 * production) open by themselves when their step starts.
 *
 * Without an active system it shows the "Activate system" starter (Action phase panel).
 */
export function TacticalActionPanel({
  activeSystem,
  tacticalStep,
  systemLabel,
  activePlayerColor,
  onMinimize,
}: {
  activeSystem: string | null;
  tacticalStep: string | null;
  systemLabel: string | null;
  activePlayerColor: string | null;
  onMinimize?: () => void;
}) {
  const { tacticalNextStep, endTactical, battleStart, undoMove } = useBoardEditor();
  const activateMode = useAppStore((s) => s.activateMode);
  const toggleActivateMode = useAppStore((s) => s.toggleActivateMode);
  const setBattleHidden = useAppStore((s) => s.setBattleHidden);
  const setProductionHidden = useAppStore((s) => s.setProductionHidden);
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const flight = useFlightPlan();
  const [busy, setBusy] = useState(false);

  // Steps seen during this activation: earlier steps never seen were skipped by the engine.
  const [visited, setVisited] = useState<{ system: string | null; steps: string[] }>({
    system: activeSystem,
    steps: [],
  });
  if (visited.system !== activeSystem) {
    setVisited({ system: activeSystem, steps: tacticalStep ? [tacticalStep] : [] });
  } else if (tacticalStep && !visited.steps.includes(tacticalStep)) {
    setVisited({ system: activeSystem, steps: [...visited.steps, tacticalStep] });
  }

  // Big windows open with their step (RULES.md 19.1): once per step entry, so "Hide" sticks.
  const opened = useRef<string | null>(null);
  const inCombat = gameState?.activeCombat != null;
  useEffect(() => {
    const key = `${activeSystem}:${tacticalStep}:${inCombat}`;
    if (!activeSystem || opened.current === key) return;
    opened.current = key;
    if (inCombat) setBattleHidden(false);
    if (tacticalStep === "PRODUCTION") setProductionHidden(false);
  }, [activeSystem, tacticalStep, inCombat, setBattleHidden, setProductionHidden]);

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // The reason (422) is shown by the notice panel.
    } finally {
      setBusy(false);
    }
  };

  if (!activeSystem) {
    return (
      <button
        type="button"
        className={cx(styles.bigAction, activateMode && styles.bigActionOn)}
        onClick={toggleActivateMode}
        title="Click, then pick a system on the map to activate it"
      >
        <IconTarget size={16} aria-hidden="true" />
        <span>{activateMode ? "Pick a system on the map…" : "Activate system"}</span>
      </button>
    );
  }

  const activeTile = gameData?.tiles?.[activeSystem];
  const combatOwed =
    Object.values(activeTile?.unitsByFaction ?? {}).filter((entities) =>
      entities.some(
        (e) => e.entityType === "unit" && e.count > 0 && SHIP_ASYNC_IDS.has(e.entityId),
      ),
    ).length >= 2;
  const systemName = activeTile ? getTileById(activeTile.systemId)?.name : undefined;
  const ctx: StepContext = {
    system: systemName ?? activeSystem,
    moved: gameState?.tacticalMoved === true,
    stagedShips: flight.ships,
    stagedCargo: flight.cargo,
    stagedSystems: flight.systems,
    flightBlocker: flight.blocker,
    windowType: gameState?.pendingWindow?.windowType ?? null,
    inCombat,
    combatOwed,
    invasionOpen:
      tacticalStep === "INVASION" &&
      gameState?.activeInvasion != null &&
      gameState.activeInvasion.phase !== "ESTABLISH",
    invasionResolved: gameState?.invasionResolved === true,
  };
  const statuses = stepStatuses(tacticalStep, visited.steps);
  const primary = primaryAction(tacticalStep, ctx);
  // Ending the action early: legal unless something is unresolved (backend: tactical.end_action).
  const endLock =
    lockReason(ctx, null) ??
    (combatOwed && ["MOVEMENT", "SPACE_CANNON", "SPACE_COMBAT"].includes(tacticalStep ?? "")
      ? "Space combat is mandatory - resolve it first."
      : null);
  const callout = primary.disabled ?? null;

  const onPrimary = () => {
    switch (primary.kind) {
      case "fly":
        return void run(flight.fly);
      case "battle":
        return setBattleHidden(false);
      case "startCombat":
        return void run(async () => {
          setBattleHidden(false);
          await battleStart(null);
        });
      default:
        return void run(async () => {
          flight.discard();
          await tacticalNextStep();
        });
    }
  };

  return (
    <div className={styles.panel}>
      <header className={styles.head}>
        <div className={styles.system}>
          <IconTarget size={16} aria-hidden="true" />
          <span className={styles.systemName} title={systemLabel ?? activeSystem}>
            {systemName ?? activeSystem}
          </span>
          <small className={styles.tileId}>{activeSystem}</small>
        </div>
        <PlanetSummary position={activeSystem} />
      </header>

      <ol className={styles.stepper} aria-label="Tactical action steps">
        {TACTICAL_STEPS.map(({ step, label }, index) => {
          const status = statuses[step];
          return (
            <li
              key={step}
              className={styles.step}
              data-status={status}
              aria-current={status === "active" ? "step" : undefined}
              aria-label={`${index + 1}. ${label}: ${STATUS_LABEL[status]}`}
            >
              <span className={styles.stepDot}>
                {status === "done" ? <IconCheck size={11} aria-hidden="true" /> : index + 1}
              </span>
              <span className={styles.stepLabel}>{label}</span>
              <small className={styles.stepStatus}>{STATUS_LABEL[status]}</small>
            </li>
          );
        })}
      </ol>
      <p className={styles.prompt} role="status">
        {stepPrompt(tacticalStep, ctx)}
      </p>

      <div className={styles.body}>
        {tacticalStep === "MOVEMENT" && (
          <MovementStepPanel activeSystem={activeSystem} activePlayerColor={activePlayerColor} />
        )}
        {tacticalStep === "SPACE_CANNON" && <SpaceCannonStepPanel />}
        {tacticalStep === "SPACE_COMBAT" && inCombat && (
          <button
            type="button"
            className={styles.secondary}
            onClick={() => setBattleHidden(false)}
          >
            <IconSwords size={14} aria-hidden="true" /> Open the battle window
          </button>
        )}
        {tacticalStep === "INVASION" && <InvasionStepPanel />}
        {tacticalStep === "PRODUCTION" && <ProductionStepBody />}
      </div>

      <footer className={styles.foot}>
        {callout && (
          <p className={styles.lock} role="status">
            <IconLock size={13} aria-hidden="true" /> {callout}
          </p>
        )}
        <div className={styles.footRow}>
          <div className={styles.footLeft}>
            {tacticalStep === "MOVEMENT" && (
              <button
                type="button"
                className={styles.ghost}
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    flight.discard();
                    await undoMove();
                  })
                }
                title={
                  ctx.moved
                    ? "Undo the whole flight plan that just flew"
                    : "Nothing moved yet - take the command token back and cancel the activation"
                }
              >
                <IconArrowBackUp size={14} aria-hidden="true" />
                {ctx.moved ? "Undo movement" : "Undo activation"}
              </button>
            )}
            {onMinimize && (
              <button
                type="button"
                className={styles.ghost}
                onClick={onMinimize}
                title="Minimize to look at the map"
              >
                <IconMinimize size={14} aria-hidden="true" /> Map
              </button>
            )}
          </div>
          <button
            type="button"
            className={styles.primary}
            disabled={busy || primary.disabled !== null}
            onClick={onPrimary}
            title={primary.disabled ?? undefined}
          >
            {primary.kind === "fly" ? (
              <IconRocket size={16} aria-hidden="true" />
            ) : primary.kind === "battle" || primary.kind === "startCombat" ? (
              <IconSwords size={16} aria-hidden="true" />
            ) : null}
            {primary.label}
            {(primary.kind === "next" || primary.kind === "finish") && (
              <IconArrowRight size={16} aria-hidden="true" />
            )}
          </button>
        </div>
        <button
          type="button"
          className={styles.endAction}
          disabled={busy || endLock !== null}
          onClick={() =>
            void run(async () => {
              flight.discard();
              await endTactical();
            })
          }
          title={endLock ?? "End the tactical action now (skip the remaining steps)"}
        >
          End action now
        </button>
      </footer>
    </div>
  );
}

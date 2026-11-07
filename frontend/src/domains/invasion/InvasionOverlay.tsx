import { useEffect, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  IconArrowRight,
  IconFlag,
  IconMinimize,
  IconMinus,
  IconPlus,
  IconRocket,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { getTileById } from "@/entities/lookup/systems";
import { getPlanetData } from "@/entities/lookup/planets";
import { Unit } from "@/shared/ui/Unit";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { InvasionPlanetCard } from "./InvasionPlanetCard";
import { usePlayerLook } from "./invasionUi";
import {
  bombardList,
  bumpStage,
  defaultBombardPlan,
  landAll,
  remainingOf,
  shiftBombard,
  stageList,
  stageTotal,
  type BombardPlan,
  type Stage,
} from "./invasionStage";
import {
  useInvasion,
  useInvasionActions,
  type InvasionPhase,
  type InvasionView,
} from "./useInvasion";
import styles from "./InvasionOverlay.module.css";

const PHASES: { key: InvasionPhase; label: string }[] = [
  { key: "BOMBARDMENT", label: "Bombardment" },
  { key: "COMMIT", label: "Commit ground forces" },
  { key: "SPACE_CANNON_DEFENSE", label: "Space Cannon Defense" },
  { key: "GROUND_COMBAT", label: "Ground combat" },
  { key: "ESTABLISH", label: "Establish control" },
];

const HINT: Record<InvasionPhase, string> = {
  BOMBARDMENT:
    "Choose a planet for each bombarding ship. If you bombard, every unit with Bombardment must be used.",
  COMMIT:
    "Land ground forces from orbit: use + / − on a planet, drag a unit onto it (Shift = all), or Land all.",
  SPACE_CANNON_DEFENSE:
    "Space Cannon on the planets you landed on may fire at your ground forces.",
  GROUND_COMBAT:
    "Fight each contested planet. You choose the order; combat ends when one side is left.",
  ESTABLISH:
    "Control is settled: structures of the loser are gone, the planet card is exhausted.",
};

function InvasionWindow({ view }: { view: InvasionView }) {
  const gameData = useGameData();
  const look = usePlayerLook();
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);
  const setBattleHidden = useAppStore((s) => s.setBattleHidden);
  const { battleStart } = useBoardEditor();
  const actions = useInvasionActions();
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<Stage>({});
  const [userPlan, setUserPlan] = useState<BombardPlan | null>(null);

  const phase = view.phase ?? "BOMBARDMENT";
  const attacker = view.attacker ? look(view.attacker) : null;
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName = tile
    ? (getTileById(tile.systemId)?.name ?? view.position)
    : view.position;
  const planetName = (id: string) => getPlanetData(id)?.name ?? id;

  const bombard = view.bombard;
  const plan = userPlan ?? defaultBombardPlan(bombard.groups, bombard.targets);
  const canBombard = bombard.groups.length > 0 && !bombard.done;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód (422) pokazuje panel komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  const cardActions = {
    busy,
    stage,
    bombardPlan: canBombard ? plan : {},
    onBump: (planet: string, baseType: string, delta: number) =>
      setStage((s) => bumpStage(s, view.cargo, planet, baseType, delta)),
    onLandAll: (planet: string) =>
      setStage((s) => landAll(s, view.cargo, planet)),
    onFight: (planet: string) =>
      void run(async () => {
        setBattleHidden(false);
        await battleStart(planet);
      }),
    onDefenseFire: (planet: string) => void run(() => actions.defenseFire(planet)),
    onDefensePass: (planet: string) => void run(() => actions.defensePass(planet)),
    onAssignBombard: (
      planet: string,
      faction: string,
      p: Parameters<typeof actions.assignBombard>[2],
    ) => void run(() => actions.assignBombard(planet, faction, p)),
    onAssignDefense: (
      planet: string,
      faction: string,
      p: Parameters<typeof actions.assignDefense>[2],
    ) => void run(() => actions.assignDefense(planet, faction, p)),
  };

  const staged = stageTotal(stage);
  const allDefenseDone = view.defense.every((d) => d.status === "resolved");
  const advance = (() => {
    switch (phase) {
      case "BOMBARDMENT":
        return {
          label: canBombard ? "Skip bombardment" : "Continue to commit",
          disabled: bombard.pending.length > 0,
        };
      case "COMMIT":
        return {
          label: view.planets.some((p) => Object.keys(p.committed).length > 0)
            ? "Continue to Space Cannon Defense"
            : "No landing - skip",
          disabled: staged > 0,
        };
      case "SPACE_CANNON_DEFENSE":
        return { label: "Continue to ground combat", disabled: !allDefenseDone };
      case "GROUND_COMBAT":
        return {
          label: "Continue to establish control",
          disabled: view.combatPlanets.length > 0 || view.inCombat,
        };
      default:
        return { label: "Finish invasion", disabled: false };
    }
  })();

  if (hidden) {
    return createPortal(
      <button
        type="button"
        className={styles.returnPill}
        onClick={() => setHidden(false)}
      >
        <IconRocket size={16} aria-hidden="true" />
        Invasion in progress - return
      </button>,
      document.body,
    );
  }

  const currentIndex = PHASES.findIndex((p) => p.key === phase);
  return createPortal(
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label={`Invasion of ${systemName ?? ""}`}
      style={{ "--att-rgb": attacker?.rgb ?? "148 163 184" } as CSSProperties}
    >
      <div className={styles.backdrop} aria-hidden="true" />
      <header className={styles.topBar}>
        <span className={styles.title}>
          <IconRocket size={18} aria-hidden="true" />
          Invasion
          <small>
            {view.position} · {systemName}
          </small>
        </span>
        <ol className={styles.phases} aria-label="Invasion steps">
          {PHASES.map((p, i) => (
            <li
              key={p.key}
              className={styles.phasePill}
              data-state={
                i < currentIndex ? "done" : i === currentIndex ? "now" : "next"
              }
              aria-current={i === currentIndex ? "step" : undefined}
            >
              <b>{i + 1}</b> {p.label}
            </li>
          ))}
        </ol>
        <span className={styles.topActions}>
          {view.attacker && (
            <span className={styles.attacker} title="Active player">
              <CircularFactionIcon faction={view.attacker} size={22} />
              {attacker?.name}
            </span>
          )}
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => setHidden(true)}
            title="Hide the invasion and look at the map"
          >
            <IconMinimize size={14} aria-hidden="true" /> Hide
          </button>
        </span>
      </header>

      {notice && (
        <div className={styles.notice} data-kind={notice.kind} role="alert">
          <span>{notice.text}</span>
          <button type="button" onClick={clearNotice} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <p className={styles.hint}>{HINT[phase]}</p>

      <div className={styles.planets}>
        {view.planets.map((info) => (
          <InvasionPlanetCard
            key={info.planet}
            view={view}
            info={info}
            actions={cardActions}
          />
        ))}
      </div>

      <footer className={styles.dock}>
        <section className={styles.orbit} aria-label="Orbit">
          <h4>In orbit</h4>
          {phase === "BOMBARDMENT" && canBombard && (
            <div className={styles.bombardList}>
              {bombard.groups.map((g) => (
                <div className={styles.bombardRow} key={g.baseType}>
                  <span className={styles.bombardName}>
                    <b>{g.count}×</b> {g.name}
                    <small>
                      Bombardment {g.hitsOn}+
                      {g.dicePerUnit > 1 ? ` ×${g.dicePerUnit}` : ""} · ~
                      {g.expectedHits} hits
                    </small>
                  </span>
                  <span className={styles.targets}>
                    {bombard.targets.map((t) => (
                      <span className={styles.target} key={t}>
                        {bombard.targets.length > 1 && (
                          <button
                            type="button"
                            className={styles.stepBtn}
                            aria-label={`Bombard ${planetName(t)} with one fewer ${g.name}`}
                            onClick={() =>
                              setUserPlan(
                                shiftBombard(plan, g, bombard.targets, t, -1),
                              )
                            }
                          >
                            <IconMinus size={11} />
                          </button>
                        )}
                        <span>
                          {planetName(t)} <b>{plan[g.baseType]?.[t] ?? 0}</b>
                        </span>
                        {bombard.targets.length > 1 && (
                          <button
                            type="button"
                            className={styles.stepBtn}
                            aria-label={`Bombard ${planetName(t)} with one more ${g.name}`}
                            onClick={() =>
                              setUserPlan(
                                shiftBombard(plan, g, bombard.targets, t, 1),
                              )
                            }
                          >
                            <IconPlus size={11} />
                          </button>
                        )}
                      </span>
                    ))}
                  </span>
                </div>
              ))}
            </div>
          )}
          {phase === "BOMBARDMENT" && !canBombard && (
            <span className={styles.empty}>
              {bombard.done
                ? "Bombardment resolved."
                : "Nothing can bombard here."}
            </span>
          )}
          {phase === "COMMIT" && (
            <div className={styles.cargo}>
              {view.cargo.length === 0 && (
                <span className={styles.empty}>
                  No ground forces left in orbit.
                </span>
              )}
              {view.cargo.map((u) => {
                const left = remainingOf(view.cargo, stage, u.baseType);
                return (
                  <span
                    className={styles.cargoChip}
                    key={u.baseType}
                    draggable={left > 0}
                    data-empty={left === 0 || undefined}
                    onDragStart={(e) =>
                      e.dataTransfer.setData("text/x-basetype", u.baseType)
                    }
                    title={`${u.name}: drag onto a planet (Shift = all)`}
                  >
                    <span className={styles.cargoSprite}>
                      <Unit
                        unitType={u.asyncId}
                        colorAlias={attacker?.colorAlias ?? "gry"}
                        faction={view.attacker ?? undefined}
                        scaleSprite
                      />
                    </span>
                    <b>
                      {left}/{u.count}
                    </b>
                    <small>{u.name}</small>
                  </span>
                );
              })}
            </div>
          )}
          {phase !== "BOMBARDMENT" && phase !== "COMMIT" && (
            <span className={styles.empty}>
              {view.cargo.length > 0
                ? `${view.cargo.reduce((n, u) => n + u.count, 0)} ground force(s) still in orbit.`
                : "Orbit is clear of ground forces."}
            </span>
          )}
        </section>

        <div className={styles.dockActions}>
          {phase === "BOMBARDMENT" && canBombard && (
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={busy}
              onClick={() =>
                void run(() => actions.bombard(bombardList(plan)))
              }
            >
              <IconRocket size={14} /> Roll bombardment
            </button>
          )}
          {phase === "COMMIT" && staged > 0 && (
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await actions.commit(stageList(stage));
                  setStage({});
                })
              }
            >
              <IconFlag size={14} /> Land {staged} unit{staged === 1 ? "" : "s"}
            </button>
          )}
          <button
            type="button"
            className={
              phase === "BOMBARDMENT" && canBombard
                ? styles.ghostBtn
                : styles.primaryBtn
            }
            disabled={busy || advance.disabled}
            onClick={() => void run(actions.next)}
          >
            {advance.label} <IconArrowRight size={14} />
          </button>
        </div>
      </footer>
    </div>,
    document.body,
  );
}

/**
 * Okno INWAZJI (RULES.md 40) — pełnoekranowe, pojawia się samo, gdy trwa inwazja
 * (``gameState.activeInvasion``). Pięć podkroków: Bombardment → Commit → Space Cannon Defense →
 * Walka naziemna → Establish Control. Walka naziemna otwiera okno pola bitwy (nad tym oknem).
 */
export function InvasionOverlay() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const queryClient = useQueryClient();
  const active = gameState?.activeInvasion != null;
  const { data: view } = useInvasion(active);

  // Każda zmiana stanu gry (walka zamknięta, ruch innego gracza…) odświeża widok inwazji.
  useEffect(() => {
    if (active) void queryClient.invalidateQueries({ queryKey: ["invasion"] });
  }, [gameState, active, queryClient]);

  if (!active || !view?.active) return null;
  return <InvasionWindow key={view.position} view={view} />;
}

export default InvasionOverlay;

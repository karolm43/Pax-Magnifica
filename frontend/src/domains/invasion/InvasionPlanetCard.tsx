import { type CSSProperties, type DragEvent } from "react";
import {
  IconCrosshair,
  IconMinus,
  IconPlus,
  IconShield,
  IconSwords,
  IconTargetArrow,
} from "@tabler/icons-react";
import { getPlanetData } from "@/entities/lookup/planets";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { BattleAssignPlan } from "@/api/useBoardEditor";
import { AssignPanel } from "./AssignPanel";
import {
  PlanetStage,
  StrikeLayer,
  surfaceOf,
  type OrbitItem,
} from "./InvasionFx";
import { Unit } from "@/shared/ui/Unit";
import { DiceRow, GroundToken, expandForces, usePlayerLook } from "./invasionUi";
import { remainingOf, type BombardPlan, type Stage } from "./invasionStage";
import type { InvasionPlanet, InvasionView } from "./useInvasion";
import styles from "./InvasionOverlay.module.css";

const OUTCOME_LABEL: Record<string, string> = {
  captured: "Captured",
  retained: "Defender keeps control",
  lost: "Landing failed",
  already_controlled: "Already controlled",
};

export type PlanetActions = {
  busy: boolean;
  stage: Stage;
  bombardPlan: BombardPlan;
  onBump: (planet: string, baseType: string, delta: number) => void;
  onLandAll: (planet: string) => void;
  onFight: (planet: string) => void;
  onDefenseFire: (planet: string) => void;
  onDefensePass: (planet: string) => void;
  onAssignBombard: (
    planet: string,
    faction: string,
    plan: BattleAssignPlan,
  ) => void;
  onAssignDefense: (
    planet: string,
    faction: string,
    plan: BattleAssignPlan,
  ) => void;
};

/**
 * Karta planety okna inwazji: kto ją trzyma, siły obrońców, siły zlądowane i działania bieżącego
 * podkroku (cel bombardowania, lądowanie, Space Cannon Defense, walka, wynik).
 */
export function InvasionPlanetCard({
  view,
  info,
  actions,
}: {
  view: InvasionView;
  info: InvasionPlanet;
  actions: PlanetActions;
}) {
  const look = usePlayerLook();
  const data = getPlanetData(info.planet);
  const attacker = view.attacker ?? "";
  const phase = view.phase;
  const defenders = Object.keys(info.forces).filter((k) => k !== attacker);
  const owner = info.owner ? look(info.owner) : null;

  const logFor = (kind: "BOMBARDMENT" | "DEFENSE") =>
    [...view.log]
      .reverse()
      .find((e) => e.phase === kind && e.planet === info.planet);
  const bombardLog = logFor("BOMBARDMENT");
  const defenseLog = logFor("DEFENSE");
  const idOf = (kind: "BOMBARDMENT" | "DEFENSE") =>
    view.log.reduce(
      (found, e, i) =>
        e.phase === kind && e.planet === info.planet ? i : found,
      -1,
    );
  const pendingBombard = view.bombard.pending.find(
    (p) => p.planet === info.planet,
  );
  const defense = view.defense.find((d) => d.planet === info.planet);
  const result = view.results.find((r) => r.planet === info.planet);
  const combat = view.combatResults[info.planet];
  const planned = Object.values(actions.bombardPlan).reduce(
    (n, row) => n + (row[info.planet] ?? 0),
    0,
  );
  // Statki bombardujące tę planetę: przed rzutem wg przydziału, po rzucie wg dziennika.
  const orbitCounts: Record<string, number> = {};
  if (phase === "BOMBARDMENT") {
    if (bombardLog) {
      for (const r of bombardLog.rolls) {
        orbitCounts[r.baseType] = (orbitCounts[r.baseType] ?? 0) + r.count;
      }
    } else {
      for (const [bt, row] of Object.entries(actions.bombardPlan)) {
        if ((row[info.planet] ?? 0) > 0) orbitCounts[bt] = row[info.planet];
      }
    }
  }
  const bombardShips = Object.entries(orbitCounts).flatMap(([bt, n]) => {
    const g = view.bombard.groups.find((x) => x.baseType === bt);
    return Array.from({ length: n }, () => ({
      baseType: bt,
      asyncId: g?.asyncId ?? bt,
      name: g?.name ?? bt,
    }));
  });
  // Statki: war sun jak na planszy (bez obrotu), reszta poziomo - na przemian w prawo i w lewo.
  const shipItems: OrbitItem[] = bombardShips.map((s, n) => ({
    node: (
      <span
        key={n}
        className={styles.shipSprite}
        data-base={s.asyncId}
        data-face={n % 2 === 0 ? "right" : "left"}
        title={s.name}
      >
        <Unit
          unitType={s.asyncId}
          colorAlias={look(attacker).colorAlias}
          faction={attacker}
          scaleSprite
        />
      </span>
    ),
  }));

  // Kapsuły desantu (małe jednostki spadające na planetę): przy lądowaniu spadają,
  // w Space Cannon Defense zawisają w locie, są ostrzeliwane (zestrzelone wybuchają),
  // a ocalałe lądują.
  const ASYNC: Record<string, string> = { infantry: "gf", mech: "mf" };
  const landed = (info.forces[attacker] ?? []).flatMap((u) =>
    Array.from({ length: u.count }, () => ({ asyncId: u.asyncId, name: u.name })),
  );
  const lostPods = Object.entries(defenseLog?.losses ?? {}).flatMap(([bt, n]) =>
    Array.from({ length: n }, () => ({
      asyncId: ASYNC[bt] ?? bt,
      name: bt,
    })),
  );
  const podState = (survivor: boolean): OrbitItem["state"] => {
    if (phase === "COMMIT") return "drop";
    if (!survivor) return "dead";
    return defense?.status === "resolved" ? "land" : "hold";
  };
  const podItems: OrbitItem[] =
    phase === "COMMIT" && landed.length > 0
      ? landed.map((u, n) => ({ node: podNode(u, n), state: podState(true) }))
      : phase === "SPACE_CANNON_DEFENSE" && defense
        ? [
            ...landed.map((u, n) => ({ node: podNode(u, n), state: podState(true) })),
            ...lostPods.map((u, n) => ({
              node: podNode(u, n + 100),
              state: podState(false),
            })),
          ]
        : [];
  function podNode(u: { asyncId: string; name: string }, n: number) {
    return (
      <span key={n} className={styles.pod} title={u.name}>
        <Unit
          unitType={u.asyncId}
          colorAlias={look(attacker).colorAlias}
          faction={attacker}
          scaleSprite
        />
      </span>
    );
  }
  const orbitItems = phase === "BOMBARDMENT" ? shipItems : podItems;
  const staged = actions.stage[info.planet] ?? {};
  const stagedCount = Object.values(staged).reduce((a, b) => a + b, 0);

  const onDragOver = (e: DragEvent<HTMLElement>) => {
    if (phase === "COMMIT") e.preventDefault();
  };
  const onDrop = (e: DragEvent<HTMLElement>) => {
    if (phase !== "COMMIT") return;
    const baseType = e.dataTransfer.getData("text/x-basetype");
    if (!baseType) return;
    e.preventDefault();
    const left = remainingOf(view.cargo, actions.stage, baseType);
    actions.onBump(info.planet, baseType, e.shiftKey ? left : 1);
  };

  return (
    <article
      className={styles.planet}
      data-contested={info.contested || undefined}
      data-shielded={info.shielded || undefined}
      data-droppable={phase === "COMMIT" || undefined}
      onDragOver={onDragOver}
      onDrop={onDrop}
      aria-label={`Planet ${data?.name ?? info.planet}`}
    >
      <PlanetStage
        surface={surfaceOf(data?.planetType)}
        shielded={info.shielded}
        collapsed={info.hasShield && !info.shielded}
        ships={orbitItems}
        strike={
          phase === "BOMBARDMENT" ? (
            <StrikeLayer
              entry={bombardLog}
              entryId={idOf("BOMBARDMENT")}
              from="orbit"
              shipCount={bombardShips.length}
            />
          ) : phase === "SPACE_CANNON_DEFENSE" ? (
            <StrikeLayer
              entry={defenseLog}
              entryId={idOf("DEFENSE")}
              from="ground"
              shipCount={podItems.length}
            />
          ) : null
        }
      />
      <header className={styles.planetHead}>
        <div className={styles.planetTitle}>
          <b>{data?.name ?? info.planet}</b>
          <small>
            {data ? `${data.resources} res · ${data.influence} inf` : ""}
            {data?.planetType ? ` · ${data.planetType.toLowerCase()}` : ""}
          </small>
        </div>
        <div className={styles.badges}>
          {owner && info.owner && (
            <span className={styles.ownerBadge} title={`Controlled by ${owner.name}`}>
              <CircularFactionIcon faction={info.owner} size={20} />
            </span>
          )}
          {!info.owner && <span className={styles.badge}>Uncontrolled</span>}
          {info.shielded && (
            <span
              className={styles.badge}
              data-tone="shield"
              title="Planetary Shield: cannot be bombarded (a war sun ignores it)"
            >
              <IconShield size={12} /> Shield
            </span>
          )}
          {info.hasSpaceCannon && (
            <span
              className={styles.badge}
              data-tone="cannon"
              title="Space Cannon on this planet can fire at landing forces"
            >
              <IconCrosshair size={12} /> Space Cannon
            </span>
          )}
          {info.contested && (
            <span className={styles.badge} data-tone="war">
              <IconSwords size={12} /> Contested
            </span>
          )}
        </div>
      </header>

      <div className={styles.sides}>
        <section className={styles.side} aria-label="Defending forces">
          <h4>Defenders</h4>
          {defenders.length === 0 && Object.keys(info.structures).length === 0 && (
            <span className={styles.empty}>Empty</span>
          )}
          {defenders.map((key) => {
            const p = look(key);
            return (
              <div className={styles.tokens} key={key} style={{ "--c": p.rgb } as CSSProperties}>
                {expandForces(key, info.forces[key]).map((ship) => (
                  <GroundToken
                    key={ship.id}
                    ship={ship}
                    colorAlias={p.colorAlias}
                    faction={key}
                  />
                ))}
              </div>
            );
          })}
          {Object.entries(info.structures).map(([key, list]) => (
            <div className={styles.structures} key={key}>
              {list.map((s) => (
                <span className={styles.chip} key={s.baseType}>
                  {s.count}× {s.name}
                </span>
              ))}
            </div>
          ))}
        </section>
        <section className={styles.side} aria-label="Landed forces">
          <h4>Landed</h4>
          {(info.forces[attacker] ?? []).length === 0 ? (
            <span className={styles.empty}>—</span>
          ) : (
            <div className={styles.tokens}>
              {expandForces(attacker, info.forces[attacker]).map((ship) => (
                <GroundToken
                  key={ship.id}
                  ship={ship}
                  colorAlias={look(attacker).colorAlias}
                  faction={attacker}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {/* --- Działania bieżącego podkroku --- */}
      {phase === "BOMBARDMENT" && (
        <div className={styles.foot}>
          {info.shielded && !info.bombardable && (
            <span className={styles.note}>
              <IconShield size={13} /> Protected by Planetary Shield.
            </span>
          )}
          {info.bombardable && !view.bombard.done && (
            <span className={styles.note}>
              <IconTargetArrow size={13} />
              {planned > 0
                ? `${planned} ship${planned === 1 ? "" : "s"} will bombard here`
                : "No ship assigned"}
            </span>
          )}
          {bombardLog && (
            <div className={styles.rolls}>
              {bombardLog.rolls.map((r, i) => (
                <DiceRow key={i} roll={r} />
              ))}
              <p className={styles.rollSum}>
                {bombardLog.hits} bombardment hit
                {bombardLog.hits === 1 ? "" : "s"}
                {Object.keys(bombardLog.losses).length > 0 &&
                  ` · lost ${Object.entries(bombardLog.losses)
                    .map(([bt, n]) => `${n}× ${bt}`)
                    .join(", ")}`}
              </p>
            </div>
          )}
          {pendingBombard && (
            <AssignPanel
              title="Bombardment"
              ships={expandForces(
                pendingBombard.defender,
                info.forces[pendingBombard.defender] ?? [],
              )}
              required={pendingBombard.required}
              hits={pendingBombard.hits}
              colorAlias={look(pendingBombard.defender).colorAlias}
              faction={pendingBombard.defender}
              busy={actions.busy}
              onConfirm={(plan) =>
                actions.onAssignBombard(info.planet, pendingBombard.defender, plan)
              }
            />
          )}
        </div>
      )}

      {phase === "COMMIT" && (
        <div className={styles.foot}>
          {view.cargo.length === 0 ? (
            <span className={styles.note}>
              {info.committed && Object.keys(info.committed).length > 0
                ? `Landed: ${Object.entries(info.committed)
                    .map(([bt, n]) => `${n}× ${bt}`)
                    .join(", ")}`
                : "No ground forces left in orbit."}
            </span>
          ) : (
            <>
              {view.cargo.map((unit) => (
                <div className={styles.stepper} key={unit.baseType}>
                  <span>{unit.name}</span>
                  <button
                    type="button"
                    className={styles.stepBtn}
                    aria-label={`Land one fewer ${unit.name} on ${data?.name ?? info.planet}`}
                    disabled={(staged[unit.baseType] ?? 0) === 0}
                    onClick={() => actions.onBump(info.planet, unit.baseType, -1)}
                  >
                    <IconMinus size={12} />
                  </button>
                  <b>{staged[unit.baseType] ?? 0}</b>
                  <button
                    type="button"
                    className={styles.stepBtn}
                    aria-label={`Land one more ${unit.name} on ${data?.name ?? info.planet}`}
                    disabled={remainingOf(view.cargo, actions.stage, unit.baseType) === 0}
                    onClick={() => actions.onBump(info.planet, unit.baseType, 1)}
                  >
                    <IconPlus size={12} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                className={styles.ghostBtn}
                onClick={() => actions.onLandAll(info.planet)}
                title="Send everything still in orbit to this planet"
              >
                Land all here
              </button>
              {stagedCount > 0 && (
                <span className={styles.note}>{stagedCount} to land</span>
              )}
            </>
          )}
        </div>
      )}

      {phase === "SPACE_CANNON_DEFENSE" && defense && (
        <div className={styles.foot}>
          <span className={styles.note}>
            <IconCrosshair size={13} />
            {defense.shooters
              .map((s) => `${s.count}× ${s.name} ${s.hitsOn}+`)
              .join(", ")}
          </span>
          {defense.status === "open" && (
            <div className={styles.row}>
              <button
                type="button"
                className={styles.primaryBtn}
                disabled={actions.busy}
                onClick={() => actions.onDefenseFire(info.planet)}
              >
                Fire
              </button>
              <button
                type="button"
                className={styles.ghostBtn}
                disabled={actions.busy}
                onClick={() => actions.onDefensePass(info.planet)}
              >
                Don't fire
              </button>
            </div>
          )}
          {defenseLog && !defenseLog.passed && (
            <div className={styles.rolls}>
              {defenseLog.rolls.map((r, i) => (
                <DiceRow key={i} roll={r} />
              ))}
            </div>
          )}
          {defense.status === "pending" && (
            <AssignPanel
              title="Space Cannon"
              ships={expandForces(attacker, info.forces[attacker] ?? [])}
              required={defense.required}
              hits={defense.hits}
              colorAlias={look(attacker).colorAlias}
              faction={attacker}
              busy={actions.busy}
              onConfirm={(plan) =>
                actions.onAssignDefense(info.planet, attacker, plan)
              }
            />
          )}
          {defense.status === "resolved" && (
            <span className={styles.note} data-done>
              {defenseLog?.passed ? "Declined." : "Resolved."}
            </span>
          )}
        </div>
      )}

      {phase === "GROUND_COMBAT" && (
        <div className={styles.foot}>
          {info.contested && !view.inCombat && (
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={actions.busy}
              onClick={() => actions.onFight(info.planet)}
            >
              <IconSwords size={14} /> Fight for {data?.name ?? info.planet}
            </button>
          )}
          {combat && (
            <span className={styles.note} data-done>
              Fought in {combat.rounds} round{combat.rounds === 1 ? "" : "s"}:{" "}
              {combat.outcome === "draw"
                ? "everyone died - draw"
                : `${look(combat.winner ?? "").name} won`}
            </span>
          )}
        </div>
      )}

      {phase === "ESTABLISH" && result && (
        <div className={styles.foot}>
          <span className={styles.outcome} data-outcome={result.outcome}>
            {OUTCOME_LABEL[result.outcome] ?? result.outcome}
          </span>
          {Object.entries(result.destroyedStructures).map(([key, list]) => (
            <span className={styles.note} key={key}>
              Destroyed {look(key).name}'s{" "}
              {Object.entries(list)
                .map(([bt, n]) => `${n}× ${bt}`)
                .join(", ")}
            </span>
          ))}
          {result.outcome === "captured" && (
            <span className={styles.note}>
              Planet card gained and exhausted
              {result.explore ? " · explore it!" : ""}
            </span>
          )}
        </div>
      )}
    </article>
  );
}

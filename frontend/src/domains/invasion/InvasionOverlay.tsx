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
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { HoldRollButton } from "@/domains/dice/HoldRollButton";
import {
  soloHold,
  useDiceStage,
  type DiceThrowInput,
} from "@/domains/dice/diceStage";
import { countDice, volleyStartMs } from "@/domains/battle/diceRoll";
import { useDiceHold } from "@/domains/dice/useDiceHold";
import { CustodiansClaim } from "./CustodiansClaim";
import { InvasionPlanetCard } from "./InvasionPlanetCard";
import { usePlayerLook } from "./invasionUi";
import {
  bombardList,
  bumpStage,
  defaultBombardPlan,
  landAll,
  moveBombard,
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

/* Tło okna inwazji: jedna grafika na WSZYSTKIE podkroki naziemne (bombardowanie, lądowanie,
   Space Cannon Defense, walka, ustanowienie kontroli); sama bitwa ma własne okno. Plik
   podmienny w `assets/extra/`, serwowany pod `/static`; brak pliku = ciemne tło. */
const INVASION_BG = "/static/extra/invasion_bombard.jpg";

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
  const setBattleHidden = useAppStore((s) => s.setBattleHidden);
  const { battleStart } = useBoardEditor();
  const actions = useInvasionActions();
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<Stage>({});
  const [userPlan, setUserPlan] = useState<BombardPlan | null>(null);
  // Trwa przeciąganie jednostek/statków: karty planet podświetlają się jako cele.
  const [dragging, setDragging] = useState(false);
  // Plasma Scoring ("may"): wybrany przydział (typ|planeta); undefined = domyślnie najcelniejszy.
  const [plasmaPick, setPlasmaPick] = useState<string | null | undefined>(undefined);

  const phase = view.phase ?? "BOMBARDMENT";
  const attacker = view.attacker ? look(view.attacker) : null;
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName = tile
    ? (getTileById(tile.systemId)?.name ?? view.position)
    : view.position;
  const planetName = (id: string) => getPlanetData(id)?.name ?? id;

  // Nowe wpisy dziennika = świeży rzut: kości na wspólnej scenie (fizyczny rzut), a wynik i
  // salwy efektów czekają, aż kości wylądują. Stan pochodny liczony w renderze (bez migotania).
  const throwDice = useDiceStage((s) => s.throwDice);
  const [seenLen, setSeenLen] = useState(view.log.length);
  const [rollBatch, setRollBatch] = useState({ from: view.log.length, ms: 0 });
  const [queuedThrow, setQueuedThrow] = useState<DiceThrowInput | null>(null);
  if (view.log.length !== seenLen) {
    setSeenLen(view.log.length);
    if (view.log.length < seenLen) {
      setRollBatch({ from: view.log.length, ms: 0 }); // cofnięcie (Undo)
    } else {
      const fresh = view.log.slice(seenLen).filter((e) => !e.passed);
      const groupsOf = (kind: "BOMBARDMENT" | "DEFENSE") =>
        fresh
          .filter((e) => e.phase === kind)
          .flatMap((e) =>
            e.rolls.map((r) => ({
              dice: r.dice,
              modifier: r.modifier ?? 0,
              hitsOn: r.hitsOn,
            })),
          );
      const bombRolls = groupsOf("BOMBARDMENT");
      const defRolls = groupsOf("DEFENSE");
      const defKey = fresh.find((e) => e.phase === "DEFENSE")?.defender ?? "";
      const attRgb = attacker?.rgb ?? "148 163 184";
      const defRgb = look(defKey).rgb;
      let input: DiceThrowInput | null = null;
      if (bombRolls.length > 0 && defRolls.length > 0) {
        input = {
          left: bombRolls,
          right: defRolls,
          leftRgb: attRgb,
          rightRgb: defRgb,
          solo: false,
        };
      } else if (bombRolls.length > 0) {
        input = { left: bombRolls, leftRgb: attRgb };
      } else if (defRolls.length > 0) {
        input = { left: defRolls, leftRgb: defRgb };
      }
      setRollBatch({
        from: seenLen,
        ms: input
          ? volleyStartMs(countDice(input.left), countDice(input.right ?? []))
          : 0,
      });
      setQueuedThrow(input);
    }
  }
  useEffect(() => {
    if (!queuedThrow) return;
    throwDice(queuedThrow);
    setQueuedThrow(null);
  }, [queuedThrow, throwDice]);

  const bombard = view.bombard;
  const plan = userPlan ?? defaultBombardPlan(bombard.groups, bombard.targets);
  const canBombard = bombard.groups.length > 0 && !bombard.done;
  // Przydziały z co najmniej jednym statkiem - kandydaci na jednostkę z dodatkową kością.
  const plasmaOptions = bombard.groups.flatMap((g) =>
    Object.entries(plan[g.baseType] ?? {})
      .filter(([, n]) => n > 0)
      .map(([planet]) => ({ key: `${g.baseType}|${planet}`, group: g, planet })),
  );
  const bestPlasma = [...plasmaOptions].sort((a, b) => a.group.hitsOn - b.group.hitsOn)[0];
  const plasmaUnit =
    bombard.plasmaDice > 0 && plasmaPick !== null
      ? (plasmaOptions.find((o) => o.key === plasmaPick)?.key ?? bestPlasma?.key ?? null)
      : null;

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
    rollBatch,
    bombardPlan: canBombard ? plan : {},
    dragging,
    onDrag: setDragging,
    bombardEditable: canBombard && bombard.targets.length > 1,
    onBombardMove: (
      planet: string,
      baseType: string,
      from: string | null,
      all: boolean,
    ) =>
      setUserPlan(moveBombard(plan, baseType, bombard.targets, planet, from, all)),
    onBump: (planet: string, baseType: string, delta: number) =>
      setStage((s) => bumpStage(s, view.cargo, planet, baseType, delta)),
    onLandAll: (planet: string) =>
      setStage((s) => landAll(s, view.cargo, planet)),
    onFight: (planet: string) =>
      void run(async () => {
        setBattleHidden(false);
        await battleStart(planet);
      }),
    onDefenseFire: (planet: string, plasmaKey: string | null) =>
      void run(() => actions.defenseFire(planet, plasmaKey)),
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
          // Po zdjęciu żetonu Custodians trzeba zlądować na Mecatol Rex (jedyna planeta systemu).
          disabled:
            staged > 0 ||
            (view.custodians?.claimed === true &&
              !view.planets.some((p) => Object.keys(p.committed).length > 0)),
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
      // Okno pełnoekranowe: dok ręki zwija się do paska, a okno rezerwuje pod nim miejsce.
      data-fullscreen-overlay=""
      role="dialog"
      aria-modal="true"
      aria-label={`Invasion of ${systemName ?? ""}`}
      style={{ "--att-rgb": attacker?.rgb ?? "148 163 184" } as CSSProperties}
    >
      <div
        className={styles.backdrop}
        style={{ backgroundImage: `url("${INVASION_BG}")` }}
        aria-hidden="true"
      />
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

      <p className={styles.hint}>{HINT[phase]}</p>
      {/* Technologie atakującego i obrońców działające w inwazji (Plasma Scoring, X-89, Magen...). */}
      <div className={styles.techRow}>
        <ActiveTechs context="invasion" faction={view.attacker} label="Attacker" />
        {[...new Set(view.planets.map((p) => p.owner))]
          .filter((owner): owner is string => owner != null && owner !== view.attacker)
          .map((owner) => (
            <ActiveTechs key={owner} context="invasion" faction={owner} label="Defender" />
          ))}
      </div>

      {view.custodians &&
        (phase === "BOMBARDMENT" || phase === "COMMIT") &&
        (view.custodians.onBoard || view.custodians.claimed) && (
          <div className={styles.custodians}>
            <CustodiansClaim
              view={view.custodians}
              busy={busy}
              onClaim={(planets, tradeGoods) =>
                actions.claimCustodians(planets, tradeGoods)
              }
            />
          </div>
        )}

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
                  <span
                    className={styles.bombardName}
                    draggable={bombard.targets.length > 1 || undefined}
                    title={
                      bombard.targets.length > 1
                        ? "Drag onto a planet to move a ship there (Shift = all)"
                        : undefined
                    }
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = "move";
                      e.dataTransfer.setData(
                        "text/x-bombard",
                        JSON.stringify({ baseType: g.baseType, from: null }),
                      );
                      setDragging(true);
                    }}
                    onDragEnd={() => setDragging(false)}
                  >
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
                            <IconMinus size={18} />
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
                            <IconPlus size={18} />
                          </button>
                        )}
                      </span>
                    ))}
                  </span>
                </div>
              ))}
              {bombard.plasmaDice > 0 && plasmaOptions.length > 0 && (
                <div className={styles.plasma} role="radiogroup" aria-label="Plasma Scoring">
                  <small>Plasma Scoring: 1 unit may roll 1 additional die</small>
                  {plasmaOptions.map((o) => (
                    <label className={styles.plasmaOption} key={o.key}>
                      <input
                        type="radio"
                        name="plasma-bombard"
                        checked={plasmaUnit === o.key}
                        onChange={() => setPlasmaPick(o.key)}
                      />
                      {o.group.name} ({o.group.hitsOn}+) at {planetName(o.planet)}
                    </label>
                  ))}
                  <label className={styles.plasmaOption}>
                    <input
                      type="radio"
                      name="plasma-bombard"
                      checked={plasmaUnit === null}
                      onChange={() => setPlasmaPick(null)}
                    />
                    No extra die
                  </label>
                </div>
              )}
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
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = "move";
                      e.dataTransfer.setData("text/x-basetype", u.baseType);
                      setDragging(true);
                    }}
                    onDragEnd={() => setDragging(false)}
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
            <HoldRollButton
              className={styles.primaryBtn}
              disabled={busy}
              onFire={() =>
                void run(() => actions.bombard(bombardList(plan), plasmaUnit))
              }
              onHold={soloHold(
                bombard.groups.reduce(
                  (n, g) =>
                    n +
                    Object.values(plan[g.baseType] ?? {}).reduce(
                      (a, b) => a + b,
                      0,
                    ) *
                      g.dicePerUnit,
                  0,
                ) + (plasmaUnit ? bombard.plasmaDice : 0),
                attacker?.rgb ?? "148 163 184",
              )}
              hint={false}
              title="Roll bombardment (hold to shake the dice, release to throw)"
            >
              <IconRocket size={14} /> Roll bombardment
            </HoldRollButton>
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

/** Czas trzymania sił sprzed rzutu: kości na stole + salwa efektów (jak `rollBatch`). */
function invasionHoldMs(view: InvasionView, fromLen: number): number {
  const fresh = view.log.slice(fromLen).filter((e) => !e.passed);
  const dice = (kind: "BOMBARDMENT" | "DEFENSE") =>
    fresh
      .filter((e) => e.phase === kind)
      .flatMap((e) => e.rolls)
      .reduce((n, r) => n + r.dice.length, 0);
  const bomb = dice("BOMBARDMENT");
  const def = dice("DEFENSE");
  return bomb + def > 0 ? volleyStartMs(bomb, def) + 1800 : 0;
}

/** Widok z siłami naziemnymi sprzed rzutu; reszta (dziennik, panele) żywa. */
function freezeInvasionForces(
  live: InvasionView,
  before: InvasionView,
): InvasionView {
  return {
    ...live,
    planets: live.planets.map((p) => {
      const old = before.planets.find((o) => o.planet === p.planet);
      return old ? { ...p, forces: old.forces } : p;
    }),
  };
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
  const { data: live } = useInvasion(active);
  // Straty od bombardowania/Space Cannon pokazujemy dopiero po kościach i salwie efektów.
  const { view } = useDiceHold(live, invasionHoldMs, freezeInvasionForces);

  // Każda zmiana stanu gry (walka zamknięta, ruch innego gracza…) odświeża widok inwazji.
  useEffect(() => {
    if (active) void queryClient.invalidateQueries({ queryKey: ["invasion"] });
  }, [gameState, active, queryClient]);

  if (!active || !view?.active || view.simple) return null;
  return <InvasionWindow key={view.position} view={view} />;
}

export default InvasionOverlay;

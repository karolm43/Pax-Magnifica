import { useMemo, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import {
  IconAlertTriangle,
  IconCheck,
  IconChevronsRight,
  IconHourglass,
  IconTrophy,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { Tooltip } from "@/ds";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import type {
  Objective,
  ObjectivePaymentBody,
  PlayerData,
  StatusObjectiveOption,
  StatusPhaseData,
  StatusStepName,
} from "@/entities/data/types";
import { publicObjectives } from "@/entities/data/publicObjectives";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { FleetPoolStatusMeter } from "@/domains/map/components/FleetPoolWarning";
import { CommandPools } from "@/shared/ui/CommandPools/CommandPools";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useCanActAs } from "@/domains/network/useNetworkMe";
import { autoAlloc, type Alloc } from "./autoAlloc";
import { ObjectiveSpendForm } from "./ObjectiveSpendForm";
import styles from "./StatusPhasePanel.module.css";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { PHASE_WINDOW } from "@/hooks/useDecisionZone";

/** Osiem kroków fazy statusu (R_status_phase): krótka etykieta + czy robi to silnik. */
const STEPS: { n: number; label: string; auto: boolean }[] = [
  { n: 1, label: "Score", auto: false },
  { n: 2, label: "Reveal", auto: true },
  { n: 3, label: "Draw", auto: true },
  { n: 4, label: "Clear tokens", auto: true },
  { n: 5, label: "Tokens", auto: false },
  { n: 6, label: "Ready", auto: true },
  { n: 7, label: "Repair", auto: true },
  { n: 8, label: "Return cards", auto: false },
];

const STEP_TITLES = [
  "Score objectives",
  "Reveal public objective",
  "Draw action cards",
  "Remove command tokens",
  "Gain & redistribute command tokens",
  "Ready cards",
  "Repair units",
  "Return strategy cards",
];

const publicText = new Map(publicObjectives.map((o) => [o.alias, o.text]));

/** Który krok jest teraz bieżący (1–8) dla danego etapu interakcji. */
function currentStepNumber(step: StatusStepName): number {
  if (step === "SCORE_OBJECTIVES") return 1;
  if (step === "REDISTRIBUTE") return 5;
  return 8;
}

function allocOf(player: PlayerData): Alloc {
  return { t: player.tacticalCC, f: player.fleetCC, s: player.strategicCC };
}

/**
 * Panel fazy statusu — prowadzi przez 8 kroków (RULES.md 41). Interaktywne są krok 1
 * (punktowanie, gracze po kolei wg inicjatywy) i krok 5 (rozdział żetonów); kroki 2–4
 * i 6–7 wykonuje silnik, krok 8 ogłasza mówca („Next phase"). Panel niczego nie liczy:
 * postęp i gotowość celów przychodzą z backendu (`core/objective_progress`).
 */
export function StatusPhasePanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: webData } = usePlayerData(gameId);
  const { statusScore, statusFinishScoring, statusRedistribute } = useBoardEditor();
  const drag = useDraggablePanel("statusPanel.pos.v2");
  // Gra sieciowa (RULES.md 44.3): każdy klient decyduje tylko za siebie; reszta = „czeka na”.
  const canActAs = useCanActAs();
  const [busy, setBusy] = useState(false);
  const [allocs, setAllocs] = useState<Record<string, Alloc>>({});

  const status: StatusPhaseData | null | undefined = gameState?.status;
  const players = useMemo(() => webData?.playerData ?? [], [webData?.playerData]);
  const objectivesByKey = useMemo(() => {
    const map = new Map<string, Objective>();
    for (const o of webData?.objectives?.allObjectives ?? []) map.set(o.key, o);
    return map;
  }, [webData?.objectives?.allObjectives]);

  if (!status || !gameState || !gameState.phase.startsWith("status")) return null;

  const byId = new Map(players.map((p) => [p.discordId, p]));
  const nameOf = (id: string) => {
    const player = byId.get(id);
    return player ? getPlayerFactionDisplayName(player) : id;
  };
  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn().finally(() => setBusy(false));
  };

  const current = currentStepNumber(status.step);
  const winner = gameState.winnerId ? byId.get(gameState.winnerId) : undefined;
  const scorer = players.find((p) => p.color === gameState.activeTurnPlayer);
  const waitingTokens = players.filter((p) => !status.done.includes(p.discordId));
  const myTokens = waitingTokens.filter((p) => canActAs(p.discordId));
  const othersTokens = waitingTokens.filter((p) => !canActAs(p.discordId));

  return (
    <aside
      className={styles.panel}
      aria-label="Status phase"
      style={drag.style}
      // Okno fazy (U3): centrum Decisions czeka jako „+N”, dymki mapy go nie zasłaniają.
      {...PHASE_WINDOW}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
    >
      <header
        className={styles.header}
        data-grab
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move · double-click resets position"
      >
        <span className={styles.label}>Status phase</span>
        <b className={styles.title}>
          {current}. {STEP_TITLES[current - 1]}
        </b>
        <span className={styles.round}>Round {webData?.gameRound}</span>
      </header>

      <ol className={styles.steps}>
        {STEPS.map((step) => {
          const state = step.n < current ? "done" : step.n === current ? "now" : "next";
          return (
            <Tooltip
              key={step.n}
              multiline
              w={290}
              openDelay={80}
              position="top"
              label={
                <StepTip
                  n={step.n}
                  state={state}
                  status={status}
                  nameOf={nameOf}
                  objectivesByKey={objectivesByKey}
                  custodiansRemoved={status.custodiansRemoved}
                />
              }
            >
              <li className={styles.step} data-state={state} data-auto={step.auto || undefined} tabIndex={0}>
                <span className={styles.stepNo}>
                  {state === "done" ? <IconCheck size={12} aria-hidden="true" /> : step.n}
                </span>
                <span className={styles.stepLabel}>{step.label}</span>
              </li>
            </Tooltip>
          );
        })}
      </ol>

      <div className={styles.well}>
        {winner && (
          <p className={styles.winner}>
            <IconTrophy size={18} aria-hidden="true" />
            <span>
              Game over — <b>{getPlayerFactionDisplayName(winner)}</b> wins.
            </span>
          </p>
        )}

        {!winner && status.step === "SCORE_OBJECTIVES" && scorer && !canActAs(scorer.discordId) && (
          <WaitingFor ids={[scorer.discordId]} nameOf={nameOf} what="to score objectives" />
        )}

        {!winner && status.step === "SCORE_OBJECTIVES" && scorer && canActAs(scorer.discordId) && (
          <ScoreStep
            scorer={scorer}
            status={status}
            objectivesByKey={objectivesByKey}
            busy={busy}
            onScore={(kind, id, pay) =>
              run(() => statusScore(scorer.discordId, kind, id, pay))
            }
            onFinish={() => run(() => statusFinishScoring(scorer.discordId))}
          />
        )}

        {!winner && status.step === "REDISTRIBUTE" && (
          <div className={styles.section}>
            <p className={styles.note}>
              Each player gained command tokens. Split <b>all</b> of your tokens between the
              tactic, fleet and strategy pools.
            </p>
            <div className={styles.cards}>
              {myTokens.map((player) => {
                  const unassigned = status.unassignedCc[player.discordId] ?? 0;
                  const base = allocOf(player);
                  const alloc = allocs[player.discordId] ?? base;
                  const total = base.t + base.f + base.s + unassigned;
                  const left = total - (alloc.t + alloc.f + alloc.s);
                  const set = (next: Alloc) =>
                    setAllocs((prev) => ({ ...prev, [player.discordId]: next }));
                  const ships = status.fleetShips?.[player.discordId] ?? {};
                  return (
                    <div key={player.discordId} className={styles.card}>
                      <div className={styles.cardHead}>
                        <CircularFactionIcon faction={player.faction} size={22} />
                        <b>{nameOf(player.discordId)}</b>
                        <span className={styles.left} data-ok={left === 0 || undefined}>
                          {left === 0 ? "ready" : `${left} to place`}
                        </span>
                      </div>
                      {/* Hyper Metabolism, Neural Motivator... - dodatkowe żetony/karty w tej fazie. */}
                      <ActiveTechs context="status" faction={player.faction} />
                      <CommandPools
                        alloc={alloc}
                        total={total}
                        disabled={busy}
                        onChange={set}
                        onAuto={() => set(autoAlloc(base, unassigned, ships))}
                        autoTitle="New tokens fill the fleet pool up to your largest fleet, the rest go to the tactic pool"
                      />
                      {/* Fleet pool (RULES.md 42): podgląd floty względem planowanej puli. */}
                      <FleetPoolStatusMeter pool={alloc.f} ships={ships} />
                      <button
                        type="button"
                        className={styles.primary}
                        disabled={busy || left !== 0}
                        onClick={() =>
                          run(async () => {
                            await statusRedistribute(player.discordId, {
                              tactical: alloc.t,
                              fleet: alloc.f,
                              strategic: alloc.s,
                            });
                            setAllocs((prev) => {
                              const next = { ...prev };
                              delete next[player.discordId];
                              return next;
                            });
                          })
                        }
                      >
                        <IconCheck size={15} aria-hidden="true" />
                        <span>Confirm</span>
                      </button>
                    </div>
                  );
                })}
            </div>
            {othersTokens.length > 0 && (
              <WaitingFor
                ids={othersTokens.map((p) => p.discordId)}
                nameOf={nameOf}
                what="to place their command tokens"
              />
            )}
            <ExcessNotice status={status} nameOf={nameOf} />
          </div>
        )}

        {!winner && status.step === "COMPLETE" && (
          <div className={styles.section}>
            <p className={styles.note}>
              Cards are readied and units repaired. The speaker returns the Strategy Cards with{" "}
              <b>Next phase</b>
              {status.custodiansRemoved ? " — the agenda phase follows." : " — a new round follows."}
            </p>
            <ExcessNotice status={status} nameOf={nameOf} />
            <p className={styles.hint}>
              <IconChevronsRight size={14} aria-hidden="true" />
              <span>Use “Next phase” in the turn panel.</span>
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

/** Co robi dany krok fazy statusu (R_status_phase) — pokazywane w podpowiedzi. */
const STEP_RULES: string[] = [
  "In initiative order each player may score one public and one secret objective whose requirements they meet right now. Spend-type objectives are paid on scoring.",
  "The speaker reveals the next public objective (Stage I first, Stage II only after all Stage I are revealed). With nothing left to reveal the game ends.",
  "In initiative order each player draws one action card. If the deck runs short, the lowest-initiative players draw first, then the discard pile is reshuffled.",
  "Every command token is taken off the board and returned to its owner's reinforcements.",
  "Each player gains two command tokens, then freely splits all of them between the tactic, fleet and strategy pools.",
  "All exhausted planets, technologies, leaders and strategy cards are readied.",
  "All damaged units are repaired, even ones that lost Sustain Damage.",
  "The speaker returns all Strategy Cards. If the Custodians token was removed, the agenda phase follows; otherwise a new round starts.",
];

type Entry = { step: number; label: string; [key: string]: unknown };

function countsText(
  record: unknown,
  nameOf: (id: string) => string,
  unit: string,
): string[] {
  if (!record || typeof record !== "object") return [];
  return Object.entries(record as Record<string, number>)
    .filter(([, n]) => n > 0)
    .map(([id, n]) => `${nameOf(id)}: ${n} ${unit}`);
}

/** Zawartość podpowiedzi kroku: reguła + (gdy już się odbył) co dokładnie się stało. */
function StepTip({
  n,
  state,
  status,
  nameOf,
  objectivesByKey,
  custodiansRemoved,
}: {
  n: number;
  state: "done" | "now" | "next";
  status: StatusPhaseData;
  nameOf: (id: string) => string;
  objectivesByKey: Map<string, Objective>;
  custodiansRemoved: boolean;
}) {
  const entries = (status.log as Entry[]).filter((e) => e.step === n);
  const lines: string[] = [];
  let card: { name: string; points: number; text?: string } | null = null;

  for (const entry of entries) {
    if (entry.label === "scored") {
      const key = String(entry.objective);
      const secret = entry.kind === "secret";
      const name = secret
        ? (getSecretObjectiveData(key)?.name ?? key)
        : (objectivesByKey.get(key)?.name ?? key);
      lines.push(`${nameOf(String(entry.player))} scored ${secret ? "a secret objective" : name}${secret ? ` (${name})` : ""}`);
    } else if (entry.label === "revealed") {
      const key = String(entry.objective);
      const objective = objectivesByKey.get(key);
      card = {
        name: objective?.name ?? key,
        points: objective?.pointValue ?? 1,
        text: publicText.get(key),
      };
    } else if (entry.label === "game_end_no_objectives") {
      lines.push("No public objectives left — the game ended.");
    } else if (entry.label === "drew_action_cards") {
      lines.push(...countsText(entry.drawn, nameOf, "action card"));
    } else if (entry.label === "removed_command_tokens") {
      lines.push(...countsText(entry.returned, nameOf, "token returned"));
    } else if (entry.label === "gained_command_tokens") {
      lines.push(...countsText(entry.gained, nameOf, "new token"));
    } else if (entry.label === "redistributed") {
      lines.push(
        `${nameOf(String(entry.player))}: tactic ${Number(entry.tactical)} · fleet ${Number(entry.fleet)} · strategy ${Number(entry.strategic)}`,
      );
    }
  }
  if (n === 1 && state === "done" && lines.length === 0) lines.push("Nobody scored an objective.");
  if (n === 8) {
    lines.push(custodiansRemoved ? "Next: agenda phase." : "Next: new round (strategy phase).");
  }

  return (
    <div className={styles.tip}>
      <b>
        {n}. {STEP_TITLES[n - 1]}
        {STEPS[n - 1].auto && <em> · automatic</em>}
      </b>
      <span>{STEP_RULES[n - 1]}</span>
      {card && (
        <div className={styles.tipCard}>
          <small>Revealed</small>
          <strong>
            {card.name} <i>+{card.points} VP</i>
          </strong>
          {card.text && <span>{card.text}</span>}
        </div>
      )}
      {lines.length > 0 && (
        <ul>
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      {state === "next" && <small className={styles.tipHint}>Not reached yet.</small>}
    </div>
  );
}

/** Gracze, na których decyzję czeka ten klient (sieć: cudze decyzje nie są tu klikalne). */
function WaitingFor({
  ids,
  nameOf,
  what,
}: {
  ids: string[];
  nameOf: (id: string) => string;
  what: string;
}) {
  return (
    <p className={styles.waiting} role="status">
      <IconHourglass size={14} aria-hidden="true" />
      <span>Waiting for</span>
      {ids.map((id) => (
        <PlayerTag key={id} playerId={id} size={14} fallback={nameOf(id)} />
      ))}
      <span>{what}</span>
    </p>
  );
}

function ExcessNotice({
  status,
  nameOf,
}: {
  status: StatusPhaseData;
  nameOf: (id: string) => string;
}) {
  const entries = Object.entries(status.fleetExcess);
  if (entries.length === 0) return null;
  return (
    <div className={styles.warn} role="status">
      <IconAlertTriangle size={15} aria-hidden="true" />
      <div>
        <b>Fleet pool exceeded</b>
        {entries.map(([playerId, systems]) => (
          <span key={playerId}>
            <PlayerTag playerId={playerId} size={14} fallback={nameOf(playerId)} />: remove{" "}
            {Object.entries(systems)
              .map(([position, n]) => `${n} ship${n === 1 ? "" : "s"} in ${position}`)
              .join(", ")}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Jedna pozycja celu: nazwa + wymaganie + postęp + przycisk zdobycia. Eksportowana -
 * ten sam pasek postępu używa okno Imperial (spójny wygląd punktowania celów).
 */
export function ObjectiveRow({
  name,
  text,
  points,
  option,
  stage,
  scored,
  busy,
  onScore,
}: {
  name: string;
  text?: string;
  points: number;
  option: StatusObjectiveOption;
  stage: "orange" | "blue" | "red";
  scored: boolean;
  busy: boolean;
  onScore: (payment?: ObjectivePaymentBody) => void;
}) {
  // Cele „Spend…": zamiast zdobywać od razu, otwieramy okno wyboru płatności.
  const [paying, setPaying] = useState(false);
  const hasMeter = option.progress != null && option.threshold > 0;
  const fill = hasMeter ? Math.min(1, (option.progress ?? 0) / option.threshold) : 0;
  const can = option.ready && !scored;
  return (
    <div className={styles.row} data-stage={stage} data-ready={can || undefined}>
      <div className={styles.rowText}>
        <span className={styles.rowName}>{name}</span>
        {text && <span className={styles.rowReq}>{text}</span>}
      </div>
      <div className={styles.meter} data-manual={option.manual || undefined}>
        {hasMeter ? (
          <>
            <span className={styles.count}>
              {option.progress}
              <i>/{option.threshold}</i>
            </span>
            <span className={styles.bar} style={{ "--fill": fill } as CSSProperties} />
          </>
        ) : (
          <span className={styles.manual} title="The game does not track this condition — you confirm it">
            confirm manually
          </span>
        )}
      </div>
      <button
        type="button"
        className={styles.score}
        disabled={busy || !can}
        onClick={() => (option.spend ? setPaying((open) => !open) : onScore())}
        title={
          can
            ? "Requirements met — score it"
            : scored
              ? "You already scored an objective of this type this phase"
              : "Requirements not met yet"
        }
      >
        {can ? (option.spend ? `Pay & score +${points}` : `Score +${points}`) : "Not yet"}
      </button>
      {can && paying && option.spend && (
        <ObjectiveSpendForm spend={option.spend} busy={busy} onConfirm={(pay) => onScore(pay)} />
      )}
    </div>
  );
}

function ScoreStep({
  scorer,
  status,
  objectivesByKey,
  busy,
  onScore,
  onFinish,
}: {
  scorer: PlayerData;
  status: StatusPhaseData;
  objectivesByKey: Map<string, Objective>;
  busy: boolean;
  onScore: (
    kind: "public" | "secret",
    objectiveId: string,
    payment?: ObjectivePaymentBody,
  ) => void;
  onFinish: () => void;
}) {
  const id = scorer.discordId;
  const byReady = (a: StatusObjectiveOption, b: StatusObjectiveOption) =>
    Number(b.ready) - Number(a.ready);
  const publics = [...(status.publicOptions[id] ?? [])].sort(byReady);
  const secrets = [...(status.secretOptions[id] ?? [])].sort(byReady);
  const scoredPublic = status.scoredPublic.includes(id);
  const scoredSecret = status.scoredSecret.includes(id);
  const homeOk = status.homeControlled[id] !== false;

  return (
    <div className={styles.section}>
      <div className={styles.cardHead}>
        <CircularFactionIcon faction={scorer.faction} size={24} />
        <b>{getPlayerFactionDisplayName(scorer)}</b>
        <span className={styles.left}>{scorer.totalVps} VP</span>
      </div>

      <div className={styles.group}>
        <h4>
          Public objectives
          <small>{scoredPublic ? "scored this phase" : "score up to one"}</small>
        </h4>
        {!homeOk && (
          <p className={styles.warnLine}>
            <IconAlertTriangle size={14} aria-hidden="true" />
            You do not control every planet in your home system — public objectives are locked.
          </p>
        )}
        {publics.length === 0 && <span className={styles.empty}>No revealed objectives left to score.</span>}
        {publics.map((option) => {
          const objective = objectivesByKey.get(option.key);
          const points = objective?.pointValue ?? 1;
          return (
            <ObjectiveRow
              key={option.key}
              name={objective?.name ?? option.key}
              text={publicText.get(option.key)}
              points={points}
              option={option}
              stage={points >= 2 ? "blue" : "orange"}
              scored={scoredPublic}
              busy={busy}
              onScore={(pay) => onScore("public", option.key, pay)}
            />
          );
        })}
      </div>

      <div className={styles.group}>
        <h4>
          Secret objectives
          <small>{scoredSecret ? "scored this phase" : "score up to one"}</small>
        </h4>
        {secrets.length === 0 && <span className={styles.empty}>No secret objectives to score in the status phase.</span>}
        {secrets.map((option) => {
          const data = getSecretObjectiveData(option.key);
          return (
            <ObjectiveRow
              key={option.key}
              name={data?.name ?? option.key}
              text={data?.text}
              points={data?.points ?? 1}
              option={option}
              stage="red"
              scored={scoredSecret}
              busy={busy}
              onScore={(pay) => onScore("secret", option.key, pay)}
            />
          );
        })}
      </div>

      <button type="button" className={styles.primary} disabled={busy} onClick={onFinish}>
        <IconCheck size={15} aria-hidden="true" />
        <span>{scoredPublic || scoredSecret ? "Done scoring" : "Score nothing"}</span>
      </button>
    </div>
  );
}

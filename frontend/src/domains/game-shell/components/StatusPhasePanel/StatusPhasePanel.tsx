import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  IconCheck,
  IconChevronsRight,
  IconMinus,
  IconPlus,
  IconStar,
  IconTrophy,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import type {
  Objective,
  PlayerData,
  StatusPhaseData,
  StatusStepName,
} from "@/entities/data/types";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import styles from "./StatusPhasePanel.module.css";

/** Osiem kroków fazy statusu (R_status_phase) — etykieta + kto je wykonuje. */
const STEPS: { n: number; label: string; auto: boolean }[] = [
  { n: 1, label: "Score objectives", auto: false },
  { n: 2, label: "Reveal public objective", auto: true },
  { n: 3, label: "Draw action cards", auto: true },
  { n: 4, label: "Remove command tokens", auto: true },
  { n: 5, label: "Gain & redistribute tokens", auto: false },
  { n: 6, label: "Ready cards", auto: true },
  { n: 7, label: "Repair units", auto: true },
  { n: 8, label: "Return strategy cards", auto: false },
];

/** Który krok jest teraz bieżący (1–8) dla danego etapu interakcji. */
function currentStepNumber(step: StatusStepName): number {
  if (step === "SCORE_OBJECTIVES") return 1;
  if (step === "REDISTRIBUTE") return 5;
  return 8;
}

type Alloc = { t: number; f: number; s: number };

function allocOf(player: PlayerData): Alloc {
  return { t: player.tacticalCC, f: player.fleetCC, s: player.strategicCC };
}

/**
 * Panel fazy statusu — prowadzi przez 8 kroków (RULES.md 41). Interaktywne są krok 1
 * (punktowanie celów, gracze po kolei wg inicjatywy) i krok 5 (rozdział żetonów
 * dowodzenia); kroki 2–4 i 6–7 silnik wykonuje sam, krok 8 ogłasza mówca („Next phase"
 * w panelu tury). Dane tylko z web-data — panel nie liczy reguł.
 */
export function StatusPhasePanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: webData } = usePlayerData(gameId);
  const { statusScore, statusFinishScoring, statusRedistribute } = useBoardEditor();
  const drag = useDraggablePanel("statusPanel.pos");
  const [busy, setBusy] = useState(false);
  // Lokalne rozdziały żetonów (player_id → pule); brak wpisu = stan z serwera.
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
  const activeColor = gameState.activeTurnPlayer;
  const scorer = players.find((p) => p.color === activeColor);

  return (
    <aside
      className={styles.panel}
      aria-label="Status phase"
      style={drag.style}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
    >
      <header
        className={styles.head}
        data-grab
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move · double-click resets position"
      >
        <small>Status phase</small>
        <b>
          Step {current} · {STEPS[current - 1].label}
        </b>
      </header>

      <ol className={styles.steps}>
        {STEPS.map((step) => {
          const state = step.n < current ? "done" : step.n === current ? "now" : "next";
          return (
            <li key={step.n} className={styles.step} data-state={state} data-auto={step.auto || undefined}>
              <span className={styles.stepNo}>
                {state === "done" ? <IconCheck size={11} aria-hidden="true" /> : step.n}
              </span>
              <span className={styles.stepLabel}>{step.label}</span>
              {step.auto && <em>auto</em>}
            </li>
          );
        })}
      </ol>

      {winner && (
        <p className={styles.winner}>
          <IconTrophy size={16} aria-hidden="true" />
          <span>
            Game over — <b>{getPlayerFactionDisplayName(winner)}</b> wins.
          </span>
        </p>
      )}

      {!winner && status.step === "SCORE_OBJECTIVES" && scorer && (
        <ScoreStep
          scorer={scorer}
          status={status}
          objectivesByKey={objectivesByKey}
          busy={busy}
          onScore={(kind, id) => run(() => statusScore(scorer.discordId, kind, id))}
          onFinish={() => run(() => statusFinishScoring(scorer.discordId))}
        />
      )}

      {!winner && status.step === "REDISTRIBUTE" && (
        <div className={styles.body}>
          <p className={styles.note}>
            Each player gained command tokens. Split <b>all</b> of your tokens between the
            tactic, fleet and strategy pools.
          </p>
          {players
            .filter((p) => !status.done.includes(p.discordId))
            .map((player) => {
              const unassigned = status.unassignedCc[player.discordId] ?? 0;
              const base = allocOf(player);
              const alloc = allocs[player.discordId] ?? base;
              const total = base.t + base.f + base.s + unassigned;
              const left = total - (alloc.t + alloc.f + alloc.s);
              const set = (next: Alloc) =>
                setAllocs((prev) => ({ ...prev, [player.discordId]: next }));
              const row = (key: keyof Alloc, label: string) => (
                <div className={styles.pool}>
                  <span>{label}</span>
                  <button
                    type="button"
                    aria-label={`Fewer ${label} tokens`}
                    disabled={busy || alloc[key] <= 0}
                    onClick={() => set({ ...alloc, [key]: alloc[key] - 1 })}
                  >
                    <IconMinus size={12} aria-hidden="true" />
                  </button>
                  <b>{alloc[key]}</b>
                  <button
                    type="button"
                    aria-label={`More ${label} tokens`}
                    disabled={busy || left <= 0}
                    onClick={() => set({ ...alloc, [key]: alloc[key] + 1 })}
                  >
                    <IconPlus size={12} aria-hidden="true" />
                  </button>
                </div>
              );
              return (
                <div key={player.discordId} className={styles.card}>
                  <div className={styles.cardHead}>
                    <CircularFactionIcon faction={player.faction} size={20} />
                    <b>{nameOf(player.discordId)}</b>
                    <span className={styles.left} data-ok={left === 0 || undefined}>
                      {left === 0 ? "ready" : `${left} to place`}
                    </span>
                  </div>
                  <div className={styles.pools}>
                    {row("t", "Tactic")}
                    {row("f", "Fleet")}
                    {row("s", "Strategy")}
                  </div>
                  <button
                    type="button"
                    className={styles.confirm}
                    disabled={busy || left !== 0}
                    onClick={() =>
                      run(async () => {
                        await statusRedistribute(player.discordId, {
                          tactical: alloc.t,
                          fleet: alloc.f,
                          strategic: alloc.s,
                        });
                        setAllocs((prev) => {
                          const { [player.discordId]: _drop, ...rest } = prev;
                          void _drop;
                          return rest;
                        });
                      })
                    }
                  >
                    <IconCheck size={14} aria-hidden="true" />
                    <span>Confirm</span>
                  </button>
                </div>
              );
            })}
          <ExcessNotice status={status} nameOf={nameOf} />
        </div>
      )}

      {!winner && status.step === "COMPLETE" && (
        <div className={styles.body}>
          <p className={styles.note}>
            Cards are readied and units repaired. The speaker returns the Strategy Cards with{" "}
            <b>Next phase</b>
            {status.custodiansRemoved ? " — the agenda phase follows." : " — a new round follows."}
          </p>
          <ExcessNotice status={status} nameOf={nameOf} />
          <p className={styles.hint}>
            <IconChevronsRight size={13} aria-hidden="true" />
            <span>Use “Next phase” in the turn panel.</span>
          </p>
        </div>
      )}
    </aside>
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
      <b>Fleet pool exceeded</b>
      {entries.map(([playerId, systems]) => (
        <span key={playerId}>
          {nameOf(playerId)}: remove{" "}
          {Object.entries(systems)
            .map(([position, n]) => `${n} ship${n === 1 ? "" : "s"} in ${position}`)
            .join(", ")}
        </span>
      ))}
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
  onScore: (kind: "public" | "secret", objectiveId: string) => void;
  onFinish: () => void;
}) {
  const id = scorer.discordId;
  const publics = status.scoreablePublic[id] ?? [];
  const secrets = status.scoreableSecret[id] ?? [];
  const scoredPublic = status.scoredPublic.includes(id);
  const scoredSecret = status.scoredSecret.includes(id);

  return (
    <div className={styles.body}>
      <div className={styles.cardHead}>
        <CircularFactionIcon faction={scorer.faction} size={20} />
        <b>{getPlayerFactionDisplayName(scorer)}</b>
        <span className={styles.left}>{scorer.totalVps} VP</span>
      </div>
      <p className={styles.note}>
        Score up to one public and one secret objective whose requirements you meet now.
      </p>

      <div className={styles.group}>
        <small>Public objectives</small>
        {publics.length === 0 && <span className={styles.empty}>Nothing to score</span>}
        {publics.map((key) => {
          const objective = objectivesByKey.get(key);
          return (
            <button
              key={key}
              type="button"
              className={styles.score}
              disabled={busy || scoredPublic}
              onClick={() => onScore("public", key)}
            >
              <IconStar size={14} aria-hidden="true" />
              <span>{objective?.name ?? key}</span>
              <em>+{objective?.pointValue ?? 1}</em>
            </button>
          );
        })}
      </div>

      <div className={styles.group}>
        <small>Secret objectives</small>
        {secrets.length === 0 && <span className={styles.empty}>Nothing to score</span>}
        {secrets.map((key) => (
          <button
            key={key}
            type="button"
            className={styles.score}
            data-secret
            disabled={busy || scoredSecret}
            onClick={() => onScore("secret", key)}
          >
            <IconStar size={14} aria-hidden="true" />
            <span>{getSecretObjectiveData(key)?.name ?? key}</span>
            <em>+1</em>
          </button>
        ))}
      </div>

      <button type="button" className={styles.confirm} disabled={busy} onClick={onFinish}>
        <IconCheck size={14} aria-hidden="true" />
        <span>{scoredPublic || scoredSecret ? "Done scoring" : "Score nothing"}</span>
      </button>
    </div>
  );
}

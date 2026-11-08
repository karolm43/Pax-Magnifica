import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import {
  IconCheck,
  IconChevronsRight,
  IconCrown,
  IconEye,
  IconGavel,
  IconHandStop,
  IconScale,
  IconSparkles,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import type {
  AgendaPhaseData,
  AgendaVoter,
  PlayerData,
} from "@/entities/data/types";
import { getAgenda } from "@/entities/lookup/agendas";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
import {
  prettifyId,
  resolvePlanetName,
} from "@/domains/game-shell/components/GameEventPanel/eventFormatting";
import styles from "./AgendaOverlay.module.css";

/*
 * OKNO RADY GALAKTYCZNEJ - faza agendy (RULES.md 51), pełny ekran na tle assets/extra/agenda2.jpg.
 * [pasek: tytuł, numer agendy, talia/prawa, „pokaż planszę"]
 * [Senat (półkole miejsc w kolejności głosowania) | Podium: karta agendy i wyniki | Urna: akcja]
 * Panel niczego nie liczy - kolejność, głosy i wyniki przychodzą z backendu (core/agenda_phase).
 * Efekty agend NIE są jeszcze kodowane: wynik jest tylko zapisywany.
 */

const BACKDROP = 'url("/static/extra/agenda2.jpg"), url("/static/extra/starfield.png")';

type Look = { name: string; rgb: string; faction: string | null };

function rgbOf(player: PlayerData | undefined): string {
  const rgb = player?.color ? resolvePrimaryRgb(player.color) : undefined;
  return rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184";
}

function outcomeLabel(
  agenda: AgendaPhaseData,
  outcome: string,
  lookOf: (id: string) => Look,
): string {
  switch (agenda.kind) {
    case "for_against":
      return outcome === "for" ? "For" : "Against";
    case "player":
    case "player_techs":
      return lookOf(outcome).name;
    case "player_or_against":
      return outcome === "against" ? "Against" : lookOf(outcome).name;
    case "planet":
    case "planet_non_home":
    case "planet_non_home_not_mecatol":
      return resolvePlanetName(outcome);
    case "strategy_card": {
      const n = Number(outcome);
      return getStrategyCardByInitiative(n)?.name ?? `Strategy ${outcome}`;
    }
    case "law":
      return getAgenda(outcome)?.name ?? prettifyId(outcome);
    default:
      return prettifyId(outcome);
  }
}

function usePlayers() {
  const params = useParams<{ mapid: string }>();
  const { data: webData } = usePlayerData(params.mapid ?? DEFAULT_GAME_ID);
  const players = useMemo(() => webData?.playerData ?? [], [webData?.playerData]);
  const byId = useMemo(() => new Map(players.map((p) => [p.discordId, p])), [players]);
  const lookOf = (id: string): Look => {
    const p = byId.get(id);
    return {
      name: p ? getPlayerFactionDisplayName(p) : id,
      rgb: rgbOf(p),
      faction: p?.faction ?? null,
    };
  };
  return { byId, lookOf, round: webData?.gameRound };
}

/** Półkole miejsc Senatu: gracze wg kolejności głosowania, mówca na podium pośrodku. */
function Senate({
  agenda,
  lookOf,
}: {
  agenda: AgendaPhaseData;
  lookOf: (id: string) => Look;
}) {
  const order = agenda.voteOrder.filter((id) => id !== agenda.speakerId);
  const seats = order;
  const count = seats.length;
  const stateOf = (id: string) => {
    const vote = agenda.votes[id];
    if (vote) return "voted";
    if (agenda.abstained.includes(id)) return "abstained";
    if (agenda.blocked.includes(id)) return "blocked";
    if (agenda.step === "VOTE" && agenda.currentVoter === id) return "now";
    return "waiting";
  };
  const seatBody = (id: string) => {
    const look = lookOf(id);
    const st = stateOf(id);
    const vote = agenda.votes[id];
    const voter: AgendaVoter | undefined = agenda.voters[id];
    return (
      <div
        className={styles.seat}
        data-state={st}
        style={{ "--seat-rgb": look.rgb } as CSSProperties}
      >
        <span className={styles.seatIcon}>
          {look.faction ? <CircularFactionIcon faction={look.faction} size={34} /> : null}
        </span>
        <b className={styles.seatName}>{look.name}</b>
        <span className={styles.seatInfo}>
          {st === "voted" && vote
            ? `${vote.votes} → ${outcomeLabel(agenda, vote.outcome, lookOf)}`
            : st === "abstained"
              ? "Abstained"
              : st === "blocked"
                ? "Cannot vote"
                : st === "now"
                  ? "Speaking"
                  : `${voter?.available ?? 0} influence`}
        </span>
      </div>
    );
  };
  const speaker = agenda.speakerId;
  return (
    <section className={styles.panel} aria-label="Senate">
      <h3>
        <IconScale size={15} aria-hidden="true" /> Senate
      </h3>
      <div className={styles.hemicycle} style={{ "--n": count } as CSSProperties}>
        {seats.map((id, i) => {
          // Rozmieszczenie na łuku 180° -> 0° (lewa strona stołu = pierwszy głosujący).
          const t = count === 1 ? 0.5 : i / (count - 1);
          const angle = Math.PI * (1 - t);
          const x = 50 + 42 * Math.cos(angle);
          const y = 88 - 74 * Math.sin(angle);
          return (
            <div
              key={id}
              className={styles.seatPos}
              style={{ left: `${x}%`, top: `${y}%`, "--i": i } as CSSProperties}
            >
              <span className={styles.seatOrder}>{i + 1}</span>
              {seatBody(id)}
            </div>
          );
        })}
        {speaker ? (
          <div className={styles.podium}>
            <span className={styles.podiumTag}>
              <IconCrown size={13} aria-hidden="true" /> Speaker · votes last
            </span>
            {seatBody(speaker)}
          </div>
        ) : null}
      </div>
      <p className={styles.hint}>
        Voting starts with the player to the left of the speaker and goes clockwise. The speaker
        votes last.
      </p>
    </section>
  );
}

/** Karta agendy + wyniki (słupki głosów) + historia tej fazy. */
function Podium({
  agenda,
  lookOf,
  canPick,
  selected,
  onSelect,
  manual,
  setManual,
}: {
  agenda: AgendaPhaseData;
  lookOf: (id: string) => Look;
  canPick: boolean;
  selected: string | null;
  onSelect: (outcome: string) => void;
  manual: string;
  setManual: (v: string) => void;
}) {
  const card = agenda.card;
  const data = card ? getAgenda(card.id) : undefined;
  const name = card?.name ?? data?.name;
  const type = card?.type ?? data?.type;
  const target = card?.target ?? data?.target;
  const text1 = card?.text1 ?? data?.text1;
  const text2 = card?.text2 ?? data?.text2;
  const maxVotes = Math.max(1, ...Object.values(agenda.totals));
  const resolved = agenda.step === "RESOLVED" || agenda.step === "COMPLETE";
  const votersFor = (outcome: string) =>
    Object.entries(agenda.votes).filter(([, v]) => v.outcome === outcome);
  return (
    <section className={styles.panel} aria-label="Agenda">
      <h3>
        <IconGavel size={15} aria-hidden="true" /> Agenda {agenda.agendaNumber} of{" "}
        {agenda.totalAgendas}
      </h3>
      {card ? (
        <article className={styles.agendaCard} data-type={(type ?? "").toLowerCase()}>
          <header>
            <span className={styles.agendaType}>{type ?? "Agenda"}</span>
            <b>{name}</b>
            {target ? <small>{target}</small> : null}
          </header>
          {text1 ? <p>{text1}</p> : null}
          {text2 ? <p>{text2}</p> : null}
        </article>
      ) : (
        <div className={styles.emptyCard}>
          <IconGavel size={28} aria-hidden="true" />
          <span>
            {agenda.step === "REVEAL"
              ? "The speaker has not revealed the next agenda yet."
              : "No agenda on the podium."}
          </span>
        </div>
      )}

      {card && agenda.unresolvable ? (
        <p className={styles.warn}>
          This agenda has no valid outcome right now. The speaker discards it and reveals another.
        </p>
      ) : null}

      {card && !agenda.unresolvable ? (
        <ul className={styles.outcomes} aria-label="Outcomes">
          {agenda.outcomes.map((outcome) => {
            const total = agenda.totals[outcome] ?? 0;
            const isWinner = resolved && agenda.resolvedOutcome === outcome;
            const isTied = agenda.step === "TIEBREAK" && agenda.tied.includes(outcome);
            return (
              <li
                key={outcome}
                className={styles.outcome}
                data-winner={isWinner || undefined}
                data-tied={isTied || undefined}
                data-selected={selected === outcome || undefined}
              >
                <button
                  type="button"
                  className={styles.outcomeBtn}
                  disabled={!canPick}
                  onClick={() => onSelect(outcome)}
                  aria-pressed={selected === outcome}
                >
                  <span className={styles.outcomeName}>
                    {agenda.kind === "player" || agenda.kind === "player_or_against" ? (
                      (() => {
                        const l = lookOf(outcome);
                        return l.faction ? (
                          <CircularFactionIcon faction={l.faction} size={20} />
                        ) : null;
                      })()
                    ) : null}
                    {outcomeLabel(agenda, outcome, lookOf)}
                    {isWinner ? (
                      <IconCheck size={15} aria-label="Winning outcome" />
                    ) : null}
                  </span>
                  <span className={styles.outcomeVotes}>{total}</span>
                </button>
                <div className={styles.bar} aria-hidden="true">
                  <span style={{ width: `${(total / maxVotes) * 100}%` }} />
                </div>
                {votersFor(outcome).length > 0 ? (
                  <div className={styles.chips}>
                    {votersFor(outcome).map(([pid, v]) => {
                      const l = lookOf(pid);
                      return (
                        <span
                          key={pid}
                          className={styles.chip}
                          style={{ "--seat-rgb": l.rgb } as CSSProperties}
                          title={`${l.name}: ${v.votes}`}
                        >
                          {l.faction ? <CircularFactionIcon faction={l.faction} size={16} /> : null}
                          {v.votes}
                        </span>
                      );
                    })}
                  </div>
                ) : null}
              </li>
            );
          })}
          {agenda.kind === "manual" ? (
            <li className={styles.outcome} data-selected={selected === manual || undefined}>
              <input
                className={styles.manualInput}
                value={manual}
                maxLength={80}
                disabled={!canPick}
                placeholder="Describe the outcome (no model for this agenda yet)"
                onChange={(e) => {
                  setManual(e.target.value);
                  onSelect(e.target.value);
                }}
              />
            </li>
          ) : null}
        </ul>
      ) : null}

      {agenda.history.length > 0 ? (
        <div className={styles.history}>
          <h4>Resolved this phase</h4>
          {agenda.history.map((h, i) => (
            <div key={`${h.agenda}-${i}`} className={styles.historyRow}>
              <b>{getAgenda(h.agenda)?.name ?? prettifyId(h.agenda)}</b>
              <span>
                {h.discarded
                  ? "discarded"
                  : `${outcomeLabel(
                      { ...agenda, kind: h.kind ?? agenda.kind },
                      h.outcome ?? "",
                      lookOf,
                    )}${h.bySpeaker ? " (speaker)" : ""}${h.stays ? " · law in play" : ""}`}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

/** Urna: akcja właściwa dla kroku (ujawnienie, głos, remis, dalej, koniec). */
function Ballot({
  agenda,
  lookOf,
  selected,
  busy,
  canAdvance,
  onSelect,
  run,
}: {
  agenda: AgendaPhaseData;
  lookOf: (id: string) => Look;
  selected: string | null;
  busy: boolean;
  canAdvance: boolean;
  onSelect: (outcome: string | null) => void;
  run: (fn: () => Promise<void>) => void;
}) {
  const api = useBoardEditor();
  const [picked, setPicked] = useState<string[]>([]);
  const speaker = agenda.speakerId ?? "";
  const voterId = agenda.currentVoter;
  const voter = voterId ? agenda.voters[voterId] : undefined;
  const planets = voter?.planets ?? [];
  const votes =
    planets.filter((p) => picked.includes(p.planet)).reduce((n, p) => n + p.influence, 0) +
    (voter?.extra ?? 0);

  // Nowy głosujący = czysta urna.
  useEffect(() => {
    setPicked([]);
  }, [voterId, agenda.agendaNumber, agenda.step]);

  const speakerLook = lookOf(speaker);
  const head = (
    <div className={styles.ballotHead} style={{ "--seat-rgb": speakerLook.rgb } as CSSProperties}>
      <IconCrown size={15} aria-hidden="true" /> Speaker: <b>{speakerLook.name}</b>
    </div>
  );

  if (agenda.step === "REVEAL") {
    return (
      <>
        {head}
        <p className={styles.note}>
          The speaker draws the top card of the agenda deck and reads it aloud, including every
          possible outcome. <b>{agenda.deckSize}</b> cards left
          {agenda.deckSeeded ? "" : " (deck not shuffled yet)"}, {agenda.discardSize} discarded,{" "}
          {Object.keys(agenda.lawsInPlay).length} laws in play.
        </p>
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={busy}
          onClick={() => run(() => api.agendaReveal(speaker))}
        >
          <IconSparkles size={16} aria-hidden="true" /> Reveal agenda {agenda.agendaNumber}
        </button>
      </>
    );
  }

  if (agenda.step === "VOTE" && agenda.unresolvable) {
    return (
      <>
        {head}
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={busy}
          onClick={() => run(() => api.agendaDiscard(speaker))}
        >
          Discard and reveal another
        </button>
      </>
    );
  }

  if (agenda.step === "VOTE" && voterId && voter) {
    const look = lookOf(voterId);
    const ready = planets.filter((p) => !p.exhausted);
    const canCast = selected != null && selected !== "" && votes > 0 && !busy;
    return (
      <>
        <div className={styles.ballotHead} style={{ "--seat-rgb": look.rgb } as CSSProperties}>
          {look.faction ? <CircularFactionIcon faction={look.faction} size={26} /> : null}
          <b>{look.name}</b> votes
        </div>
        <p className={styles.note}>
          Exhaust planets to cast votes equal to their influence. All votes go to <b>one</b>{" "}
          outcome. Trade goods cannot buy votes. Pick an outcome on the podium.
        </p>
        <div className={styles.votesBig}>
          <b>{votes}</b>
          <span>
            votes of {voter.available + voter.extra} available
            {selected ? (
              <>
                {" "}
                for <em>{outcomeLabel(agenda, selected, lookOf)}</em>
              </>
            ) : null}
          </span>
        </div>
        <div className={styles.planets}>
          {planets.length === 0 ? (
            <span className={styles.empty}>No planets with influence.</span>
          ) : null}
          {planets.map((p) => (
            <div className={styles.planetSlot} key={p.planet}>
              <PlanetCard
                planetId={p.planet}
                isExhausted={p.exhausted}
                picked={picked.includes(p.planet)}
                onPick={
                  p.exhausted || busy
                    ? undefined
                    : () =>
                        setPicked((cur) =>
                          cur.includes(p.planet)
                            ? cur.filter((x) => x !== p.planet)
                            : [...cur, p.planet],
                        )
                }
              />
            </div>
          ))}
        </div>
        <div className={styles.btnRow}>
          <button
            type="button"
            className={styles.ghostBtn}
            disabled={ready.length === 0 || busy}
            onClick={() => setPicked(ready.map((p) => p.planet))}
          >
            All ready
          </button>
          <button
            type="button"
            className={styles.ghostBtn}
            disabled={picked.length === 0 || busy}
            onClick={() => setPicked([])}
          >
            Clear
          </button>
        </div>
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={!canCast}
          onClick={() =>
            run(async () => {
              await api.agendaVote(voterId, selected ?? "", picked);
              onSelect(null);
            })
          }
        >
          <IconGavel size={16} aria-hidden="true" /> Cast {votes} {votes === 1 ? "vote" : "votes"}
        </button>
        <button
          type="button"
          className={styles.ghostBtn}
          disabled={busy}
          onClick={() =>
            run(async () => {
              await api.agendaAbstain(voterId);
              onSelect(null);
            })
          }
        >
          <IconHandStop size={16} aria-hidden="true" /> Abstain
        </button>
      </>
    );
  }

  if (agenda.step === "TIEBREAK") {
    return (
      <>
        {head}
        <p className={styles.note}>
          {Object.values(agenda.totals).some((n) => n > 0)
            ? "Tie for the most votes."
            : "No votes were cast."}{" "}
          The speaker decides which outcome resolves. This is not a vote.
        </p>
        <div className={styles.tieList}>
          {(agenda.tied.length > 0 ? agenda.tied : agenda.outcomes).map((o) => (
            <button
              key={o}
              type="button"
              className={styles.ghostBtn}
              disabled={busy}
              onClick={() => run(() => api.agendaDecide(speaker, o))}
            >
              {outcomeLabel(agenda, o, lookOf)}
            </button>
          ))}
        </div>
        {agenda.kind === "manual" ? (
          <>
            <p className={styles.hint}>
              Describe (or pick) the outcome on the podium, then confirm.
            </p>
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={busy || !selected}
              onClick={() => run(() => api.agendaDecide(speaker, selected ?? ""))}
            >
              Resolve as chosen
            </button>
          </>
        ) : null}
      </>
    );
  }

  if (agenda.step === "RESOLVED") {
    const last = agenda.agendaNumber >= agenda.totalAgendas;
    return (
      <>
        {head}
        <div className={styles.result}>
          <span>Outcome</span>
          <b>{outcomeLabel(agenda, agenda.resolvedOutcome ?? "", lookOf)}</b>
          {agenda.decidedBySpeaker ? <small>chosen by the speaker</small> : null}
        </div>
        <p className={styles.note}>
          Effects of the agenda are not automated yet - apply them by hand (God-Mode) if needed.
          Laws with a For or Elect outcome stay in play; everything else is discarded.
        </p>
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={busy}
          onClick={() => run(() => api.agendaContinue(speaker))}
        >
          {last ? "Ready planets and finish" : "Next agenda"}
          <IconChevronsRight size={16} aria-hidden="true" />
        </button>
      </>
    );
  }

  return (
    <>
      {head}
      <p className={styles.note}>
        Both agendas are resolved and every planet has been readied. The speaker ends the phase and
        a new round begins with the strategy phase.
      </p>
      <button
        type="button"
        className={styles.primaryBtn}
        disabled={busy || !canAdvance}
        onClick={() => run(() => api.nextPhase())}
      >
        End agenda phase <IconChevronsRight size={16} aria-hidden="true" />
      </button>
    </>
  );
}

function CouncilWindow({ agenda, canAdvance }: { agenda: AgendaPhaseData; canAdvance: boolean }) {
  const { lookOf, round } = usePlayers();
  const setHidden = useAppStore((s) => s.setAgendaHidden);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [manual, setManual] = useState("");
  const voterLook = agenda.currentVoter ? lookOf(agenda.currentVoter) : null;

  // Nowa agenda / nowy krok zeruje wybór wyniku.
  useEffect(() => {
    setSelected(null);
    setManual("");
  }, [agenda.agendaNumber, agenda.card?.id, agenda.step]);

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn()
      .catch(() => undefined)
      .finally(() => setBusy(false));
  };
  const canPick =
    !busy &&
    ((agenda.step === "VOTE" && agenda.currentVoter != null && !agenda.unresolvable) ||
      (agenda.step === "TIEBREAK" && agenda.kind === "manual"));

  return createPortal(
    <div
      className={styles.overlay}
      style={{ "--att-rgb": voterLook?.rgb ?? "214 178 94" } as CSSProperties}
      role="dialog"
      aria-label="Galactic Council - agenda phase"
    >
      <div className={styles.backdrop} style={{ backgroundImage: BACKDROP }} aria-hidden="true" />
      <header className={styles.topBar}>
        <div className={styles.title}>
          <IconGavel size={20} aria-hidden="true" />
          Galactic Council
          <small>
            Round {round ?? "?"} · Agenda {agenda.agendaNumber} of {agenda.totalAgendas}
          </small>
        </div>
        <div className={styles.topStats}>
          <span className={styles.stat}>
            Deck <b>{agenda.deckSize}</b>
          </span>
          <span className={styles.stat}>
            Discard <b>{agenda.discardSize}</b>
          </span>
          <span className={styles.stat}>
            Laws in play <b>{Object.keys(agenda.lawsInPlay).length}</b>
          </span>
        </div>
        <button type="button" className={styles.ghostBtn} onClick={() => setHidden(true)}>
          <IconEye size={15} aria-hidden="true" /> Show board
        </button>
      </header>
      <div className={styles.grid}>
        <Senate agenda={agenda} lookOf={lookOf} />
        <Podium
          agenda={agenda}
          lookOf={lookOf}
          canPick={canPick}
          selected={selected}
          onSelect={setSelected}
          manual={manual}
          setManual={setManual}
        />
        <section className={styles.panel} aria-label="Ballot">
          <h3>
            <IconScale size={15} aria-hidden="true" /> Ballot
          </h3>
          <Ballot
            agenda={agenda}
            lookOf={lookOf}
            selected={selected}
            busy={busy}
            canAdvance={canAdvance}
            onSelect={setSelected}
            run={run}
          />
        </section>
      </div>
    </div>,
    document.body,
  );
}

/** Brama: okno Rady otwiera się samo w fazie agendy; „Show board" zwija je do przycisku. */
export function AgendaOverlay() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const hidden = useAppStore((s) => s.agendaHidden);
  const setHidden = useAppStore((s) => s.setAgendaHidden);
  const agenda = gameState?.agendaPhase ?? null;
  const ended = gameState?.winnerId != null;

  // Poza fazą agendy okno wraca do stanu otwartego - następna agenda otwiera się sama.
  useEffect(() => {
    if (!agenda && hidden) setHidden(false);
  }, [agenda, hidden, setHidden]);

  if (!agenda || ended) return null;
  if (hidden) {
    return createPortal(
      <button type="button" className={styles.returnPill} onClick={() => setHidden(false)}>
        <IconGavel size={16} aria-hidden="true" />
        Open Galactic Council
      </button>,
      document.body,
    );
  }
  return (
    <CouncilWindow agenda={agenda} canAdvance={gameState?.canAdvancePhase === true} />
  );
}

export default AgendaOverlay;

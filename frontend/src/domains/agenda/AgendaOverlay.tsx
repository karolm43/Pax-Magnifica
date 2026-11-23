import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import {
  IconArrowRight,
  IconArrowsExchange,
  IconThumbDown,
  IconThumbUp,
  IconCheck,
  IconChevronsRight,
  IconCrown,
  IconEye,
  IconGavel,
  IconHandStop,
  IconMapPin,
  IconScale,
  IconSparkles,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import { useActivityFeed, useBoardEditor } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { humanHandOwners } from "@/domains/offers/handReactions";
import { AgendaPassButtons } from "./AgendaPassButtons";
import { AgendaMapPickBar, isPlanetAgenda, useAgendaMapPick } from "./AgendaMapPick";
import { TransactionModal } from "@/domains/game-shell/components/TurnControls/TransactionModal";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { Switch } from "@/ds";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import type {
  AgendaPhaseData,
  AgendaPrediction,
  AgendaVoter,
  PlayerData,
} from "@/entities/data/types";
import { getAgenda } from "@/entities/lookup/agendas";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { useFactionImageUrl } from "@/hooks/useFactionImages";
import { FanSourceBadge } from "@/shared/ui/FanSourceBadge";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
import {
  HintBody,
  hintFor,
  Named,
  type Hint,
} from "@/domains/game-shell/components/ActivityPanel/Named";
import { Tooltip } from "@/ds";
import { getPlanetData } from "@/entities/lookup/planets";
import { clearMapMarks, mapRefKeys, showOnMap } from "@/domains/search/mapPeek";
import { getActionCard } from "@/entities/lookup/actionCards";
import {
  prettifyId,
  resolvePlanetName,
} from "@/domains/game-shell/components/GameEventPanel/eventFormatting";
import {
  ComponentInfoButton,
  type ComponentKind,
} from "@/domains/cards/components/ComponentInfo";
import styles from "./AgendaOverlay.module.css";
import { PHASE_WINDOW } from "@/hooks/useDecisionZone";

/*
 * OKNO RADY GALAKTYCZNEJ - faza agendy (RULES.md 51), pełny ekran na tle assets/extra/agenda2.jpg.
 * [pasek: tytuł, numer agendy, talia/prawa, „pokaż planszę"]
 * [Senat (półkole miejsc w kolejności głosowania) | Podium: karta agendy i wyniki | Urna: akcja]
 * Panel niczego nie liczy - kolejność, głosy i wyniki przychodzą z backendu (core/agenda_phase).
 * Efekty agend liczy silnik (RULES.md 51.6); decyzje graczy z efektów wyskakują jako oferty.
 * Riders są jawne: przy każdym wyniku widać, kto i jaką kartą na niego postawił.
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

const OUTCOME_PALETTE = [
  "#60a5fa",
  "#f59e0b",
  "#c084fc",
  "#2dd4bf",
  "#f472b6",
  "#a3e635",
  "#fb923c",
  "#94a3b8",
];

/** Kolor wyniku (For zielony, Against czerwony, reszta z palety wg kolejności). */
function outcomeColor(agenda: AgendaPhaseData, outcome: string): string {
  if (outcome === "for") return "#4ade80";
  if (outcome === "against") return "#f87171";
  const rest = agenda.outcomes.filter((o) => o !== "for" && o !== "against");
  const idx = Math.max(0, rest.indexOf(outcome));
  return OUTCOME_PALETTE[idx % OUTCOME_PALETTE.length] ?? "#94a3b8";
}

const HEMI = { w: 600, h: 310, cx: 300, cy: 300, rIn: 105, rOut: 285 };
const MAX_SEATS_PER_PLAYER = 40;

/** Miejsca półkola (jak wykres parlamentu): rzędy łuków, posortowane od lewej do prawej. */
function hemicycleSeats(total: number): { x: number; y: number; r: number }[] {
  if (total <= 0) return [];
  const rows = Math.max(1, Math.min(8, total, Math.round(Math.sqrt(total / 2.2))));
  const radii = Array.from({ length: rows }, (_, i) =>
    rows === 1 ? (HEMI.rIn + HEMI.rOut) / 2 : HEMI.rIn + (i * (HEMI.rOut - HEMI.rIn)) / (rows - 1),
  );
  const sumR = radii.reduce((a, b) => a + b, 0);
  const counts = radii.map((r) => Math.max(1, Math.round((total * r) / sumR)));
  let diff = total - counts.reduce((a, b) => a + b, 0);
  while (diff !== 0) {
    const step = diff > 0 ? 1 : -1;
    let best = -1;
    counts.forEach((c, i) => {
      if (step < 0 && c <= 1) return;
      if (best < 0 || (counts[best] ?? 0) < c) best = i;
    });
    if (best < 0) break;
    counts[best] = (counts[best] ?? 0) + step;
    diff -= step;
  }
  const rowGap = rows > 1 ? (HEMI.rOut - HEMI.rIn) / (rows - 1) : 40;
  const arcGap = Math.min(...radii.map((r, i) => (Math.PI * r) / (counts[i] ?? 1)));
  const dot = Math.min(17, Math.min(rowGap, arcGap) * 0.42);
  const seats: { x: number; y: number; r: number; a: number; rad: number }[] = [];
  radii.forEach((rad, i) => {
    const n = counts[i] ?? 1;
    for (let j = 0; j < n; j += 1) {
      const a = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * j) / (n - 1);
      seats.push({
        x: HEMI.cx + rad * Math.cos(a),
        y: HEMI.cy - rad * Math.sin(a),
        r: dot,
        a,
        rad,
      });
    }
  });
  seats.sort((p, q) => q.a - p.a || p.rad - q.rad);
  return seats.map(({ x, y, r }) => ({ x, y, r }));
}

/** Jedno miejsce = jeden głos: ikona frakcji w kółku; obwódka w kolorze wybranego wyniku. */
function FactionSeat({
  x,
  y,
  r,
  faction,
  state,
  rgb,
  ring,
  delay,
  label,
}: {
  x: number;
  y: number;
  r: number;
  faction: string | null;
  state: string;
  rgb: string;
  ring?: string;
  delay: number;
  label: string;
}) {
  const url = useFactionImageUrl(faction ?? "", null, null);
  const cast = state === "voted";
  return (
    <g
      className={styles.seat}
      data-state={state}
      style={
        {
          "--seat-rgb": rgb,
          ...(ring ? { "--ring": ring } : null),
          animationDelay: `${delay}ms`,
        } as CSSProperties
      }
    >
      <title>{label}</title>
      <circle cx={x} cy={y} r={r} className={styles.seatDisc} />
      {faction ? (
        <image
          href={url}
          x={x - r * 0.86}
          y={y - r * 0.86}
          width={r * 1.72}
          height={r * 1.72}
          clipPath="url(#seatClip)"
          className={styles.seatIcon}
          preserveAspectRatio="xMidYMid slice"
        />
      ) : null}
      <circle cx={x} cy={y} r={r} className={styles.seatRing} data-cast={cast || undefined} />
    </g>
  );
}

/** SENAT: wykres parlamentu. Jedno miejsce = jeden głos, bloki w kolorach graczy. */
function Senate({
  agenda,
  lookOf,
}: {
  agenda: AgendaPhaseData;
  lookOf: (id: string) => Look;
}) {
  const speaker = agenda.speakerId;
  // Kolejka z silnika bez zmian: Hack Election Ω sadza zagrywającego PO mówcy.
  const order =
    agenda.voteOrder.length > 0
      ? agenda.voteOrder
      : speaker
        ? [speaker]
        : [];
  const stateOf = (id: string) => {
    if (agenda.votes[id]) return "voted";
    if (agenda.abstained.includes(id)) return "abstained";
    if (agenda.blocked.includes(id)) return "blocked";
    if (agenda.step === "VOTE" && agenda.currentVoter === id) return "now";
    return "waiting";
  };
  // Głosy „możliwe": Predictive Intelligence (+3, decyzja gracza) dopóki gracz nie zagłosował.
  // Pokazujemy je od razu jako przygaszone miejsca, żeby nie „wyskakiwały" dopiero po głosie.
  const possibleOf = (id: string): number => {
    if (agenda.votes[id] || agenda.abstained.includes(id) || agenda.blocked.includes(id)) return 0;
    const predictive = agenda.voters[id]?.predictive;
    return predictive?.ready ? predictive.votes : 0;
  };
  const seatsOf = (id: string): { real: number; possible: number } => {
    const vote = agenda.votes[id];
    const voter: AgendaVoter | undefined = agenda.voters[id];
    const n = vote ? vote.votes : (voter?.available ?? 0) + (voter?.extra ?? 0);
    const real = Math.min(MAX_SEATS_PER_PLAYER, Math.max(0, n));
    const possible = Math.min(MAX_SEATS_PER_PLAYER - real, possibleOf(id));
    return { real, possible };
  };
  const counts = order.map(seatsOf);
  const total = counts.reduce((a, c) => a + c.real + c.possible, 0);
  const totalReal = counts.reduce((a, c) => a + c.real, 0);
  const totalPossible = total - totalReal;
  const seats = hemicycleSeats(total);
  // Przydział miejsc po kolei: pierwszy głosujący po lewej, mówca na końcu po prawej;
  // miejsca możliwe (PI) na końcu bloku gracza.
  const owner: { id: string; possible: boolean }[] = [];
  order.forEach((id, i) => {
    const c = counts[i] ?? { real: 0, possible: 0 };
    for (let k = 0; k < c.real; k += 1) owner.push({ id, possible: false });
    for (let k = 0; k < c.possible; k += 1) owner.push({ id, possible: true });
  });
  const totalCast = Object.values(agenda.totals).reduce((a, b) => a + b, 0);
  const showOutcomes = agenda.card != null && !agenda.unresolvable;

  return (
    <section className={styles.panel} aria-label="Senate">
      <h3>
        <IconScale size={15} aria-hidden="true" /> Senate
      </h3>
      <div className={styles.chamber}>
        <svg
          className={styles.hemi}
          viewBox={`0 0 ${HEMI.w} ${HEMI.h}`}
          role="img"
          aria-label="Senate seating: one seat per vote"
        >
          <defs>
            <clipPath id="seatClip" clipPathUnits="objectBoundingBox">
              <circle cx="0.5" cy="0.5" r="0.5" />
            </clipPath>
          </defs>
          {[HEMI.rIn - 22, HEMI.rOut + 22].map((r) => (
            <path
              key={r}
              className={styles.hemiRim}
              d={`M ${HEMI.cx - r} ${HEMI.cy} A ${r} ${r} 0 0 1 ${HEMI.cx + r} ${HEMI.cy}`}
            />
          ))}
          {seats.map((s, i) => {
            const id = owner[i]?.id ?? "";
            const possible = owner[i]?.possible ?? false;
            const look = lookOf(id);
            const st = possible ? "possible" : stateOf(id);
            const vote = agenda.votes[id];
            const cast = st === "voted" && vote != null;
            const ring = cast ? outcomeColor(agenda, vote.outcome) : undefined;
            return (
              <FactionSeat
                key={i}
                x={s.x}
                y={s.y}
                r={s.r}
                faction={look.faction}
                state={st}
                rgb={look.rgb}
                ring={ring}
                delay={Math.min(i, 120) * 8}
                label={`${look.name}${
                  cast
                    ? `: ${vote.votes} for ${outcomeLabel(agenda, vote.outcome, lookOf)}`
                    : st === "possible"
                      ? ": possible vote (Predictive Intelligence, not counted yet)"
                      : st === "abstained"
                      ? ": abstains"
                      : st === "blocked"
                        ? ": cannot vote"
                        : ": votes not cast yet"
                }`}
              />
            );
          })}
        </svg>
        <div className={styles.chamberCore}>
          <b>{totalCast}</b>
          <span>votes cast</span>
          {totalReal > 0 ? (
            <small>
              {totalReal - totalCast > 0 ? `${totalReal - totalCast} still to spend` : "all spent"}
            </small>
          ) : null}
          {totalPossible > 0 ? <small>+{totalPossible} possible</small> : null}
        </div>
      </div>

      {showOutcomes ? (
        <ul className={styles.legend} aria-label="Outcome colours">
          {agenda.outcomes.map((o) => (
            <li key={o} style={{ "--ring": outcomeColor(agenda, o) } as CSSProperties}>
              <i aria-hidden="true" />
              <span>{outcomeLabel(agenda, o, lookOf)}</span>
              <b>{agenda.totals[o] ?? 0}</b>
            </li>
          ))}
        </ul>
      ) : null}

      <ol className={styles.roster} aria-label="Voting order">
        {order.map((id, i) => {
          const look = lookOf(id);
          const st = stateOf(id);
          const vote = agenda.votes[id];
          const voter: AgendaVoter | undefined = agenda.voters[id];
          const isSpeaker = id === speaker;
          return (
            <li
              key={id}
              className={styles.rosterRow}
              data-state={st}
              style={{ "--seat-rgb": look.rgb } as CSSProperties}
            >
              <span className={styles.rosterNo}>
                {isSpeaker ? <IconCrown size={13} aria-label="Speaker" /> : i + 1}
              </span>
              {look.faction ? <CircularFactionIcon faction={look.faction} size={26} /> : <span />}
              <span className={styles.rosterName}>
                <b>{look.name}</b>
                <small>
                  {isSpeaker ? "Speaker · votes last" : `Seat ${i + 1}`}
                  {st === "now" ? " · voting now" : ""}
                </small>
              </span>
              <span className={styles.rosterVotes}>
                {st === "voted" && vote ? (
                  <span
                    className={styles.pick}
                    style={{ "--ring": outcomeColor(agenda, vote.outcome) } as CSSProperties}
                  >
                    {vote.outcome === "for" ? (
                      <IconThumbUp size={16} aria-hidden="true" />
                    ) : vote.outcome === "against" ? (
                      <IconThumbDown size={16} aria-hidden="true" />
                    ) : (
                      <IconArrowRight size={16} aria-hidden="true" />
                    )}
                    {outcomeLabel(agenda, vote.outcome, lookOf)}
                    <b>{vote.votes}</b>
                  </span>
                ) : st === "abstained" ? (
                  <em>abstains</em>
                ) : st === "blocked" ? (
                  <em>cannot vote</em>
                ) : (
                  <em>
                    <b>{(voter?.available ?? 0) + (voter?.extra ?? 0)}</b> to spend
                    {possibleOf(id) > 0 ? ` (+${possibleOf(id)} possible)` : ""}
                  </em>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/** Karta agendy + wyniki (słupki głosów) + historia tej fazy. */
/** Rodzaj komponentu za wynikiem (planeta, prawo, cel, karta strategii) albo ``null``. */
function outcomeKind(agenda: AgendaPhaseData): ComponentKind | null {
  switch (agenda.kind) {
    case "planet":
    case "planet_non_home":
    case "planet_non_home_not_mecatol":
      return "planet";
    case "law":
      return "agenda";
    case "secret_objective":
    case "public_objective":
      return "objective";
    case "strategy_card":
      return "strategy";
    default:
      return null;
  }
}

/** Opis komponentu za wynikiem albo ``null``. */
function outcomeHint(
  agenda: AgendaPhaseData,
  outcome: string,
  idMap?: Record<number, string>,
): Hint | null {
  const kind = outcomeKind(agenda);
  return kind ? hintFor(kind, outcome, { idMap }) : null;
}

/**
 * Linijka informacji pod wynikiem: CO się wybiera (planeta: wartości, typ i kto ją trzyma +
 * podgląd na mapie; gracz: punkty i głosy; prawo / cel / karta strategii: tekst zasady).
 */
function OutcomeInfo({
  agenda,
  outcome,
  lookOf,
}: {
  agenda: AgendaPhaseData;
  outcome: string;
  lookOf: (id: string) => Look;
}) {
  const { byId } = usePlayers();
  const idMap = useGameData()?.strategyCardIdMap;
  const isPlayer =
    agenda.kind === "player" ||
    agenda.kind === "player_techs" ||
    (agenda.kind === "player_or_against" && outcome !== "against");
  if (isPlayer) {
    const player = byId.get(outcome);
    if (!player) return null;
    return (
      <span className={styles.outcomeInfo}>
        {player.totalVps} VP
        {player.isSpeaker ? " · speaker" : ""}
      </span>
    );
  }
  if (agenda.kind.startsWith("planet") && agenda.kind !== "planet_trait") {
    const planet = getPlanetData(outcome);
    const owner = [...byId.values()].find((p) => p.planets.includes(outcome));
    const keys = mapRefKeys(outcome, { planet: outcome });
    const traits = (planet?.planetTypes ?? (planet?.planetType ? [planet.planetType] : []))
      .map((t) => prettifyId(t.toLowerCase()))
      .join(", ");
    return (
      <span className={styles.outcomeInfo}>
        {planet ? `${planet.resources} res · ${planet.influence} inf` : ""}
        {traits ? ` · ${traits}` : ""}
        {planet?.techSpecialties?.length ? ` · ${planet.techSpecialties.join(", ")} specialty` : ""}
        {" · "}
        {owner ? (
          <>
            held by{" "}
            {owner.faction ? <CircularFactionIcon faction={owner.faction} size={14} /> : null}{" "}
            {lookOf(owner.discordId).name}
          </>
        ) : (
          "uncontrolled"
        )}
        <ComponentInfoButton
          componentRef={{ kind: "planet", id: outcome }}
          name={resolvePlanetName(outcome)}
        />
        <button
          type="button"
          className={styles.outcomeLocate}
          aria-label={`Show ${resolvePlanetName(outcome)} on the map`}
          title="Hover to see it on the map, click to centre the map on it"
          onMouseEnter={() => showOnMap(keys, { peek: true })}
          onMouseLeave={clearMapMarks}
          onFocus={() => showOnMap(keys, { peek: true })}
          onBlur={clearMapMarks}
          onClick={() => showOnMap(keys, { peek: true, jump: true })}
        >
          <IconEye size={13} aria-hidden="true" />
        </button>
      </span>
    );
  }
  const hint = outcomeHint(agenda, outcome, idMap);
  const kind = outcomeKind(agenda);
  if (!hint || !kind) return null;
  return (
    <span className={styles.outcomeInfoRow}>
      <Tooltip
        label={<HintBody hint={hint} />}
        multiline
        withArrow
        openDelay={200}
        maw={340}
        events={{ hover: true, focus: true, touch: true }}
      >
        {/* Cały tekst (np. primary i secondary karty strategii), nie tylko pierwszy akapit. */}
        <span className={styles.outcomeInfo} data-text="" tabIndex={0}>
          {hint.meta ? <em>{hint.meta}</em> : null} {hint.lines.join(" ")}
        </span>
      </Tooltip>
      <ComponentInfoButton componentRef={{ kind, id: outcome }} name={hint.name || outcome} />
    </span>
  );
}

function Podium({
  agenda,
  lookOf,
  canPick,
  selected,
  onSelect,
  manual,
  setManual,
  covertCard,
}: {
  agenda: AgendaPhaseData;
  lookOf: (id: string) => Look;
  canPick: boolean;
  selected: string | null;
  onSelect: (outcome: string) => void;
  manual: string;
  setManual: (v: string) => void;
  covertCard: AgendaPhaseData["card"];
}) {
  const card = agenda.card;
  const predictions = agenda.predictions ?? [];
  const ridersOn = (outcome: string) => predictions.filter((r) => r.outcome === outcome);
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
  const planetPick = isPlanetAgenda(agenda.kind);
  const startMapPick = useAgendaMapPick((s) => s.start);
  return (
    <section className={styles.panel} aria-label="Agenda">
      <h3>
        <IconGavel size={15} aria-hidden="true" /> Agenda
      </h3>
      {card ? (
        <article className={styles.agendaCard} data-type={(type ?? "").toLowerCase()}>
          <header>
            <span className={styles.agendaType}>{type ?? "Agenda"}</span>
            <b>
              {name} <FanSourceBadge source={data?.source} />
            </b>
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

      {card && agenda.covert ? (
        <div className={styles.covertBox}>
          <p className={styles.note}>
            Covert Legislation: you vote on the outcomes of a <b>hidden agenda</b> drawn by the
            speaker. It is revealed when it resolves.
          </p>
          {covertCard ? (
            <article className={styles.agendaCard} data-type={(covertCard.type ?? "").toLowerCase()}>
              <header>
                <span className={styles.agendaType}>Hidden · only you see it</span>
                <b>{covertCard.name}</b>
                {covertCard.target ? <small>{covertCard.target}</small> : null}
              </header>
              {covertCard.text1 ? <p>{covertCard.text1}</p> : null}
              {covertCard.text2 ? <p>{covertCard.text2}</p> : null}
            </article>
          ) : null}
        </div>
      ) : null}

      {agenda.revoteLaw ? (
        <p className={styles.note}>
          Miscount Disclosed: players vote again on{" "}
          <b>{getAgenda(agenda.revoteLaw)?.name ?? prettifyId(agenda.revoteLaw)}</b> as if it were
          just revealed.
        </p>
      ) : null}

      {card && agenda.unresolvable ? (
        <p className={styles.warn}>
          This agenda has no valid outcome right now. The speaker discards it and reveals another.
        </p>
      ) : null}

      {card && !agenda.unresolvable && planetPick && canPick ? (
        // „Elect Planet” (U6): planetę wybiera się WYŁĄCZNIE na mapie - lista niżej to podgląd głosów.
        <button type="button" className={`${styles.primaryBtn} ${styles.mapPickBtn}`} onClick={startMapPick}>
          <IconMapPin size={16} aria-hidden="true" />
          {selected ? "Choose another planet on the map" : "Choose a planet on the map"}
        </button>
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
                  // Planety: bez klikania z listy (wybór na mapie) - wiersz to podgląd głosów.
                  data-preview={planetPick || undefined}
                  disabled={
                    planetPick ||
                    !canPick ||
                    (agenda.step === "TIEBREAK" && agenda.tied.length > 0 && !isTied)
                  }
                  onClick={() => onSelect(outcome)}
                  aria-pressed={selected === outcome}
                >
                  <span className={styles.outcomeName}>
                    <span
                      className={styles.swatch}
                      style={{ "--ring": outcomeColor(agenda, outcome) } as CSSProperties}
                      aria-hidden="true"
                    />
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
                <OutcomeInfo agenda={agenda} outcome={outcome} lookOf={lookOf} />
                <div className={styles.bar} aria-hidden="true">
                  <span style={{ width: `${(total / maxVotes) * 100}%` }} />
                </div>
                {ridersOn(outcome).length > 0 ? (
                  <div className={styles.chips} aria-label="Riders on this outcome">
                    {ridersOn(outcome).map((r, i) => (
                      <RiderChip key={`${r.card}-${i}`} rider={r} look={lookOf(r.playerId)} />
                    ))}
                  </div>
                ) : null}
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

      {predictions.length > 0 ? (
        <div className={styles.history} aria-label="Riders">
          <h4>Riders</h4>
          {predictions.map((r, i) => {
            const l = lookOf(r.playerId);
            return (
              <div key={`${r.card}-${i}`} className={styles.historyRow}>
                <b>
                  {l.faction ? <CircularFactionIcon faction={l.faction} size={16} /> : null}{" "}
                  {l.name}
                </b>
                <span>
                  <Named kind="actionCard" id={r.card} name={r.cardName} /> on{" "}
                  <em>{r.outcomeLabel}</em>
                </span>
              </div>
            );
          })}
        </div>
      ) : null}

      {agenda.history.length > 0 ? (
        <div className={styles.history}>
          <h4>Resolved this phase</h4>
          {agenda.history.map((h, i) => (
            <div key={`${h.agenda}-${i}`} className={styles.historyRow}>
              <b>{getAgenda(h.agenda)?.name ?? prettifyId(h.agenda)}</b>
              <span>
                {h.vetoed
                  ? "vetoed"
                  : h.voided
                    ? "discarded without effect"
                    : h.discarded
                      ? "discarded"
                      : `${outcomeLabel(
                          { ...agenda, kind: h.kind ?? agenda.kind },
                          h.outcome ?? "",
                          lookOf,
                        )}${h.bySpeaker ? " (speaker)" : ""}${h.stays ? " · law in play" : ""}`}
              </span>
              {(h.riders ?? []).map((r, j) => (
                <span key={`${r.card}-${j}`} className={styles.riderResult}>
                  {lookOf(r.player).name}:{" "}
                  <Named kind="actionCard" id={r.card} name={actionCardName(r.card)} /> on{" "}
                  {outcomeLabel({ ...agenda, kind: h.kind ?? agenda.kind }, r.predicted, lookOf)}
                  {" - "}
                  {r.correct ? (r.skipped ? "correct, reward unavailable" : "correct") : "missed"}
                </span>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

/** Rider na wyniku: frakcja gracza + karta (pełny opis w podpowiedzi, jak w feedzie). */
function RiderChip({ rider, look }: { rider: AgendaPrediction; look: Look }) {
  return (
    <span
      className={styles.chip}
      data-rider=""
      style={{ "--seat-rgb": look.rgb } as CSSProperties}
      aria-label={`${look.name}: ${rider.cardName} on ${rider.outcomeLabel}`}
    >
      {look.faction ? <CircularFactionIcon faction={look.faction} size={16} /> : null}
      <Named kind="actionCard" id={rider.card} name={rider.cardName} />
    </span>
  );
}

function actionCardName(card: string): string {
  return getActionCard(card)?.name ?? prettifyId(card);
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
  const [usePredictive, setUsePredictive] = useState(false);
  const speaker = agenda.speakerId ?? "";
  const voterId = agenda.currentVoter;
  const voter = voterId ? agenda.voters[voterId] : undefined;
  const planets = voter?.planets ?? [];
  const predictive = voter?.predictive;
  const predictiveVotes = usePredictive && predictive?.ready ? predictive.votes : 0;
  const single = voter?.singleVote === true;
  const votes = single
    ? 1
    : planets.filter((p) => picked.includes(p.planet)).reduce((n, p) => n + p.influence, 0) +
      (voter?.extra ?? 0) +
      predictiveVotes;

  // Nowy głosujący = czysta urna.
  useEffect(() => {
    setPicked([]);
    setUsePredictive(false);
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
          {single ? (
            <>
              Representative Government: you cast exactly <b>1</b> vote without exhausting
              planets. Pick an outcome on the podium.
            </>
          ) : (
            <>
              Exhaust planets to cast votes equal to their influence. All votes go to{" "}
              <b>one</b> outcome. Trade goods cannot buy votes.{" "}
              {isPlanetAgenda(agenda.kind)
                ? "Choose the planet on the map (button on the podium)."
                : "Pick an outcome on the podium."}
            </>
          )}
        </p>
        <div className={styles.votesBig}>
          <b>{votes}</b>
          <span>
            votes of {voter.available + voter.extra + (predictive?.ready ? predictive.votes : 0)}{" "}
            available
            {selected ? (
              <>
                {" "}
                for <em>{outcomeLabel(agenda, selected, lookOf)}</em>
              </>
            ) : null}
          </span>
        </div>
        <div className={styles.planets} hidden={single}>
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
        <ActiveTechs context="agenda" faction={look.faction} />
        {predictive?.owned ? (
          <Switch
            size="xs"
            label={
              predictive.ready
                ? `Predictive Intelligence: +${predictive.votes} votes (exhausts if the outcome loses)`
                : "Predictive Intelligence is exhausted"
            }
            checked={usePredictive && predictive.ready}
            onChange={(event) => setUsePredictive(event.currentTarget.checked)}
            disabled={busy || !predictive.ready}
          />
        ) : null}
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={!canCast}
          onClick={() =>
            run(async () => {
              await api.agendaVote(voterId, selected ?? "", picked, predictiveVotes > 0);
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
        {agenda.kind !== "manual" ? (
          <p className={styles.hint}>Click the winning outcome on the podium.</p>
        ) : null}
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

  if (agenda.step === "COUNTED") {
    return (
      <>
        {head}
        <div className={styles.result}>
          <span>Votes counted</span>
          <b>{outcomeLabel(agenda, agenda.pendingOutcome ?? "", lookOf)}</b>
        </div>
        <p className={styles.note}>
          Players may still play action cards that react to this moment: drag them from your hand.
          When everyone is done, the speaker confirms and the outcome is resolved.
        </p>
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={busy}
          onClick={() => run(() => api.agendaConfirm(speaker))}
        >
          Resolve the outcome <IconChevronsRight size={16} aria-hidden="true" />
        </button>
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
          The agenda&apos;s effect has been applied. Players with a choice to make (units, planets,
          technologies) get a decision window - the speaker continues once they are done. Laws
          with a For or Elect outcome stay in play; everything else is discarded.
        </p>
        <button
          type="button"
          className={styles.primaryBtn}
          disabled={busy}
          onClick={() => run(() => api.agendaContinue(speaker))}
        >
          {agenda.revoteLaw
            ? `Vote on ${getAgenda(agenda.revoteLaw)?.name ?? prettifyId(agenda.revoteLaw)}`
            : last
              ? "Ready planets and finish"
              : "Next agenda"}
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

/**
 * Kto siada do stołu transakcji z okna Rady: w sieci - ja; lokalnie - głosujący człowiek albo
 * pierwszy człowiek przy ekranie (ten sam wybór co ręce w oknach reakcji).
 */
function useCouncilTrader(voter: string | null) {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: webData } = usePlayerData(gameId);
  const { data: networkMe } = useNetworkMe();
  const { data: feed } = useActivityFeed();
  const owners = humanHandOwners(networkMe, feed?.players);
  const meId = voter && owners.includes(voter) ? voter : (owners[0] ?? null);
  const players = (webData?.playerData ?? []).filter(
    (p) => p.faction && p.faction !== "neutral",
  );
  const me = players.find((p) => p.discordId === meId);
  return me ? { gameId, me, players } : null;
}

function CouncilWindow({
  agenda,
  canAdvance,
  covertCard,
}: {
  agenda: AgendaPhaseData;
  canAdvance: boolean;
  covertCard: AgendaPhaseData["card"];
}) {
  const { lookOf, round } = usePlayers();
  const api = useBoardEditor();
  const setHidden = useAppStore((s) => s.setAgendaHidden);
  const [busy, setBusy] = useState(false);
  const [tradeOpen, setTradeOpen] = useState(false);
  const trader = useCouncilTrader(agenda.currentVoter ?? null);
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
  // Remis (U4): speaker rozstrzyga KLIKIEM wyniku na podium (bez osobnej listy przycisków).
  const tiebreakClick = agenda.step === "TIEBREAK" && agenda.kind !== "manual";
  const canPick =
    !busy &&
    ((agenda.step === "VOTE" && agenda.currentVoter != null && !agenda.unresolvable) ||
      (agenda.step === "TIEBREAK" && agenda.kind === "manual") ||
      tiebreakClick);
  const pickOutcome = (outcome: string) => {
    if (tiebreakClick) run(() => api.agendaDecide(agenda.speakerId ?? "", outcome));
    else setSelected(outcome);
  };
  // Planeta wskazana na mapie (U6): po powrocie do Rady staje się wybranym wynikiem (przy
  // remisie - rozstrzygnięciem mówcy). Efekt po zerowaniu wyboru wyżej, więc go nie nadpisze.
  const takeMapPick = useAgendaMapPick((s) => s.take);
  useEffect(() => {
    const planet = takeMapPick();
    if (planet != null && canPick) pickOutcome(planet);
    // Tylko przy otwarciu okna (powrót z mapy).
  }, []);

  return createPortal(
    <div
      className={styles.overlay}
      // Okno pełnoekranowe: dok ręki zwija się do paska, a okno rezerwuje pod nim miejsce.
      data-fullscreen-overlay=""
      // Okno fazy (U3): centrum Decisions czeka jako „+N” i nie leży na karcie Ballot.
      {...PHASE_WINDOW}
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
        {/* Transakcje przy agendzie (RULES.md 47.5): każda para raz na agendę, bez sąsiedztwa. */}
        {trader && (
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => setTradeOpen(true)}
            title="Trade with any player: one transaction with each player during each agenda"
          >
            <IconArrowsExchange size={15} aria-hidden="true" /> Transaction
          </button>
        )}
        <button type="button" className={styles.ghostBtn} onClick={() => setHidden(true)}>
          <IconEye size={15} aria-hidden="true" /> Show board
        </button>
      </header>
      {tradeOpen && trader && (
        <TransactionModal
          opened
          onClose={() => setTradeOpen(false)}
          gameId={trader.gameId}
          me={trader.me}
          players={trader.players}
        />
      )}
      <div className={styles.grid}>
        <Senate agenda={agenda} lookOf={lookOf} />
        <Podium
          agenda={agenda}
          lookOf={lookOf}
          canPick={canPick}
          selected={selected}
          onSelect={pickOutcome}
          manual={manual}
          setManual={setManual}
          covertCard={covertCard}
        />
        <section className={styles.panel} aria-label="Ballot">
          <h3>
            <IconScale size={15} aria-hidden="true" /> Ballot
          </h3>
          {/* „No whens” / „No afters” zaraz po ujawnieniu agendy (RULES.md 54.12). */}
          {trader && agenda.step === "VOTE" && agenda.card ? (
            <AgendaPassButtons me={trader.me} />
          ) : null}
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
  const mapPicking = useAgendaMapPick((s) => s.picking);
  const finishMapPick = useAgendaMapPick((s) => s.finish);
  const agenda = gameState?.agendaPhase ?? null;
  // Koniec agendy / zmiana kroku przerywa wybór na mapie (inaczej pasek zostałby bez celu).
  const pickKey = `${agenda?.agendaNumber}:${agenda?.card?.id}:${agenda?.step}`;
  useEffect(() => {
    if (useAgendaMapPick.getState().picking) finishMapPick(null);
  }, [pickKey, finishMapPick]);
  const ended = gameState?.winnerId != null;

  // Poza fazą agendy okno wraca do stanu otwartego - następna agenda otwiera się sama.
  useEffect(() => {
    if (!agenda && hidden) setHidden(false);
  }, [agenda, hidden, setHidden]);

  if (!agenda || ended) return null;
  if (mapPicking) return <AgendaMapPickBar agenda={agenda} />;
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
    <CouncilWindow
      agenda={agenda}
      canAdvance={gameState?.canAdvancePhase === true}
      covertCard={gameState?.agendaCovertCard ?? null}
    />
  );
}

export default AgendaOverlay;

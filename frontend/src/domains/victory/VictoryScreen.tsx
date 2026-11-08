// Ekran zwycięstwa: pojawia się natychmiast, gdy ktoś zdobędzie próg VP albo skończy się
// ostatnia runda (backend ustawia `gameState.winnerId`). Cztery etapy, jak wieczór kończący
// partię przy stole:
//   1. triumph   — zwycięzca (portret frakcji, nazwa, punkty, powód końca gry),
//   2. vote      — pozostali gracze głosują: zwycięstwo honorowe czy niehonorowe,
//   3. chronicle — epilog frakcji zwycięzcy jako przewijana Kronika (jak w intrze gry),
//   4. summary   — klasyfikacja końcowa, statystyki i „nagrody" za najlepsze wyniki.
//
// Komponent jest tylko oprawą: wynik głosowania liczy backend (`core/epilogue.py`), a liczby
// do statystyk pochodzą z web-data. Montowany raz na stronie gry (GameMapPage).

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import { useNavigate, useParams } from "react-router-dom";
import { IconCheck, IconCrown, IconTrophy } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import { useFactions, type FactionInfo } from "@/api/useNewGame";
import type {
  EpilogueChoice,
  GameHighlight,
  GameState,
  PlayerData,
} from "@/entities/data/types";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { portraitCandidates, useFactionAccent } from "@/domains/setup/FactionBackdrop";
import { getEpilogue, DEFAULT_EPILOGUE_AUTHOR } from "./factionEpilogues";
import { buildAwards, summarize } from "./gameStats";
import styles from "./VictoryScreen.module.css";

type Stage = "triumph" | "vote" | "chronicle" | "summary";

/** Kolory graczy → CSS (tylko prezentacja; spójne z intrem i krokiem „Gracze"). */
const COLOR_SWATCH: Record<string, string> = {
  red: "#d94a4a",
  green: "#49a14a",
  white: "#e8e8e8",
  blue: "#4a7fd9",
  purple: "#9a4ad9",
  yellow: "#e0c23a",
};

/** Tempo Kroniki: znaków na sekundę (jak w intrze, ~15) i dolna granica czasu (s). */
const CRAWL_CHARS_PER_SECOND = 15;
const CRAWL_MIN_SECONDS = 26;
const CRAWL_DELAY_S = 1.6;
const CRAWL_REST_FRACTION = 0.6;

const CHOICE_LABEL: Record<EpilogueChoice, string> = {
  honorable: "Honorable",
  dishonorable: "Dishonorable",
};

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function playerName(player: PlayerData): string {
  return player.playerName?.trim() || player.userName;
}

function isBot(player: PlayerData | undefined): boolean {
  return player?.controlType === "BOT";
}

/** Powód końca gry — jedno zdanie pod nagłówkiem „Victory". */
function reasonText(
  gameState: GameState,
  vpsToWin: number,
  round: number,
): string {
  switch (gameState.endReason) {
    case "round_limit":
      return `Round ${gameState.maxRounds ?? round} has ended. The highest score takes the throne.`;
    case "no_objectives":
      return "No public objectives remain. The highest score takes the throne.";
    default:
      return `Reached ${vpsToWin} victory points in round ${round}.`;
  }
}

/** Portret frakcji z łańcuchem zapasowym (portret → bohater → ikona), jak w intrze. */
function FactionArt({
  factionId,
  faction,
  className,
  iconClassName,
}: {
  factionId: string;
  faction: FactionInfo | undefined;
  className: string;
  iconClassName: string;
}) {
  const sources = useMemo(
    () =>
      faction ? portraitCandidates(faction) : [`/static/factions/${factionId}.png`],
    [faction, factionId],
  );
  const [index, setIndex] = useState(0);
  if (index >= sources.length) return null;
  const isIcon = index === sources.length - 1;
  return (
    <img
      key={sources[index]}
      src={sources[index]}
      alt=""
      className={isIcon ? iconClassName : className}
      onError={() => setIndex((i) => i + 1)}
    />
  );
}

function Crest({ factionId, size }: { factionId: string; size: number }) {
  return (
    <img
      src={`/static/factions/${factionId}.png`}
      alt=""
      width={size}
      height={size}
      className={styles.crest}
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

function swatchStyle(player: PlayerData): CSSProperties {
  const color = COLOR_SWATCH[player.color];
  return color ? ({ "--player": color } as CSSProperties) : {};
}

export function VictoryScreen() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: webData } = usePlayerData(gameId);
  const { data: factions } = useFactions();
  const [dismissed, setDismissed] = useState(false);
  const winnerId = gameState?.winnerId ?? null;

  // Nowa gra (brak zwycięzcy) odblokowuje ekran na kolejny koniec partii.
  useEffect(() => {
    if (!winnerId) setDismissed(false);
  }, [winnerId]);

  if (!gameState || !winnerId || !webData || dismissed) return null;
  const winner = webData.playerData.find((p) => p.discordId === winnerId);
  if (!winner) return null;

  return createPortal(
    <VictoryContent
      key={winnerId}
      gameState={gameState}
      players={webData.playerData}
      winner={winner}
      factions={factions ?? []}
      round={webData.gameRound}
      vpsToWin={webData.vpsToWin}
      onDismiss={() => setDismissed(true)}
    />,
    document.body,
  );
}

function VictoryContent({
  gameState,
  players,
  winner,
  factions,
  round,
  vpsToWin,
  onDismiss,
}: {
  gameState: GameState;
  players: PlayerData[];
  winner: PlayerData;
  factions: FactionInfo[];
  round: number;
  vpsToWin: number;
  onDismiss: () => void;
}) {
  const [stage, setStage] = useState<Stage>("triumph");
  const accent = useFactionAccent(winner.faction);
  const factionById = useMemo(
    () => new Map(factions.map((f) => [f.id, f])),
    [factions],
  );
  const epilogue = gameState.epilogue ?? null;
  const result = epilogue?.result ?? null;

  // Czy w ogóle jest kto głosować (gra jednoosobowa → od razu do epilogu).
  const hasVoters = (epilogue?.voters.length ?? 0) > 0;
  const afterTriumph = () => setStage(hasVoters ? "vote" : "chronicle");

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label="Victory"
      style={{ "--accent": accent } as CSSProperties}
    >
      {stage === "triumph" && (
        <TriumphStage
          gameState={gameState}
          winner={winner}
          faction={factionById.get(winner.faction)}
          round={round}
          vpsToWin={vpsToWin}
          onContinue={afterTriumph}
        />
      )}
      {stage === "vote" && (
        <VoteStage
          gameState={gameState}
          players={players}
          winner={winner}
          factionById={factionById}
          onContinue={() => setStage("chronicle")}
        />
      )}
      {stage === "chronicle" && (
        <ChronicleStage
          winner={winner}
          factionName={
            factionById.get(winner.faction)?.name ??
            getPlayerFactionDisplayName(winner)
          }
          choice={result ?? "honorable"}
          onContinue={() => setStage("summary")}
        />
      )}
      {stage === "summary" && (
        <SummaryStage
          players={players}
          winner={winner}
          result={result}
          highlights={gameState.highlights ?? []}
          factionById={factionById}
          onReview={onDismiss}
        />
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- 1. triumph

function TriumphStage({
  gameState,
  winner,
  faction,
  round,
  vpsToWin,
  onContinue,
}: {
  gameState: GameState;
  winner: PlayerData;
  faction: FactionInfo | undefined;
  round: number;
  vpsToWin: number;
  onContinue: () => void;
}) {
  return (
    <section className={`${styles.stage} ${styles.triumph}`} style={swatchStyle(winner)}>
      <div className={styles.triumphArt} aria-hidden>
        <FactionArt
          factionId={winner.faction}
          faction={faction}
          className={styles.triumphPortrait}
          iconClassName={styles.triumphIcon}
        />
      </div>
      <div className={styles.triumphText}>
        <p className={styles.kicker}>Round {round}</p>
        <h1 className={styles.victory}>Victory</h1>
        <div className={styles.winnerLine}>
          <Crest factionId={winner.faction} size={44} />
          <h2 className={styles.winnerFaction}>
            {faction?.name ?? getPlayerFactionDisplayName(winner)}
          </h2>
        </div>
        <p className={styles.winnerPlayer}>
          <span className={styles.dot} aria-hidden />
          {playerName(winner)}
          <span className={styles.sep} aria-hidden>
            ·
          </span>
          <IconTrophy size={18} aria-hidden="true" />
          <b>{winner.totalVps}</b> / {vpsToWin} VP
        </p>
        <p className={styles.reason}>{reasonText(gameState, vpsToWin, round)}</p>
        <button type="button" className={styles.primary} onClick={onContinue} autoFocus>
          Continue
        </button>
      </div>
    </section>
  );
}

// --------------------------------------------------------------------------- 2. vote

function VoteStage({
  gameState,
  players,
  winner,
  factionById,
  onContinue,
}: {
  gameState: GameState;
  players: PlayerData[];
  winner: PlayerData;
  factionById: Map<string, FactionInfo>;
  onContinue: () => void;
}) {
  const { epilogueOpen, epilogueVote } = useBoardEditor();
  const epilogue = gameState.epilogue;
  const [busy, setBusy] = useState(false);

  // Otwarcie głosowania (idempotentne): boty oddają głosy od razu.
  useEffect(() => {
    void epilogueOpen().catch(() => undefined);
  }, [epilogueOpen]);

  const byId = useMemo(
    () => new Map(players.map((p) => [p.discordId, p])),
    [players],
  );
  const voters = epilogue?.voters ?? [];
  const votes = epilogue?.votes ?? {};
  const result = epilogue?.result ?? null;
  // Następny człowiek, który jeszcze nie głosował (hot-seat: po kolei przy tym samym ekranie).
  const currentId = voters.find((id) => !(id in votes) && !isBot(byId.get(id)));
  const current = currentId ? byId.get(currentId) : undefined;
  const winnerFaction = factionById.get(winner.faction)?.name ?? getPlayerFactionDisplayName(winner);

  const cast = (choice: EpilogueChoice) => {
    if (!currentId || busy) return;
    setBusy(true);
    void epilogueVote(currentId, choice)
      .catch(() => undefined)
      .finally(() => setBusy(false));
  };

  const tally = (choice: EpilogueChoice) =>
    Object.values(votes).filter((v) => v === choice).length;

  return (
    <section className={`${styles.stage} ${styles.vote}`}>
      <header className={styles.voteHead}>
        <p className={styles.kicker}>The Galactic Council judges</p>
        <h1 className={styles.voteTitle}>How was this victory won?</h1>
        <p className={styles.voteSub}>
          {winnerFaction} holds the throne. The other players decide whether the
          victory was honorable. A tie is judged honorable.
        </p>
      </header>

      {result === null && current && (
        <div className={styles.ballot} style={swatchStyle(current)}>
          <p className={styles.ballotWho}>
            <Crest factionId={current.faction} size={30} />
            <span>
              <b>{getPlayerFactionDisplayName(current)}</b>
              <small>{playerName(current)}, cast your vote</small>
            </span>
          </p>
          <div className={styles.choices}>
            <button
              type="button"
              className={`${styles.choice} ${styles.choiceHonor}`}
              onClick={() => cast("honorable")}
              disabled={busy}
            >
              <b>Honorable</b>
              <span>Won fairly, with oaths kept.</span>
            </button>
            <button
              type="button"
              className={`${styles.choice} ${styles.choiceShame}`}
              onClick={() => cast("dishonorable")}
              disabled={busy}
            >
              <b>Dishonorable</b>
              <span>Won through treachery and broken oaths.</span>
            </button>
          </div>
        </div>
      )}

      {result === null && !current && (
        <p className={styles.waiting}>Waiting for the remaining votes…</p>
      )}

      <ul className={styles.voters} aria-label="Voters">
        {voters.map((id) => {
          const voter = byId.get(id);
          if (!voter) return null;
          const vote = votes[id];
          // Tajne głosowanie: wybór ujawniamy dopiero po komplecie głosów.
          const revealed = result !== null && vote;
          return (
            <li
              key={id}
              className={styles.voter}
              data-choice={revealed ? vote : undefined}
              style={swatchStyle(voter)}
            >
              <Crest factionId={voter.faction} size={26} />
              <span className={styles.voterName}>
                {getPlayerFactionDisplayName(voter)}
                <small>{isBot(voter) ? "Bot" : playerName(voter)}</small>
              </span>
              <span className={styles.voterState}>
                {revealed ? (
                  CHOICE_LABEL[vote]
                ) : vote ? (
                  <>
                    <IconCheck size={14} aria-hidden="true" /> Voted
                  </>
                ) : (
                  "Waiting"
                )}
              </span>
            </li>
          );
        })}
      </ul>

      {result !== null && (
        <div className={styles.verdict} data-choice={result}>
          <p className={styles.verdictLabel}>Verdict</p>
          <h2 className={styles.verdictTitle}>{CHOICE_LABEL[result]} victory</h2>
          <p className={styles.verdictTally}>
            {tally("honorable")} honorable · {tally("dishonorable")} dishonorable
          </p>
          <button type="button" className={styles.primary} onClick={onContinue} autoFocus>
            Read the epilogue
          </button>
        </div>
      )}
    </section>
  );
}

// --------------------------------------------------------------------------- 3. chronicle

function ChronicleStage({
  winner,
  factionName,
  choice,
  onContinue,
}: {
  winner: PlayerData;
  factionName: string;
  choice: EpilogueChoice;
  onContinue: () => void;
}) {
  const reduced = useRef(prefersReducedMotion()).current;
  const [arrived, setArrived] = useState(reduced);
  const boxRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const [route, setRoute] = useState<{ from: number; to: number; dur: number } | null>(
    null,
  );
  const epilogue = useMemo(
    () => getEpilogue(winner.faction, factionName, choice),
    [winner.faction, factionName, choice],
  );
  const chars = epilogue.paragraphs.reduce((n, p) => n + p.length, 0);
  const duration = Math.max(CRAWL_MIN_SECONDS, chars / CRAWL_CHARS_PER_SECOND);

  useLayoutEffect(() => {
    if (reduced) return;
    const measure = () => {
      const box = boxRef.current;
      const text = textRef.current;
      if (!box || !text) return;
      const h = box.clientHeight;
      const to = h * CRAWL_REST_FRACTION - text.scrollHeight;
      setRoute((prev) =>
        prev && Math.abs(prev.to - to) < 24 && Math.abs(prev.from - h) < 24
          ? prev
          : { from: h, to, dur: duration },
      );
    };
    measure();
    void document.fonts?.ready.then(measure);
  }, [reduced, duration]);

  const skip = useCallback(() => onContinue(), [onContinue]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") skip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [skip]);

  const style = route
    ? ({
        "--from": `${route.from}px`,
        "--to": `${route.to}px`,
        "--dur": `${route.dur}s`,
        "--t-crawl-delay": `${CRAWL_DELAY_S}s`,
      } as CSSProperties)
    : undefined;

  return (
    <section className={`${styles.stage} ${styles.chronicle}`} data-choice={choice}>
      <header className={styles.chronicleHead}>
        <p className={styles.kicker}>Epilogue</p>
        <h1 className={styles.chronicleTitle}>{CHOICE_LABEL[choice]} Victory</h1>
      </header>

      <div
        ref={boxRef}
        className={`${styles.crawlBox} ${reduced ? styles.crawlStatic : ""}`}
      >
        <div
          ref={textRef}
          className={`${styles.crawlText} ${route ? styles.crawlRunning : ""}`}
          style={style}
          onAnimationEnd={(e) => {
            if (e.animationName.includes("crawl")) setArrived(true);
          }}
        >
          <p className={styles.chronicleLabel}>The Custodian Chronicle</p>
          {epilogue.paragraphs.map((paragraph) => (
            <p key={paragraph.slice(0, 24)} className={styles.paragraph}>
              {paragraph}
            </p>
          ))}
          {epilogue.quote && (
            <blockquote className={styles.epilogueQuote}>“{epilogue.quote}”</blockquote>
          )}
          {(epilogue.author || !epilogue.quote) && (
            <p className={styles.author}>— {epilogue.author ?? DEFAULT_EPILOGUE_AUTHOR}</p>
          )}
          <div className={styles.outro}>
            <p className={styles.motto}>Pax Magnifica</p>
            <p className={styles.outroLine}>
              {choice === "honorable"
                ? "A worthy ruler takes the throne"
                : "A feared ruler takes the throne"}
            </p>
          </div>
        </div>
      </div>

      <div className={styles.footer}>
        {arrived && (
          <button type="button" className={styles.primary} onClick={onContinue} autoFocus>
            Final standings
          </button>
        )}
      </div>
      <button type="button" className={styles.skip} onClick={skip}>
        Skip
      </button>
    </section>
  );
}

// --------------------------------------------------------------------------- 4. summary

function SummaryStage({
  players,
  winner,
  result,
  highlights,
  factionById,
  onReview,
}: {
  players: PlayerData[];
  winner: PlayerData;
  result: EpilogueChoice | null;
  highlights: GameHighlight[];
  factionById: Map<string, FactionInfo>;
  onReview: () => void;
}) {
  const navigate = useNavigate();
  const rows = useMemo(() => summarize(players, winner.discordId), [players, winner]);
  const awards = useMemo(() => buildAwards(rows), [rows]);
  const columns: { key: string; label: string; value: (i: number) => number }[] = [
    { key: "vp", label: "VP", value: (i) => rows[i].vp },
    { key: "planets", label: "Planets", value: (i) => rows[i].planets },
    { key: "res", label: "Resources", value: (i) => rows[i].resources },
    { key: "inf", label: "Influence", value: (i) => rows[i].influence },
    { key: "tech", label: "Techs", value: (i) => rows[i].techs },
    { key: "tg", label: "Trade goods", value: (i) => rows[i].tradeGoods },
    { key: "fleet", label: "Fleet", value: (i) => rows[i].fleet },
    { key: "ground", label: "Ground", value: (i) => rows[i].ground },
  ];

  return (
    <section className={`${styles.stage} ${styles.summary}`}>
      <header className={styles.summaryHead}>
        <p className={styles.kicker}>
          {result ? `${CHOICE_LABEL[result]} victory` : "Game over"}
        </p>
        <h1 className={styles.summaryTitle}>Final standings</h1>
      </header>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col" className={styles.leftCol}>
                Player
              </th>
              {columns.map((c) => (
                <th key={c.key} scope="col">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isWinner = row.player.discordId === winner.discordId;
              return (
                <tr
                  key={row.player.discordId}
                  className={isWinner ? styles.winnerRow : undefined}
                  style={swatchStyle(row.player)}
                >
                  <td className={styles.rank}>
                    {isWinner ? <IconCrown size={18} aria-label="Winner" /> : row.rank}
                  </td>
                  <th scope="row" className={styles.leftCol}>
                    <span className={styles.cell}>
                      <Crest factionId={row.player.faction} size={28} />
                      <span className={styles.cellName}>
                        {factionById.get(row.player.faction)?.name ??
                          getPlayerFactionDisplayName(row.player)}
                        <small>
                          <span className={styles.dot} aria-hidden />
                          {isBot(row.player) ? "Bot" : playerName(row.player)}
                        </small>
                      </span>
                    </span>
                  </th>
                  {columns.map((c) => (
                    <td key={c.key} data-strong={c.key === "vp" || undefined}>
                      {c.value(i)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {highlights.length > 0 && (
        <div className={styles.highlightsWrap}>
          <h2 className={styles.sectionTitle}>Chronicle of the war</h2>
          <ul className={styles.highlights}>
            {highlights.map((h) => {
              const involved = h.players
                .map((id) => players.find((p) => p.discordId === id))
                .filter((p): p is PlayerData => p !== undefined);
              return (
                <li
                  key={h.key}
                  className={styles.highlight}
                  data-kind={h.key === "betrayal" ? "betrayal" : undefined}
                >
                  <span className={styles.highlightCrests}>
                    {involved.map((p) => (
                      <Crest key={p.discordId} factionId={p.faction} size={30} />
                    ))}
                  </span>
                  <span className={styles.awardText}>
                    <small>{h.title}</small>
                    <em>{h.detail}</em>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {awards.length > 0 && (
        <ul className={styles.awards} aria-label="Distinctions">
          {awards.map((award) => (
            <li key={award.key} className={styles.award} style={swatchStyle(award.player)}>
              <Crest factionId={award.player.faction} size={34} />
              <span className={styles.awardText}>
                <small>{award.title}</small>
                <b>
                  {factionById.get(award.player.faction)?.name ??
                    getPlayerFactionDisplayName(award.player)}
                </b>
                <em>{award.detail}</em>
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className={styles.footer}>
        <button type="button" className={styles.secondary} onClick={onReview}>
          Review the board
        </button>
        <button type="button" className={styles.primary} onClick={() => navigate("/")}>
          Main menu
        </button>
      </div>
    </section>
  );
}

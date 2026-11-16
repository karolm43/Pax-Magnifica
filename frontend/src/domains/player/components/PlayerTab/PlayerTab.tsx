import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import {
  IconAlertTriangle,
  IconBolt,
  IconBulb,
  IconCrown,
  IconFlag,
  IconStar,
} from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import PlayerCard from "@/domains/player/components/composition/PlayerCard";
import { SecretHand } from "@/domains/game-shell/components/SecretHand";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { useSecretHandAccess } from "@/domains/game-shell/components/SecretHand/useSecretHandAccess";
import { GameStateActionControls } from "@/domains/game-shell/components/GameStatePanel";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { ResourceBarFor } from "@/domains/game-shell/components/ResourceBar/ResourceBar";
import { Named } from "@/domains/game-shell/components/ActivityPanel/Named";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { filterPlayersWithAssignedFaction } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import { commanderTips, vpRank, type Tip, type TipTone } from "./commanderTips";
import styles from "./PlayerTab.module.css";

/*
 * PANEL DOWÓDCY (zakładka „Player”) - jeden gracz z KOMPLETEM informacji, zawsze aktywny:
 * nie zależy od tego, czy ktoś ma teraz turę (agenda / status nie mają aktywnego gracza).
 * Domyślnie pokazuje gracza pulpitu (``useDeskPlayer``: moje miejsce w sieci, inaczej gracz
 * z turą / mówca); pasek graczy u góry przełącza na dowolnego innego.
 * [nagłówek: frakcja, VP i miejsce, mówca, karty strategii, faza]
 * [odprawa: wskazówki z danych silnika | zasoby | stół: wszyscy gracze]
 * [pełna karta gracza (ta sama co w „Players”) | akcje + ręka - tylko dla gracza pulpitu]
 */

const PHASE_LABEL: [string, string][] = [
  ["strategy", "Strategy phase"],
  ["action", "Action phase"],
  ["status", "Status phase"],
  ["agenda", "Agenda phase"],
  ["setup", "Setup"],
  ["finished", "Game over"],
];

function phaseLabel(phase: string): string {
  return PHASE_LABEL.find(([key]) => phase.startsWith(key))?.[1] ?? "Game";
}

const TONE_ICON: Record<TipTone, typeof IconBolt> = {
  action: IconBolt,
  good: IconStar,
  warn: IconAlertTriangle,
  info: IconBulb,
};

const TONE_LABEL: Record<TipTone, string> = {
  action: "Now",
  good: "Opportunity",
  warn: "Warning",
  info: "Tip",
};

function TipRow({ tip, idMap }: { tip: Tip; idMap?: Record<number, string> }) {
  const Icon = TONE_ICON[tip.tone];
  return (
    <li className={styles.tip} data-tone={tip.tone}>
      <Icon size={15} aria-label={TONE_LABEL[tip.tone]} className={styles.tipIcon} />
      <span>
        {tip.text}
        {tip.refs?.map((ref, i) => (
          <span key={`${ref.kind}-${ref.id}`} className={styles.ref}>
            {i === 0 ? " " : ", "}
            <Named kind={ref.kind} id={ref.id} name={ref.name} idMap={idMap} />
          </span>
        ))}
      </span>
    </li>
  );
}

/** Wiersz stołu: gracz, punkty (pasek do zwycięstwa), karty strategii, stan tury. */
function SeatRow({
  player,
  vpsToWin,
  selected,
  isTurn,
  idMap,
  onSelect,
}: {
  player: PlayerData;
  vpsToWin: number;
  selected: boolean;
  isTurn: boolean;
  idMap?: Record<number, string>;
  onSelect: () => void;
}) {
  return (
    <li className={styles.seat} data-selected={selected || undefined}>
      <button
        type="button"
        className={styles.seatBtn}
        style={{ "--pc": playerRgb(player.color) } as CSSProperties}
        aria-pressed={selected}
        onClick={onSelect}
        aria-label={`Show ${playerName(player)}`}
      >
        <span className={styles.seatRing} aria-hidden="true">
          {player.faction ? <CircularFactionIcon faction={player.faction} size={20} /> : null}
        </span>
        <span className={styles.seatName}>{playerName(player)}</span>
        <span className={styles.seatVp}>
          <i style={{ width: `${Math.min(100, (player.totalVps / Math.max(1, vpsToWin)) * 100)}%` }} />
          <b>{player.totalVps}</b>
        </span>
      </button>
      <span className={styles.seatMeta}>
        {player.isSpeaker ? <IconCrown size={13} aria-label="Speaker" /> : null}
        {isTurn ? <span className={styles.badge} data-kind="turn">turn</span> : null}
        {player.passed ? <span className={styles.badge}>passed</span> : null}
        {player.scs.map((sc) => (
          <span key={sc} className={styles.sc} data-used={player.exhaustedSCs.includes(sc) || undefined}>
            <Named kind="strategy" id={String(sc)} idMap={idMap}>
              {sc}
            </Named>
          </span>
        ))}
      </span>
    </li>
  );
}

export function PlayerTab() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const gameData = useGameData();
  const { data: gameState } = useGameState(gameId);
  const desk = useDeskPlayer();
  const players = useMemo(
    () => filterPlayersWithAssignedFaction(gameData?.playerData ?? []),
    [gameData?.playerData],
  );
  const [chosenColor, setChosenColor] = useState<string | null>(null);
  // Zmiana gracza pulpitu (np. logowanie do miejsca) wraca do niego.
  useEffect(() => setChosenColor(null), [desk?.color]);
  const player = players.find((p) => p.color === chosenColor) ?? desk ?? players[0];

  const { canViewSecretHand } = useSecretHandAccess(gameData?.playerData ?? []);
  const { data: handData, isLoading, error } = usePlayerHand(gameId);

  if (!player) {
    return (
      <div className={styles.empty}>
        <p>No players seated in this game yet.</p>
      </div>
    );
  }

  const phase = gameState?.phase ?? "unknown";
  const turnColor = gameState?.activeTurnPlayer ?? gameState?.activePlayer ?? null;
  const isDesk = desk != null && player.color === desk.color;
  const vpsToWin = gameData?.vpsToWin ?? 10;
  const idMap = gameData?.strategyCardIdMap;
  const objectives = [
    ...(gameData?.objectives?.stage1Objectives ?? []),
    ...(gameData?.objectives?.stage2Objectives ?? []),
    ...(gameData?.objectives?.customObjectives ?? []),
  ];
  const tips = commanderTips({
    player,
    players,
    objectives,
    vpsToWin,
    phase,
    isTurn: turnColor === player.color,
    agenda: gameState?.agendaPhase ?? null,
  });
  const rank = vpRank(player, players);
  const standings = [...players].sort((a, b) => b.totalVps - a.totalVps);

  return (
    <div className={styles.layout} style={{ "--pc": playerRgb(player.color) } as CSSProperties}>
      <header className={styles.hero} aria-label="Commander">
        <span className={styles.heroIcon} aria-hidden="true">
          {player.faction ? <CircularFactionIcon faction={player.faction} size={44} /> : null}
        </span>
        <div className={styles.heroText}>
          <h2>{playerName(player)}</h2>
          <p>
            {player.flexibleDisplayName && player.flexibleDisplayName !== playerName(player)
              ? `${player.flexibleDisplayName} · `
              : ""}
            {phaseLabel(phase)} · round {gameData?.gameRound ?? "?"}
            {player.isSpeaker ? " · speaker" : ""}
            {player.controlType === "BOT" ? " · bot" : ""}
            {isDesk ? "" : " · viewing another player"}
          </p>
        </div>
        <div className={styles.heroVp} title={`${player.totalVps} of ${vpsToWin} victory points`}>
          <IconFlag size={16} aria-hidden="true" />
          <b>{player.totalVps}</b>
          <small>/ {vpsToWin} VP</small>
          <span className={styles.rank}>#{rank}</span>
        </div>
      </header>

      <div className={styles.grid}>
        <div className={styles.main}>
          <section className={styles.panel} aria-label="Briefing">
            <h3 className={styles.panelTitle}>Briefing</h3>
            {tips.length > 0 ? (
              <ul className={styles.tips}>
                {tips.map((tip) => (
                  <TipRow key={tip.id} tip={tip} idMap={idMap} />
                ))}
              </ul>
            ) : (
              <p className={styles.hint}>Nothing urgent right now.</p>
            )}
          </section>

          <section className={styles.panel} aria-label="Stores">
            <h3 className={styles.panelTitle}>Stores</h3>
            <ResourceBarFor desk={player} label={`${playerName(player)} stores`} />
          </section>

          <PlayerCard key={player.color} playerData={player} />
        </div>

        <div className={styles.side}>
          <section className={styles.panel} aria-label="Table">
            <h3 className={styles.panelTitle}>Table</h3>
            <p className={styles.hint}>Victory race - click a player to brief on them.</p>
            <ol className={styles.seats}>
              {standings.map((p) => (
                <SeatRow
                  key={p.color}
                  player={p}
                  vpsToWin={vpsToWin}
                  selected={p.color === player.color}
                  isTurn={turnColor === p.color}
                  idMap={idMap}
                  onSelect={() => setChosenColor(p.color === desk?.color ? null : p.color)}
                />
              ))}
            </ol>
          </section>

          {isDesk ? (
            <>
              <section className={styles.panel} aria-label="Actions">
                <h3 className={styles.panelTitle}>Actions</h3>
                <p className={styles.hint}>What you can do now in the {phaseLabel(phase).toLowerCase()}.</p>
                <GameStateActionControls />
              </section>

              <section className={styles.panel} aria-label="Your hand">
                <h3 className={styles.panelTitle}>Your hand</h3>
                <p className={styles.hint}>
                  Action cards, secret objectives and promissory notes - tap a card to read it.
                </p>
                {canViewSecretHand ? (
                  <SecretHand handData={handData} isLoading={isLoading} error={error} inlineDetails />
                ) : (
                  <p className={styles.hint}>Full hand visible only to the logged-in player in this game.</p>
                )}
              </section>
            </>
          ) : (
            <section className={styles.panel} aria-label="Hand">
              <h3 className={styles.panelTitle}>Hand</h3>
              <p className={styles.hint}>
                {player.acCount} action cards · {player.soCount} secret objectives · {player.pnCount}{" "}
                promissory notes (hidden).
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerTab;

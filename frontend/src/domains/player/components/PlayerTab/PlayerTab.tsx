import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import {
  IconAlertTriangle,
  IconBolt,
  IconBulb,
  IconCrown,
  IconStar,
} from "@tabler/icons-react";
import { Tabs } from "@/ds";
import { useGameData } from "@/state/useGameContext";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import PlayerCard from "@/domains/player/components/composition/PlayerCard";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { ResourceBarFor } from "@/domains/game-shell/components/ResourceBar/ResourceBar";
import { Named } from "@/domains/game-shell/components/ActivityPanel/Named";
import { ComponentCard } from "@/domains/cards/components/ComponentInfo";
import type { DeckSection } from "@/domains/player/components/PlayerCardShared/PlayerCardDeck";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { filterPlayersWithAssignedFaction } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import {
  briefingMode,
  commanderTips,
  vpRank,
  type Tip,
  type TipRef,
  type TipTone,
} from "./commanderTips";
import { CommandBanner } from "./CommandBanner";
import { empireStats } from "./empireStats";
import { EmpirePanel } from "./EmpirePanel";
import { HandPanel } from "./HandPanel";
import styles from "./PlayerTab.module.css";

/*
 * PANEL DOWÓDCY (zakładka „Player”) - jeden gracz z KOMPLETEM informacji, zawsze aktywny:
 * nie zależy od tego, czy ktoś ma teraz turę (agenda / status nie mają aktywnego gracza).
 * Domyślnie pokazuje gracza pulpitu (``useDeskPlayer``: moje miejsce w sieci, inaczej gracz
 * z turą / mówca); pasek graczy u góry przełącza na dowolnego innego.
 * [baner: portret, frakcja, cytat, VP i miejsce, żetony stołu, sąsiedzi, lore]
 * [telemetria: zasoby / wpływy / TG / żetony / pula floty / ręka - bez przewijania]
 * [zakładki: Briefing (odprawa + imperium) | Status | Tech & units | Planets - grupy
 *  pełnej karty gracza (ta sama co w „Players”, bez nagłówka)]   [stół: wszyscy gracze | ręka]
 * Odprawa ma dwa tryby: własne miejsce = co robić teraz; cudzy gracz = wywiad (Opponent Intel).
 * Akcje tury są w panelu sterowania na mapie - tu ich nie dublujemy.
 */

/** Sub-views of the lower deck: which `PlayerCardDeck` groups each one shows. */
const DECK_VIEWS: { value: string; label: string; sections: readonly DeckSection[] }[] = [
  { value: "status", label: "Status", sections: ["loadout", "status"] },
  { value: "build", label: "Tech & units", sections: ["tech", "units"] },
  { value: "planets", label: "Planets", sections: ["planets"] },
];

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

/** A tip reference: name with hover hint; click opens the full card (same as the player panel chips). */
function TipRefLink({ tipRef, idMap }: { tipRef: TipRef; idMap?: Record<number, string> }) {
  const [opened, setOpened] = useState(false);
  const named = <Named kind={tipRef.kind} id={tipRef.id} name={tipRef.name} idMap={idMap} />;
  if (tipRef.kind === "system") return named;
  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="bottom">
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.refLink}
          aria-expanded={opened}
          title="Click for the full card"
          onClick={() => setOpened((o) => !o)}
        >
          {named}
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <ComponentCard componentRef={{ kind: tipRef.kind, id: tipRef.id }} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

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
            <TipRefLink tipRef={ref} idMap={idMap} />
          </span>
        ))}
      </span>
    </li>
  );
}

/**
 * At-a-glance numbers under the banner: the stores bar (same `ResourceBarFor` as the tab strip)
 * plus fleet pool use, hand size and - in the agenda - vote power. No scrolling needed.
 */
function TelemetryStrip({
  player,
  largestFleet,
  fleetPool,
  votes,
}: {
  player: PlayerData;
  largestFleet: number | null;
  fleetPool: number;
  votes: number | null;
}) {
  const fleetFull = largestFleet !== null && fleetPool > 0 && largestFleet >= fleetPool;
  const limit = player.actionCardLimit;
  const overLimit = typeof limit === "number" && player.acCount > limit;
  const unplayed = player.scs.filter((sc) => !player.exhaustedSCs.includes(sc)).length;
  return (
    <section className={styles.telemetry} aria-label="Telemetry">
      <ResourceBarFor desk={player} label={`${playerName(player)} stores`} />
      <div className={styles.readouts}>
        {largestFleet !== null && (
          <span
            className={styles.readout}
            data-warn={fleetFull || undefined}
            title="Largest fleet (non-fighter ships in one system) vs. fleet pool tokens"
          >
            <small>Fleet</small>
            <b>
              {largestFleet}/{fleetPool}
            </b>
          </span>
        )}
        <span
          className={styles.readout}
          data-warn={overLimit || undefined}
          title={`Action cards${typeof limit === "number" ? ` (limit ${limit})` : ""} · secret objectives · promissory notes in hand`}
        >
          <small>Hand</small>
          <b>
            {player.acCount}
            {typeof limit === "number" ? <i>/{limit}</i> : null} AC · {player.soCount ?? 0} SO ·{" "}
            {player.pnCount ?? 0} PN
          </b>
        </span>
        {player.scs.length > 0 && (
          <span className={styles.readout} title="Strategy cards still to play / held">
            <small>Strategy</small>
            <b>
              {unplayed}/{player.scs.length} ready
            </b>
          </span>
        )}
        {votes !== null && (
          <span className={styles.readout} title="Votes available on the current agenda">
            <small>Votes</small>
            <b>{votes}</b>
          </span>
        )}
      </div>
    </section>
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
  const [view, setView] = useState<string>("briefing");
  // Zmiana gracza pulpitu (np. logowanie do miejsca) wraca do niego.
  useEffect(() => setChosenColor(null), [desk?.color]);
  const player = players.find((p) => p.color === chosenColor) ?? desk ?? players[0];

  const empire = useMemo(
    () => (player ? empireStats(player, gameData?.tiles) : undefined),
    [player, gameData?.tiles],
  );

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
  const agenda = gameState?.agendaPhase ?? null;
  const tipContext = {
    player,
    players,
    objectives,
    vpsToWin,
    phase,
    isTurn: turnColor === player.color,
    agenda,
    empire,
    viewer: desk ?? null,
  };
  const tips = commanderTips(tipContext);
  const scouting = briefingMode(tipContext) === "scout";
  const voter = phase.startsWith("agenda") ? agenda?.voters[player.discordId] : undefined;
  const subtitle = [
    player.flexibleDisplayName && player.flexibleDisplayName !== playerName(player)
      ? player.flexibleDisplayName
      : null,
    phaseLabel(phase),
    `round ${gameData?.gameRound ?? "?"}`,
    player.isSpeaker ? "speaker" : null,
    player.controlType === "BOT" ? "bot" : null,
    isDesk || desk == null ? null : "viewing another player",
  ]
    .filter(Boolean)
    .join(" · ");
  const rank = vpRank(player, players);
  const standings = [...players].sort((a, b) => b.totalVps - a.totalVps);

  return (
    <div className={styles.layout} style={{ "--pc": playerRgb(player.color) } as CSSProperties}>
      <CommandBanner
        player={player}
        subtitle={subtitle}
        vpsToWin={vpsToWin}
        rank={rank}
        scouting={scouting}
      />

      <TelemetryStrip
        player={player}
        largestFleet={empire ? empire.largestFleet : null}
        fleetPool={empire?.fleetPool ?? player.fleetCC}
        votes={voter ? voter.available + voter.extra : null}
      />

      <div className={styles.grid}>
        <div className={styles.main}>
          <Tabs value={view} onChange={(v) => v && setView(v)}>
            <Tabs.List className={styles.viewTabs}>
              <Tabs.Tab value="briefing">{scouting ? "Intel" : "Briefing"}</Tabs.Tab>
              {DECK_VIEWS.map((v) => (
                <Tabs.Tab key={v.value} value={v.value}>
                  {v.label}
                </Tabs.Tab>
              ))}
            </Tabs.List>

            <Tabs.Panel value="briefing" keepMounted={false} className={styles.view}>
              <section className={styles.panel} aria-label={scouting ? "Opponent intel" : "Briefing"}>
                <h3 className={styles.panelTitle}>{scouting ? "Opponent intel" : "Briefing"}</h3>
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
              {empire ? <EmpirePanel player={player} stats={empire} /> : null}
            </Tabs.Panel>

            {DECK_VIEWS.map((v) => (
              <Tabs.Panel key={v.value} value={v.value} keepMounted={false} className={styles.view}>
                <PlayerCard key={player.color} playerData={player} hideHeader sections={v.sections} />
              </Tabs.Panel>
            ))}
          </Tabs>
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

          <HandPanel gameId={gameId} player={player} own={isDesk} />
        </div>
      </div>
    </div>
  );
}

export default PlayerTab;

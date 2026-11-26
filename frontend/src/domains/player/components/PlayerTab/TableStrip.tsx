import type { CSSProperties } from "react";
import { IconCrown, IconFlag } from "@tabler/icons-react";
import { Named } from "@/domains/game-shell/components/ActivityPanel/Named";
import { HeaderTokens } from "@/domains/player/components/PlayerCardHeader/PlayerCardHeaderCompact";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { NeedsToFollow } from "@/domains/player/components/NeedsToFollow";
import { Neighbors } from "@/domains/player/components/Neighbors";
import { StatusIndicator } from "@/domains/player/components/StatusIndicator";
import { Breakthrough } from "@/domains/player/components/Breakthrough/Breakthrough";
import breakthroughStyles from "@/domains/player/components/Breakthrough/Breakthrough.module.css";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { PlayerData } from "@/entities/data/types";
import { useSettingsStore } from "@/state/appStore";
import styles from "./TableStrip.module.css";

/*
 * Top strip of the Player tab: the seat switcher (every player, standings order) and the table
 * state of the shown player that is not printed on a faction sheet.
 */

/** One seat: player, victory points, strategy cards, turn state. */
function Seat({
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
    <li
      className={styles.seat}
      data-selected={selected || undefined}
      style={{ "--pc": playerRgb(player.color) } as CSSProperties}
    >
      <button
        type="button"
        className={styles.seatBtn}
        aria-pressed={selected}
        onClick={onSelect}
        aria-label={`Show ${playerName(player)}`}
      >
        {player.faction ? <CircularFactionIcon faction={player.faction} size={20} /> : null}
        <span className={styles.seatName}>{playerName(player)}</span>
        <b title={`${player.totalVps} of ${vpsToWin} victory points`}>{player.totalVps}</b>
      </button>
      <span className={styles.seatMeta}>
        {player.isSpeaker ? <IconCrown size={13} aria-label="Speaker" /> : null}
        {isTurn ? <span className={styles.flag} data-kind="turn">turn</span> : null}
        {player.passed ? <span className={styles.flag}>passed</span> : null}
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

export function SeatSwitcher({
  players,
  selectedColor,
  turnColor,
  vpsToWin,
  idMap,
  onSelect,
}: {
  players: PlayerData[];
  selectedColor: string;
  turnColor: string | null;
  vpsToWin: number;
  idMap?: Record<number, string>;
  onSelect: (color: string) => void;
}) {
  const standings = [...players].sort((a, b) => b.totalVps - a.totalVps);
  return (
    <nav aria-label="Table">
      <ol className={styles.seats}>
        {standings.map((p) => (
          <Seat
            key={p.color}
            player={p}
            vpsToWin={vpsToWin}
            selected={p.color === selectedColor}
            isTurn={turnColor === p.color}
            idMap={idMap}
            onSelect={() => onSelect(p.color)}
          />
        ))}
      </ol>
    </nav>
  );
}

export function TableBadges({
  player,
  subtitle,
  vpsToWin,
  rank,
  votes,
  scouting,
}: {
  player: PlayerData;
  /** Phase · round · roles line next to the name. */
  subtitle: string;
  vpsToWin: number;
  rank: number;
  /** Votes available on the current agenda; null outside the agenda phase. */
  votes: number | null;
  /** Viewing another player than my own seat (Opponent Intel). */
  scouting: boolean;
}) {
  const showNeighbors = useSettingsStore((s) => s.settings.showPlayerAreaNeighborship);
  const fields = getPlayerCardLayoutFields(player);
  const breakthrough = player.breakthrough;

  return (
    <header className={styles.badges} aria-label="Commander">
      <div className={styles.who}>
        <b>
          {playerName(player)}
          {scouting && <span className={styles.intel}>Intel</span>}
        </b>
        <small>{subtitle}</small>
      </div>
      <span className={styles.vp} title={`${player.totalVps} of ${vpsToWin} victory points`}>
        <IconFlag size={14} aria-hidden="true" />
        <b>{player.totalVps}</b>
        <small>
          / {vpsToWin} VP · #{rank}
        </small>
      </span>
      <StatusIndicator passed={player.passed} active={player.active} />
      <HeaderTokens
        faction={player.faction}
        factionDisplayName={fields.factionDisplayName}
        playerId={player.discordId}
        isSpeaker={player.isSpeaker}
        isTyrant={fields.isTyrant}
        scs={fields.scs}
        exhaustedSCs={player.exhaustedSCs}
      />
      {fields.unfollowedSCs.length > 0 && <NeedsToFollow values={fields.unfollowedSCs} />}
      {showNeighbors && <Neighbors neighbors={fields.neighbors} />}
      {breakthrough?.breakthroughId && (
        <span className={styles.breakthrough}>
          <Breakthrough
            breakthroughId={breakthrough.breakthroughId}
            exhausted={breakthrough.exhausted}
            tradeGoodsStored={breakthrough.tradeGoodsStored}
            unlocked={breakthrough.unlocked ?? false}
            flipped={breakthrough.flipped ?? false}
            strong={false}
            chipClassName={breakthroughStyles.headerChip}
          />
        </span>
      )}
      {votes !== null && (
        <span className={styles.votes} title="Votes available on the current agenda">
          Votes <b>{votes}</b>
        </span>
      )}
    </header>
  );
}

import { useEffect, useState, type CSSProperties } from "react";
import { Loader, Text, Tooltip } from "@/ds";
import cx from "clsx";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import {
  useActivityFeed,
  type ActivityEntry,
  type ActivityKind,
  type ActivityPlayer,
} from "@/api/useBoardEditor";
import {
  formatAbsoluteTime,
  formatRelativeTime,
  prettifyId,
} from "../GameEventPanel/eventFormatting";
import { describeActivity, type ActivityContext } from "./describeActivity";
import { useActivityContext } from "./useActivityContext";
import classes from "./ActivityPanel.module.css";

type FilterKey =
  | "all"
  | "strategy"
  | "moves"
  | "combat"
  | "economy"
  | "progress"
  | "flow"
  | "admin";

const FILTERS: {
  key: FilterKey;
  label: string;
  kinds: ActivityKind[] | null;
  tone?: string;
}[] = [
  { key: "all", label: "All", kinds: null },
  { key: "strategy", label: "Strategy", kinds: ["strategy"], tone: "var(--gd-purple)" },
  { key: "moves", label: "Moves", kinds: ["tactical", "exploration"], tone: "var(--gd-blue)" },
  { key: "combat", label: "Combat", kinds: ["combat"], tone: "var(--gd-red)" },
  { key: "economy", label: "Trades", kinds: ["economy"], tone: "var(--gd-cyan)" },
  { key: "progress", label: "Progress", kinds: ["scoring", "misc"], tone: "var(--gd-green)" },
  { key: "flow", label: "Turns", kinds: ["turn"], tone: "var(--gd-gray)" },
  { key: "admin", label: "God-Mode", kinds: ["godmode"], tone: "var(--gd-orange)" },
];

function matches(entry: ActivityEntry, filter: FilterKey): boolean {
  const def = FILTERS.find((f) => f.key === filter);
  if (!def || def.kinds === null) return entry.activity.kind !== "godmode";
  return def.kinds.includes(entry.activity.kind);
}

function toneStyle(tone: string): CSSProperties {
  return { "--ek": tone } as CSSProperties;
}

function displayName(id: string, player: ActivityPlayer | undefined): string {
  if (player?.display_name.trim()) return player.display_name.trim();
  return player?.faction ? prettifyId(player.faction) : prettifyId(id);
}

function PlayerBadge({
  player,
  id,
  size,
}: {
  player: ActivityPlayer | undefined;
  id: string | null;
  size: number;
}) {
  if (!id || !player?.faction) {
    return <span className={classes.noFaction} style={{ width: size, height: size }} />;
  }
  return (
    <Tooltip label={displayName(id, player)} withArrow openDelay={300}>
      <span className={classes.faction}>
        <CircularFactionIcon faction={player.faction} size={size} />
      </span>
    </Tooltip>
  );
}

function Row({
  entry,
  ctx,
  now,
  undone,
}: {
  entry: ActivityEntry;
  ctx: ActivityContext;
  now: number;
  /** Cofnięte przez Undo — wciąż w historii, ale nie w bieżącym stanie. */
  undone: boolean;
}) {
  const a = entry.activity;
  const view = describeActivity(a, ctx);
  const Icon = view.Icon;
  const actor = a.actor_id ? ctx.players[a.actor_id] : undefined;
  const timestamp = entry.created_at === null ? null : entry.created_at * 1000;
  return (
    <div
      className={classes.row}
      data-undone={undone || undefined}
      style={toneStyle(view.tone)}
    >
      <span className={classes.mark}>
        <PlayerBadge player={actor} id={a.actor_id} size={26} />
        <span className={classes.glyph}>
          <Icon size={10} stroke={2.4} />
        </span>
      </span>
      <div className={classes.body}>
        <div className={classes.headline}>{view.headline}</div>
        {view.facts.length > 0 && (
          <div className={classes.facts}>
            {view.facts.map((fact) => (
              <span key={fact.key} className={classes.fact} data-tone={fact.tone}>
                {fact.text}
              </span>
            ))}
          </div>
        )}
      </div>
      {timestamp !== null && (
        <Tooltip label={formatAbsoluteTime(timestamp)} withArrow openDelay={300}>
          <time className={classes.time}>{formatRelativeTime(timestamp, now)}</time>
        </Tooltip>
      )}
    </div>
  );
}

function groupByRound(entries: ActivityEntry[]) {
  const groups: { round: number; phase: string; entries: ActivityEntry[] }[] = [];
  for (const entry of entries) {
    const last = groups.at(-1);
    if (last && last.round === entry.activity.round) {
      last.entries.push(entry);
    } else {
      groups.push({
        round: entry.activity.round,
        phase: entry.activity.phase,
        entries: [entry],
      });
    }
  }
  return groups;
}

function phaseName(phase: string): string {
  const words = phase.replace(/[._]+/g, " ").trim().toLowerCase();
  return words ? words[0].toUpperCase() + words.slice(1) : "";
}

/**
 * Feed „kto co zrobił": każda akcja gracza jako czytelny wpis (kto, co, gdzie,
 * jaki skutek). Najnowsze na górze, pogrupowane w rundy; filtry kategorii i
 * filtr po graczu. Dane liczy backend z różnicy migawek (core/activity.py).
 */
export function ActivityPanel() {
  const { data, isLoading, isError } = useActivityFeed();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [playerFilter, setPlayerFilter] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  const ctx = useActivityContext(data?.players);

  if (isLoading) {
    return (
      <div className={classes.state}>
        <Loader size="xs" color="gray" />
        <Text size="sm" c="dimmed">
          Loading activity…
        </Text>
      </div>
    );
  }
  if (isError || !data) {
    return (
      <Text className={classes.state} size="sm" c="dimmed">
        Couldn't load the activity feed.
      </Text>
    );
  }

  const visibleEntries = data.entries.filter(
    (e) => matches(e, filter) && (!playerFilter || e.activity.actor_id === playerFilter),
  );
  const counts = Object.fromEntries(
    FILTERS.map((f) => [f.key, data.entries.filter((e) => matches(e, f.key)).length]),
  ) as Record<FilterKey, number>;
  const grouped = groupByRound([...visibleEntries].reverse());
  const playerIds = Object.keys(data.players).filter((id) => data.players[id].faction);

  return (
    <div className={classes.root}>
      <div className={classes.filters} role="toolbar" aria-label="Filter activity">
        {FILTERS.filter((f) => f.key !== "admin" || counts.admin > 0).map((f) => (
          <button
            key={f.key}
            type="button"
            className={classes.chip}
            aria-pressed={filter === f.key}
            style={f.tone ? toneStyle(f.tone) : undefined}
            onClick={() => setFilter(f.key)}
          >
            {f.tone && <i aria-hidden="true" />}
            {f.label}
            <b>{counts[f.key]}</b>
          </button>
        ))}
      </div>
      {playerIds.length > 1 && (
        <div className={classes.players} role="toolbar" aria-label="Filter by player">
          {playerIds.map((id) => (
            <button
              key={id}
              type="button"
              className={classes.playerButton}
              aria-pressed={playerFilter === id}
              aria-label={displayName(id, data.players[id])}
              title={displayName(id, data.players[id])}
              onClick={() => setPlayerFilter((cur) => (cur === id ? null : id))}
            >
              <CircularFactionIcon faction={data.players[id].faction ?? ""} size={22} />
            </button>
          ))}
        </div>
      )}
      <div className={classes.list}>
        {grouped.length === 0 && (
          <p className={classes.empty}>
            {data.entries.length === 0
              ? "Nothing has happened yet. Player actions will show up here."
              : "No activity matches this filter."}
          </p>
        )}
        {grouped.map((group, groupIndex) => (
          <section key={`${group.round}-${groupIndex}`} aria-label={`Round ${group.round}`}>
            <div className={classes.band}>
              <b>Round {group.round}</b>
              <span className={classes.bandLabel}>{phaseName(group.phase)}</span>
              <span className={cx(classes.bandLabel, classes.bandEnd)}>
                {group.entries.length}
              </span>
            </div>
            {group.entries.map((entry) => (
              <Row
                key={entry.seq}
                entry={entry}
                ctx={ctx}
                now={now}
                undone={data.current_seq !== null && entry.seq > data.current_seq}
              />
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}

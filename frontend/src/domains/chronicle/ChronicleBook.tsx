import { useEffect, useMemo, useState, type ComponentType } from "react";
import cx from "clsx";
import {
  IconBolt,
  IconBook2,
  IconBuildingCastle,
  IconCards,
  IconChevronLeft,
  IconChevronRight,
  IconCompass,
  IconCrown,
  IconDiamond,
  IconFeather,
  IconFlag,
  IconFlame,
  IconFlask,
  IconGavel,
  IconHeartHandshake,
  IconHomeOff,
  IconPlanet,
  IconSkull,
  IconSparkles,
  IconSwords,
  IconTarget,
} from "@tabler/icons-react";
import { Modal } from "@/ds";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { ActivityPlayer } from "@/api/useBoardEditor";
import type { ChronicleChapter, ChronicleEntry } from "./buildChronicle";
import type { ChronicleKind } from "./chronicleLore";
import { useChronicle, useChronicleUnread } from "./useChronicle";
import { useChronicleStore } from "./useChronicleStore";
import classes from "./ChronicleBook.module.css";

type Glyph = ComponentType<{ size?: number; stroke?: number }>;

const KIND_ICON: Record<ChronicleKind, Glyph> = {
  prologue: IconBook2,
  battle: IconSwords,
  conquest: IconFlag,
  homeworld: IconHomeOff,
  settle: IconPlanet,
  score: IconTarget,
  law: IconGavel,
  agenda: IconGavel,
  tech: IconFlask,
  relic: IconDiamond,
  leader: IconCrown,
  hero: IconBolt,
  throne: IconBuildingCastle,
  fall: IconSkull,
  fracture: IconSparkles,
  supernova: IconFlame,
  deal: IconHeartHandshake,
  strategy: IconCards,
  explore: IconCompass,
  speaker: IconCrown,
  victory: IconCrown,
};

function Actors({ ids, players }: { ids: string[]; players: Record<string, ActivityPlayer> }) {
  const known = ids.filter((id) => players[id]?.faction);
  if (known.length === 0) return null;
  return (
    <span className={classes.actors}>
      {known.map((id) => (
        <span key={id} title={players[id].faction_name ?? players[id].display_name}>
          <CircularFactionIcon faction={players[id].faction ?? ""} size={22} />
        </span>
      ))}
    </span>
  );
}

function Entry({
  entry,
  players,
  showFacts,
}: {
  entry: ChronicleEntry;
  players: Record<string, ActivityPlayer>;
  showFacts: boolean;
}) {
  const [open, setOpen] = useState(false);
  const Icon = KIND_ICON[entry.kind];
  const expanded = showFacts || open;
  return (
    <article className={cx(classes.entry, entry.minor && classes.minor)} data-kind={entry.kind}>
      <span className={classes.node} aria-hidden="true">
        <Icon size={14} stroke={2} />
      </span>
      <header className={classes.entryHead}>
        <span className={classes.kind}>{entry.label}</span>
        {entry.place && <span className={classes.place}>{entry.place}</span>}
        <Actors ids={entry.actors} players={players} />
      </header>
      <p className={classes.text}>{entry.text}</p>
      {entry.epigraph && (
        <figure className={classes.epigraph}>
          <blockquote>“{entry.epigraph.text}”</blockquote>
          <figcaption>— {entry.epigraph.author}</figcaption>
        </figure>
      )}
      {entry.facts.length > 0 && (
        <div className={classes.factsBox}>
          <button
            type="button"
            className={classes.factsToggle}
            aria-expanded={expanded}
            onClick={() => setOpen((v) => !v)}
          >
            {expanded ? "Hide the facts" : "What exactly happened"}
          </button>
          {expanded && (
            <ul className={classes.facts}>
              {entry.facts.map((fact) => (
                <li key={fact}>{fact}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  );
}

function Page({
  chapter,
  players,
  majorOnly,
  showFacts,
}: {
  chapter: ChronicleChapter;
  players: Record<string, ActivityPlayer>;
  majorOnly: boolean;
  showFacts: boolean;
}) {
  const entries = chapter.entries.filter((e) => !majorOnly || !e.minor);
  return (
    <section className={classes.page} key={chapter.round} aria-label={chapter.title}>
      <h3 className={classes.chapterTitle}>{chapter.title}</h3>
      <figure className={classes.opener}>
        <blockquote>“{chapter.opener.text}”</blockquote>
        <figcaption>— {chapter.opener.author}</figcaption>
      </figure>
      {entries.length === 0 ? (
        <p className={classes.quiet}>
          This cycle passed quietly. Switch on “All events” to see the small things.
        </p>
      ) : (
        <div className={classes.timeline}>
          {entries.map((entry) => (
            <Entry key={entry.id} entry={entry} players={players} showFacts={showFacts} />
          ))}
        </div>
      )}
      {chapter.closing && (
        <footer className={classes.closing}>
          <p>{chapter.closing}</p>
          <div className={classes.standings}>
            {chapter.standings
              .filter((s) => players[s.playerId]?.faction)
              .map((s) => (
                <span key={s.playerId} className={classes.standing}>
                  <CircularFactionIcon faction={players[s.playerId].faction ?? ""} size={20} />
                  <b>{s.vp}</b>
                </span>
              ))}
          </div>
        </footer>
      )}
    </section>
  );
}

function Book() {
  const { chapters, players, isLoading } = useChronicle();
  const { markSeen } = useChronicleUnread(chapters);
  const [index, setIndex] = useState<number | null>(null);
  const [majorOnly, setMajorOnly] = useState(true);
  const [showFacts, setShowFacts] = useState(false);

  // Otwarcie księgi = uznanie wpisów za przeczytane; domyślnie ostatni rozdział.
  useEffect(() => {
    if (chapters.length > 0) markSeen();
  }, [chapters.length]);

  const current = Math.min(index ?? chapters.length - 1, chapters.length - 1);
  const chapter = chapters[current];
  const totals = useMemo(
    () => chapters.reduce((sum, c) => sum + c.entries.filter((e) => !e.minor).length, 0),
    [chapters],
  );

  if (isLoading) return <p className={classes.quiet}>Unrolling the scrolls…</p>;
  if (!chapter) {
    return (
      <p className={classes.quiet}>
        The pages are still blank. The first deeds of the houses will be written here.
      </p>
    );
  }
  return (
    <div className={classes.book}>
      <div className={classes.toolbar}>
        <button
          type="button"
          className={classes.nav}
          aria-label="Previous chapter"
          disabled={current === 0}
          onClick={() => setIndex(current - 1)}
        >
          <IconChevronLeft size={16} />
        </button>
        <div className={classes.chips} role="tablist" aria-label="Chapters">
          {chapters.map((c, i) => (
            <button
              key={c.round}
              type="button"
              role="tab"
              aria-selected={i === current}
              className={classes.chip}
              onClick={() => setIndex(i)}
            >
              {c.round}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={classes.nav}
          aria-label="Next chapter"
          disabled={current === chapters.length - 1}
          onClick={() => setIndex(current + 1)}
        >
          <IconChevronRight size={16} />
        </button>
        <span className={classes.spacer} />
        <label className={classes.toggle}>
          <input
            type="checkbox"
            checked={!majorOnly}
            onChange={(e) => setMajorOnly(!e.target.checked)}
          />
          All events
        </label>
        <label className={classes.toggle}>
          <input
            type="checkbox"
            checked={showFacts}
            onChange={(e) => setShowFacts(e.target.checked)}
          />
          Show all facts
        </label>
      </div>
      <Page chapter={chapter} players={players} majorOnly={majorOnly} showFacts={showFacts} />
      <p className={classes.colophon}>
        {totals} deeds recorded in {chapters.length} cycle{chapters.length === 1 ? "" : "s"}.
      </p>
    </div>
  );
}

/** Księga „Chronicle of the Empire”: lorowa opowieść o partii + suche fakty pod każdym wpisem. */
export function ChronicleBook() {
  const open = useChronicleStore((s) => s.open);
  const setOpen = useChronicleStore((s) => s.setOpen);
  return (
    <Modal
      opened={open}
      onClose={() => setOpen(false)}
      size={980}
      padding={0}
      title={
        <span className={classes.title}>
          <IconFeather size={18} /> Chronicle of the Empire
        </span>
      }
    >
      {open && <Book />}
    </Modal>
  );
}

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useDeckSearchStore } from "@/domains/search/deckSearchStore";
import { IconBug, IconFlame, IconStack2 } from "@tabler/icons-react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { AppModal } from "@/shared/ui/AppModal";
import { Cardback } from "@/shared/ui/Cardback/Cardback";
import { CardPoolBrowser } from "@/domains/cards/components/CardPoolBrowser/CardPoolBrowser";
import type { PoolEntry } from "@/domains/cards/model/cardPoolBrowser";
import {
  groupsForTab,
  pileCount,
  type DeckSpec,
  type PileTab,
} from "@/domains/cards/model/deckPiles";
import { useMoveCard, type MoveTarget } from "./useMoveCard";
import styles from "./DeckInspector.module.css";

const TAB_LABEL: Record<PileTab, string> = {
  deck: "In deck",
  discard: "Discard",
  purged: "Purged",
};

const DEBUG_KEY = "ce.deckDebug";

/** Tryb debug (przyciski przenoszenia kart) pamiętany między sesjami. */
export function useDebugMode(): [boolean, (on: boolean) => void] {
  const [on, setOn] = useState(() => {
    try {
      return window.localStorage.getItem(DEBUG_KEY) === "1";
    } catch {
      return false;
    }
  });
  const set = (value: boolean) => {
    setOn(value);
    try {
      window.localStorage.setItem(DEBUG_KEY, value ? "1" : "0");
    } catch {
      // brak localStorage - tryb działa do końca sesji
    }
  };
  return [on, set];
}

/** Ruchy debug dostępne dla karty w danej zakładce. */
const MOVES: Record<PileTab, { to: MoveTarget; label: string }[]> = {
  deck: [
    { to: "top", label: "Make next" },
    { to: "discard", label: "To discard" },
    { to: "purged", label: "Purge" },
  ],
  discard: [
    { to: "top", label: "Make next" },
    { to: "deck", label: "Back to deck" },
    { to: "purged", label: "Purge" },
  ],
  purged: [
    { to: "top", label: "Make next" },
    { to: "deck", label: "Back to deck" },
    { to: "discard", label: "To discard" },
  ],
};

type InspectorProps = {
  spec: DeckSpec;
  opened: boolean;
  onClose: () => void;
  initialTab?: PileTab;
};

/**
 * Zawartość jednej talii: karty w talii (z szansą dobrania każdej), stos odrzuconych i
 * stos purge. W trybie debug każda karta ma przyciski przenoszenia - w tym „Make next",
 * które ustawia, jaka karta zostanie dobrana jako następna.
 */
export function DeckInspector({ spec, opened, onClose, initialTab = "deck" }: InspectorProps) {
  const [tab, setTab] = useState<PileTab>(initialTab);
  const [debug, setDebug] = useDebugMode();
  const move = useMoveCard();
  const groups = useMemo(() => groupsForTab(spec, tab, debug), [spec, tab, debug]);

  const renderActions = debug
    ? (entry: PoolEntry) =>
        MOVES[tab].map((m) => (
          <button
            key={m.to}
            type="button"
            className={styles.moveBtn}
            disabled={!entry.ids?.length}
            onClick={() => entry.ids?.[0] && void move(entry.ids[0], m.to)}
          >
            {m.label}
          </button>
        ))
    : undefined;

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      size={880}
      title={
        <span className={styles.title}>
          {spec.label}
          <small>
            {pileCount(spec, "deck")} in deck · {pileCount(spec, "discard")} discarded ·{" "}
            {pileCount(spec, "purged")} purged
          </small>
        </span>
      }
    >
      <div className={styles.bar}>
        <div className={styles.tabs} role="tablist">
          {(Object.keys(TAB_LABEL) as PileTab[]).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              className={styles.tab}
              data-active={tab === t || undefined}
              onClick={() => setTab(t)}
            >
              {TAB_LABEL[t]} <b>{pileCount(spec, t)}</b>
            </button>
          ))}
        </div>
        <label className={styles.debug} title="Move cards between piles / pick the next card">
          <input
            type="checkbox"
            checked={debug}
            onChange={(e) => setDebug(e.target.checked)}
          />
          <IconBug size={14} aria-hidden="true" /> Debug
        </label>
      </div>
      {tab === "deck" && (
        <p className={styles.hint}>
          Cards still in the deck. The % on a card is the chance it is drawn next.
          {debug && " Debug: use “Make next” to decide what the next draw will be."}
        </p>
      )}
      {groups.length > 0 ? (
        <CardPoolBrowser groups={groups} renderActions={renderActions} deckId={spec.key} />
      ) : (
        <p className={styles.empty}>No cards here.</p>
      )}
    </AppModal>
  );
}

type BackProps = { spec: DeckSpec };

/** Rewers talii z liczbą kart, które w niej ZOSTAŁY; klik → zawartość talii. */
export function DeckBack({ spec }: BackProps) {
  const [opened, setOpened] = useState(false);
  const request = useDeckSearchStore((state) => state.request);
  const searchTab = request?.deckId === spec.key ? request.tab : undefined;
  /* Prośba z wyszukiwarki planszy otwiera tę talię na zakładce z szukaną kartą. */
  useEffect(() => {
    if (request?.deckId === spec.key) setOpened(true);
  }, [request, spec.key]);
  return (
    <>
      <button
        type="button"
        className={styles.trigger}
        onClick={() => setOpened(true)}
        aria-label={`${spec.label} deck, ${pileCount(spec, "deck")} cards left`}
      >
        <Cardback
          src={assetUrl(`/player_area/${spec.back}`)}
          alt={`${spec.label} deck`}
          count={pileCount(spec, "deck")}
        />
      </button>
      {opened && (
        <DeckInspector
          key={request?.nonce}
          spec={spec}
          opened
          initialTab={searchTab}
          onClose={() => setOpened(false)}
        />
      )}
    </>
  );
}

type PileProps = {
  spec: DeckSpec;
  tab: Exclude<PileTab, "deck">;
};

/** Stos odrzuconych / purge danej talii: karta z liczbą, klik → lista. */
export function PileSlot({ spec, tab }: PileProps) {
  const [opened, setOpened] = useState(false);
  const count = pileCount(spec, tab);
  return (
    <>
      <button
        type="button"
        className={styles.pile}
        data-kind={tab}
        data-empty={count === 0 || undefined}
        style={{ "--tone": spec.tone } as CSSProperties}
        onClick={() => setOpened(true)}
        aria-label={`${spec.label} ${TAB_LABEL[tab].toLowerCase()} pile, ${count} cards`}
      >
        {tab === "purged" ? (
          <IconFlame size={22} aria-hidden="true" />
        ) : (
          <IconStack2 size={22} aria-hidden="true" />
        )}
        <b>{count}</b>
      </button>
      {opened && (
        <DeckInspector spec={spec} opened initialTab={tab} onClose={() => setOpened(false)} />
      )}
    </>
  );
}

/** Wspólny stos PURGE: karty usunięte z gry ze WSZYSTKICH talii naraz (debug: ruchy kart). */
export function PurgedPile({ specs }: { specs: DeckSpec[] }) {
  const [opened, setOpened] = useState(false);
  const [debug, setDebug] = useDebugMode();
  const move = useMoveCard();
  const total = specs.reduce((n, s) => n + s.purged.length, 0);
  const groups = useMemo(
    () => specs.flatMap((s) => groupsForTab(s, "purged", false)),
    [specs],
  );
  const renderActions = debug
    ? (entry: PoolEntry) =>
        MOVES.purged.map((m) => (
          <button
            key={m.to}
            type="button"
            className={styles.moveBtn}
            disabled={!entry.ids?.length}
            onClick={() => entry.ids?.[0] && void move(entry.ids[0], m.to)}
          >
            {m.label}
          </button>
        ))
    : undefined;
  return (
    <>
      <button
        type="button"
        className={styles.pile}
        data-kind="purged"
        data-empty={total === 0 || undefined}
        onClick={() => setOpened(true)}
        aria-label={`Purged cards, ${total}`}
      >
        <IconFlame size={22} aria-hidden="true" />
        <b>{total}</b>
      </button>
      {opened && (
        <AppModal
          opened
          onClose={() => setOpened(false)}
          size={880}
          title={
            <span className={styles.title}>
              Purged cards
              <small>{total} removed from the game</small>
            </span>
          }
        >
          <div className={styles.bar}>
            <span className={styles.hint}>Purged cards never return to a deck.</span>
            <label className={styles.debug}>
              <input
                type="checkbox"
                checked={debug}
                onChange={(e) => setDebug(e.target.checked)}
              />
              <IconBug size={14} aria-hidden="true" /> Debug
            </label>
          </div>
          {groups.length > 0 ? (
            <CardPoolBrowser groups={groups} renderActions={renderActions} />
          ) : (
            <p className={styles.empty}>Nothing has been purged yet.</p>
          )}
        </AppModal>
      )}
    </>
  );
}

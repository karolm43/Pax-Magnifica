import { actionCards } from "@/entities/data/actionCards";
import { explorations } from "@/entities/data/explorations";
import { isOfficialSource } from "@/entities/data/officialSources";
import type { CardPoolData } from "@/entities/data/types";
import { actionCardPool, type PoolEntry, type PoolGroup } from "./cardPoolBrowser";

/*
 * Stan TALII w panelu General: co zostało w talii, co leży na stosie odrzuconych i co
 * purge'owano (RULES.md 46.4). Dane z `cardPool` (backend: core/deck_piles.py); karty
 * (nazwa, treść) ze statycznych danych frontendu po id.
 */

export type DeckKind = "explore" | "action";
export type PileTab = "deck" | "discard" | "purged";

export type DeckSpec = {
  /** Klucz talii: cultural / hazardous / industrial / frontier / action. */
  key: string;
  label: string;
  kind: DeckKind;
  /** Typ karty w danych eksploracji (Cultural...), tylko dla `explore`. */
  type?: string;
  /** Plik rewersu w /player_area/. */
  back: string;
  tone: string;
  deck: string[];
  discard: string[];
  purged: string[];
  /** Wierzch talii (tryb debug). */
  top?: string;
};

const exploreById = new Map(explorations.map((c) => [c.id, c]));
const actionByAlias = new Map(actionCards.map((c) => [c.alias, c]));

const TONE: Record<string, string> = {
  cultural: "var(--ds-sig-prop)",
  hazardous: "var(--ds-sig-war)",
  industrial: "var(--ds-sig-bio)",
  frontier: "var(--ds-sig-pn)",
  action: "var(--ds-sig-war)",
};

/** Id kart z `purged` należące do danej talii. */
function purgedOf(kind: DeckKind, key: string, purged: string[]): string[] {
  return purged.filter((id) =>
    kind === "explore"
      ? exploreById.get(id)?.type?.toLowerCase() === key
      : actionByAlias.has(id),
  );
}

const naturalCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

/**
 * Pozycje listy z id kart: identyczne karty (nazwa + treść) łączą się w jedną z liczbą
 * kopii; `chance` = kopie / `total` w % (gdy podano `total`).
 */
export function entriesFromIds(
  kind: DeckKind,
  ids: string[],
  total?: number,
  topId?: string,
): PoolEntry[] {
  const byCard = new Map<string, PoolEntry>();
  for (const id of ids) {
    const card = kind === "explore" ? exploreById.get(id) : actionByAlias.get(id);
    if (!card || !isOfficialSource(card.source)) continue;
    const key = `${card.name}\u0000${card.text}`;
    const existing = byCard.get(key);
    if (existing) {
      existing.copies = (existing.copies ?? 1) + 1;
      existing.ids = [...(existing.ids ?? []), id];
    } else {
      byCard.set(key, {
        alias: id,
        name: card.name,
        text: card.text,
        meta:
          kind === "explore"
            ? (card as { resolution?: string }).resolution
            : (card as { window?: string }).window,
        copies: 1,
        flavor: card.flavorText,
        ids: [id],
      });
    }
  }
  const entries = [...byCard.values()];
  for (const entry of entries) {
    if (total && total > 0) entry.chance = ((entry.copies ?? 1) / total) * 100;
    if (topId && entry.ids?.includes(topId)) entry.next = true;
  }
  return entries.sort((a, b) => naturalCollator.compare(a.name, b.name));
}

/** Specyfikacje talii (eksploracja + karty akcji) zbudowane z `cardPool`. */
export function deckSpecs(pool: CardPoolData): DeckSpec[] {
  const purged = pool.purgedCards ?? [];
  const top = pool.exploreTop ?? {};
  const explore = (
    key: "cultural" | "industrial" | "hazardous" | "frontier",
    label: string,
    type: string,
    deck: string[],
    discard: string[],
  ): DeckSpec => ({
    key,
    label,
    kind: "explore",
    type,
    back: `cardback_${key}.jpg`,
    tone: TONE[key],
    deck,
    discard,
    purged: purgedOf("explore", key, purged),
    top: top[key],
  });
  const actionDeck = pool.actionCardDeck ?? [];
  const actionDiscard = pool.actionCardDiscard ?? [];
  const actionPurged = purgedOf("action", "action", purged);
  return [
    explore("cultural", "Cultural", "Cultural", pool.culturalExploreDeck, pool.culturalExploreDiscard),
    explore("industrial", "Industrial", "Industrial", pool.industrialExploreDeck, pool.industrialExploreDiscard),
    explore("hazardous", "Hazardous", "Hazardous", pool.hazardousExploreDeck, pool.hazardousExploreDiscard),
    explore("frontier", "Frontier", "Frontier", pool.frontierExploreDeck, pool.frontierExploreDiscard),
    {
      key: "action",
      label: "Action",
      kind: "action",
      back: "cardback_action.jpg",
      tone: TONE.action,
      deck: actionDeck,
      discard: actionDiscard,
      purged: actionPurged,
    },
  ];
}

/** Liczba fizycznych kart w grupach (sumuje kopie). */
export function poolTotal(groups: PoolGroup[]): number {
  return groups.reduce(
    (sum, g) => sum + g.entries.reduce((n, e) => n + (e.copies ?? 1), 0),
    0,
  );
}

/**
 * Grupy do przeglądarki dla jednej zakładki. Talia, której stan gry jeszcze nie śledzi
 * (np. karty akcji przed setupem), pokazuje całą pulę - tak jak dotąd.
 */
export function groupsForTab(
  spec: DeckSpec,
  tab: PileTab,
  withTop: boolean,
): PoolGroup[] {
  const ids =
    tab === "deck" ? spec.deck : tab === "discard" ? spec.discard : spec.purged;
  const untracked =
    spec.kind === "action" &&
    spec.deck.length + spec.discard.length + spec.purged.length === 0;
  if (tab === "deck" && untracked) {
    return actionCardPool().map((g) => ({ ...g, title: `${spec.label} deck` }));
  }
  const title =
    tab === "deck" ? `${spec.label} deck` : tab === "discard" ? `${spec.label} discard` : `${spec.label} purged`;
  const entries = entriesFromIds(
    spec.kind,
    ids,
    tab === "deck" ? ids.length : undefined,
    tab === "deck" && withTop ? spec.top : undefined,
  );
  return entries.length > 0 ? [{ title, tone: spec.tone, entries }] : [];
}

/** Ile kart jest w danym stosie (do plakietek). */
export function pileCount(spec: DeckSpec, tab: PileTab): number {
  if (tab === "deck") {
    const untracked =
      spec.kind === "action" &&
      spec.deck.length + spec.discard.length + spec.purged.length === 0;
    return untracked ? poolTotal(actionCardPool()) : spec.deck.length;
  }
  return tab === "discard" ? spec.discard.length : spec.purged.length;
}

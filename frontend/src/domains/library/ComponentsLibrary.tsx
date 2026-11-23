/*
 * Biblioteka komponentów gry („Components” w menu głównym): wszystkie frakcje, karty
 * strategii, technologie ogólne, jednostki i KOMPLET talii (akcje, agendy, cele, relikty,
 * eksploracja, notki) — poza partią, bez stanu gry.
 *
 * Reużycie (CLAUDE.md „Spójność”): frakcja = `FactionSummary` z kreatora, talie =
 * `CardPoolBrowser` (to samo, co klik w rewers talii w grze), technologie =
 * `GeneralTechCatalog` (zakładka General w grze), karty strategii =
 * `StrategyCardDetailsCard`, jednostki = `UnitDetailsCard`.
 */
import { useMemo, useState, type ReactNode } from "react";
import { TextInput } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { useFactions, type FactionInfo } from "@/api/useNewGame";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import { FactionSummary } from "@/domains/setup/FactionSummary";
import {
  familyOfVariant,
  firstVariant,
  groupByExpansion,
  VARIANT_FAMILIES,
  VARIANT_LABEL,
  type FactionListEntry,
} from "@/domains/setup/factionVariants";
import { CardPoolBrowser } from "@/domains/cards/components/CardPoolBrowser/CardPoolBrowser";
import {
  actionCardPool,
  agendaPool,
  explorationPool,
  genericPromissoryPool,
  publicObjectivePool,
  relicPool,
  secretObjectivePool,
  type PoolGroup,
} from "@/domains/cards/model/cardPoolBrowser";
import { GeneralTechCatalog } from "@/domains/game-shell/components/GeneralTechCatalog";
import { StrategyCardDetailsCard } from "@/domains/cards/components/StrategyCardDetailsCard";
import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard";
import styles from "./ComponentsLibrary.module.css";

type DeckSectionId =
  | "action"
  | "agenda"
  | "public"
  | "secret"
  | "relic"
  | "exploration"
  | "promissory";
type SectionId = "factions" | "strategy" | "tech" | "units" | DeckSectionId;

/** Talie: pula kart z danych statycznych (aktywne źródła + moduły wariantów). */
const DECKS: Record<DeckSectionId, () => PoolGroup[]> = {
  action: actionCardPool,
  agenda: agendaPool,
  public: () => [...publicObjectivePool(1), ...publicObjectivePool(2)],
  secret: secretObjectivePool,
  relic: relicPool,
  exploration: () =>
    (["Cultural", "Industrial", "Hazardous", "Frontier"] as const).flatMap((t) =>
      explorationPool(t),
    ),
  promissory: genericPromissoryPool,
};

const NAV: { group: string; items: { id: SectionId; label: string }[] }[] = [
  { group: "Empires", items: [{ id: "factions", label: "Factions" }] },
  {
    group: "Table",
    items: [
      { id: "strategy", label: "Strategy cards" },
      { id: "tech", label: "Technologies" },
      { id: "units", label: "Units" },
    ],
  },
  {
    group: "Decks",
    items: [
      { id: "action", label: "Action cards" },
      { id: "agenda", label: "Agendas" },
      { id: "public", label: "Public objectives" },
      { id: "secret", label: "Secret objectives" },
      { id: "relic", label: "Relics" },
      { id: "exploration", label: "Exploration" },
      { id: "promissory", label: "Promissory notes" },
    ],
  },
];

/** Jednostki ogólne (wersje bazowe; ulepszenia są w Technologiach i na karcie jednostki). */
const GENERIC_UNITS = [
  "fighter",
  "infantry",
  "destroyer",
  "cruiser",
  "carrier",
  "dreadnought",
  "warsun",
  "pds",
  "spacedock",
];

const STRATEGY_INITIATIVES = [1, 2, 3, 4, 5, 6, 7, 8];

/** Liczba FIZYCZNYCH kart w grupach (sumuje kopie). */
function cardCount(groups: PoolGroup[]): number {
  return groups.reduce(
    (sum, g) => sum + g.entries.reduce((n, e) => n + (e.copies ?? 1), 0),
    0,
  );
}

/** Filtr talii po nazwie, tekście i metadanych karty. */
function filterGroups(groups: PoolGroup[], query: string): PoolGroup[] {
  const q = query.trim().toLowerCase();
  if (!q) return groups;
  return groups.map((g) => ({
    ...g,
    entries: g.entries.filter((e) =>
      [e.name, e.text, e.meta ?? ""].some((part) => part.toLowerCase().includes(q)),
    ),
  }));
}

function SectionHead({ title, hint }: { title: string; hint: string }) {
  return (
    <header className={styles.sectionHead}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      <p className={styles.sectionHint}>{hint}</p>
    </header>
  );
}

/** Frakcje: lista wg dodatków (jak w kreatorze) + pełny opis frakcji obok. */
function FactionsSection() {
  const { data: factions = [], isLoading, isError } = useFactions();
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const sections = useMemo(() => {
    const q = query.trim().toLowerCase();
    const sorted = [...factions]
      .sort((a, b) => a.name.localeCompare(b.name))
      .filter((f) => !q || f.name.toLowerCase().includes(q) || f.id.includes(q));
    return groupByExpansion(sorted);
  }, [factions, query]);

  const byId = useMemo(() => new Map(factions.map((f) => [f.id, f])), [factions]);
  const selected: FactionInfo | null =
    (selectedId ? byId.get(selectedId) : null) ?? null;

  const family = selectedId ? familyOfVariant(selectedId) : null;
  const variantSwitch =
    family && selectedId
      ? {
          variants: (VARIANT_FAMILIES[family] ?? []).map((id) => ({
            id,
            label: VARIANT_LABEL[id] ?? id,
          })),
          currentId: selectedId,
          onSelect: setSelectedId,
        }
      : undefined;

  const renderEntry = (entry: FactionListEntry) => {
    const id = entry.kind === "family" ? firstVariant(entry.family) : entry.faction.id;
    const label = entry.kind === "family" ? entry.label : entry.faction.name;
    const active =
      selectedId !== null &&
      (entry.kind === "family"
        ? familyOfVariant(selectedId) === entry.family
        : selectedId === id);
    return (
      <button
        key={entry.kind === "family" ? entry.family : id}
        type="button"
        role="option"
        aria-selected={active}
        className={`${styles.factionItem} ${active ? styles.factionItemActive : ""}`}
        onClick={() => setSelectedId(id)}
      >
        <CircularFactionIcon faction={id} size={22} />
        <span>{label}</span>
      </button>
    );
  };

  return (
    <div className={styles.factions}>
      <div className={styles.factionList}>
        <TextInput
          placeholder="Search factions…"
          aria-label="Search factions"
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
        />
        {isLoading && <p className={styles.empty}>Loading factions…</p>}
        {isError && <p className={styles.empty}>Failed to load factions from the server.</p>}
        <div role="listbox" aria-label="Factions" className={styles.factionScroll}>
          {sections.map((section) => (
            <div key={section.group} role="group" aria-label={section.label}>
              <div className={styles.factionGroup}>{section.label}</div>
              {section.entries.map(renderEntry)}
            </div>
          ))}
        </div>
      </div>
      <div className={styles.factionDetail} key={selected?.id ?? "none"}>
        <FactionSummary faction={selected} variantSwitch={variantSwitch} />
      </div>
    </div>
  );
}

function DeckSection({ id, title }: { id: DeckSectionId; title: string }) {
  const groups = useMemo(() => DECKS[id](), [id]);
  const [query, setQuery] = useState("");
  const visible = filterGroups(groups, query);
  const shown = cardCount(visible);
  return (
    <>
      <SectionHead
        title={title}
        hint={`${cardCount(groups)} cards in the deck. Copies of the same card are shown once with a ×N count.`}
      />
      <TextInput
        className={styles.search}
        placeholder={`Search ${title.toLowerCase()}…`}
        aria-label={`Search ${title.toLowerCase()}`}
        value={query}
        onChange={(e) => setQuery(e.currentTarget.value)}
      />
      {shown === 0 ? (
        <p className={styles.empty}>No cards match “{query}”.</p>
      ) : (
        <CardPoolBrowser groups={visible} />
      )}
    </>
  );
}

function SectionBody({ id, label }: { id: SectionId; label: string }): ReactNode {
  switch (id) {
    case "factions":
      return (
        <>
          <SectionHead
            title="Factions"
            hint="Every playable faction: abilities, technologies, leaders, units, promissory note and starting setup."
          />
          <FactionsSection />
        </>
      );
    case "strategy":
      return (
        <>
          <SectionHead
            title="Strategy cards"
            hint="Primary ability for the player who holds the card, secondary for everyone else (costs a strategy token)."
          />
          <div className={styles.cardGrid}>
            {STRATEGY_INITIATIVES.map((n) => (
              <StrategyCardDetailsCard key={n} initiative={n} fluid />
            ))}
          </div>
        </>
      );
    case "tech":
      return (
        <>
          <SectionHead
            title="Technologies"
            hint="Generic technologies by colour, then unit upgrades. Faction technologies are listed under each faction."
          />
          <GeneralTechCatalog playerData={[]} />
        </>
      );
    case "units":
      return (
        <>
          <SectionHead
            title="Units"
            hint="Base units every faction starts with. Faction units (flagship, mech, special units) are listed under each faction."
          />
          <div className={styles.unitGrid}>
            {GENERIC_UNITS.map((unitId) => (
              <UnitDetailsCard key={unitId} unitId={unitId} />
            ))}
          </div>
        </>
      );
    default:
      return <DeckSection key={id} id={id} title={label} />;
  }
}

type Props = { opened: boolean; onClose: () => void };

/** Okno biblioteki komponentów: nawigacja sekcji po lewej, treść po prawej. */
export function ComponentsLibrary({ opened, onClose }: Props) {
  const [section, setSection] = useState<SectionId>("factions");
  const counts = useMemo(() => {
    const result: Partial<Record<SectionId, number>> = {};
    for (const id of Object.keys(DECKS) as DeckSectionId[]) {
      result[id] = cardCount(DECKS[id]());
    }
    return result;
  }, []);
  const label =
    NAV.flatMap((g) => g.items).find((item) => item.id === section)?.label ?? "";

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title="Components"
      size="min(1360px, 96vw)"
      centered
    >
      <div className={styles.layout}>
        <nav className={styles.nav} aria-label="Component categories">
          {NAV.map((group) => (
            <div key={group.group} className={styles.navGroup}>
              <span className={styles.navGroupLabel}>{group.group}</span>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-current={section === item.id ? "page" : undefined}
                  className={`${styles.navItem} ${section === item.id ? styles.navItemActive : ""}`}
                  onClick={() => setSection(item.id)}
                >
                  <span>{item.label}</span>
                  {counts[item.id] !== undefined && (
                    <span className={styles.navCount}>{counts[item.id]}</span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className={styles.content}>
          <SectionBody id={section} label={label} />
        </div>
      </div>
    </AppModal>
  );
}

// Podgląd wybranej frakcji na ekranie setupu (faction summary).
//
// Panel główny: prosty nagłówek (lokalna ikona frakcji + nazwa + cytat + złożoność) oraz
// bogate dane — zdolności, przełom (breakthrough), technologie frakcyjne, liderzy, weksel,
// WSZYSTKIE jednostki frakcyjne, dane startu z PEŁNYMI nazwami i planety z resource/influence.
//
// Portret POSTACI + lore żyją w OSOBNYM komponencie `LorePanel`, renderowanym przez
// `Step_Faction` jako WYSUWANA kolumna obok panelu (styl „wybór frakcji w grze", np.
// Endless Legend: duży portret jako tło + nazwa na dole + lore pod spodem). `FactionSummary`
// steruje tylko przełącznikiem (`onToggleLore`) i zgłasza, KTÓRĄ frakcję pokazać w panelu
// lore (`onActiveFactionChange`) — bo widok pochodnej (Obsidian) zmienia aktywną frakcję.
//
// Edge-case Firmament → Obsidian: Obsidian to „druga frakcja" Firmamentu (rozwinięcie),
// niewybieralna przy setupie, ale wchodząca do gry przez akcję Firmamentu. Dla Firmamentu
// pokazujemy przycisk „Zobacz Obsidian", który dociąga i renderuje summary Obsidiana
// (osobny endpoint /factions/{id}).
//
// Reużywa komponenty panelu gracza (`Ability`, `Tech`, `LeaderChip`, `PromissoryNote`,
// `Breakthrough`, `UnitDetailsCard`) — identyfikatory rozwiązywane po danych AsyncTI4,
// spójnie z grą. Działa na etapie setupu (hooki stanu gry degradują do undefined).

import { useEffect, useMemo, useState } from "react";
import { Button, MultiSelect, Stack, Text } from "@/ds";
import { IconArrowLeft, IconBook, IconChevronRight } from "@tabler/icons-react";
import { type FactionInfo, useFaction } from "@/api/useNewGame";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { Ability } from "@/domains/player/components/Ability";
import { Tech } from "@/domains/player/components/Tech";
import { LeaderChip } from "@/domains/player/components/Leader/LeaderChip";
import { PromissoryNote } from "@/domains/player/components/PromissoryNote";
import { Breakthrough } from "@/domains/player/components/Breakthrough/Breakthrough";
import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard/UnitDetailsCard";
import { Unit } from "@/shared/ui/Unit";
import { getLeaderById } from "@/entities/lookup/leaders";
import { getUnitData } from "@/entities/lookup/units";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTechData } from "@/entities/lookup/tech";
import { getPlanetData } from "@/entities/lookup/planets";
import { useDisclosure } from "@/hooks/useDisclosure";
import {
  defaultPortraitCandidates,
  getFactionLore,
  loreToBlocks,
} from "./factionLore";
import styles from "./FactionSummary.module.css";

/** Kolejność slotów liderów — jak w panelu gracza (agent → commander → hero). */
const LEADER_ORDER = ["agent", "commander", "hero"] as const;

/**
 * Mapa „frakcja → jej frakcja pochodna" (rozwinięcie, osobny komplet komponentów).
 * Jedyny przypadek: Firmament → Obsidian (Thunder's Edge). Obsidian nie jest wybieralny,
 * ale gracz może go podejrzeć. Rozszerzalna, gdyby doszły kolejne takie pary.
 */
const DERIVED_FACTION: Record<string, string> = {
  firmament: "obsidian",
};

/** Usuwa końcówkę poziomu z nazwy jednostki bazowej („Carrier I" → „Carrier"). */
function cleanUnitName(name: string): string {
  return name.replace(/\s+I$/i, "").trim();
}

/** Pełna nazwa typu jednostki (generyczna baza) po `base_type` — bez surowych kodów. */
function unitTypeName(baseType: string): string {
  const data = getUnitData(baseType);
  return data ? cleanUnitName(data.name) : baseType;
}

/** Sekcja summary z nagłówkiem i treścią. */
function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.section}>
      <Text className={styles.sectionTitle}>{title}</Text>
      <div className={styles.sectionBody}>{children}</div>
    </div>
  );
}

/** Id lidera-bohatera (hero) frakcji — do domyślnego portretu, gdy brak własnego pliku. */
function heroLeaderId(faction: FactionInfo): string | undefined {
  return faction.leaders.find((id) => getLeaderById(id)?.type === "hero");
}

/**
 * Duży portret postaci do panelu lore. Łańcuch źródeł LOKALNYCH (pierwsze istniejące):
 *   1. własny plik gracza `/faction_portraits/<id>.{png,jpg,jpeg,webp}` (lub `lore.portrait`),
 *   2. portret BOHATERA frakcji `/leaders/<heroId>.webp`,
 *   3. lokalna ikona frakcji `/static/factions/<id>.png` (placeholder).
 * Bez zewnętrznego CDN. Degraduje bez błędu (onError → następne źródło).
 */
function LeaderPortrait({ faction }: { faction: FactionInfo }) {
  const lore = getFactionLore(faction.id);
  const candidates = useMemo(() => {
    const own = lore?.portrait
      ? [lore.portrait]
      : defaultPortraitCandidates(faction.id);
    const hero = heroLeaderId(faction);
    return [
      ...own,
      ...(hero ? [`/leaders/${hero}.webp`] : []),
      `/static/factions/${faction.id}.png`,
    ];
  }, [faction, lore?.portrait]);

  const [index, setIndex] = useState(0);
  // Reset źródła przy zmianie frakcji (inaczej zostałby wyczerpany index).
  useEffect(() => setIndex(0), [candidates]);
  const exhausted = index >= candidates.length;

  if (exhausted) {
    return (
      <div className={styles.portraitFallback}>
        <Text size="xs" c="dimmed" ta="center">
          Brak portretu — dodaj plik do /faction_portraits/{faction.id}.png
        </Text>
      </div>
    );
  }
  return (
    <img
      key={candidates[index]}
      src={candidates[index]}
      alt={`Portret: ${faction.name}`}
      className={styles.portrait}
      onError={() => setIndex((i) => i + 1)}
    />
  );
}

/** Renderuje lore jako bloki (akapit / śródtytuł / cytat) z własnymi stylami. */
function LoreBlocks({ faction }: { faction: FactionInfo }) {
  const blocks = loreToBlocks(getFactionLore(faction.id)?.lore);
  if (blocks.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Brak lore — uzupełnij w factionLore.ts (klucz „{faction.id}").
      </Text>
    );
  }
  return (
    <div className={styles.lore}>
      {blocks.map((block, i) => {
        if (block.kind === "heading") {
          return (
            <h4 key={i} className={styles.loreHeading}>
              {block.text}
            </h4>
          );
        }
        if (block.kind === "quote") {
          return (
            <blockquote key={i} className={styles.loreQuote}>
              {block.text}
            </blockquote>
          );
        }
        return (
          <p key={i} className={styles.loreParagraph}>
            {block.text}
          </p>
        );
      })}
    </div>
  );
}

/**
 * Kolumna „postać" (prawa, styl wyboru frakcji w grze): DUŻY portret PNG bez tła,
 * wtopiony w stronę (brak ramki/boxa) — stoi na wspólnym tle z poświatą. Pod nazwą
 * przycisk „Pokaż / Ukryj lore"; lore jest DOMYŚLNIE UKRYTE i rozwija się pod portretem.
 * Portret pojawia się z animacją przy KAŻDEJ zmianie frakcji (`key` resetuje animację).
 */
export function LorePanel({
  faction,
  loreOpen = false,
  onToggleLore,
}: {
  faction: FactionInfo | null;
  loreOpen?: boolean;
  onToggleLore?: () => void;
}) {
  if (!faction) return null;
  const quote = getFactionLore(faction.id)?.quote;
  const hasLore = loreToBlocks(getFactionLore(faction.id)?.lore).length > 0;
  return (
    <div className={styles.character} key={faction.id}>
      {/* Duży portret PNG (przezroczyste tło) wtopiony w poświatę — bez boxa. */}
      <div className={styles.portraitStage}>
        <LeaderPortrait faction={faction} />
      </div>

      <div className={styles.characterCaption}>
        <Text className={styles.characterName}>{faction.name}</Text>
        {quote && <p className={styles.characterQuote}>„{quote}”</p>}
        {onToggleLore && (
          <Button
            variant="subtle"
            size="xs"
            leftSection={<IconBook size={14} />}
            onClick={onToggleLore}
            className={styles.loreToggle}
          >
            {loreOpen ? "Ukryj lore" : "Pokaż lore"}
          </Button>
        )}
      </div>

      {/* Lore — domyślnie ukryte; rozwija się pod portretem. */}
      <div
        className={`${styles.loreReveal} ${loreOpen ? styles.loreRevealOpen : ""}`}
        aria-hidden={!loreOpen}
      >
        {hasLore ? (
          <LoreBlocks faction={faction} />
        ) : (
          <Text size="sm" c="dimmed">
            Brak lore — uzupełnij w factionLore.ts (klucz „{faction.id}").
          </Text>
        )}
      </div>
    </div>
  );
}

/** Pojedyncza jednostka frakcyjna: sprite (neutralny kolor) + podgląd `UnitDetailsCard`. */
function FactionUnit({ unitId }: { unitId: string }) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const unitData = getUnitData(unitId);
  if (!unitData) return null;

  const label = cleanUnitName(unitData.name || unitData.baseType);

  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.unitChip}
          onClick={toggle}
          title={label}
        >
          <span className={styles.unitSprite}>
            <Unit
              unitType={unitData.asyncId}
              colorAlias={getColorAlias(undefined)}
              faction={unitData.faction}
              scaleSprite
              showFactionTokens={false}
            />
          </span>
          <span className={styles.unitName}>{label}</span>
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <UnitDetailsCard unitId={unitId} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

/** Wbudowany wybór technologii startowych (zastępuje osobny krok kreatora). */
function StartingTechChoice({
  faction,
  value,
  onChange,
}: {
  faction: FactionInfo;
  value: string[];
  onChange: (techs: string[]) => void;
}) {
  const amount = faction.starting_tech_amount;
  const options = faction.starting_tech_options.map((alias) => ({
    value: alias,
    label: getTechData(alias)?.name ?? alias,
  }));
  return (
    <Stack gap={4}>
      <MultiSelect
        label={`Technologie startowe (wybierz ${amount})`}
        placeholder={`Wybierz ${amount}`}
        data={options}
        value={value}
        onChange={(next) =>
          onChange(next.length > amount ? next.slice(next.length - amount) : next)
        }
      />
      <Text size="xs" c={value.length === amount ? "dimmed" : "red"}>
        Wybrano {value.length} z {amount}.
      </Text>
    </Stack>
  );
}

/** Lista planet startowych z ich wartościami resource / influence. */
function PlanetList({ planetIds }: { planetIds: string[] }) {
  return (
    <ul className={styles.planetList}>
      {planetIds.map((id) => {
        const data = getPlanetData(id);
        const name = data?.name ?? id;
        return (
          <li key={id} className={styles.planetItem}>
            <span className={styles.planetName}>{name}</span>
            <span className={styles.planetValues}>
              <span className={`${styles.pval} ${styles.pvalRes}`}>
                {data?.resources ?? "?"}
              </span>
              <span className={`${styles.pval} ${styles.pvalInf}`}>
                {data?.influence ?? "?"}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export interface FactionSummaryProps {
  faction: FactionInfo | null;
  /** Akcje pod summary (np. przycisk „Wybierz dla gracza N"). */
  footer?: React.ReactNode;
  /**
   * Wybór technologii startowych — pokazywany TYLKO gdy frakcja wymaga wyboru
   * i podana jest para value/onChange (frakcja przypisana aktywnemu graczowi).
   */
  startingTech?: {
    value: string[];
    onChange: (techs: string[]) => void;
  };
  /**
   * Zgłasza, KTÓRĄ frakcję pokazywać w kolumnie postaci/lore (zmienia się przy
   * wejściu/wyjściu w podgląd pochodnej — Obsidian). `Step_Faction` renderuje `LorePanel`.
   */
  onActiveFactionChange?: (faction: FactionInfo | null) => void;
}

/**
 * Środkowy panel szczegółów frakcji (nazwa + umiejętności + dane). Zarządza podglądem
 * frakcji pochodnej (Firmament → Obsidian) i zgłasza aktywną frakcję w górę, by
 * `Step_Faction` pokazał jej portret/lore w prawej kolumnie.
 */
export function FactionSummary({
  faction,
  footer,
  startingTech,
  onActiveFactionChange,
}: FactionSummaryProps) {
  // Id frakcji pochodnej aktualnie oglądanej (np. "obsidian") albo null.
  const [derivedId, setDerivedId] = useState<string | null>(null);
  const derived = useFaction(derivedId);

  // Aktualnie pokazywana frakcja (bazowa albo pochodna). Zgłaszamy ją w górę, by
  // `Step_Faction` pokazał właściwą postać/lore w wysuwanej kolumnie.
  const activeFaction = derivedId ? derived.data ?? null : faction;
  const activeFactionId = activeFaction?.id ?? null;
  useEffect(() => {
    // Zależność po id (stabilne), nie po obiekcie `activeFaction`.
    onActiveFactionChange?.(activeFaction ?? null);
  }, [activeFactionId, activeFaction, onActiveFactionChange]);

  // Reset podglądu pochodnej, gdy zmieni się frakcja bazowa.
  useEffect(() => {
    setDerivedId(null);
  }, [faction?.id]);

  if (!faction) {
    return (
      <div className={styles.emptyState}>
        <Text c="dimmed" ta="center">
          Kliknij frakcję z galerii, aby zobaczyć jej zdolności, technologie, liderów
          i jednostki. Przycisk „Postać i lore" wysunie panel z portretem.
        </Text>
      </div>
    );
  }

  // Widok frakcji pochodnej (Obsidian) — bez footera/techów (nie jest wybieralna).
  if (derivedId) {
    return (
      <div className={styles.summary}>
        <Button
          variant="subtle"
          size="sm"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => setDerivedId(null)}
          className={styles.backButton}
        >
          Wróć do {faction.name}
        </Button>
        {derived.isLoading && <Text c="dimmed">Ładowanie…</Text>}
        {derived.isError && (
          <Text c="red">Nie udało się wczytać danych frakcji.</Text>
        )}
        {derived.data && <SummaryBody faction={derived.data} />}
      </div>
    );
  }

  const derivedFactionId = DERIVED_FACTION[faction.id] ?? null;

  return (
    <div className={styles.summary}>
      <SummaryBody
        faction={faction}
        startingTech={startingTech}
        derivedFactionId={derivedFactionId}
        onViewDerived={() => setDerivedId(derivedFactionId)}
      />
      {footer && <div className={styles.footer}>{footer}</div>}
    </div>
  );
}

/** Treść podglądu jednej frakcji (bez zarządzania stanem pochodnej). */
function SummaryBody({
  faction,
  startingTech,
  derivedFactionId,
  onViewDerived,
}: {
  faction: FactionInfo;
  startingTech?: FactionSummaryProps["startingTech"];
  derivedFactionId?: string | null;
  onViewDerived?: () => void;
}) {
  // Liderzy w kanonicznej kolejności (agent → commander → hero), reszta na końcu.
  const leadersByType = (type: string) =>
    faction.leaders.filter((id) => getLeaderById(id)?.type === type);
  const orderedLeaders = [
    ...LEADER_ORDER.flatMap((type) => leadersByType(type)),
    ...faction.leaders.filter(
      (id) => !LEADER_ORDER.includes(getLeaderById(id)?.type as never),
    ),
  ];

  // Jednostki frakcyjne = warianty specyficzne dla frakcji (mają pole `faction`).
  const factionUnits = faction.units.filter(
    (id) => getUnitData(id)?.faction !== undefined,
  );

  // Flota startowa z pełnymi nazwami; łączymy pozycje tego samego typu.
  const fleetByType = new Map<string, number>();
  for (const u of faction.starting_units) {
    fleetByType.set(u.base_type, (fleetByType.get(u.base_type) ?? 0) + u.count);
  }
  const fleetSummary = [...fleetByType.entries()]
    .map(([baseType, count]) => `${count}× ${unitTypeName(baseType)}`)
    .join(", ");

  const requiresTechChoice = faction.starting_tech_amount > 0;

  return (
    <>
      {/* Prosty nagłówek: lokalna ikona frakcji + nazwa + złożoność + akcje. */}
      <div className={`${styles.header} ${styles.fadeIn}`} key={faction.id}>
        <img
          src={`/static/factions/${faction.id}.png`}
          alt=""
          className={styles.headerIcon}
          onError={(e) => {
            e.currentTarget.style.visibility = "hidden";
          }}
        />
        <div className={styles.headerText}>
          <Text className={styles.factionName}>{faction.name}</Text>
          {getFactionLore(faction.id)?.quote && (
            <Text className={styles.headerQuote}>
              „{getFactionLore(faction.id)?.quote}”
            </Text>
          )}
          {faction.complexity && (
            <Text className={styles.complexity}>
              Złożoność: {faction.complexity}
            </Text>
          )}
        </div>
        {derivedFactionId && onViewDerived && (
          <div className={styles.headerActions}>
            <Button
              variant="light"
              size="xs"
              rightSection={<IconChevronRight size={14} />}
              onClick={onViewDerived}
            >
              Zobacz Obsidian
            </Button>
          </div>
        )}
      </div>

      <Stack gap="md" className={styles.sections}>
        {faction.abilities.length > 0 && (
          <Section title="Zdolności frakcji">
            <div className={styles.chipRow}>
              {faction.abilities.map((id) => (
                <Ability key={id} id={id} />
              ))}
            </div>
          </Section>
        )}

        {faction.breakthrough && (
          <Section title="Przełom (breakthrough)">
            <div className={styles.chipRow}>
              <Breakthrough breakthroughId={faction.breakthrough} unlocked />
            </div>
          </Section>
        )}

        {faction.faction_tech.length > 0 && (
          <Section title="Technologie frakcyjne">
            <div className={styles.chipRow}>
              {faction.faction_tech.map((id) => (
                <Tech key={id} techId={id} unresearched />
              ))}
            </div>
          </Section>
        )}

        {factionUnits.length > 0 && (
          <Section title="Jednostki frakcyjne">
            <div className={styles.unitRow}>
              {factionUnits.map((id) => (
                <FactionUnit key={id} unitId={id} />
              ))}
            </div>
          </Section>
        )}

        {orderedLeaders.length > 0 && (
          <Section title="Liderzy">
            <div className={styles.leaderGrid}>
              {orderedLeaders.map((id) => {
                const data = getLeaderById(id);
                const type = (data?.type ?? "agent") as
                  | "agent"
                  | "commander"
                  | "hero";
                return (
                  <LeaderChip
                    key={id}
                    id={id}
                    type={type}
                    exhausted={false}
                    locked={type !== "agent"}
                    active={false}
                  />
                );
              })}
            </div>
          </Section>
        )}

        {faction.promissory_notes.length > 0 && (
          <Section title="Weksel frakcji">
            <div className={styles.chipRow}>
              {faction.promissory_notes.map((id) => (
                <PromissoryNote key={id} promissoryNoteId={id} />
              ))}
            </div>
          </Section>
        )}

        <Section title="Start gry">
          <dl className={styles.startList}>
            {requiresTechChoice ? (
              <div className={styles.startRowFull}>
                <dt>Technologie startowe</dt>
                <dd>
                  {startingTech ? (
                    <StartingTechChoice
                      faction={faction}
                      value={startingTech.value}
                      onChange={startingTech.onChange}
                    />
                  ) : (
                    <Text size="sm" c="dimmed">
                      Ta frakcja wybiera {faction.starting_tech_amount} technologii.
                      Przypisz ją graczowi (przycisk niżej), by wybrać.
                    </Text>
                  )}
                </dd>
              </div>
            ) : (
              faction.starting_tech.length > 0 && (
                <div className={styles.startRowFull}>
                  <dt>Technologie startowe</dt>
                  <dd className={styles.startChips}>
                    {faction.starting_tech.map((id) => (
                      <Tech key={id} techId={id} />
                    ))}
                  </dd>
                </div>
              )
            )}
            {faction.home_planets.length > 0 && (
              <div className={styles.startRowFull}>
                <dt>Planety</dt>
                <dd>
                  <PlanetList planetIds={faction.home_planets} />
                </dd>
              </div>
            )}
            {fleetSummary && (
              <div className={styles.startRow}>
                <dt>Flota startowa</dt>
                <dd>{fleetSummary}</dd>
              </div>
            )}
            <div className={styles.startRow}>
              <dt>Towary (commodities)</dt>
              <dd>{faction.commodities}</dd>
            </div>
          </dl>
        </Section>
      </Stack>
    </>
  );
}

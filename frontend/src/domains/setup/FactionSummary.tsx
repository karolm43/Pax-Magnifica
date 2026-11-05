// Podgląd wybranej frakcji na ekranie setupu (faction summary).
//
// Panel środkowy sceny: prosty nagłówek (lokalna ikona frakcji + nazwa + złożoność) oraz
// bogate dane — zdolności, przełom (breakthrough), technologie frakcyjne, liderzy, weksel,
// WSZYSTKIE jednostki frakcyjne, dane startu z PEŁNYMI nazwami i planety z resource/influence.
//
// Portret POSTACI + lore żyją w `FactionBackdrop.tsx` (warstwy sceny rysowane przez
// `Step_Faction`). `FactionSummary` zgłasza tylko, KTÓRĄ frakcję pokazać na scenie
// (`onActiveFactionChange`) — bo widok pochodnej (Obsidian) zmienia aktywną frakcję.
//
// Edge-case Firmament → Obsidian: Obsidian to „druga frakcja" Firmamentu (rozwinięcie),
// niewybieralna przy setupie, ale wchodząca do gry przez akcję Firmamentu. Dla Firmamentu
// pokazujemy przycisk „View Obsidian", który dociąga i renderuje summary Obsidiana
// (osobny endpoint /factions/{id}).
//
// Reużywa komponenty panelu gracza (`Ability`, `Tech`, `LeaderChip`, `PromissoryNote`,
// `Breakthrough`, `UnitDetailsCard`) — identyfikatory rozwiązywane po danych AsyncTI4,
// spójnie z grą. Działa na etapie setupu (hooki stanu gry degradują do undefined).

import { useEffect, useState } from "react";
import { Button, MultiSelect, Stack, Text } from "@/ds";
import { IconArrowLeft, IconChevronRight } from "@tabler/icons-react";
import { type FactionInfo, useFaction } from "@/api/useNewGame";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { Ability } from "@/domains/player/components/Ability";
import { Tech } from "@/domains/player/components/Tech";
import { LeaderChip } from "@/domains/player/components/Leader/LeaderChip";
import { PromissoryNote } from "@/domains/player/components/PromissoryNote";
import { Breakthrough } from "@/domains/player/components/Breakthrough/Breakthrough";
import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard/UnitDetailsCard";
import { PlanetDetailsCard } from "@/domains/cards/components/PlanetDetailsCard";
import { Unit } from "@/shared/ui/Unit";
import { getLeaderById } from "@/entities/lookup/leaders";
import { getUnitData } from "@/entities/lookup/units";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTechData } from "@/entities/lookup/tech";
import { getPlanetData } from "@/entities/lookup/planets";
import { useDisclosure } from "@/hooks/useDisclosure";
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

/**
 * Mała ikonka jednostki floty startowej (generyczny typ, neutralny kolor). Renderuje
 * ten sam sprite co lista jednostek frakcyjnych, ale w mniejszym, stałej wysokości boxie.
 * Gdy typ nie ma danych sprite'a, nie rysuje nic (nie psuje chipa).
 */
function FleetUnitIcon({ baseType }: { baseType: string }) {
  const unitData = getUnitData(baseType);
  if (!unitData) return null;
  return (
    <span className={styles.fleetSprite} aria-hidden>
      <Unit
        unitType={unitData.asyncId}
        colorAlias={getColorAlias(undefined)}
        faction={unitData.faction}
        scaleSprite
        showFactionTokens={false}
      />
    </span>
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
        label={`Starting technologies (choose ${amount})`}
        placeholder={`Choose ${amount}`}
        data={options}
        value={value}
        onChange={(next) =>
          onChange(next.length > amount ? next.slice(next.length - amount) : next)
        }
      />
      <Text size="xs" c={value.length === amount ? "dimmed" : "red"}>
        Chosen {value.length} of {amount}.
      </Text>
    </Stack>
  );
}

/**
 * Jedna planeta startowa — klikalny wiersz, który w popoverze pokazuje pełną kartę
 * planety (`PlanetDetailsCard`: nazwa, typ/„Faction homeworld", resources/influence,
 * tech-skip, opis). Ta sama karta co w grze (po kliknięciu w planetę na mapie).
 */
function PlanetItem({ planetId }: { planetId: string }) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const data = getPlanetData(planetId);
  const name = data?.name ?? planetId;
  return (
    <li className={styles.planetItem}>
      <SmoothPopover opened={opened} onChange={setOpened}>
        <SmoothPopover.Target>
          <button
            type="button"
            className={styles.planetRow}
            onClick={toggle}
            title={`Show details for ${name}`}
          >
            <span className={styles.planetName}>{name}</span>
            <span className={styles.planetValues}>
              <span className={`${styles.pval} ${styles.pvalRes}`}>
                {data?.resources ?? "?"}
              </span>
              <span className={`${styles.pval} ${styles.pvalInf}`}>
                {data?.influence ?? "?"}
              </span>
            </span>
          </button>
        </SmoothPopover.Target>
        <SmoothPopover.Dropdown p={0}>
          <PlanetDetailsCard planetId={planetId} />
        </SmoothPopover.Dropdown>
      </SmoothPopover>
    </li>
  );
}

/** Lista planet startowych — każda klikalna, z kartą szczegółów w popoverze. */
function PlanetList({ planetIds }: { planetIds: string[] }) {
  return (
    <ul className={styles.planetList}>
      {planetIds.map((id) => (
        <PlanetItem key={id} planetId={id} />
      ))}
    </ul>
  );
}

/**
 * Przełącznik wariantu frakcji (np. Keleres: Mentak/Xxcha/Argent). Gdy podany, panel
 * pokazuje dobrze widoczny przycisk, który cyklicznie przełącza wariant oglądanej
 * frakcji. Rodzina zajmuje jeden wpis na liście; TU wybiera się konkretny wariant.
 */
export interface VariantSwitch {
  /** Warianty rodziny (id + krótka etykieta, np. „Mentak"). */
  variants: { id: string; label: string }[];
  /** Id aktualnie oglądanego wariantu. */
  currentId: string;
  /** Wybiera konkretny wariant (podgląd + ew. zapis do slotu). */
  onSelect: (id: string) => void;
}

export interface FactionSummaryProps {
  faction: FactionInfo | null;
  /** Akcje pod summary (np. przycisk „Wybierz dla gracza N"). */
  footer?: React.ReactNode;
  /** Przełącznik wariantu frakcji (Keleres) — pokazywany w nagłówku, gdy podany. */
  variantSwitch?: VariantSwitch;
  /**
   * Wybór technologii startowych — pokazywany TYLKO gdy frakcja wymaga wyboru
   * i podana jest para value/onChange (frakcja przypisana aktywnemu graczowi).
   */
  startingTech?: {
    value: string[];
    onChange: (techs: string[]) => void;
  };
  /**
   * Zgłasza, KTÓRĄ frakcję pokazywać na scenie (portret + lore) — zmienia się przy
   * wejściu/wyjściu w podgląd pochodnej (Obsidian). `Step_Faction` renderuje warstwy.
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
  variantSwitch,
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
          Click a faction in the list to see its portrait, lore, abilities,
          technologies, leaders and units.
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
          Back to {faction.name}
        </Button>
        {derived.isLoading && <Text c="dimmed">Loading…</Text>}
        {derived.isError && (
          <Text c="red">Failed to load faction data.</Text>
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
        variantSwitch={variantSwitch}
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
  variantSwitch,
  derivedFactionId,
  onViewDerived,
}: {
  faction: FactionInfo;
  startingTech?: FactionSummaryProps["startingTech"];
  variantSwitch?: VariantSwitch;
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

  // Flota startowa z pełnymi nazwami; łączymy pozycje tego samego typu. Trzymamy jako
  // listę pozycji (liczba + nazwa) — renderowana jako „chipy", nie goły tekst.
  const fleetByType = new Map<string, number>();
  for (const u of faction.starting_units) {
    fleetByType.set(u.base_type, (fleetByType.get(u.base_type) ?? 0) + u.count);
  }
  const fleetItems = [...fleetByType.entries()].map(([baseType, count]) => ({
    baseType,
    count,
    name: unitTypeName(baseType),
  }));

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
          {faction.complexity && (
            <Text className={styles.complexity}>
              Complexity: {faction.complexity}
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
              View Obsidian
            </Button>
          </div>
        )}
      </div>

      {/* Wybór wariantu (np. Keleres) — trzy duże, klikalne przyciski. Aktywny wariant
          jest wyróżniony; klik wybiera konkretny wariant (podgląd + ew. zapis do slotu). */}
      {variantSwitch && variantSwitch.variants.length > 1 && (
        <div
          className={styles.variantSwitch}
          role="group"
          aria-label="Choose faction variant"
        >
          {variantSwitch.variants.map((v) => {
            const active = v.id === variantSwitch.currentId;
            return (
              <button
                key={v.id}
                type="button"
                aria-pressed={active}
                className={`${styles.variantButton} ${
                  active ? styles.variantButtonActive : ""
                }`}
                onClick={() => variantSwitch.onSelect(v.id)}
              >
                {v.label}
              </button>
            );
          })}
        </div>
      )}

      {/* `key` odtwarza kaskadowe pojawianie się sekcji przy każdej zmianie frakcji. */}
      <Stack gap="md" className={styles.sections} key={`sections-${faction.id}`}>
        {faction.abilities.length > 0 && (
          <Section title="Faction abilities">
            <div className={styles.chipRow}>
              {faction.abilities.map((id) => (
                <Ability key={id} id={id} />
              ))}
            </div>
          </Section>
        )}

        {faction.breakthrough && (
          <Section title="Breakthrough">
            <div className={styles.chipRow}>
              <Breakthrough breakthroughId={faction.breakthrough} unlocked />
            </div>
          </Section>
        )}

        {faction.faction_tech.length > 0 && (
          <Section title="Faction technologies">
            <div className={styles.chipRow}>
              {faction.faction_tech.map((id) => (
                <Tech key={id} techId={id} unresearched />
              ))}
            </div>
          </Section>
        )}

        {factionUnits.length > 0 && (
          <Section title="Faction units">
            <div className={styles.unitRow}>
              {factionUnits.map((id) => (
                <FactionUnit key={id} unitId={id} />
              ))}
            </div>
          </Section>
        )}

        {orderedLeaders.length > 0 && (
          <Section title="Leaders">
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
          <Section title="Faction promissory note">
            <div className={styles.chipRow}>
              {faction.promissory_notes.map((id) => (
                <PromissoryNote key={id} promissoryNoteId={id} />
              ))}
            </div>
          </Section>
        )}

        <Section title="Game start">
          <dl className={styles.startList}>
            {requiresTechChoice ? (
              <div className={styles.startRowFull}>
                <dt>Starting technologies</dt>
                <dd>
                  {startingTech ? (
                    <StartingTechChoice
                      faction={faction}
                      value={startingTech.value}
                      onChange={startingTech.onChange}
                    />
                  ) : (
                    <Text size="sm" c="dimmed">
                      This faction chooses {faction.starting_tech_amount} technologies.
                      Assign it to a player (button below) to choose.
                    </Text>
                  )}
                </dd>
              </div>
            ) : (
              faction.starting_tech.length > 0 && (
                <div className={styles.startRowFull}>
                  <dt>Starting technologies</dt>
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
                <dt>Planets</dt>
                <dd>
                  <PlanetList planetIds={faction.home_planets} />
                </dd>
              </div>
            )}
            {fleetItems.length > 0 && (
              <div className={styles.startRowFull}>
                <dt>Starting fleet</dt>
                <dd className={styles.fleetChips}>
                  {fleetItems.map((item) => (
                    <span key={item.baseType} className={styles.fleetChip}>
                      <span className={styles.fleetCount}>{item.count}</span>
                      <FleetUnitIcon baseType={item.baseType} />
                      <span className={styles.fleetName}>{item.name}</span>
                    </span>
                  ))}
                </dd>
              </div>
            )}
            <div className={styles.startRow}>
              <dt>Commodities</dt>
              <dd>
                <span className={styles.commodityChip}>
                  <img
                    src="/comms.png"
                    alt=""
                    className={styles.commodityIcon}
                    aria-hidden
                  />
                  <span className={styles.commodityCount}>
                    {faction.commodities}
                  </span>
                </span>
              </dd>
            </div>
          </dl>
        </Section>
      </Stack>
    </>
  );
}

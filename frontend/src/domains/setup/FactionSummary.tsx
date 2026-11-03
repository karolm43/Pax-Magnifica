// Podgląd wybranej frakcji na ekranie setupu (faction summary).
//
// Pokazuje bogate dane frakcji — portret + lore (uzupełniane w `factionLore.ts`),
// zdolności, przełom (breakthrough), technologie frakcyjne, liderów, weksel, WSZYSTKIE
// jednostki frakcyjne (warianty specyficzne dla frakcji), technologie startowe (z
// wyborem wbudowanym TUTAJ, bez osobnego kroku) oraz dane startu z PEŁNYMI nazwami
// (jednostki, system domowy, planety — nie surowe kody).
//
// Reużywa komponenty panelu gracza (`Ability`, `Tech`, `LeaderChip`, `PromissoryNote`,
// `Breakthrough`, `UnitDetailsCard`) — identyfikatory rozwiązywane po danych AsyncTI4,
// więc summary jest wizualnie spójne z grą. Działa na etapie setupu (hooki stanu gry
// degradują do undefined poza providerem, bez rzutów).

import { useMemo, useState } from "react";
import { MultiSelect, Stack, Text } from "@/ds";
import type { FactionInfo } from "@/api/useNewGame";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
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
import { getTileById } from "@/entities/lookup/systems";
import { useDisclosure } from "@/hooks/useDisclosure";
import {
  defaultPortraitCandidates,
  getFactionLore,
} from "./factionLore";
import styles from "./FactionSummary.module.css";

/** Kolejność slotów liderów — jak w panelu gracza (agent → commander → hero). */
const LEADER_ORDER = ["agent", "commander", "hero"] as const;

/** Usuwa końcówkę poziomu z nazwy jednostki bazowej („Carrier I" → „Carrier"). */
function cleanUnitName(name: string): string {
  return name.replace(/\s+I$/i, "").trim();
}

/** Pełna nazwa typu jednostki (generyczna baza) po `base_type` — bez surowych kodów. */
function unitTypeName(baseType: string): string {
  const data = getUnitData(baseType);
  return data ? cleanUnitName(data.name) : baseType;
}

/** Pełna nazwa planety po id (lub id, gdy brak w danych). */
function planetName(planetId: string): string {
  return getPlanetData(planetId)?.name ?? planetId;
}

/** Pełna nazwa systemu po id kafelka (lub id, gdy brak w danych). */
function systemName(systemId: string): string {
  const tile = getTileById(systemId);
  return tile?.name ? `${tile.name} (${systemId})` : systemId;
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

/**
 * Portret frakcji: próbuje kolejnych ścieżek z `factionLore` (jpg→png→webp) albo
 * własnej ścieżki z wpisu lore; gdy żadna nie istnieje — placeholder z ikoną frakcji.
 */
function FactionPortrait({ faction }: { faction: FactionInfo }) {
  const lore = getFactionLore(faction.id);
  const candidates = useMemo(
    () =>
      lore?.portrait
        ? [lore.portrait]
        : defaultPortraitCandidates(faction.id),
    [faction.id, lore?.portrait],
  );
  const [index, setIndex] = useState(0);
  const exhausted = index >= candidates.length;

  if (exhausted) {
    return (
      <div className={styles.portraitFallback}>
        <CircularFactionIcon faction={faction.id} size={72} />
      </div>
    );
  }
  return (
    <img
      src={candidates[index]}
      alt={`Portret: ${faction.name}`}
      className={styles.portrait}
      onError={() => setIndex((i) => i + 1)}
    />
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

export interface FactionSummaryProps {
  faction: FactionInfo | null;
  /** Akcje pod summary (np. przycisk „Wybierz dla gracza N"). */
  footer?: React.ReactNode;
  /**
   * Wybór technologii startowych — pokazywany TYLKO gdy frakcja wymaga wyboru
   * (`starting_tech_amount > 0`) i podana jest para value/onChange (tj. frakcja jest
   * przypisana aktywnemu graczowi). Brak → sekcja technologii jest informacyjna.
   */
  startingTech?: {
    value: string[];
    onChange: (techs: string[]) => void;
  };
}

/**
 * Panel szczegółów frakcji (po prawej od galerii). `faction === null` → zachęta.
 */
export function FactionSummary({
  faction,
  footer,
  startingTech,
}: FactionSummaryProps) {
  if (!faction) {
    return (
      <div className={styles.emptyState}>
        <Text c="dimmed" ta="center">
          Kliknij frakcję z galerii, aby zobaczyć jej portret, zdolności, technologie,
          liderów i jednostki.
        </Text>
      </div>
    );
  }

  const lore = getFactionLore(faction.id)?.lore;

  // Liderzy w kanonicznej kolejności (agent → commander → hero), reszta na końcu.
  const leadersByType = (type: string) =>
    faction.leaders.filter((id) => getLeaderById(id)?.type === type);
  const orderedLeaders = [
    ...LEADER_ORDER.flatMap((type) => leadersByType(type)),
    ...faction.leaders.filter(
      (id) => !LEADER_ORDER.includes(getLeaderById(id)?.type as never),
    ),
  ];

  // Jednostki frakcyjne = warianty specyficzne dla frakcji (mają pole `faction` w
  // danych jednostek, np. argent_destroyer, *_flagship, *_mech). Pokazujemy WSZYSTKIE,
  // nie tylko flagship/mech — Argent Flight ma np. własny niszczyciel.
  const factionUnits = faction.units.filter(
    (id) => getUnitData(id)?.faction !== undefined,
  );

  // Flota startowa z pełnymi nazwami; łączymy pozycje tego samego typu (np. piechota
  // z różnych planet) w jedną liczbę.
  const fleetByType = new Map<string, number>();
  for (const u of faction.starting_units) {
    fleetByType.set(u.base_type, (fleetByType.get(u.base_type) ?? 0) + u.count);
  }
  const fleetSummary = [...fleetByType.entries()]
    .map(([baseType, count]) => `${count}× ${unitTypeName(baseType)}`)
    .join(", ");

  const requiresTechChoice = faction.starting_tech_amount > 0;

  return (
    <div className={styles.summary}>
      <div className={styles.header}>
        <FactionPortrait faction={faction} />
        <div className={styles.headerText}>
          <Text className={styles.factionName}>{faction.name}</Text>
          {faction.complexity && (
            <Text className={styles.complexity}>
              Złożoność: {faction.complexity}
            </Text>
          )}
        </div>
      </div>

      <Stack gap="md" className={styles.sections}>
        {lore && (
          <Section title="Lore">
            <div className={styles.lore}>{lore}</div>
          </Section>
        )}

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
            {fleetSummary && (
              <div className={styles.startRow}>
                <dt>Flota startowa</dt>
                <dd>{fleetSummary}</dd>
              </div>
            )}
            {faction.home_system && (
              <div className={styles.startRow}>
                <dt>System domowy</dt>
                <dd>{systemName(faction.home_system)}</dd>
              </div>
            )}
            {faction.home_planets.length > 0 && (
              <div className={styles.startRow}>
                <dt>Planety domowe</dt>
                <dd>{faction.home_planets.map(planetName).join(", ")}</dd>
              </div>
            )}
            <div className={styles.startRow}>
              <dt>Towary (commodities)</dt>
              <dd>{faction.commodities}</dd>
            </div>
          </dl>
        </Section>
      </Stack>

      {footer && <div className={styles.footer}>{footer}</div>}
    </div>
  );
}

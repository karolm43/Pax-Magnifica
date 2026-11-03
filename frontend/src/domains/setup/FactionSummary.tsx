// Podgląd wybranej frakcji na ekranie setupu (faction summary).
//
// Pokazuje bogate dane frakcji — zdolności, technologie frakcyjne, liderów, weksel,
// jednostki frakcyjne (flagship/mech), technologie startowe, dom i flotę — korzystając
// z TYCH SAMYCH komponentów co panel gracza w grze (`Ability`, `Tech`, `LeaderChip`,
// `PromissoryNote`, `UnitDetailsCard`). Komponenty rozwiązują identyfikatory po
// wbudowanych danych AsyncTI4, więc summary jest spójne wizualnie z resztą aplikacji.
//
// Dane wejściowe to `FactionInfo` z `/factions` (rozszerzone o pola bogate) — same
// identyfikatory ze statycznego rejestru backendu. Nie potrzebujemy stanu gry: panel
// działa na etapie setupu, PRZED utworzeniem gry (hooki stanu gry degradują do undefined).

import { Stack, Text } from "@/ds";
import type { FactionInfo } from "@/api/useNewGame";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { Ability } from "@/domains/player/components/Ability";
import { Tech } from "@/domains/player/components/Tech";
import { LeaderChip } from "@/domains/player/components/Leader/LeaderChip";
import { PromissoryNote } from "@/domains/player/components/PromissoryNote";
import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard/UnitDetailsCard";
import { Unit } from "@/shared/ui/Unit";
import { getLeaderById } from "@/entities/lookup/leaders";
import { getUnitData } from "@/entities/lookup/units";
import { getColorAlias } from "@/entities/lookup/colors";
import { useDisclosure } from "@/hooks/useDisclosure";
import styles from "./FactionSummary.module.css";

/** Kolejność slotów liderów — jak w panelu gracza (agent → commander → hero). */
const LEADER_ORDER = ["agent", "commander", "hero"] as const;

/** Jednostki frakcyjne warte pokazania w summary (unikalne „smaczki" frakcji). */
const HIGHLIGHT_UNIT_BASE_TYPES = new Set(["flagship", "mech", "warsun"]);

/** Sekcja summary z nagłówkiem i treścią; chowa się, gdy nie ma czego pokazać. */
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
 * Pojedyncza jednostka frakcyjna (flagship/mech/war sun): sprite jednostki w neutralnym
 * kolorze + klikalny podgląd `UnitDetailsCard` (statystyki i zdolność jednostki). Kolor
 * neutralny (brak właściciela) — na etapie setupu nie ma przypisanego koloru gracza.
 */
function FactionUnit({ unitId }: { unitId: string }) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const unitData = getUnitData(unitId);
  if (!unitData) return null;

  const label = unitData.name || unitData.baseType;

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
 * Panel szczegółów frakcji. Renderowany po prawej stronie galerii po kliknięciu frakcji.
 * Gdy `faction` jest `null` (nic nie wybrano) — pokazuje zachętę do wyboru.
 */
export function FactionSummary({
  faction,
  footer,
}: {
  faction: FactionInfo | null;
  /** Akcje pod summary (np. przycisk „Wybierz dla gracza N"). */
  footer?: React.ReactNode;
}) {
  if (!faction) {
    return (
      <div className={styles.emptyState}>
        <Text c="dimmed" ta="center">
          Kliknij frakcję z galerii, aby zobaczyć jej zdolności, technologie, liderów
          i jednostki.
        </Text>
      </div>
    );
  }

  // Liderzy w kanonicznej kolejności (agent → commander → hero), reszta na końcu.
  const leadersByType = (type: string) =>
    faction.leaders.filter((id) => getLeaderById(id)?.type === type);
  const orderedLeaders = [
    ...LEADER_ORDER.flatMap((type) => leadersByType(type)),
    ...faction.leaders.filter(
      (id) => !LEADER_ORDER.includes(getLeaderById(id)?.type as never),
    ),
  ];

  // Jednostki frakcyjne do wyróżnienia (flagship/mech/war sun), bez duplikatów.
  const highlightUnits = faction.units.filter((id) => {
    const data = getUnitData(id);
    return data ? HIGHLIGHT_UNIT_BASE_TYPES.has(data.baseType) : false;
  });

  return (
    <div className={styles.summary}>
      <div className={styles.header}>
        <CircularFactionIcon faction={faction.id} size={44} />
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
        {faction.abilities.length > 0 && (
          <Section title="Zdolności frakcji">
            <div className={styles.chipRow}>
              {faction.abilities.map((id) => (
                <Ability key={id} id={id} />
              ))}
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

        {highlightUnits.length > 0 && (
          <Section title="Jednostki frakcyjne">
            <div className={styles.unitRow}>
              {highlightUnits.map((id) => (
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
            {faction.starting_tech_amount > 0 ? (
              <div className={styles.startRow}>
                <dt>Technologie startowe</dt>
                <dd>
                  Wybierz {faction.starting_tech_amount} w kolejnym kroku
                </dd>
              </div>
            ) : (
              faction.starting_tech.length > 0 && (
                <div className={styles.startRow}>
                  <dt>Technologie startowe</dt>
                  <dd className={styles.startChips}>
                    {faction.starting_tech.map((id) => (
                      <Tech key={id} techId={id} />
                    ))}
                  </dd>
                </div>
              )
            )}
            {faction.starting_fleet && (
              <div className={styles.startRow}>
                <dt>Flota startowa</dt>
                <dd>{faction.starting_fleet}</dd>
              </div>
            )}
            {faction.home_planets.length > 0 && (
              <div className={styles.startRow}>
                <dt>Planety domowe</dt>
                <dd>{faction.home_planets.join(", ")}</dd>
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

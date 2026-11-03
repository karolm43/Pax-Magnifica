// Krok setupu: wybór frakcji per gracz (zadanie 12.2, R8).
//
// Prezentuje listę WSZYSTKICH grywalnych frakcji ze StaticDataRegistry (przez
// `useFactions`, reużyty z kontenera przez propsy `factions`/`factionById`), per slot
// gracza. Dla każdej frakcji pokazuje:
//   - nazwę frakcji,
//   - identyfikator (`faction.id`),
//   - quick reference z CDN na hover/focus (`QuickReferenceImage`, degraduje bez błędu).
//
// ⚠️ DECYZJA (design.md, Data Models / R8.2): krok prezentuje TYLKO nazwę + identyfikator
// + quick reference. Opisu stylu gry NIE prezentujemy — assety AsyncTI4 nie mają takiego
// pola, więc jego brak NIE jest błędem (R8.2/R8.4: brak pola → pokaż resztę bez błędu).
//
// Stan konfiguracji żyje w `useSetupStore` (jedno źródło prawdy). Zmiana frakcji przez
// `setFaction` czyści technologie startowe slotu (R9.4). Podgląd quick reference degraduje
// bez błędu, gdy obrazu nie ma (R8.3/R8.4) — obsługuje to `QuickReferenceImage`.

import { useMemo, useState } from "react";
import { Stack, Text } from "@/ds";
import type { SetupStepProps } from "../SetupWizard";
import { RANDOM_FACTION, useSetupStore } from "../useSetupStore";
import { FactionItem, factionListStyles as styles } from "../FactionList";

/**
 * Lista frakcji dla jednego slotu gracza: „Losowa" na górze + wszystkie grywalne
 * frakcje posortowane po nazwie. Stan podglądu quick reference trzymamy lokalnie
 * (per slot), więc naraz widać najwyżej jeden podgląd, a wyjście myszą poza listę
 * zawsze go chowa — to likwiduje „zacinający się" hover przy szybkim przeskakiwaniu.
 */
function FactionSlotList({
  slotIndex,
  selectedId,
  sortedFactions,
}: {
  slotIndex: number;
  selectedId: string;
  sortedFactions: SetupStepProps["factions"];
}) {
  const setFaction = useSetupStore((s) => s.setFaction);
  // Która frakcja ma pokazany podgląd (id) albo null — stan lokalny slotu.
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div
      className={styles.factionList}
      role="listbox"
      aria-label={`Frakcja gracza ${slotIndex + 1}`}
      // Wyjście myszą poza listę zawsze chowa podgląd slotu.
      onMouseLeave={() => setHoveredId(null)}
      // Scroll listy chowa podgląd — inaczej karta „odjeżdża" od swojej pozycji
      // i zostaje wisieć (popover nie nadąża za przewijanym kontenerem).
      onScroll={() => setHoveredId((prev) => (prev == null ? prev : null))}
    >
      <button
        type="button"
        className={`${styles.factionItem} ${
          selectedId === RANDOM_FACTION ? styles.factionItemActive : ""
        }`}
        aria-pressed={selectedId === RANDOM_FACTION}
        onClick={() => setFaction(slotIndex, RANDOM_FACTION)}
      >
        <span className={styles.randomIcon} aria-hidden>
          🎲
        </span>
        <span className={styles.factionItemLabel}>Losowa</span>
      </button>

      {sortedFactions.map((faction) => (
        <FactionItem
          key={faction.id}
          faction={faction}
          active={selectedId === faction.id}
          opened={hoveredId === faction.id}
          // R8.2: w kroku wyboru pokazujemy nazwę + identyfikator frakcji.
          showId
          onHover={setHoveredId}
          // Zmiana frakcji czyści technologie startowe slotu (R9.4) — robi to `setFaction`.
          onPick={() => setFaction(slotIndex, faction.id)}
        />
      ))}
    </div>
  );
}

/**
 * Krok wyboru frakcji. Renderuje listę frakcji dla każdego slotu gracza. Dane frakcji
 * (lista grywalnych ze StaticDataRegistry) przychodzą z kontenera przez `factions`.
 */
export default function Step_Faction({ factions }: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);

  // Frakcje do listy wyboru, posortowane alfabetycznie po nazwie (stabilna kolejność).
  const sortedFactions = useMemo(
    () => [...factions].sort((a, b) => a.name.localeCompare(b.name)),
    [factions],
  );

  return (
    <Stack gap="lg">
      <Text size="sm" c="dimmed">
        Wybierz frakcję dla każdego gracza albo zostaw „Losową" — backend dobierze
        nieprzypisaną frakcję bez powtórzeń. Najedź na frakcję, by zobaczyć jej quick
        reference (kartę pomocy).
      </Text>

      {slots.map((slot, index) => (
        <Stack key={index} gap="xs">
          <Text fw={600} size="sm">
            Gracz {index + 1}
          </Text>
          <FactionSlotList
            slotIndex={index}
            selectedId={slot.factionId}
            sortedFactions={sortedFactions}
          />
        </Stack>
      ))}
    </Stack>
  );
}

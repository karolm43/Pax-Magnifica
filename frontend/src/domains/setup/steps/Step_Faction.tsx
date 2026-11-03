// Krok setupu: wybór frakcji per gracz (R8) — układ master-detail.
//
// Zastępuje dawną listę-pod-listą (osobna przewijalna lista 30+ frakcji dla KAŻDEGO
// slotu). Nowy układ:
//   1. Przełącznik graczy u góry — jeden widok galerii obsługuje wszystkich graczy;
//      pasek pokazuje, kto już wybrał frakcję (ikona + nazwa frakcji).
//   2. Galeria frakcji (lewa kolumna) — responsywna siatka większych kafli (ikona +
//      nazwa) z polem wyszukiwania. „Losowa" jako pierwszy kafel. Klik = PODGLĄD
//      (nie od razu przypisanie), żeby dało się obejrzeć frakcję przed wyborem.
//   3. Faction summary (prawa kolumna) — bogate dane frakcji (zdolności, technologie
//      frakcyjne, liderzy, weksel, jednostki) renderowane TYMI SAMYMI komponentami co
//      panel gracza w grze (`FactionSummary`). Pod spodem przycisk „Wybierz dla gracza N".
//
// Stan konfiguracji żyje w `useSetupStore` (jedno źródło prawdy). Zmiana frakcji przez
// `setFaction` czyści technologie startowe slotu (R9.4). Podgląd/przełącznik to stan
// lokalny kroku (który gracz jest aktywny, którą frakcję oglądamy) — nie wpływa na model.

import { useEffect, useMemo, useState } from "react";
import { Button, Stack, Text, TextInput } from "@/ds";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import type { SetupStepProps } from "../SetupWizard";
import { RANDOM_FACTION, useSetupStore } from "../useSetupStore";
import { FactionSummary } from "../FactionSummary";
import styles from "./Step_Faction.module.css";

/** Etykieta frakcji slotu w pasku graczy („Losowa" / nazwa / „—"). */
function slotFactionLabel(
  factionId: string,
  factionById: SetupStepProps["factionById"],
): string {
  if (factionId === RANDOM_FACTION) return "Losowa";
  return factionById.get(factionId)?.name ?? factionId;
}

export default function Step_Faction({ factions, factionById }: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);
  const setFaction = useSetupStore((s) => s.setFaction);

  // Który gracz jest właśnie konfigurowany (indeks slotu).
  const [activeSlot, setActiveSlot] = useState(0);
  // Którą frakcję oglądamy w summary (id) — podgląd, zanim przypiszemy do slotu.
  const [previewId, setPreviewId] = useState<string | null>(null);
  // Filtr galerii.
  const [query, setQuery] = useState("");

  // Przy przełączeniu gracza pokaż jego aktualnie wybraną frakcję (jeśli jawna).
  const activeSlotFaction = slots[activeSlot]?.factionId;
  useEffect(() => {
    setPreviewId(
      activeSlotFaction && activeSlotFaction !== RANDOM_FACTION
        ? activeSlotFaction
        : null,
    );
  }, [activeSlot, activeSlotFaction]);

  // Frakcje do galerii, posortowane po nazwie i przefiltrowane zapytaniem.
  const visibleFactions = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...factions]
      .sort((a, b) => a.name.localeCompare(b.name))
      .filter(
        (f) =>
          q.length === 0 ||
          f.name.toLowerCase().includes(q) ||
          f.id.toLowerCase().includes(q),
      );
  }, [factions, query]);

  const previewFaction = previewId ? factionById.get(previewId) ?? null : null;
  const selectedForActive = slots[activeSlot]?.factionId;

  // Czy frakcja jest już wzięta przez INNEGO gracza (jawny wybór) — pokazujemy ostrzeżenie.
  const takenBy = useMemo(() => {
    const map = new Map<string, number>();
    slots.forEach((slot, i) => {
      if (slot.factionId !== RANDOM_FACTION) map.set(slot.factionId, i);
    });
    return map;
  }, [slots]);

  const assign = (factionId: string) => {
    setFaction(activeSlot, factionId);
  };

  const previewTakenByOther =
    previewId && takenBy.has(previewId) && takenBy.get(previewId) !== activeSlot;

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Wybierz gracza, obejrzyj frakcje w galerii i kliknij „Wybierz dla gracza N".
        Zostaw „Losową", by backend dobrał nieprzypisaną frakcję bez powtórzeń.
      </Text>

      {/* Przełącznik graczy — kto jest konfigurowany + co już wybrał. */}
      <div className={styles.playerBar} role="tablist" aria-label="Gracze">
        {slots.map((slot, index) => {
          const isRandom = slot.factionId === RANDOM_FACTION;
          return (
            <button
              key={index}
              type="button"
              role="tab"
              aria-selected={index === activeSlot}
              className={`${styles.playerTab} ${
                index === activeSlot ? styles.playerTabActive : ""
              }`}
              onClick={() => setActiveSlot(index)}
            >
              <span className={styles.playerTabHead}>Gracz {index + 1}</span>
              <span className={styles.playerTabFaction}>
                {!isRandom ? (
                  <CircularFactionIcon faction={slot.factionId} size={18} />
                ) : (
                  <span className={styles.randomDot} aria-hidden>
                    🎲
                  </span>
                )}
                <span className={styles.playerTabName}>
                  {slotFactionLabel(slot.factionId, factionById)}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <div className={styles.layout}>
        {/* Galeria frakcji (master). */}
        <div className={styles.gallery}>
          <TextInput
            placeholder="Szukaj frakcji…"
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            aria-label="Szukaj frakcji"
          />
          <div className={styles.grid} role="listbox" aria-label="Frakcje">
            {/* „Losowa" jako pierwszy kafel — wybiera od razu (nie ma co podglądać). */}
            <button
              type="button"
              role="option"
              aria-selected={selectedForActive === RANDOM_FACTION}
              className={`${styles.card} ${styles.randomCard} ${
                selectedForActive === RANDOM_FACTION ? styles.cardSelected : ""
              }`}
              onClick={() => {
                setPreviewId(null);
                assign(RANDOM_FACTION);
              }}
            >
              <span className={styles.randomIcon} aria-hidden>
                🎲
              </span>
              <span className={styles.cardName}>Losowa</span>
            </button>

            {visibleFactions.map((faction) => {
              const isSelectedHere = selectedForActive === faction.id;
              const otherOwner =
                takenBy.has(faction.id) && takenBy.get(faction.id) !== activeSlot;
              return (
                <button
                  key={faction.id}
                  type="button"
                  role="option"
                  aria-selected={previewId === faction.id}
                  className={`${styles.card} ${
                    isSelectedHere ? styles.cardSelected : ""
                  } ${previewId === faction.id ? styles.cardPreview : ""} ${
                    otherOwner ? styles.cardTaken : ""
                  }`}
                  onClick={() => setPreviewId(faction.id)}
                >
                  <CircularFactionIcon faction={faction.id} size={34} />
                  <span className={styles.cardName}>{faction.name}</span>
                  {isSelectedHere && (
                    <span className={styles.badgeSelected} aria-hidden>
                      ✓
                    </span>
                  )}
                  {otherOwner && (
                    <span
                      className={styles.badgeTaken}
                      title={`Wybrana przez gracza ${
                        (takenBy.get(faction.id) ?? 0) + 1
                      }`}
                      aria-hidden
                    >
                      G{(takenBy.get(faction.id) ?? 0) + 1}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Summary (detail). */}
        <div className={styles.detail}>
          <FactionSummary
            faction={previewFaction}
            footer={
              previewFaction && (
                <Stack gap="xs">
                  {previewTakenByOther && (
                    <Text size="xs" c="red">
                      Ta frakcja jest już wybrana przez gracza{" "}
                      {(takenBy.get(previewFaction.id) ?? 0) + 1}. Wybór przypisze ją
                      graczowi {activeSlot + 1} (duplikat zablokuje przejście dalej).
                    </Text>
                  )}
                  <Button
                    fullWidth
                    disabled={selectedForActive === previewFaction.id}
                    onClick={() => assign(previewFaction.id)}
                  >
                    {selectedForActive === previewFaction.id
                      ? `Wybrana dla gracza ${activeSlot + 1}`
                      : `Wybierz dla gracza ${activeSlot + 1}`}
                  </Button>
                </Stack>
              )
            }
          />
        </div>
      </div>
    </Stack>
  );
}

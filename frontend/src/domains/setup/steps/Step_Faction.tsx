// Krok setupu: wybór frakcji per gracz (R8) — scena PEŁNOEKRANOWA.
//
// Jedna kompozycja na cały ekran:
//   - pasek górny: „Wstecz" + przełącznik graczy + „Start gry" (zastępuje ramkę
//     kreatora — ten krok jest ostatni i renderowany bez `Paper` z `SetupWizard`);
//   - duży portret postaci maksymalnie przy LEWEJ krawędzi (tło sceny) z lore
//     nałożonym na jego dolną część, w dwóch kolumnach (`FactionBackdrop.tsx`);
//   - panel szczegółów (`FactionSummary`) na szkle, pośrodku, NAD portretem;
//   - pionowa lista frakcji po prawej, z wyszukiwarką — sam klik wybiera podgląd
//     (bez hover-popoverów, by nie migało przy przewijaniu).
//
// Zmiana podglądanej frakcji odtwarza animacje wejścia (`key={previewId}` na warstwach
// portretu/lore/detail), więc całość „pojawia się" przy każdym wyborze, nie tylko portret.
//
// Stan konfiguracji żyje w `useSetupStore` (jedno źródło prawdy). Zmiana frakcji przez
// `setFaction` czyści technologie startowe slotu (R9.4). Podgląd/przełącznik gracza to
// stan lokalny kroku — nie wpływa na model.

import { useEffect, useMemo, useState } from "react";
import { Button, TextInput } from "@/ds";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import type { SetupStepProps } from "../SetupWizard";
import { RANDOM_FACTION, useSetupStore } from "../useSetupStore";
import { FactionSummary } from "../FactionSummary";
import { FactionLore, FactionPortraitLayer } from "../FactionBackdrop";
import type { FactionInfo } from "@/api/useNewGame";
import styles from "./Step_Faction.module.css";

/** Etykieta frakcji slotu w pasku graczy („Losowa" / nazwa / „—"). */
function slotFactionLabel(
  factionId: string,
  factionById: SetupStepProps["factionById"],
): string {
  if (factionId === RANDOM_FACTION) return "Losowa";
  return factionById.get(factionId)?.name ?? factionId;
}

export default function Step_Faction({ factions, factionById, stage }: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);
  const setFaction = useSetupStore((s) => s.setFaction);
  const updateSlot = useSetupStore((s) => s.updateSlot);

  // Który gracz jest właśnie konfigurowany (indeks slotu).
  const [activeSlot, setActiveSlot] = useState(0);
  // Którą frakcję oglądamy w summary (id) — podgląd, zanim przypiszemy do slotu.
  const [previewId, setPreviewId] = useState<string | null>(null);
  // Filtr listy.
  const [query, setQuery] = useState("");
  // Frakcja aktywna na scenie (bazowa albo pochodna — Obsidian); `FactionSummary`
  // zgłasza ją przez callback, bo podgląd pochodnej zmienia, co pokazujemy na scenie.
  const [stageFaction, setStageFaction] = useState<FactionInfo | null>(null);

  // Przy przełączeniu gracza pokaż jego aktualnie wybraną frakcję (jeśli jawna).
  const activeSlotFaction = slots[activeSlot]?.factionId;
  useEffect(() => {
    setPreviewId(
      activeSlotFaction && activeSlotFaction !== RANDOM_FACTION
        ? activeSlotFaction
        : null,
    );
  }, [activeSlot, activeSlotFaction]);

  // Frakcje do listy, posortowane po nazwie i przefiltrowane zapytaniem.
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

  // Czy frakcja jest już wzięta przez INNEGO gracza (jawny wybór) — pokazujemy znacznik.
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

  return (
    <div className={styles.stage}>
      {/* Pasek górny: Wstecz · przełącznik graczy · Start gry (zastępuje ramkę kreatora). */}
      <div className={styles.topBar}>
        <button type="button" className={styles.backButton} onClick={stage?.onBack}>
          ← Wstecz
        </button>

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
                    <CircularFactionIcon faction={slot.factionId} size={16} />
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

        {stage?.message && (
          <span className={styles.topMessage} style={{ color: "var(--ds-ink-lo)" }}>
            {stage.message}
          </span>
        )}

        <Button
          className={styles.submitButton}
          loading={stage?.submitting}
          disabled={!stage?.canSubmit}
          onClick={stage?.onSubmit}
        >
          Start gry →
        </Button>
      </div>

      {/* Zawartość: portret+lore (tło pełnoekranowe) | detail (szkło) | lista (prawo). */}
      <div className={styles.content}>
        {stageFaction && (
          <div className={styles.backdropWrap} key={`backdrop-${stageFaction.id}`}>
            <FactionPortraitLayer faction={stageFaction} />
            <div className={styles.loreSlot}>
              <FactionLore faction={stageFaction} />
            </div>
          </div>
        )}

        {/* Summary (detail) — szkło nad portretem. */}
        <div className={styles.detail} key={`detail-${previewFaction?.id ?? "empty"}`}>
          <FactionSummary
            faction={previewFaction}
            onActiveFactionChange={setStageFaction}
            // Wybór technologii startowych pokazujemy TYLKO, gdy oglądana frakcja jest
            // przypisana aktywnemu graczowi (wtedy zapis idzie do jego slotu). Scala to
            // dawny osobny krok „Technologie startowe" w ten panel.
            startingTech={
              previewFaction && selectedForActive === previewFaction.id
                ? {
                    value: slots[activeSlot]?.startingTech ?? [],
                    onChange: (techs) =>
                      updateSlot(activeSlot, { startingTech: techs }),
                  }
                : undefined
            }
            footer={
              previewFaction && (
                <div className={styles.footer}>
                  {takenBy.has(previewFaction.id) &&
                    takenBy.get(previewFaction.id) !== activeSlot && (
                      <p style={{ color: "var(--ds-ink-lo)", fontSize: 12 }}>
                        Ta frakcja jest już wybrana przez gracza{" "}
                        {(takenBy.get(previewFaction.id) ?? 0) + 1}. Wybór przypisze
                        ją graczowi {activeSlot + 1} (duplikat zablokuje start gry).
                      </p>
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
                </div>
              )
            }
          />
        </div>

        {/* Lista frakcji (prawo) — sam klik wybiera podgląd, bez hover-popoverów. */}
        <div className={styles.gallery}>
          <TextInput
            placeholder="Szukaj frakcji…"
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            aria-label="Szukaj frakcji"
          />
          <div className={styles.list} role="listbox" aria-label="Frakcje">
            {/* „Losowa" jako pierwsza pozycja — wybiera od razu (nie ma co podglądać). */}
            <button
              type="button"
              role="option"
              aria-selected={selectedForActive === RANDOM_FACTION}
              className={`${styles.item} ${
                selectedForActive === RANDOM_FACTION ? styles.itemSelected : ""
              }`}
              onClick={() => {
                setPreviewId(null);
                assign(RANDOM_FACTION);
              }}
            >
              <span className={styles.randomDot2} aria-hidden>
                🎲
              </span>
              <span className={styles.itemName}>Losowa</span>
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
                  className={`${styles.item} ${
                    isSelectedHere ? styles.itemSelected : ""
                  } ${previewId === faction.id ? styles.itemPreview : ""} ${
                    otherOwner ? styles.itemTaken : ""
                  }`}
                  onClick={() => setPreviewId(faction.id)}
                >
                  <CircularFactionIcon faction={faction.id} size={22} />
                  <span className={styles.itemName}>{faction.name}</span>
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
      </div>
    </div>
  );
}

// Krok setupu: wybór frakcji per gracz (R8) — scena PEŁNOEKRANOWA.
//
// Jedna kompozycja na cały ekran:
//   - pasek górny: „Wstecz" + przełącznik graczy + „Start gry" (zastępuje ramkę
//     kreatora — ten krok jest ostatni i renderowany bez `Paper` z `SetupWizard`);
//   - strefa postaci: duży portret równo z LEWĄ i DOLNĄ krawędzią ekranu (prawa
//     krawędź zanika maską), lore w dwóch kolumnach tuż OBOK postaci, nie na niej
//     (`FactionBackdrop.tsx`); portret powoli „wyłania się" z mgły;
//   - WĄSKI panel szczegółów (`FactionSummary`) na szkle;
//   - pionowa lista frakcji po prawej, z wyszukiwarką — sam klik wybiera podgląd
//     (bez hover-popoverów, by nie migało przy przewijaniu);
//   - wyróżniony przycisk „Wybierz dla gracza N" wyśrodkowany na dole sceny.
//
// Zmiana podglądanej frakcji odtwarza animacje wejścia (`key={previewId}` na warstwach
// portretu/lore/detail), więc całość „pojawia się" przy każdym wyborze, nie tylko portret.
//
// Stan konfiguracji żyje w `useSetupStore` (jedno źródło prawdy). Zmiana frakcji przez
// `setFaction` czyści technologie startowe slotu (R9.4). Podgląd/przełącznik gracza to
// stan lokalny kroku — nie wpływa na model.

import { Fragment, useEffect, useMemo, useState } from "react";
import { TextInput } from "@/ds";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import type { SetupStepProps } from "../SetupWizard";
import { RANDOM_FACTION, useSetupStore } from "../useSetupStore";
import { FactionSummary } from "../FactionSummary";
import {
  FactionLore,
  FactionPortraitLayer,
  FactionHeader,
  hasFactionQuote,
} from "../FactionBackdrop";
import type { FactionInfo } from "@/api/useNewGame";
import {
  type FactionListEntry,
  familyOfVariant,
  firstVariant,
  groupByExpansion,
  VARIANT_FAMILIES,
  VARIANT_LABEL,
} from "../factionVariants";
import { hasDeferredStartingTech } from "../deferredTech";
import styles from "./Step_Faction.module.css";

/** Etykieta frakcji slotu w pasku graczy („Losowa" / nazwa / „—"). */
function slotFactionLabel(
  factionId: string,
  factionById: SetupStepProps["factionById"],
): string {
  if (factionId === RANDOM_FACTION) return "Random";
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
  // Aktywny wariant w każdej rodzinie wariantów (np. keleres → keleresm/x/a). Rodzina
  // zajmuje JEDEN wiersz listy, a przycisk cyklu przełącza, który wariant jest aktywny.
  const [familyVariant, setFamilyVariant] = useState<Record<string, string>>({});

  /** Aktualny wariant rodziny — jawnie wybrany albo domyślnie pierwszy. */
  const activeVariant = (family: string): string =>
    familyVariant[family] ?? firstVariant(family);
  // Filtr listy.
  const [query, setQuery] = useState("");
  // Frakcja aktywna na scenie (bazowa albo pochodna — Obsidian); `FactionSummary`
  // zgłasza ją przez callback, bo podgląd pochodnej zmienia, co pokazujemy na scenie.
  const [stageFaction, setStageFaction] = useState<FactionInfo | null>(null);
  // Środek widocznej sylwetki postaci (px od lewej krawędzi strefy) albo null.
  const [figureCx, setFigureCx] = useState<number | null>(null);

  // Przy przełączeniu gracza pokaż jego aktualnie wybraną frakcję (jeśli jawna).
  const activeSlotFaction = slots[activeSlot]?.factionId;
  useEffect(() => {
    const explicit =
      activeSlotFaction && activeSlotFaction !== RANDOM_FACTION
        ? activeSlotFaction
        : null;
    setPreviewId(explicit);
    // Jeśli gracz ma wybrany wariant, ustaw go jako aktywny w jego rodzinie, by wiersz
    // rodziny i przycisk cyklu pokazały właśnie ten wariant.
    const family = explicit ? familyOfVariant(explicit) : null;
    if (family && explicit) {
      setFamilyVariant((prev) => ({ ...prev, [family]: explicit }));
    }
  }, [activeSlot, activeSlotFaction]);

  // Frakcje do listy: przefiltrowane zapytaniem, zwinięte warianty (Keleres → jeden
  // wpis) i pogrupowane wg dodatków (Base Game / PoK / Thunder's Edge).
  const sections = useMemo(() => {
    const q = query.trim().toLowerCase();
    const sorted = [...factions]
      .sort((a, b) => a.name.localeCompare(b.name))
      .filter(
        (f) =>
          q.length === 0 ||
          f.name.toLowerCase().includes(q) ||
          f.id.toLowerCase().includes(q),
      );
    return groupByExpansion(sorted);
  }, [factions, query]);

  const previewFaction = previewId ? factionById.get(previewId) ?? null : null;
  const selectedForActive = slots[activeSlot]?.factionId;

  // Przełącznik wariantu dla panelu szczegółów: aktywny, gdy oglądana frakcja należy do
  // rodziny wariantów (np. Keleres). Przełączenie zmienia podgląd, a gdy rodzina jest już
  // przypisana aktywnemu graczowi — także jego slot. Przekazywane do `FactionSummary`,
  // żeby przycisk był dobrze widoczny tam, gdzie pokazujemy dane frakcji.
  const previewFamily = previewId ? familyOfVariant(previewId) : null;
  const variantSwitch =
    previewFamily && previewId
      ? {
          variants: (VARIANT_FAMILIES[previewFamily] ?? []).map((id) => ({
            id,
            label: VARIANT_LABEL[id] ?? id,
          })),
          currentId: previewId,
          // Klik w konkretny wariant: od razu podgląd, a gdy rodzina jest już przypisana
          // aktywnemu graczowi — także zapis do jego slotu.
          onSelect: (id: string) => {
            setFamilyVariant((prev) => ({ ...prev, [previewFamily]: id }));
            setPreviewId(id);
            if (familyOfVariant(selectedForActive ?? "") === previewFamily) {
              assign(id);
            }
          },
        }
      : undefined;

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

  // Gotowość: ilu graczy ma już wybraną frakcję (jawną albo losową). Służy do
  // czytelnego podpisu przy przycisku startu („wszyscy gotowi" vs „N z M"). To tylko
  // sygnał wizualny — autorytatywną blokadę startu daje `stage.canSubmit` (walidacja).
  const chosenCount = slots.filter((s) => s.factionId.length > 0).length;
  const allChosen = chosenCount === slots.length;
  const ready = (stage?.canSubmit ?? false) && allChosen;

  // Oglądana frakcja jest już wzięta przez INNEGO gracza — pokazujemy ostrzeżenie.
  const previewTakenByOther =
    previewId !== null &&
    takenBy.has(previewId) &&
    takenBy.get(previewId) !== activeSlot;

  /** Renderuje jeden wiersz listy — zwykłą frakcję albo rodzinę wariantów (jeden wpis). */
  const renderEntry = (entry: FactionListEntry) => {
    // Rodzina wariantów (np. Keleres): JEDEN wiersz reprezentujący aktywny wariant.
    // Przełącznik wariantu jest w panelu szczegółów, nie tutaj — klik wiersza podgląda
    // aktywny wariant rodziny.
    if (entry.kind === "family") {
      const currentId = activeVariant(entry.family);
      const isSelectedHere =
        selectedForActive !== undefined &&
        familyOfVariant(selectedForActive) === entry.family;
      const ownerSlot = entry.variants
        .map((v) => takenBy.get(v.id))
        .find((i) => i !== undefined && i !== activeSlot);
      const otherOwner = ownerSlot !== undefined;
      const previewsThis =
        previewId !== null && familyOfVariant(previewId) === entry.family;
      return (
        <button
          key={entry.family}
          type="button"
          role="option"
          aria-selected={previewsThis}
          className={`${styles.item} ${
            isSelectedHere ? styles.itemSelected : ""
          } ${previewsThis ? styles.itemPreview : ""} ${
            otherOwner ? styles.itemTaken : ""
          }`}
          onClick={() => setPreviewId(currentId)}
        >
          <CircularFactionIcon faction={currentId} size={22} />
          <span className={styles.itemName}>{entry.label}</span>
          {isSelectedHere && (
            <span className={styles.badgeSelected} aria-hidden>
              ✓
            </span>
          )}
          {otherOwner && (
            <span
              className={styles.badgeTaken}
              title={`Chosen by player ${(ownerSlot ?? 0) + 1}`}
              aria-hidden
            >
              G{(ownerSlot ?? 0) + 1}
            </span>
          )}
        </button>
      );
    }

    // Zwykła frakcja — jeden wiersz.
    const faction = entry.faction;
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
            title={`Chosen by player ${(takenBy.get(faction.id) ?? 0) + 1}`}
            aria-hidden
          >
            G{(takenBy.get(faction.id) ?? 0) + 1}
          </span>
        )}
      </button>
    );
  };

  return (
    <div className={styles.stage}>
      {/* Pasek górny: Wstecz · przełącznik graczy · Start gry (zastępuje ramkę kreatora). */}
      <div className={styles.topBar}>
        <button type="button" className={styles.backButton} onClick={stage?.onBack}>
          ← Back
        </button>

        <div className={styles.playerBar} role="tablist" aria-label="Players">
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
                <span className={styles.playerTabHead}>Player {index + 1}</span>
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
          <span className={styles.topMessage}>{stage.message}</span>
        )}

        {/*
         * Strefa startu: czytelny podpis gotowości + duży, „świecący" przycisk startu.
         * Przycisk jest głównym wezwaniem do akcji sceny — wyróżniony kolorem akcentu,
         * większy od reszty paska i pulsujący, gdy wszyscy gracze są gotowi, żeby nie
         * ginął w prawym górnym rogu.
         */}
        <div className={styles.startZone}>
          <span className={styles.readyLabel}>
            {allChosen ? (
              <span className={styles.readyAll}></span>
            ) : (
              <span className={styles.readyPartial}>
                {chosenCount} of {slots.length} empires chosen
              </span>
            )}
          </span>
          <button
            type="button"
            className={`${styles.startButton} ${ready ? styles.startButtonReady : ""}`}
            disabled={!stage?.canSubmit || stage?.submitting}
            onClick={stage?.onSubmit}
          >
            {stage?.submitting ? "Starting…" : "Start game"}
            <span className={styles.startArrow} aria-hidden>
              →
            </span>
          </button>
        </div>
      </div>

      {/* Zawartość: portret+lore (tło pełnoekranowe) | detail (szkło) | lista (prawo). */}
      <div className={styles.content}>
        {/* Strefa postaci: strefa jest zawsze (zajmuje wolne miejsce), zawartość
            remontowana przy zmianie frakcji — to odtwarza wolne wyłanianie. */}
        <div
          className={`${styles.characterZone} ${
            stageFaction && hasFactionQuote(stageFaction.id)
              ? styles.characterZoneQuote
              : ""
          }`}
          // Środek widocznej sylwetki — nagłówek (nazwa/cytat) centruje się nad nią.
          style={
            figureCx !== null
              ? ({ ["--figure-cx" as string]: `${figureCx}px` } as React.CSSProperties)
              : undefined
          }
        >
          {stageFaction && (
            <Fragment key={`character-${stageFaction.id}`}>
              <FactionPortraitLayer
                faction={stageFaction}
                onFigureCenter={setFigureCx}
              />
              <FactionHeader faction={stageFaction} />
              <div className={styles.loreSlot}>
                <FactionLore faction={stageFaction} />
              </div>
            </Fragment>
          )}
        </div>

        {/* Summary (detail) — wąski pasek na szkle. */}
        <div className={styles.detail} key={`detail-${previewFaction?.id ?? "empty"}`}>
          <FactionSummary
            faction={previewFaction}
            onActiveFactionChange={setStageFaction}
            variantSwitch={variantSwitch}
            // Wybór technologii startowych pokazujemy TYLKO, gdy oglądana frakcja jest
            // przypisana aktywnemu graczowi (wtedy zapis idzie do jego slotu). Scala to
            // dawny osobny krok „Technologie startowe" w ten panel. Frakcje z ODROCZONYM
            // wyborem (Keleres, Deepwrought) wybierają w grze — nie dostają panelu wyboru,
            // tylko komunikat w summary, więc nie przekazujemy im propsów wyboru.
            startingTech={
              previewFaction &&
              selectedForActive === previewFaction.id &&
              !hasDeferredStartingTech(previewFaction.id)
                ? {
                    value: slots[activeSlot]?.startingTech ?? [],
                    onChange: (techs) =>
                      updateSlot(activeSlot, { startingTech: techs }),
                  }
                : undefined
            }
          />
        </div>

        {/*
         * Przycisk wyboru — OSOBNY, wyśrodkowany element na dole sceny (nie w panelu
         * szczegółów). Pokazywany dla oglądanej frakcji; po wyborze zmienia się w stan
         * „zatwierdzone". `key` odtwarza płynne pojawienie się przy zmianie frakcji.
         */}
        {previewFaction && (
          <div className={styles.pickBar} key={`pick-${previewFaction.id}`}>
            {previewTakenByOther && (
              <p className={styles.pickNote}>
                This faction is already chosen by player{" "}
                {(takenBy.get(previewFaction.id) ?? 0) + 1}. Choosing it will assign it to player{" "}
                {activeSlot + 1} (a duplicate will block starting the game).
              </p>
            )}
            <button
              type="button"
              className={`${styles.pickButton} ${
                selectedForActive === previewFaction.id ? styles.pickButtonDone : ""
              }`}
              aria-disabled={selectedForActive === previewFaction.id}
              onClick={() => {
                if (selectedForActive !== previewFaction.id) assign(previewFaction.id);
              }}
            >
              {selectedForActive === previewFaction.id
                ? `✓ Chosen for player ${activeSlot + 1}`
                : `Choose for player ${activeSlot + 1}`}
            </button>
          </div>
        )}

        {/* Lista frakcji (prawo) — sam klik wybiera podgląd, bez hover-popoverów. */}
        <div className={styles.gallery}>
          <TextInput
            placeholder="Search factions…"
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            aria-label="Search factions"
          />
          <div className={styles.list} role="listbox" aria-label="Factions">
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
              <span className={styles.itemName}>Random</span>
            </button>

            {/* Sekcje wg dodatków (Base Game / PoK / Thunder's Edge) z nagłówkami. */}
            {sections.map((section) => (
              <div key={section.group} className={styles.section} role="group">
                <div className={styles.sectionHeader}>{section.label}</div>
                {section.entries.map((entry) => renderEntry(entry))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

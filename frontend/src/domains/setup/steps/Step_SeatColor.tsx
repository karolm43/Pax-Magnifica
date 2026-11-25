// Krok setupu: kolor (Step_SeatColor) — ostatni krok kreatora.
//
// Kolor wybieramy PO frakcji, bo każda frakcja ma listę preferowanych kolorów
// (`preferred_colours` z danych AsyncTI4). Miejsce przy stole NIE jest tu wybierane —
// ustala je lobby (krok 1, `Step_Players`); tu widać je tylko w opisie gracza.
//   - pasek górny: ← Back · tytuł · przycisk „Start game";
//   - lewa kolumna: gracze (frakcja, miejsce, kolor) — klik wybiera, kogo konfigurujemy;
//   - prawy panel: kolory preferowane przez frakcję oraz pełna paleta AsyncTI4.
//
// Duplikatów nie da się zrobić: wybór koloru zajętego przez innego gracza ZAMIENIA oba
// (`swapColor`). Gracz z losową frakcją nie ma jeszcze preferencji (frakcję dobiera
// backend przy starcie gry).

import { canEditSlot, useLobbyRole } from "@/domains/network/setupSync";
import { IconDice5, IconStar } from "@tabler/icons-react";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import { SpriteUnitImage } from "@/shared/ui/Unit/components/SpriteUnitImage";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import type { SetupStepProps } from "../SetupWizard";
import {
  RANDOM_FACTION,
  useSetupStore,
  type SetupSlot,
} from "../useSetupStore";
import {
  COLOR_KINDS,
  COLOR_KIND_LABEL,
  PLAYER_COLOR_OPTIONS,
  colorAccent,
  colorLabel,
  colorSwatchBackground,
  preferredColorsOf,
} from "../playerColors";
import base from "./Step_Players.module.css";
import styles from "./Step_SeatColor.module.css";

/** Jednostki w podglądzie koloru (flota + naziemne + struktury). */
const PREVIEW_UNITS = ["dn", "ca", "dd", "ff", "gf", "sd", "pd"] as const;

/** Podgląd koloru na jednostkach (te same sprite'y co na mapie). */
function UnitPreview({ alias }: { alias: string }) {
  return (
    <div className={styles.unitRow} aria-label="Unit preview">
      {PREVIEW_UNITS.map((unit) => {
        const sprite = getUnitSprite(alias, unit);
        return sprite ? (
          <SpriteUnitImage key={unit} sprite={sprite} alt={`${colorLabel(alias)} ${unit}`} />
        ) : null;
      })}
    </div>
  );
}

/** Nazwa frakcji slotu albo „Random faction". */
function factionName(slot: SetupSlot, factionById: SetupStepProps["factionById"]): string {
  if (slot.factionId === RANDOM_FACTION) return "Random faction";
  return factionById.get(slot.factionId)?.name ?? slot.factionId;
}

/** Przycisk-próbka koloru z oznaczeniem wybranego / zajętego / preferowanego. */
function Swatch({
  alias,
  selected,
  preferred,
  owner,
  onPick,
}: {
  alias: string;
  selected: boolean;
  preferred: boolean;
  /** Numer gracza, który ma ten kolor (klik = zamiana), albo `null`. */
  owner: number | null;
  onPick: () => void;
}) {
  const label = colorLabel(alias);
  const title = [
    label,
    preferred ? "preferred by this faction" : null,
    owner !== null ? `swap with Player ${owner + 1}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      aria-label={title}
      title={title}
      className={`${styles.swatch} ${selected ? styles.swatchOn : ""} ${
        preferred ? styles.swatchPreferred : ""
      }`}
      style={{ background: colorSwatchBackground(alias) }}
      onClick={onPick}
    >
      {owner !== null && (
        <span className={styles.swatchOwner} aria-hidden>
          {owner + 1}
        </span>
      )}
    </button>
  );
}

export default function Step_SeatColor({ factions, factionById, stage }: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);
  const swapColor = useSetupStore((s) => s.swapColor);
  const shuffleColors = useSetupStore((s) => s.shuffleColors);
  const applyPreferredColors = useSetupStore((s) => s.applyPreferredColors);
  const rollRandomFactions = useSetupStore((s) => s.rollRandomFactions);

  // Lobby sieciowe (RULES.md 44.5a): gość ustawia tylko swój kolor i miejsce; losowanie
  // frakcji „Random" robi host (jedno źródło — inaczej każdy klient losowałby co innego).
  const role = useLobbyRole();
  const guestSlot = role.active && role.isGuest ? role.mySlot : null;
  const isGuest = role.active && role.isGuest;

  // Gracze z „Random" dostają frakcję już tutaj, więc znamy ich preferowane kolory.
  useEffect(() => {
    if (factions.length > 0 && !isGuest) rollRandomFactions(factions);
  }, [factions, rollRandomFactions, isGuest]);

  const [activeIndex, setActiveIndex] = useState(0);
  useEffect(() => {
    if (guestSlot !== null) setActiveIndex(guestSlot);
  }, [guestSlot]);
  const active = slots[Math.min(activeIndex, slots.length - 1)];
  const activeSlotIndex = slots.indexOf(active);

  const colorOwner = (alias: string): number | null => {
    const i = slots.findIndex((s, idx) => idx !== activeSlotIndex && s.color === alias);
    return i >= 0 ? i : null;
  };

  const activeFaction =
    active.factionId !== RANDOM_FACTION ? factionById.get(active.factionId) : undefined;
  const preferred = useMemo(
    () => preferredColorsOf(activeFaction?.preferred_colours),
    [activeFaction],
  );
  const preferredSet = useMemo(() => new Set(preferred), [preferred]);

  const sections = useMemo(
    () =>
      COLOR_KINDS.map((kind) => ({
        kind,
        options: PLAYER_COLOR_OPTIONS.filter((o) => o.kind === kind),
      })).filter((section) => section.options.length > 0),
    [],
  );

  return (
    <div className={base.stage}>
      <div className={base.topBar}>
        <button type="button" className={base.backButton} onClick={stage?.onBack}>
          ← Back
        </button>

        <div className={base.titleBlock}>
          <span className={base.kicker}>New game · Step 3 of 3</span>
          <h1 className={base.title}>Color</h1>
        </div>

        {stage?.message && <span className={base.topMessage}>{stage.message}</span>}

        <div className={base.startZone}>
          <button
            type="button"
            className={`${base.startButton} ${stage?.canSubmit ? base.startButtonReady : ""}`}
            disabled={!stage?.canSubmit || stage?.submitting}
            onClick={stage?.isLastStep ? stage?.onSubmit : stage?.onNext}
          >
            {stage?.submitting ? "Starting…" : "Start game"}
            <span className={base.startArrow} aria-hidden>
              →
            </span>
          </button>
        </div>
      </div>

      <div className={base.content}>
        {/* Lewa kolumna: gracze. */}
        <aside className={base.settings} aria-label="Players">
          <section className={base.section}>
            <h2 className={base.sectionTitle}>Players</h2>
            <div className={styles.playerList} role="tablist" aria-label="Players">
              {slots.map((slot, index) => (
                <button
                  key={index}
                  type="button"
                  role="tab"
                  aria-selected={index === activeSlotIndex}
                  className={`${styles.playerRow} ${
                    index === activeSlotIndex ? styles.playerRowOn : ""
                  }`}
                  style={{ "--pc": colorAccent(slot.color) } as CSSProperties}
                  onClick={() => {
                    if (canEditSlot(role, index)) setActiveIndex(index);
                  }}
                  aria-disabled={!canEditSlot(role, index)}
                >
                  <span
                    className={styles.playerChip}
                    style={{ background: colorSwatchBackground(slot.color) }}
                    aria-hidden
                  />
                  <span className={styles.playerInfo}>
                    <span className={styles.playerName}>
                      {slot.name.trim() || `Player ${index + 1}`}
                      {slot.controlType === "BOT" ? " · bot" : ""}
                      {role.active && role.mySlot === index ? " (you)" : ""}
                    </span>
                    <span className={styles.playerMeta}>
                      {slot.factionId !== RANDOM_FACTION && (
                        <CircularFactionIcon faction={slot.factionId} size={14} />
                      )}
                      {factionName(slot, factionById)} · seat {slot.seat + 1} ·{" "}
                      {colorLabel(slot.color)}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </section>

          {!isGuest && (
          <section className={base.section}>
            <h2 className={base.sectionTitle}>Quick setup</h2>
            <div className={base.actionList}>
              <button
                type="button"
                className={base.action}
                onClick={() => applyPreferredColors(factionById)}
              >
                <IconStar size={14} aria-hidden="true" /> Use preferred colors
              </button>
              <button type="button" className={base.action} onClick={shuffleColors}>
                <IconDice5 size={14} aria-hidden="true" /> Shuffle colors
              </button>
            </div>
            <p className={base.hint}>
              Picking a color held by another player swaps the two.
            </p>
          </section>
          )}
          {isGuest && (
            <section className={base.section}>
              <p className={base.hint}>
                Pick a free color. Everyone sees the choices live; the host starts
                the game.
              </p>
            </section>
          )}
        </aside>

        {/* Prawy panel: kolory aktywnego gracza (miejsce wybiera lobby, krok 1). */}
        <section className={styles.panel} aria-label="Color">
          <header className={styles.panelHead}>
            <h2 className={styles.panelTitle}>
              {active.name.trim() || `Player ${activeSlotIndex + 1}`}
            </h2>
            <span className={styles.panelSub}>{factionName(active, factionById)}</span>
          </header>

          <div className={styles.block}>
            <h3 className={base.sectionTitle}>
              Preferred by {activeFaction ? activeFaction.name : "the faction"}
            </h3>
            {preferred.length > 0 ? (
              <div className={styles.swatchRow} role="radiogroup" aria-label="Preferred colors">
                {preferred.map((alias) => (
                  <Swatch
                    key={alias}
                    alias={alias}
                    selected={active.color === alias}
                    preferred
                    owner={colorOwner(alias)}
                    onPick={() => swapColor(activeSlotIndex, alias)}
                  />
                ))}
              </div>
            ) : (
              <p className={base.hint}>
                {active.factionId === RANDOM_FACTION
                  ? "Random faction — pick any color."
                  : "This faction has no preferred colors."}
              </p>
            )}
          </div>

          <div className={styles.block}>
            <div className={styles.currentColor}>
              <span
                className={styles.currentChip}
                style={{ background: colorSwatchBackground(active.color) }}
                aria-hidden
              />
              <span>
                Color: <strong>{colorLabel(active.color)}</strong>
              </span>
            </div>
            <UnitPreview alias={active.color} />
            {sections.map(({ kind, options }) => (
              <div key={kind} className={styles.paletteSection}>
                <h3 className={base.sectionTitle}>{COLOR_KIND_LABEL[kind]}</h3>
                <div
                  className={styles.swatchRow}
                  role="radiogroup"
                  aria-label={`${COLOR_KIND_LABEL[kind]} colors`}
                >
                  {options.map((option) => (
                    <Swatch
                      key={option.alias}
                      alias={option.alias}
                      selected={active.color === option.alias}
                      preferred={preferredSet.has(option.alias)}
                      owner={colorOwner(option.alias)}
                      onPick={() => swapColor(activeSlotIndex, option.alias)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

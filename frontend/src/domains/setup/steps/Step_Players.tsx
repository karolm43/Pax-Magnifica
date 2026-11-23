// Krok setupu: gracze i mapa (Step_Players) — pierwszy krok po „Play".
//
// Pełnoekranowa scena w tym samym języku wizualnym co wybór frakcji (Step_Faction):
// to samo tło, pasek górny z „Wstecz" i dużym przyciskiem akcji, panele na szkle,
// bursztynowy akcent TI4. Układ:
//   - pasek górny: ← Main menu · tytuł kroku · podsumowanie (ludzie/boty) · „Choose factions →";
//   - lewy panel „Game": liczba graczy (2–6), mapa (domyślna / własny map string),
//     szybkie ustawienia (wszyscy ludzie, ja + boty);
//   - siatka kart graczy: nazwa, człowiek/bot, trudność i osobowość bota, miejsce przy
//     stole i strzałki zmiany numeru gracza (gracz 1 = mówca na start);
//   - plansza miejsc (`SeatBoard`): klik w kartę gracza, potem w miejsce = przesiadka.
//
// Gotowa mapa z domami (np. z draftu Milty): miejsce = frakcja domu, którą gracz dostaje
// domyślnie w kroku frakcji (`applySeatFactions`). Kolor wybiera ostatni krok
// (`Step_SeatColor`), bo zależy od frakcji.
//
// Odpowiedzialności (R7.1/R7.2/R7.4/R7.5):
//  1. dane zapisujemy WYŁĄCZNIE do store'a (`useSetupStore`) — jedno źródło prawdy;
//  2. lokalne podpowiedzi walidacji per slot (długość nazwy, duplikat nazwy). Twarde
//     blokowanie „Dalej" robi kontener przez `validateStep`/`validateSetup`.

import { canEditSlot, swapPlayers, useLobbyRole } from "@/domains/network/setupSync";
import { useState, type CSSProperties } from "react";
import { useEngineConfig } from "@/api/useNewGame";
import type { SetupStepProps } from "../SetupWizard";
import {
  MAX_NAME_LENGTH,
  MAX_PLAYERS,
  MIN_PLAYERS,
  RANDOM_MAP,
  type ControlType,
  type SetupSlot,
  useSetupStore,
} from "../useSetupStore";
import { colorAccent } from "../playerColors";
import { useMapSeatInfo } from "../useMapSeatInfo";
import { SeatBoard } from "./SeatBoard";
import styles from "./Step_Players.module.css";

/** Wartości dozwolonej liczby graczy (przyciski 2..6). */
const PLAYER_COUNTS = Array.from(
  { length: MAX_PLAYERS - MIN_PLAYERS + 1 },
  (_, i) => MIN_PLAYERS + i,
);

/**
 * Sposób przygotowania partii (frakcje + mapa). Dziś działa tylko „Standard"
 * (frakcję wybiera każdy gracz — także „Random" w scenie frakcji — a mapę host
 * w sekcji „Map"). Drafty to następny etap: widoczne jako niedostępne z powodem,
 * żeby lobby miało już docelowy kształt. Gdy draft powstanie, wybór trafi do
 * `useSetupStore` i szkicu lobby (`lobby_draft.py`), a krok draftu do `setupSteps.ts`.
 */
const SETUP_METHODS: { id: string; title: string; text: string; available: boolean }[] = [
  {
    id: "standard",
    title: "Standard",
    text: "Everyone picks a faction (or Random); the host chooses the map below.",
    available: true,
  },
  {
    id: "random",
    title: "Full random",
    text: "Random factions, seats and map for everyone.",
    available: false,
  },
  {
    id: "milty",
    title: "Milty Draft",
    text: "Draft a faction, a map slice and a seat in snake order.",
    available: false,
  },
  {
    id: "franken",
    title: "Franken Draft",
    text: "Build your own faction by drafting abilities and components.",
    available: false,
  },
];

/** Wartość „losowo" w selektorach bota (pusty string = `null` w store'ie). */
const RANDOM_OPTION = "";

/** Lokalny komunikat walidacji nazwy slotu (albo `null`) — źródłem blokady jest store. */
function slotNameError(slot: SetupSlot, index: number, slots: SetupSlot[]): string | null {
  const name = slot.name.trim();
  if (name.length > MAX_NAME_LENGTH) {
    return `At most ${MAX_NAME_LENGTH} characters.`;
  }
  if (name.length === 0) return null; // pusta nazwa jest OK — backend nada automatyczną
  // Duplikat niepustej nazwy (case-insensitive) z WCZEŚNIEJSZYM slotem — R7.5.
  const normalized = name.toLowerCase();
  for (let i = 0; i < index; i++) {
    if (slots[i].name.trim().toLowerCase() === normalized) {
      return `The name "${name}" is already used by Player ${i + 1}.`;
    }
  }
  return null;
}

/** Zakres opcji bota z `/engine/config` (zero hardkodowania konfiguracji silnika). */
interface BotOptions {
  difficulties: string[];
  personalities: string[];
  loading: boolean;
  failed: boolean;
}

/** Karta jednego gracza: numer w kolorze, nazwa, kolor, człowiek/bot, opcje bota. */
function PlayerCard({
  slot,
  index,
  slots,
  bot,
  selected,
  onSelect,
  seatHome,
}: {
  slot: SetupSlot;
  index: number;
  slots: SetupSlot[];
  bot: BotOptions;
  /** Ten gracz jest wybrany do przesiadki na planszy miejsc. */
  selected: boolean;
  onSelect: () => void;
  /** Pełna nazwa frakcji, której dom leży na miejscu gracza (gotowa mapa). */
  seatHome: string | null;
}) {
  const updateSlot = useSetupStore((s) => s.updateSlot);
  const setControlType = useSetupStore((s) => s.setControlType);
  // Lobby sieciowe (RULES.md 44.5a): kto siedzi na tym miejscu; gość edytuje tylko swój slot.
  const role = useLobbyRole();
  const editable = canEditSlot(role, index);
  const owner = role.active ? role.owners[index] : undefined;
  const ownerLabel = !role.active
    ? null
    : owner === "host"
      ? role.isGuest
        ? "Host"
        : "You (host)"
      : owner
        ? `${role.ownerNames[index] ?? "Player"}${role.mySlot === index ? " (you)" : ""} · joined`
        : slot.controlType === "HUMAN"
          ? "Open seat - waiting for a player…"
          : null;

  const nameError = slotNameError(slot, index, slots);
  const canReorder = !(role.active && role.isGuest);
  const move = (to: number) => void swapPlayers(index, to).catch(() => undefined);
  const isBot = slot.controlType === "BOT";
  const cardStyle = { "--pc": colorAccent(slot.color) } as CSSProperties;

  return (
    <article
      className={`${styles.card} ${selected ? styles.cardSelected : ""}`}
      style={cardStyle}
      aria-label={`Player ${index + 1}`}
    >
      <header className={styles.cardHead}>
        <span className={styles.badge} aria-hidden>
          {index + 1}
        </span>
        <h2 className={styles.cardTitle}>Player {index + 1}</h2>
        {canReorder && (
          <span className={styles.moveSet}>
            <button
              type="button"
              className={styles.moveButton}
              aria-label={`Make Player ${index + 1} Player ${index}`}
              title={index === 0 ? undefined : `Swap with Player ${index}`}
              disabled={index === 0}
              onClick={() => move(index - 1)}
            >
              ◀
            </button>
            <button
              type="button"
              className={styles.moveButton}
              aria-label={`Make Player ${index + 1} Player ${index + 2}`}
              title={index === slots.length - 1 ? undefined : `Swap with Player ${index + 2}`}
              disabled={index === slots.length - 1}
              onClick={() => move(index + 1)}
            >
              ▶
            </button>
          </span>
        )}
        <fieldset
          disabled={role.active && role.isGuest}
          className={styles.lockSet}
        >
        <div
          className={styles.segment}
          role="radiogroup"
          aria-label={`Player ${index + 1} control type`}
        >
          {(["HUMAN", "BOT"] as ControlType[]).map((type) => (
            <button
              key={type}
              type="button"
              role="radio"
              aria-checked={slot.controlType === type}
              className={`${styles.segmentItem} ${
                slot.controlType === type ? styles.segmentItemOn : ""
              }`}
              onClick={() => setControlType(index, type)}
            >
              {type === "HUMAN" ? "Human" : "Bot"}
            </button>
          ))}
        </div>
        </fieldset>
      </header>

      <button
        type="button"
        className={`${styles.seatChip} ${selected ? styles.seatChipOn : ""}`}
        aria-pressed={selected}
        onClick={onSelect}
        title="Select, then click a seat on the table to move this player"
      >
        Seat {slot.seat + 1}
        {seatHome && <span className={styles.seatHome}> · {seatHome} home</span>}
      </button>

      {ownerLabel && (
        <span
          className={`${styles.ownerChip} ${owner ? styles.ownerChipTaken : styles.ownerChipOpen}`}
        >
          {ownerLabel}
        </span>
      )}

      <fieldset disabled={!editable} className={styles.lockSet}>
      <label className={styles.field}>
        <span className={styles.fieldLabel}>Name</span>
        <input
          className={`${styles.input} ${nameError ? styles.inputError : ""}`}
          type="text"
          placeholder="(empty → automatic name)"
          value={slot.name}
          maxLength={MAX_NAME_LENGTH}
          onChange={(e) => updateSlot(index, { name: e.currentTarget.value })}
          aria-invalid={nameError !== null}
        />
        {nameError && <span className={styles.error}>{nameError}</span>}
      </label>

      {isBot && (
        <div className={styles.botBox}>
          {bot.loading ? (
            <span className={styles.hint}>Loading bot options…</span>
          ) : bot.failed ? (
            <span className={styles.error}>
              Failed to load bot options. Try again later.
            </span>
          ) : (
            <>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Difficulty</span>
                <select
                  className={styles.input}
                  aria-label={`Player ${index + 1} bot difficulty level`}
                  value={slot.difficulty ?? RANDOM_OPTION}
                  onChange={(e) =>
                    updateSlot(index, { difficulty: e.currentTarget.value || null })
                  }
                >
                  <option value={RANDOM_OPTION}>Random</option>
                  {bot.difficulties.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Personality</span>
                <select
                  className={styles.input}
                  aria-label={`Player ${index + 1} bot personality`}
                  value={slot.personality ?? RANDOM_OPTION}
                  onChange={(e) =>
                    updateSlot(index, { personality: e.currentTarget.value || null })
                  }
                >
                  <option value={RANDOM_OPTION}>Random</option>
                  {bot.personalities.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
        </div>
      )}
      </fieldset>
    </article>
  );
}

/**
 * Krok „Gracze i mapa": pasek górny + panel ustawień gry + karty graczy.
 * Walidacja żyje w store'ie; kontener (`SetupWizard`) blokuje „Dalej" przez `stage.canSubmit`.
 */
export default function Step_Players({ stage, factionById }: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);
  const playerCount = useSetupStore((s) => s.playerCount);
  const mapString = useSetupStore((s) => s.mapString);
  const setPlayerCount = useSetupStore((s) => s.setPlayerCount);
  const setMapString = useSetupStore((s) => s.setMapString);

  const applyControlPreset = useSetupStore((s) => s.applyControlPreset);
  const swapSeat = useSetupStore((s) => s.swapSeat);
  const { seatFactions, unknownTiles } = useMapSeatInfo();
  const factionName = (id: string) => factionById.get(id)?.name ?? id;
  // Gracz wybrany do przesiadki (klik w „Seat N" na karcie, potem w miejsce na planszy).
  const [seatPicker, setSeatPicker] = useState(0);
  const pickerIndex = Math.min(seatPicker, slots.length - 1);
  const role = useLobbyRole();
  const [copied, setCopied] = useState<string | null>(null);
  const copy = async (link: string) => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(link);
    } catch {
      window.prompt("Copy this link:", link);
    }
  };

  // Tryb mapy to wybór UI: „default" = mapa domyślna backendu (pusty map string),
  // „custom" = własny map string. Start zgodny z tym, co już jest w store'ie.
  const [mapMode, setMapMode] = useState<"default" | "random" | "custom">(
    mapString.trim() === RANDOM_MAP ? "random" : mapString.trim() ? "custom" : "default",
  );

  // Opcje bota pobieramy RAZ dla całego kroku (nie per karta).
  const { data: engineConfig, isLoading, isError } = useEngineConfig();
  const bot: BotOptions = {
    difficulties: engineConfig?.valid_difficulties ?? [],
    personalities: engineConfig?.valid_personalities ?? [],
    loading: isLoading,
    failed: isError,
  };

  const botCount = slots.filter((s) => s.controlType === "BOT").length;
  const humanCount = slots.length - botCount;

  const chooseMapMode = (mode: "default" | "random" | "custom") => {
    setMapMode(mode);
    // Powrót do mapy domyślnej czyści własny map string (backend użyje mapy testowej).
    if (mode === "default") setMapString("");
    // Losowa mapa: backend losuje kafelki przy starcie gry (nowa mapa przy każdej grze).
    if (mode === "random") setMapString(RANDOM_MAP);
    if (mode === "custom" && mapString.trim() === RANDOM_MAP) setMapString("");
  };

  return (
    <div className={styles.stage}>
      {/* Pasek górny: Wstecz · tytuł · podsumowanie · przycisk akcji (jak w scenie frakcji). */}
      <div className={styles.topBar}>
        <button type="button" className={styles.backButton} onClick={stage?.onBack}>
          {role.active && role.isGuest ? "← Leave lobby" : "← Main menu"}
        </button>

        <div className={styles.titleBlock}>
          <span className={styles.kicker}>New game · Step 1 of 3</span>
          <h1 className={styles.title}>Players &amp; map</h1>
        </div>

        {stage?.message && <span className={styles.topMessage}>{stage.message}</span>}

        <div className={styles.startZone}>
          <span className={styles.readyLabel}>
            {humanCount} {humanCount === 1 ? "human" : "humans"} · {botCount}{" "}
            {botCount === 1 ? "bot" : "bots"}
          </span>
          <button
            type="button"
            className={`${styles.startButton} ${
              stage?.canSubmit ? styles.startButtonReady : ""
            }`}
            disabled={!stage?.canSubmit || stage?.submitting}
            onClick={stage?.isLastStep ? stage?.onSubmit : stage?.onNext}
          >
            Choose factions
            <span className={styles.startArrow} aria-hidden>
              →
            </span>
          </button>
        </div>
      </div>

      <div className={styles.content}>
        {/* Lewy panel na szkle: ustawienia całej gry. */}
        <aside className={styles.settings} aria-label="Game settings">
          {role.active && !role.isGuest && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Invite friends</h2>
              <p className={styles.hint}>
                Friends open this link (ZeroTier / LAN), enter their name and take an open seat.
              </p>
              {role.links.length === 0 && (
                <p className={styles.error}>No network address found - is ZeroTier connected?</p>
              )}
              {role.links.map((link) => (
                <div key={link} className={styles.inviteRow}>
                  <code className={styles.inviteLink}>{link}</code>
                  <button type="button" className={styles.action} onClick={() => void copy(link)}>
                    {copied === link ? "Copied" : "Copy"}
                  </button>
                </div>
              ))}
            </section>
          )}
          {role.active && role.isGuest && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Lobby</h2>
              <p className={styles.hint}>
                The host sets up the map and the players. Next you pick your faction and color.
              </p>
            </section>
          )}
          <fieldset disabled={role.active && role.isGuest} className={styles.lockSet}>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Players</h2>
            <div
              className={styles.countRow}
              role="radiogroup"
              aria-label="Number of players"
            >
              {PLAYER_COUNTS.map((n) => (
                <button
                  key={n}
                  type="button"
                  role="radio"
                  aria-checked={playerCount === n}
                  className={`${styles.countButton} ${
                    playerCount === n ? styles.countButtonOn : ""
                  }`}
                  onClick={() => setPlayerCount(n)}
                >
                  {n}
                </button>
              ))}
            </div>
            <p className={styles.hint}>
              Lowering the count keeps the first players&apos; settings.
            </p>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Seats</h2>
            <SeatBoard
              slots={slots}
              activeIndex={pickerIndex}
              onPickSeat={(seat) => swapSeat(pickerIndex, seat)}
              seatFactions={seatFactions}
              factionName={factionName}
            />
            <p className={styles.hint}>
              Player {pickerIndex + 1} is selected: click a seat to move them (an occupied
              seat swaps). Player 1 is the first speaker; turns go clockwise around the table.
            </p>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Setup method</h2>
            <div className={styles.optionList} role="radiogroup" aria-label="Setup method">
              {SETUP_METHODS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  role="radio"
                  aria-checked={m.id === "standard"}
                  disabled={!m.available}
                  className={`${styles.option} ${m.id === "standard" ? styles.optionOn : ""}`}
                >
                  <span className={styles.optionHead}>
                    <span className={styles.optionTitle}>{m.title}</span>
                    {!m.available && <span className={styles.soon}>Soon</span>}
                  </span>
                  <span className={styles.optionText}>{m.text}</span>
                </button>
              ))}
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Map</h2>
            <div className={styles.optionList} role="radiogroup" aria-label="Map source">
              <button
                type="button"
                role="radio"
                aria-checked={mapMode === "default"}
                className={`${styles.option} ${
                  mapMode === "default" ? styles.optionOn : ""
                }`}
                onClick={() => chooseMapMode("default")}
              >
                <span className={styles.optionTitle}>Default map</span>
                <span className={styles.optionText}>
                  The built-in 6-player test layout.
                </span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={mapMode === "random"}
                className={`${styles.option} ${
                  mapMode === "random" ? styles.optionOn : ""
                }`}
                onClick={() => chooseMapMode("random")}
              >
                <span className={styles.optionTitle}>Random map</span>
                <span className={styles.optionText}>
                  Random systems on every ring, new layout each game.
                </span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={mapMode === "custom"}
                className={`${styles.option} ${
                  mapMode === "custom" ? styles.optionOn : ""
                }`}
                onClick={() => chooseMapMode("custom")}
              >
                <span className={styles.optionTitle}>Custom map string</span>
                <span className={styles.optionText}>
                  Paste an AsyncTI4 map string (tile numbers).
                </span>
              </button>
            </div>
            {mapMode === "custom" && (
              <textarea
                className={`${styles.input} ${styles.textarea}`}
                aria-label="Map string"
                placeholder="e.g. 23 49 77 66 71 39 …"
                rows={4}
                spellCheck={false}
                value={mapString}
                onChange={(e) => setMapString(e.currentTarget.value)}
              />
            )}
            {mapMode === "custom" && unknownTiles.length > 0 && (
              <p className={styles.error}>
                Unknown tiles (not in the enabled sources): {unknownTiles.join(", ")}
              </p>
            )}
            {mapMode === "custom" && seatFactions && (
              <p className={styles.hint}>
                This map has home systems: each player gets the faction of their seat by
                default (you can still change it in the next step).
              </p>
            )}
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Quick setup</h2>
            <div className={styles.actionList}>
              <button
                type="button"
                className={styles.action}
                onClick={() => applyControlPreset("HUMAN")}
              >
                All humans
              </button>
              <button
                type="button"
                className={styles.action}
                onClick={() => applyControlPreset("BOT")}
              >
                Me vs. bots
              </button>
            </div>
            <p className={styles.hint}>
              Names must be unique. An empty name is filled in automatically.
            </p>
          </section>
          </fieldset>
        </aside>

        {/* Siatka kart graczy — własne przewijanie. */}
        <section className={styles.grid} aria-label="Players">
          {slots.map((slot, index) => (
            <PlayerCard
              key={index}
              slot={slot}
              index={index}
              slots={slots}
              bot={bot}
              selected={index === pickerIndex}
              onSelect={() => setSeatPicker(index)}
              seatHome={(() => {
                const home = seatFactions?.[slot.seat];
                return home ? factionName(home) : null;
              })()}
            />
          ))}
        </section>
      </div>
    </div>
  );
}

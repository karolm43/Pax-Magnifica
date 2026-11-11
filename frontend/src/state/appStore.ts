import { create } from "zustand";
import { isMobileDevice } from "@/utils/isTouchDevice";
import {
  loadStoredChoice,
  mergeStoredSettings,
  readStoredObject,
  saveJsonSettings,
  saveStoredChoice,
} from "@/utils/localStorageSettings";
import type { ControlTokenDisplayMode } from "@/entities/game/controlTokenDisplay";

const STORAGE_KEY = "ti4_settings";
const THEME_STORAGE_KEY = "ti4_theme";

export const THEME_NAMES = [
  "midnightbluetheme",
  "midnightgraytheme",
  "midnightredtheme",
  "vaporwavetheme",
  "midnightviolettheme",
  "midnightgreentheme",
] as const;

type ThemeName = (typeof THEME_NAMES)[number];

const DEFAULT_THEME: ThemeName = "midnightgraytheme";

/** Removed themes and the theme a stored value migrates to. */
const DEPRECATED_THEMES: Record<string, ThemeName> = {
  bluetheme: "midnightbluetheme",
  slatetheme: "midnightgraytheme",
  midnighttheme: "midnightbluetheme",
  sunsettheme: "midnightgraytheme",
  magmatheme: "midnightgraytheme",
};

const CONTROL_TOKEN_DISPLAY_MODES: ControlTokenDisplayMode[] = [
  "always",
  "ambiguous",
  "empty",
];
const DEFAULT_SETTINGS: Settings = {
  isFirefox: false,
  settingsModalOpened: false,
  keyboardShortcutsModalOpened: false,
  overlaysEnabled: false,
  planetTypesMode: false,
  techSkipsMode: false,
  attachmentsMode: false,
  showPDSLayer: false,
  showControlLayer: false,
  controlTokenDisplayMode: "ambiguous",
  showExhaustedPlanets: true,
  animateEventPreviews: true,
  themeName: DEFAULT_THEME,
  accessibleColors: false,
  showPlayerAreaCommandTokens: true,
  showPlayerAreaArmyStrength: true,
  showPlayerAreaUnitUpgrades: true,
  showPlayerAreaTotalSpend: true,
  showPlayerAreaReinforcements: true,
  showPlayerAreaFactionAbilities: true,
  showPlayerAreaNeighborship: true,
  adminFastMode: false,
  absolAgendas: false,
  blackSpectrumFirmamentPlots: false,
  freeUnitDrag: false,
  skipPhases: false,
  chessClockEnabled: false,
  chessClockMinutes: 120,
  chessClockIncrementSeconds: 30,
};

/** Legacy settings stored a boolean `showControlTokens` instead of the mode. */
function resolveControlTokenDisplayMode(
  stored: Record<string, unknown> | null,
): ControlTokenDisplayMode {
  const storedMode = CONTROL_TOKEN_DISPLAY_MODES.find(
    (mode) => mode === stored?.controlTokenDisplayMode,
  );
  if (storedMode) return storedMode;
  if (typeof stored?.showControlTokens !== "boolean") return "ambiguous";
  return stored.showControlTokens ? "always" : "empty";
}

function loadSettingsFromStorage(): Settings {
  const stored = readStoredObject(STORAGE_KEY);
  return {
    ...mergeStoredSettings(stored, DEFAULT_SETTINGS),
    controlTokenDisplayMode: resolveControlTokenDisplayMode(stored),
  };
}

function saveSettingsToStorage(settings: Settings) {
  saveJsonSettings<Settings>(STORAGE_KEY, settings);
}

function loadThemeFromStorage(): ThemeName {
  const deprecated = loadStoredChoice(
    THEME_STORAGE_KEY,
    Object.keys(DEPRECATED_THEMES),
  );
  if (deprecated) {
    const migrated = DEPRECATED_THEMES[deprecated];
    saveThemeToStorage(migrated);
    return migrated;
  }
  return loadStoredChoice(THEME_STORAGE_KEY, THEME_NAMES) ?? DEFAULT_THEME;
}

function saveThemeToStorage(themeName: Settings["themeName"]) {
  saveStoredChoice(THEME_STORAGE_KEY, themeName, "theme");
}

const defaultZoomIndex = 2;
const zoomLevels = [
  0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 0.85, 0.9, 1, 1.2, 1.4, 1.6, 1.8, 2,
];

function getInitialZoomIndex() {
  const savedZoomIndex = localStorage.getItem("zoomIndex");
  if (savedZoomIndex !== null) {
    return parseInt(savedZoomIndex, 10);
  }
  return isMobileDevice() ? 0 : defaultZoomIndex;
}

/** Wybór celu na mapie (patrz ``AppStore.mapPick``). */
export type MapPick = {
  kind: "system" | "planet";
  /** Dozwolone cele: pozycje systemów (``kind=system``) albo id planet (``kind=planet``). */
  targets: string[];
  onPick: (target: string) => void;
  /** Kolor podświetlenia (np. kolor karty strategii); domyślnie akcent. */
  hue?: string;
  /** Aktualnie wybrany cel (rysowany mocniej). */
  selected?: string | null;
};

type AppStore = {
  hoveredPlanetId: string | null;
  scrollToPlanetId: string | null;
  zoomLevel: number;
  zoomFitToScreen: boolean;
  setHoveredPlanetId: (planetId: string | null) => void;
  setScrollToPlanetId: (planetId: string | null) => void;

  /** The system whose dossier modal is open, or null when closed. */
  systemDossier: { position: string; systemId: string } | null;
  openSystemDossier: (position: string, systemId: string) => void;
  closeSystemDossier: () => void;

  /*
   * Tryb przenoszenia jednostek (God-Mode). Gdy aktywny, klik w kafelek wybiera
   * najpierw ŹRÓDŁO, potem CEL — po czym pojawia się menu „co przenieść".
   */
  moveMode: boolean;
  moveFrom: string | null; // pozycja źródłowa
  movePair: { from: string; to: string } | null; // komplet (otwiera menu)
  toggleMoveMode: () => void;
  pickMoveTile: (position: string) => void;
  clearMove: () => void;

  /*
   * Tryb aktywacji systemu (akcja taktyczna E3). Gdy aktywny, klik w kafelek
   * aktywuje system (kładzie żeton dowodzenia aktywnego gracza) zamiast otwierać
   * dossier. Samo wywołanie API robi panel taktyczny — store trzyma tylko flagę
   * oraz ostatnio klikniętą pozycję do odebrania przez panel.
   */
  activateMode: boolean;
  activateRequest: string | null; // pozycja do aktywacji (odbierana przez panel)
  toggleActivateMode: () => void;
  pickActivateTile: (position: string) => void;
  clearActivateRequest: () => void;

  /*
   * Wybór CELU NA MAPIE dla okien gry (karty strategii: system w Diplomacy / Warfare,
   * planeta pod strukturę w Construction). Okno ustawia listę dozwolonych celów i
   * callback; ``MapTile`` / ``PlanetCirclesLayer`` podświetlają cele i przekazują klik.
   * Ma pierwszeństwo przed dossier i trybami ruchu/aktywacji. ``null`` = brak wyboru.
   */
  mapPick: MapPick | null;
  setMapPick: (pick: MapPick | null) => void;

  /*
   * Podgląd zasięgu ruchu (krok MOVEMENT akcji taktycznej): zbiór pozycji systemów,
   * z których gracz ma statki mogące legalnie ruszyć do aktywnego systemu. Ustawiany
   * przez panel ruchu (z ``/tactical/move-range``), czytany przez ``MapTile`` do
   * podświetlenia heksów. Pusty zbiór = brak podglądu.
   */
  moveRangeSources: Set<string>;
  setMoveRangeSources: (positions: Set<string>) => void;
  /**
   * Gracz ŚWIADOMIE używa Gravity Drive (+1 do ruchu jednego statku w tej akcji). Dołączane do
   * każdego walidowanego ruchu (`/tactical/move`) i do podglądu zasięgu; silnik nigdy nie włącza
   * tej premii sam (RULES.md 56).
   */
  gravityDrive: boolean;
  setGravityDrive: (on: boolean) => void;
  /** Gracz świadomie używa Ionian Fuel Refinery (+1 do ruchu jednego statku, RULES.md 60). */
  tempesta: boolean;
  setTempesta: (on: boolean) => void;

  /*
   * Okno ZAŁADUNKU transportu (krok MOVEMENT, RULES.md 32.3). Gdy ustawione, otwarte
   * jest okno „pakowania": wybrany statek-nosiciel w systemie źródłowym + dostępny
   * ładunek (myśliwce/siły naziemne) z tego systemu, do spakowania w ramach capacity
   * i ruszenia razem do aktywnego systemu jednym walidowanym /tactical/move.
   */
  loadTransport: {
    fromPosition: string;
    faction: string;
    shipAsyncId: string; // nosiciel (carrier/dread/warsun/flagship)
    // Wstępnie zaznaczony ładunek (gdy okno otwarto przez upuszczenie jednostki NA
    // statek) — asyncId + strefa źródłowa ("space" albo id planety) + liczba.
    preselect?: { asyncId: string; fromZone: string; count: number };
  } | null;
  openLoadTransport: (
    target: NonNullable<AppStore["loadTransport"]>,
  ) => void;
  closeLoadTransport: () => void;

  /*
   * Podczas przeciągania ŁADUNKU: statek-nosiciel pod kursorem, na który upuszczenie
   * otworzy okno załadunku („włóż do statku"). Ustawiany na żywo w trakcie gestu
   * (useUnitDrag.onMove), czyszczony po zakończeniu. Pozwala UI podświetlić ten statek
   * i pokazać na „duchu" sygnał „załaduj". ``asyncId`` + ``position`` identyfikują stos.
   */
  /*
   * Okno pola bitwy (RULES.md 39) jest pełnoekranowe i pokazuje się samo, gdy trwa walka.
   * ``battleHidden`` pozwala je chwilowo schować (podgląd mapy) — wraca przyciskiem
   * „Return to battle" w doku albo pływającej plakietce.
   */
  battleHidden: boolean;
  setBattleHidden: (hidden: boolean) => void;
  /** Okno produkcji (RULES.md 33.3): domyślnie ZAMKNIĘTE (true); otwiera je przycisk „Open production". */
  productionHidden: boolean;
  setProductionHidden: (hidden: boolean) => void;
  /** Okno Rady Galaktycznej (faza agendy, RULES.md 51): domyślnie OTWARTE; „Show board" je chowa. */
  agendaHidden: boolean;
  setAgendaHidden: (hidden: boolean) => void;

  dragLoadTarget: { position: string; asyncId: string } | null;
  setDragLoadTarget: (
    target: { position: string; asyncId: string } | null,
  ) => void;

  /*
   * Okno walki (asystent trafień, E3). Gdy ustawione, otwarty jest modal walki dla
   * danego miejsca: ``planet`` = null → walka kosmiczna, inaczej walka naziemna.
   */
  combatTarget: { position: string; planet: string | null } | null;
  openCombat: (position: string, planet: string | null) => void;
  closeCombat: () => void;

  /*
   * Przeciągnięcie jednostki (drag-and-drop na mapie). Po upuszczeniu sprite'a na
   * inną strefę/kafelek zapisujemy TU zamiar przeniesienia; gdy stos ma >1 sztukę,
   * otwiera się pytanie „ile przenieść", inaczej przenosimy od razu. Zero reguł —
   * to wygodny God-Mode (operator decyduje). Pola camelCase = jak endpoint move.
   */
  unitDrop: {
    fromPosition: string;
    fromZone: string;
    toPosition: string;
    toZone: string;
    toLabel: string; // czytelna etykieta celu (np. „Orbita" / nazwa planety)
    faction: string;
    asyncId: string;
    available: number; // ile sztuk jest w źródle (górny limit)
    // Ruch TAKTYCZNY (walidowany) — gdy true, drop celuje w aktywny system i idzie
    // przez /tactical/move (reguły R1–R6 + capacity), a nie God-Mode /units/move.
    tactical?: boolean;
  } | null;
  beginUnitDrop: (drop: NonNullable<AppStore["unitDrop"]>) => void;
  clearUnitDrop: () => void;

  /*
   * Zaznaczenie wielu jednostek (Ctrl+klik) do wspólnego ruchu taktycznego. Jedno
   * kliknięcie = +1 sztuka danego stosu (po wyczerpaniu stosu kolejny klik zdejmuje
   * zaznaczenie). Zaznaczenie dotyczy jednego systemu źródłowego i jednej frakcji.
   * Klucz pozycji: ``asyncId|strefa``.
   */
  multiSelect: {
    fromPosition: string;
    faction: string;
    items: Record<string, { asyncId: string; fromZone: string; count: number }>;
  } | null;
  /** Dodaje 1 sztukę do zaznaczenia (cyklicznie: po ``max`` zdejmuje wpis). */
  ctrlPickUnit: (pick: {
    fromPosition: string;
    faction: string;
    asyncId: string;
    fromZone: string;
    max: number;
  }) => void;
  clearMultiSelect: () => void;

  /** Czy trwa przeciąganie jednostki (chowa tooltip na czas gestu). */
  isDraggingUnit: boolean;
  setDraggingUnit: (dragging: boolean) => void;

  /*
   * Przelotny komunikat dla gracza (np. odrzucona akcja: „system już aktywowany",
   * „za mało zasobów"). ``kind`` steruje kolorem. Ustawiany przez akcje (np. gdy
   * endpoint zwróci 422), czyszczony przez UI lub kolejny komunikat.
   */
  notice: { text: string; kind: "error" | "info" } | null;
  setNotice: (text: string, kind?: "error" | "info") => void;
  clearNotice: () => void;

  /*
   * Cel pod kursorem w trakcie przeciągania jednostki — do podświetlenia kafelka
   * (planszówkowy feedback „tu upuścisz"). ``zone`` = strefa docelowa po mapowaniu
   * (statek zawsze trafia w orbitę), ``valid`` = czy upuszczenie jest dozwolone.
   */
  dragOver: { position: string; zone: string; valid: boolean } | null;
  setDragOver: (over: AppStore["dragOver"]) => void;

  handleZoomIn: () => void;
  handleZoomOut: () => void;
  handleZoomReset: () => void;
  /** Snaps zoom to the largest ladder step that fits `contentWidth` into `viewportWidth`. */
  handleZoomFitToWidth: (contentWidth: number, viewportWidth: number) => number;
  handleZoomScreenSize: () => void;
};

export const useAppStore = create<AppStore>((set) => {
  let zoomIndex = getInitialZoomIndex();
  let zoomFitToScreen = localStorage.getItem("zoomFitToScreen") === "true";

  const changeZoomFitToScreen = (val: boolean) => {
    zoomFitToScreen = val;
    localStorage.setItem("zoomFitToScreen", val.toString());
  };

  const applyZoomIndex = (index: number) => {
    zoomIndex = index;
    localStorage.setItem("zoomIndex", index.toString());
    changeZoomFitToScreen(false);
    set({ zoomLevel: zoomLevels[index], zoomFitToScreen: false });
  };

  return {
    hoveredPlanetId: null,
    scrollToPlanetId: null,
    zoomLevel: zoomLevels[zoomIndex],
    zoomFitToScreen,

    systemDossier: null,
    openSystemDossier: (position: string, systemId: string) =>
      set({ systemDossier: { position, systemId } }),
    closeSystemDossier: () => set({ systemDossier: null }),

    moveMode: false,
    moveFrom: null,
    movePair: null,
    toggleMoveMode: () =>
      set((s) => ({
        moveMode: !s.moveMode,
        moveFrom: null,
        movePair: null,
        activateMode: false,
        activateRequest: null,
      })),
    pickMoveTile: (position: string) =>
      set((s) => {
        if (!s.moveMode) return {};
        // Pierwszy klik = źródło; drugi klik = cel (otwiera menu).
        if (s.moveFrom === null) return { moveFrom: position };
        if (position === s.moveFrom) return { moveFrom: null }; // odkliknięcie
        return { movePair: { from: s.moveFrom, to: position } };
      }),
    clearMove: () => set({ moveFrom: null, movePair: null }),

    activateMode: false,
    activateRequest: null,
    // Włączenie trybu aktywacji wyłącza tryb przenoszenia (i odwrotnie) — jeden
    // tryb klikania naraz, by klik w kafelek miał jednoznaczne znaczenie.
    toggleActivateMode: () =>
      set((s) => ({
        activateMode: !s.activateMode,
        activateRequest: null,
        moveMode: false,
        moveFrom: null,
        movePair: null,
      })),
    pickActivateTile: (position: string) =>
      set((s) => (s.activateMode ? { activateRequest: position } : {})),
    clearActivateRequest: () => set({ activateRequest: null }),

    mapPick: null,
    setMapPick: (pick: MapPick | null) => set({ mapPick: pick }),

    moveRangeSources: new Set<string>(),
    setMoveRangeSources: (positions: Set<string>) =>
      set({ moveRangeSources: positions }),
    gravityDrive: false,
    setGravityDrive: (on: boolean) => set({ gravityDrive: on }),
    tempesta: false,
    setTempesta: (on: boolean) => set({ tempesta: on }),

    loadTransport: null,
    openLoadTransport: (target) => set({ loadTransport: target }),
    closeLoadTransport: () => set({ loadTransport: null }),

    battleHidden: false,
    setBattleHidden: (hidden: boolean) => set({ battleHidden: hidden }),
    productionHidden: true,
    setProductionHidden: (hidden: boolean) => set({ productionHidden: hidden }),
    agendaHidden: false,
    setAgendaHidden: (hidden: boolean) => set({ agendaHidden: hidden }),

    dragLoadTarget: null,
    setDragLoadTarget: (target) => set({ dragLoadTarget: target }),

    combatTarget: null,
    openCombat: (position: string, planet: string | null) =>
      set({ combatTarget: { position, planet } }),
    closeCombat: () => set({ combatTarget: null }),

    unitDrop: null,
    beginUnitDrop: (drop) => set({ unitDrop: drop }),
    clearUnitDrop: () => set({ unitDrop: null }),

    multiSelect: null,
    ctrlPickUnit: ({ fromPosition, faction, asyncId, fromZone, max }) =>
      set((state) => {
        const cur = state.multiSelect;
        // Inny system/frakcja niż dotychczasowe zaznaczenie → zaczynamy od nowa.
        const base =
          cur && cur.fromPosition === fromPosition && cur.faction === faction
            ? cur.items
            : {};
        const key = `${asyncId}|${fromZone}`;
        const next = { ...base };
        const have = next[key]?.count ?? 0;
        if (have + 1 > max) delete next[key];
        else next[key] = { asyncId, fromZone, count: have + 1 };
        return {
          multiSelect:
            Object.keys(next).length > 0
              ? { fromPosition, faction, items: next }
              : null,
        };
      }),
    clearMultiSelect: () => set({ multiSelect: null }),

    notice: null,
    setNotice: (text, kind = "error") => set({ notice: { text, kind } }),
    clearNotice: () => set({ notice: null }),

    isDraggingUnit: false,
    setDraggingUnit: (dragging: boolean) => set({ isDraggingUnit: dragging }),

    dragOver: null,
    setDragOver: (over) => set({ dragOver: over }),

    setHoveredPlanetId: (planetId: string | null) =>
      set({ hoveredPlanetId: planetId }),
    setScrollToPlanetId: (planetId: string | null) =>
      set({ scrollToPlanetId: planetId }),

    handleZoomIn: () =>
      applyZoomIndex(Math.min(zoomIndex + 1, zoomLevels.length - 1)),
    handleZoomOut: () => applyZoomIndex(Math.max(zoomIndex - 1, 0)),
    handleZoomReset: () =>
      applyZoomIndex(isMobileDevice() ? 0 : defaultZoomIndex),
    /*
     * Largest ladder step whose scaled content still fits the given width.
     *
     * Snapped to the ladder rather than taking the raw ratio: zoom in/out step by
     * index, so an off-ladder value would make the next press jump to whatever
     * index happened to be current. Distinct from handleZoomScreenSize, which is
     * a persisted boolean the legacy image view reads and which computes nothing.
     */
    handleZoomFitToWidth: (contentWidth: number, viewportWidth: number) => {
      if (contentWidth <= 0 || viewportWidth <= 0) return zoomLevels[zoomIndex];
      const target = viewportWidth / contentWidth;
      let fitIndex = 0;
      for (let i = 0; i < zoomLevels.length; i++) {
        if (zoomLevels[i] <= target) fitIndex = i;
      }
      applyZoomIndex(fitIndex);
      return zoomLevels[fitIndex];
    },
    handleZoomScreenSize: () => {
      changeZoomFitToScreen(!zoomFitToScreen);
      set({ zoomFitToScreen });
    },
  };
});

export type Settings = {
  isFirefox: boolean;
  settingsModalOpened: boolean;
  keyboardShortcutsModalOpened: boolean;
  overlaysEnabled: boolean;
  planetTypesMode: boolean;
  techSkipsMode: boolean;
  attachmentsMode: boolean;
  showPDSLayer: boolean;
  showControlLayer: boolean;
  controlTokenDisplayMode: ControlTokenDisplayMode;
  showExhaustedPlanets: boolean;
  animateEventPreviews: boolean;
  themeName: ThemeName;
  accessibleColors: boolean;
  showPlayerAreaCommandTokens: boolean;
  showPlayerAreaArmyStrength: boolean;
  showPlayerAreaUnitUpgrades: boolean;
  showPlayerAreaTotalSpend: boolean;
  showPlayerAreaReinforcements: boolean;
  showPlayerAreaFactionAbilities: boolean;
  showPlayerAreaNeighborship: boolean;
  /*
   * Tryb administratora / szybkie testowanie. Gdy włączony, silnik POMIJA oprawę
   * wizualną spowalniającą testy: planszę otwierającą (`GameIntro`) i pełnoekranowe
   * plansze przejścia faz (`PhaseTransitionBanner`). Reguły gry pozostają bez zmian —
   * to wyłącznie przyspieszenie przejść dla dewelopera.
   */
  adminFastMode: boolean;
  /*
   * FAN-AGENDAS: talia agend Absol zamiast standardowej (PoK). Czytana przy tworzeniu NOWEJ gry
   * (`createNewGame` wysyła `agenda_deck`); zmiana nie wpływa na grę w toku.
   */
  absolAgendas: boolean;
  /*
   * Black Spectrum Firmament Plots zamiast standardowych Firmament Plots (fanowska
   * zmiana). Podmienia karty Plot w wyborze frakcji (FactionSummary) i w szczegółach
   * ploty w grze (Plot). Tylko WYŚWIETLANIE — efekty plotów nie są egzekwowane przez
   * silnik (patrz README, „Plany").
   */
  blackSpectrumFirmamentPlots: boolean;
  /*
   * Swobodne przeciąganie jednostek (God-Mode). Wyłączone (domyślnie): drag na mapie
   * przenosi jednostki WYŁĄCZNIE do aktywnego systemu (walidowany ruch taktyczny).
   * Włączone: jednostkę można upuścić w dowolnym miejscu (omija reguły, /units/move).
   */
  freeUnitDrag: boolean;
  /*
   * Przeskok faz (God-Mode, testy). Włączone: w panelu tury pojawia się przycisk
   * „Skip phase" (/phase/skip) omijający bramy, okna i wybór kart strategii.
   * Wyłączone (domyślnie): zwykły, walidowany przepływ.
   */
  skipPhases: boolean;
  /*
   * Zegar szachowy (RULES.md 58): pula minut na gracza + dodatek (s) za zakończoną turę.
   * Czytany przy tworzeniu NOWEJ gry (`createNewGame` wysyła `chess_clock`); gra w toku
   * zachowuje swój zegar.
   */
  chessClockEnabled: boolean;
  chessClockMinutes: number;
  chessClockIncrementSeconds: number;
};

type BooleanSettingKey = {
  [K in keyof Settings]: Settings[K] extends boolean ? K : never;
}[keyof Settings];

type SettingsHandlers = {
  updateSettings: (updates: Partial<Settings>) => void;
  setSettingsModalOpened: (opened: boolean) => void;
  setKeyboardShortcutsModalOpened: (opened: boolean) => void;
  toggleOverlays: () => void;
  togglePlanetTypesMode: () => void;
  toggleTechSkipsMode: () => void;
  toggleAttachmentsMode: () => void;
  togglePdsMode: () => void;
  toggleShowControlLayer: () => void;
  toggleShowExhaustedPlanets: () => void;
  setThemeName: (name: Settings["themeName"]) => void;
  toggleAccessibleColors: () => void;
};

export type SettingsStore = {
  settings: Settings;
  handlers: SettingsHandlers;
  updateSettings: (updates: Partial<Settings>) => void;
};

export const useSettingsStore = create<SettingsStore>((set) => {
  const persist = (getUpdates: (current: Settings) => Partial<Settings>) =>
    set((state) => {
      const settings = { ...state.settings, ...getUpdates(state.settings) };
      saveSettingsToStorage(settings);
      return { settings };
    });

  const updateSettings = (updates: Partial<Settings>) => persist(() => updates);

  const toggle = (key: BooleanSettingKey) => () =>
    persist((current) => ({ [key]: !current[key] }));

  return {
    settings: {
      ...loadSettingsFromStorage(),
      isFirefox:
        typeof navigator !== "undefined" &&
        navigator.userAgent.toLowerCase().indexOf("firefox") > -1,
      themeName: loadThemeFromStorage(),
    },

    handlers: {
      updateSettings,
      setSettingsModalOpened: (opened) =>
        updateSettings({ settingsModalOpened: opened }),
      setKeyboardShortcutsModalOpened: (opened) =>
        updateSettings({ keyboardShortcutsModalOpened: opened }),
      toggleOverlays: toggle("overlaysEnabled"),
      togglePlanetTypesMode: toggle("planetTypesMode"),
      toggleTechSkipsMode: toggle("techSkipsMode"),
      toggleAttachmentsMode: toggle("attachmentsMode"),
      togglePdsMode: toggle("showPDSLayer"),
      toggleShowControlLayer: toggle("showControlLayer"),
      toggleShowExhaustedPlanets: toggle("showExhaustedPlanets"),
      setThemeName: (name) => {
        saveThemeToStorage(name);
        set((state) => ({ settings: { ...state.settings, themeName: name } }));
      },
      toggleAccessibleColors: toggle("accessibleColors"),
    },

    updateSettings,
  };
});

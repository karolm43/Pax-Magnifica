// Sekwencja kroków kreatora setupu (Setup_Wizard).
//
// Kroki są reprezentowane jako UPORZĄDKOWANA sekwencja wpisów z jawnym, unikalnym
// indeksem porządkowym (`order`). Taki model spełnia wymaganie 14.1 i — co ważniejsze —
// przygotowuje grunt pod przyszły "draft slice": dodanie kroku sprowadza się do wstawienia
// wpisu pod wskazanym indeksem i przenumerowania kolejnych, BEZ usuwania ani modyfikowania
// kroków już istniejących (wymaganie 14.2).
//
// Moduł jest czysty (bez zależności od Reacta/Zustanda), więc logika wstawiania kroku jest
// łatwo testowalna w izolacji (patrz setupSteps.test.ts).

/**
 * Identyfikatory kroków setupu. Zbiór jest rozszerzalny — gdy dojdzie draft slice,
 * dopisujemy tu kolejny wariant (np. "slice-draft") bez naruszania pozostałych.
 */
export type SetupStepId = "players" | "faction" | "seat-color";

/**
 * Konfiguracja pojedynczego slotu gracza w setupie.
 *
 * To MINIMALNY, tymczasowy kształt wykorzystywany wyłącznie przez predykat
 * `isApplicable` poniżej. Pełny, autorytatywny model slotu powstanie w store setupu
 * (`useSetupStore.ts`, zadanie 11.3); gdy się pojawi, ten alias zostanie zastąpiony
 * importem z store'a. Dzięki temu moduł kroków kompiluje się już teraz, samodzielnie.
 */
export interface SlotConfig {
  /** Liczba technologii startowych, które frakcja każe wybrać (0 = brak wyboru). */
  startingTechAmount: number;
}

/**
 * Definicja jednego kroku kreatora.
 *
 * - `id` — stabilny identyfikator kroku (klucz logiki i renderowania).
 * - `order` — jawny, unikalny indeks porządkowy (1-bazowy, rosnący).
 * - `label` — etykieta prezentowana użytkownikowi.
 * - `isApplicable` — opcjonalny predykat decydujący, czy krok dotyczy danego slotu
 *   (np. krok wyboru technologii startowych pojawia się tylko, gdy frakcja wymaga
 *   wyboru — `startingTechAmount > 0`). Brak predykatu oznacza "krok zawsze dotyczy".
 */
export interface SetupStepDef {
  id: SetupStepId;
  order: number;
  label: string;
  isApplicable?: (slot: SlotConfig) => boolean;
}

/**
 * Domyślna sekwencja kroków setupu, posortowana rosnąco po `order` (1..3).
 *
 * Kolejność: gracze (nazwa + człowiek/bot + trudność) i mapa → frakcja (wraz
 * z wyborem technologii startowej, wbudowanym w panel podglądu frakcji) → miejsce
 * przy stole i kolor (z podpowiedzią kolorów preferowanych przez wybraną frakcję).
 * Kolor jest ostatni, bo zależy od frakcji; między „graczami" a „frakcją" ma się
 * w przyszłości znaleźć lobby / moduł sieciowy.
 */
export const SETUP_STEPS: SetupStepDef[] = [
  { id: "players", order: 1, label: "Players & map" },
  { id: "faction", order: 2, label: "Faction & starting technologies" },
  { id: "seat-color", order: 3, label: "Color" },
];

/**
 * Wstawia nowy krok do sekwencji pod wskazanym indeksem i przenumerowuje KOLEJNE wpisy
 * (wymaganie 14.2). Funkcja jest czysta: nie mutuje wejściowej sekwencji ani nowego kroku,
 * lecz zwraca NOWĄ, posortowaną po `order` tablicę.
 *
 * Gwarancje (pod przyszły draft slice):
 * - Żaden istniejący krok nie jest usuwany ani modyfikowany — zachowane zostają jego
 *   `id`, `label` oraz `isApplicable`; zmienia się wyłącznie `order` tych wpisów, które
 *   znajdą się za nowym krokiem.
 * - Wynik jest ciągły i 1-bazowy: `order` równy jest pozycji kroku (indeks + 1), więc
 *   indeksy porządkowe pozostają unikalne i bez luk.
 *
 * @param steps      istniejąca sekwencja kroków (nie jest mutowana).
 * @param newStep    nowy krok do wstawienia (jego pole `order` zostanie ustalone na nowo).
 * @param targetIndex docelowa pozycja (0-bazowa) nowego kroku w wynikowej sekwencji.
 *                    Wartości spoza zakresu są przycinane do [0, długość sekwencji].
 * @returns nowa sekwencja z wstawionym krokiem i przenumerowanymi wpisami.
 */
export function insertStep(
  steps: readonly SetupStepDef[],
  newStep: SetupStepDef,
  targetIndex: number,
): SetupStepDef[] {
  // Pracujemy na uporządkowanej kopii, by nie zależeć od kolejności wejścia ani jej nie
  // mutować. Istniejące obiekty kroków kopiujemy płytko — pól innych niż `order` nie tykamy.
  const ordered = [...steps].sort((a, b) => a.order - b.order);

  // Przycinamy indeks do dozwolonego zakresu: od początku (0) do końca (długość).
  const clampedIndex = Math.max(0, Math.min(targetIndex, ordered.length));

  // Składamy wynik: wpisy przed indeksem, nowy krok, wpisy za indeksem. Następnie
  // przenumerowujemy wszystko 1-bazowo wg pozycji — to przesuwa `order` kolejnych wpisów,
  // nie dotykając ich pozostałych pól.
  const combined = [
    ...ordered.slice(0, clampedIndex),
    newStep,
    ...ordered.slice(clampedIndex),
  ];

  return combined.map((step, index) => ({ ...step, order: index + 1 }));
}

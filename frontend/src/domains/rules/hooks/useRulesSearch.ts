/**
 * Hook wyszukiwania tematów Zasad (Rules_Browser) — filtrowanie indeksu z debounce.
 *
 * Frontendowy odpowiednik backendowego `filter_entries` z `src/core/rules_content.py`.
 * Reguła dopasowania MUSI być identyczna jak na backendzie (jedno źródło prawdy):
 * zapytanie jest przycinane (trim) i sprowadzane do małych liter; pozycja pasuje
 * WTEDY i TYLKO WTEDY, gdy przetworzone zapytanie jest podciągiem tytułu LUB slug
 * pozycji (oba także lowercase) — dopasowanie bez wielkości liter (Req 5.2). Puste
 * zapytanie po trim → PEŁNY zbiór w PIERWOTNEJ kolejności, bez filtrowania
 * (Req 5.4/5.6).
 *
 * Kształt wyniku: filtrujemy pozycje WEWNĄTRZ każdej grupy, zachowując kolejność
 * grup (Reguły → Frakcje → Komponenty) i porządek pozycji, a grupy bez trafień
 * pomijamy. Taki kształt jest wprost użyteczny dla `TopicIndexPanel` (zadanie 9.2),
 * który renderuje grupy R/F/C i komunikat o braku wyników — stąd dodatkowa flaga
 * `hasResults` do rozpoznania pustego wyniku (Req 5.5).
 *
 * Debounce ~300 ms (Req 5.3): filtrowana lista aktualizuje się nie później niż
 * 300 ms od ostatniego wprowadzonego znaku. Surowa wartość `query` jest zwracana
 * bez opóźnienia (do sterowanego pola input), a filtrowanie odbywa się nad wartością
 * zdebouncowaną. Wzorzec `useEffect` + `setTimeout` z czyszczeniem — łatwy do
 * testowania z fake timers (zadanie 8.4).
 */

import { useEffect, useMemo, useState } from "react";
import type { TopicGroup } from "@/domains/rules/types";

/** Maksymalna długość tekstu zapytania w polu wyszukiwania (Req 5.1). */
export const MAX_QUERY_LENGTH = 200;

/** Opóźnienie debounce w milisekundach (Req 5.3: ≤ 300 ms od ostatniego znaku). */
export const SEARCH_DEBOUNCE_MS = 300;

/** Wynik hooka wyszukiwania zwracany do panelu indeksu. */
export type UseRulesSearchResult = {
  /** Surowa (natychmiastowa) wartość zapytania — do powiązania z polem input. */
  query: string;
  /** Setter zapisujący nową wartość zapytania (z egzekwowaniem `maxLength`). */
  setQuery: (value: string) => void;
  /** Zdebouncowana wartość zapytania, nad którą wykonano filtrowanie. */
  debouncedQuery: string;
  /** Przefiltrowane grupy (grupy bez trafień pominięte), kolejność zachowana. */
  filteredGroups: TopicGroup[];
  /** `true`, gdy jest co najmniej jedna pasująca pozycja (inaczej brak wyników). */
  hasResults: boolean;
};

/**
 * Egzekwuje logicznie `maxLength` 200: przycina nadmiarowe znaki wejścia.
 *
 * Pole input może mieć też atrybut `maxLength`, ale walidacja w setterze gwarantuje
 * niezmiennik niezależnie od sposobu ustawienia wartości (np. wklejenie, testy).
 */
function clampQuery(value: string): string {
  return value.length > MAX_QUERY_LENGTH
    ? value.slice(0, MAX_QUERY_LENGTH)
    : value;
}

/**
 * Filtruje pojedynczą grupę po podciągu w tytule lub slug (bez wielkości liter).
 *
 * `needle` jest już przycięte i sprowadzone do małych liter przez wywołującego;
 * ta funkcja tylko dopasowuje pozycje, zachowując ich pierwotną kolejność.
 */
function filterGroup(group: TopicGroup, needle: string): TopicGroup {
  const entries = group.entries.filter(
    (entry) =>
      entry.title.toLowerCase().includes(needle) ||
      entry.slug.toLowerCase().includes(needle),
  );
  return { ...group, entries };
}

/**
 * Hook wyszukiwania: przyjmuje grupy indeksu i steruje zapytaniem + debounce.
 *
 * @param groups - grupy indeksu z `useRulesIndex` (lub pusta tablica w trakcie
 *   ładowania); kolejność grup i pozycji jest zachowywana w wyniku.
 * @returns obiekt `UseRulesSearchResult`: surowe `query` i jego setter, zdebouncowane
 *   `debouncedQuery`, przefiltrowane `filteredGroups` (grupy bez trafień pominięte)
 *   oraz flaga `hasResults`.
 */
export function useRulesSearch(groups: TopicGroup[]): UseRulesSearchResult {
  // Natychmiastowa wartość pola (sterowany input) — bez opóźnienia.
  const [query, setQueryRaw] = useState("");
  // Zdebouncowana wartość, nad którą filtrujemy (aktualizacja ≤ 300 ms, Req 5.3).
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // Setter egzekwuje logicznie maxLength 200 (Req 5.1) niezależnie od źródła zmiany.
  const setQuery = (value: string): void => {
    setQueryRaw(clampQuery(value));
  };

  // Debounce: po każdej zmianie `query` ustaw timer; sprzątanie anuluje poprzedni,
  // więc `debouncedQuery` aktualizuje się dopiero ~300 ms po OSTATNIM znaku.
  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedQuery(query);
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      clearTimeout(handle);
    };
  }, [query]);

  // Filtrowanie nad wartością zdebouncowaną — memoizowane po grupach i zapytaniu.
  const filteredGroups = useMemo(() => {
    const needle = debouncedQuery.trim().toLowerCase();
    if (!needle) {
      // Puste zapytanie po trim → pełny indeks w pierwotnej kolejności (Req 5.4/5.6).
      return groups;
    }
    // Filtrujemy w obrębie grup; grupy bez trafień pomijamy (Req 5.2).
    return groups
      .map((group) => filterGroup(group, needle))
      .filter((group) => group.entries.length > 0);
  }, [groups, debouncedQuery]);

  const hasResults = filteredGroups.some((group) => group.entries.length > 0);

  return { query, setQuery, debouncedQuery, filteredGroups, hasResults };
}

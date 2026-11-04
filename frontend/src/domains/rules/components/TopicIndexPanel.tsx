/**
 * Panel indeksu tematów Zasad (Topic_Index, Req 2, 5, 9).
 *
 * Renderuje:
 * - pole wyszukiwania (`TextInput`, `maxLength` 200, Req 5.1) sterujące filtrowaniem
 *   przez `useRulesSearch` (podciąg w tytule lub slug, bez wielkości liter, debounce
 *   ~300 ms; puste zapytanie → pełny indeks w pierwotnej kolejności — Req 5.2/5.4/5.6);
 * - grupy Reguły / Frakcje / Komponenty w stałej kolejności z etykietami po polsku
 *   (etykiety pochodzą z danych indeksu — `group.label`, Req 2.3);
 * - pozycje jako odnośniki nawigacyjne `react-router` (`NavLink`) do `/rules/<slug>`,
 *   z zachowaniem kontekstu powrotu `?from=...`, jeśli obecny w adresie (Req 4.4);
 * - oznaczenie dokładnie jednej aktywnej pozycji wg otwartego slug (Req 9.4);
 * - komunikat o braku pasujących wyników (Req 5.5).
 *
 * Dostępność (Req 9.2/9.3): pozycje to `NavLink` (natywny `<a href>`), więc są
 * fokusowalne klawiaturą i aktywowane Enterem out-of-the-box; widoczny wskaźnik
 * fokusu zapewnia globalny styl focus-visible design systemu (`ds/base.css`).
 *
 * Wszystkie elementy wizualne pochodzą wyłącznie z design systemu (`@/ds`);
 * stany aktywny/fokus stylujemy tokenami przez `style`/klasy `NavLink` react-router.
 */

import { NavLink as RouterNavLink, useSearchParams } from "react-router-dom";
import { IconSearch } from "@tabler/icons-react";
import { Box, ScrollArea, Stack, Text, TextInput } from "@/ds";
import {
  MAX_QUERY_LENGTH,
  useRulesSearch,
} from "@/domains/rules/hooks/useRulesSearch";
import type { TopicGroup } from "@/domains/rules/types";

export type TopicIndexPanelProps = {
  /** Grupy indeksu (Reguły → Frakcje → Komponenty) z `useRulesIndex`. */
  groups: TopicGroup[];
  /** Slug aktualnie otwartego tematu (do oznaczenia aktywnej pozycji) lub `null`. */
  activeSlug: string | null;
};

/**
 * Buduje ścieżkę docelową pozycji, zachowując kontekst powrotu `?from=...`.
 *
 * Jeśli bieżący adres ma parametr `from`, propagujemy go na `/rules/<slug>`, aby
 * powrót działał również po nawigacji przez indeks (spójnie z `InternalLink`).
 */
function topicHref(slug: string, from: string | null): string {
  return from
    ? `/rules/${slug}?from=${encodeURIComponent(from)}`
    : `/rules/${slug}`;
}

/** Styl pojedynczej pozycji indeksu zależny od stanu aktywności (tokeny DS). */
function entryStyle(active: boolean): React.CSSProperties {
  return {
    display: "block",
    padding: "var(--ds-space-xs) var(--ds-space-sm)",
    borderRadius: "var(--ds-radius-sm)",
    textDecoration: "none",
    color: active ? "var(--ds-ink-hi)" : "var(--ds-ink-lo)",
    background: active ? "var(--ds-socket)" : "transparent",
    boxShadow: active ? "inset 0 0 0 1px var(--ds-h28)" : undefined,
    fontWeight: active ? 600 : undefined,
  };
}

/**
 * Panel indeksu: wyszukiwarka + pogrupowana lista tematów z aktywną pozycją.
 */
export function TopicIndexPanel({ groups, activeSlug }: TopicIndexPanelProps) {
  const { query, setQuery, filteredGroups, hasResults } =
    useRulesSearch(groups);
  const [searchParams] = useSearchParams();
  const from = searchParams.get("from");

  return (
    <Stack gap="sm" style={{ height: "100%" }}>
      <TextInput
        aria-label="Search topics"
        placeholder="Search topics…"
        value={query}
        maxLength={MAX_QUERY_LENGTH}
        leftSection={<IconSearch size={16} aria-hidden="true" />}
        onChange={(event) => setQuery(event.currentTarget.value)}
      />

      <ScrollArea style={{ flex: 1, minHeight: 0 }}>
        {hasResults ? (
          <Stack gap="md">
            {filteredGroups.map((group) => (
              <Box component="section" key={group.group}>
                <Text
                  size="xs"
                  style={{
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--ds-ink-lo)",
                    marginBottom: "var(--ds-space-xs)",
                  }}
                >
                  {group.label}
                </Text>
                <Box component="ul" style={{ listStyle: "none", margin: 0, padding: 0 }}>
                  {group.entries.map((entry) => {
                    const active = entry.slug === activeSlug;
                    return (
                      <li key={entry.slug}>
                        <RouterNavLink
                          to={topicHref(entry.slug, from)}
                          style={entryStyle(active)}
                          aria-current={active ? "page" : undefined}
                        >
                          {entry.title}
                        </RouterNavLink>
                      </li>
                    );
                  })}
                </Box>
              </Box>
            ))}
          </Stack>
        ) : (
          <Text size="sm" style={{ color: "var(--ds-ink-lo)" }}>
            No matching results.
          </Text>
        )}
      </ScrollArea>
    </Stack>
  );
}

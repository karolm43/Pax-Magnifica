/**
 * Panel treści tematu Zasad (Topic view, Req 3, 6, 7).
 *
 * Renderuje — w zależności od stanu zapytania o treść tematu (`useTopicContent`,
 * zadanie 8.2) — jeden z widoków:
 * - brak wybranego tematu → komunikat zachęcający do wyboru z indeksu (indeks
 *   pozostaje widoczny po stronie strony — Req 3.4);
 * - ładowanie → informacja „Loading…";
 * - błąd 404 (brak tematu) → `Alert` „Brak tematu", indeks zachowany (Req 3.6/6.3);
 * - inny błąd odczytu → `Alert` „Błąd odczytu treści" (Req 2.7/6.5);
 * - sukces → nagłówek tematu (`Title`), opcjonalny trwały baner not-doprecyzowań
 *   dla grup Frakcje/Komponenty (Req 7.2), treść przez `MarkdownView` albo —
 *   gdy `isEmptyNote` — komunikat o braku not przy ZACHOWANYM nagłówku i widoku
 *   treści (blockquote źródła renderowany z markdownu — Req 7.3).
 *
 * Panel jest możliwie prezentacyjny: stan (loading/notFound/error) dostaje przez
 * propsy, aby być łatwo testowalnym bez react-query. Wszystkie elementy wizualne
 * pochodzą wyłącznie z design systemu (`@/ds`).
 */

import type { Ref } from "react";
import { IconAlertTriangle, IconInfoCircle } from "@tabler/icons-react";
import { Alert, Box, ScrollArea, Stack, Text, Title } from "@/ds";
import { MarkdownView } from "@/domains/rules/components/MarkdownView";
import type { TopicContent } from "@/domains/rules/types";

export type TopicContentPanelProps = {
  /** Treść tematu (gdy wczytana) albo `null`/`undefined` (brak / ładowanie / błąd). */
  topic: TopicContent | null | undefined;
  /** `true`, gdy trwa pobieranie treści wybranego tematu. */
  isLoading: boolean;
  /** `true`, gdy wystąpił błąd pobierania treści. */
  isError: boolean;
  /** `true`, gdy błąd to brak tematu (HTTP 404) — inny komunikat niż błąd odczytu. */
  isNotFound: boolean;
  /** Zbiór znanych slugów (z indeksu) dla `MarkdownView` → klasyfikacja linków. */
  knownSlugs: Set<string> | ReadonlySet<string>;
  /** Ref viewportu przewijanego obszaru treści — przekazywany do `ScrollArea`. */
  scrollViewportRef?: Ref<HTMLDivElement>;
};

/** Komunikat pustego stanu (brak wybranego tematu / ładowanie). */
function MessageView({ children }: { children: React.ReactNode }) {
  return (
    <Box style={{ padding: "var(--ds-space-lg)" }}>
      <Text size="sm" style={{ color: "var(--ds-ink-lo)" }}>
        {children}
      </Text>
    </Box>
  );
}

/**
 * Panel treści: rozstrzyga stan i renderuje odpowiedni widok tematu lub komunikat.
 */
export function TopicContentPanel({
  topic,
  isLoading,
  isError,
  isNotFound,
  knownSlugs,
  scrollViewportRef,
}: TopicContentPanelProps) {
  // Stany błędu mają pierwszeństwo — zachowujemy indeks (renderowany przez stronę).
  if (isError) {
    return isNotFound ? (
      <Box style={{ padding: "var(--ds-space-lg)" }}>
        <Alert
          color="yellow"
          title="Topic not found"
          icon={<IconAlertTriangle size={18} aria-hidden="true" />}
        >
          The requested topic does not exist in the local rules dump. Select a topic from the index.
        </Alert>
      </Box>
    ) : (
      <Box style={{ padding: "var(--ds-space-lg)" }}>
        <Alert
          color="red"
          title="Content load error"
          icon={<IconAlertTriangle size={18} aria-hidden="true" />}
        >
          Failed to load the topic content. Try again or select another topic.
        </Alert>
      </Box>
    );
  }

  if (isLoading) {
    return <MessageView>Loading…</MessageView>;
  }

  if (!topic) {
    return <MessageView>Select a topic from the index to view its content.</MessageView>;
  }

  // Trwały baner not-doprecyzowań — tylko dla grup Frakcje / Komponenty (Req 7.2).
  const showNotesBanner =
    topic.group === "factions" || topic.group === "components";

  return (
    <ScrollArea viewportRef={scrollViewportRef} style={{ height: "100%" }}>
      <Stack gap="sm" style={{ padding: "var(--ds-space-lg)" }}>
        <Title order={1} size="h2">
          {topic.title}
        </Title>

        {showNotesBanner ? (
          <Alert
            color="blue"
            icon={<IconInfoCircle size={18} aria-hidden="true" />}
          >
            Zawartość to noty-doprecyzowania (edge-case'y i interakcje reguł), a nie
            pełny opis frakcji ani komponentu.
          </Alert>
        ) : null}

        {topic.isEmptyNote ? (
          <Stack gap="sm">
            {/* Komunikat o braku not — nagłówek i blockquote źródła pozostają widoczne (Req 7.3). */}
            <Text size="sm" style={{ color: "var(--ds-ink-lo)" }}>
              No clarification notes for this topic.
            </Text>
            <MarkdownView
              markdown={topic.markdown}
              knownSlugs={knownSlugs}
              slug={topic.slug}
              scrollViewportRef={scrollViewportRef}
            />
          </Stack>
        ) : (
          <MarkdownView
            markdown={topic.markdown}
            knownSlugs={knownSlugs}
            slug={topic.slug}
            scrollViewportRef={scrollViewportRef}
          />
        )}
      </Stack>
    </ScrollArea>
  );
}

/**
 * Strona przeglądarki Zasad (Rules_Browser) — trasy `/rules` i `/rules/:slug`.
 *
 * Montuje układ dwupanelowy ekranu Zasad (Req 1.5/1.6, 2.1, 3.4, 4.4/4.5, 9.5, 10.2):
 * - nagłówek z kontrolką powrotu (`ReturnControl`) i tytułem ekranu oraz stały,
 *   zawsze widoczny baner atrybucji (`AttributionNotice`, Req 8);
 * - panel indeksu (`TopicIndexPanel`) po lewej — pełny Topic_Index z wyszukiwarką;
 * - panel treści (`TopicContentPanel`) po prawej — treść aktualnie otwartego tematu.
 *
 * Dane: indeks pobiera `useRulesIndex`, treść — `useTopicContent(slug)`, gdzie `slug`
 * pochodzi z `useParams()` trasy `/rules/:slug`. Ta sama trasa i ten sam komponent
 * obsługują wejście z menu głównego i z panelu gry (jedna implementacja — Req 10.2);
 * kontekst powrotu (`?from=`) jest zachowywany przez `ReturnControl`/`TopicIndexPanel`.
 *
 * Responsywność (Req 9.5): przy szerokości ≤768px panele układają się pionowo
 * (stack), tak aby zarówno pełny indeks, jak i treść otwartego tematu były dostępne
 * bez przycinania uniemożliwiającego odczyt. Na szerszych ekranach — układ dwukolumnowy.
 *
 * Reset scrolla przy Internal_Link (Req 4.5): `ScrollArea` panelu treści dostaje
 * `scrollViewportRef`, który `MarkdownView` wykorzystuje do przewinięcia obszaru
 * treści na początek po zmianie `slug`.
 *
 * Wszystkie elementy wizualne pochodzą wyłącznie z design systemu (`@/ds`).
 */

import { useMemo, useRef } from "react";
import { useParams } from "react-router-dom";
import { Box, Group, Loader, Paper, Text, Title, useMediaQuery } from "@/ds";
import { AttributionNotice } from "@/domains/rules/components/AttributionNotice";
import { ReturnControl } from "@/domains/rules/components/ReturnControl";
import { TopicContentPanel } from "@/domains/rules/components/TopicContentPanel";
import { TopicIndexPanel } from "@/domains/rules/components/TopicIndexPanel";
import { useRulesIndex } from "@/domains/rules/hooks/useRulesIndex";
import { useTopicContent } from "@/domains/rules/hooks/useTopicContent";

/** Próg responsywności: ≤768px → układ pionowy (Req 9.5). */
const NARROW_QUERY = "(max-width: 768px)";

/**
 * Rozpoznaje błąd braku tematu (HTTP 404) na podstawie komunikatu `fetchJson`.
 *
 * `fetchJson` rzuca `Error` z komunikatem postaci
 * `Failed to fetch rules topic: 404 Not Found`, więc wykrycie statusu 404 sprowadza
 * się do sprawdzenia obecności „404" w treści błędu. Pozwala to odróżnić brak tematu
 * (Req 4.6/6.3 — `Alert` „Brak tematu") od innego błędu odczytu (Req 2.7/6.5).
 */
function isNotFoundError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("404");
}

/**
 * Renderuje ekran Zasad: nagłówek + atrybucja + dwa panele (indeks / treść).
 *
 * Eksport nazwany `RulesBrowserPage` — używany przez trasy `createBrowserRouter`
 * (`main.tsx`) jako `Component` w lazy-importach `/rules` i `/rules/:slug`.
 */
export function RulesBrowserPage() {
  const { slug } = useParams<{ slug: string }>();
  const activeSlug = slug ?? null;
  const isNarrow = useMediaQuery(NARROW_QUERY);

  // Ref viewportu przewijanego obszaru treści — do resetu scrolla przy zmianie tematu.
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  const indexQuery = useRulesIndex();
  const topicQuery = useTopicContent(slug);

  const groups = useMemo(() => indexQuery.data?.groups ?? [], [indexQuery.data]);

  // Zbiór wszystkich znanych slugów (z indeksu) — Link_Mapper na froncie (Req 4.1/4.3).
  const knownSlugs = useMemo(
    () => new Set(groups.flatMap((group) => group.entries.map((entry) => entry.slug))),
    [groups],
  );

  const indexPanel = indexQuery.isLoading ? (
    <Group gap="xs" style={{ padding: "var(--ds-space-md)" }}>
      <Loader size="sm" />
      <Text size="sm" style={{ color: "var(--ds-ink-lo)" }}>
        Wczytywanie indeksu…
      </Text>
    </Group>
  ) : (
    <TopicIndexPanel groups={groups} activeSlug={activeSlug} />
  );

  const contentPanel = (
    <TopicContentPanel
      topic={topicQuery.data}
      isLoading={topicQuery.isLoading && Boolean(slug)}
      isError={topicQuery.isError}
      isNotFound={isNotFoundError(topicQuery.error)}
      knownSlugs={knownSlugs}
      scrollViewportRef={scrollViewportRef}
    />
  );

  return (
    <Box style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Nagłówek: kontrolka powrotu + tytuł ekranu. */}
      <Group
        justify="space-between"
        style={{
          padding: "var(--ds-space-sm) var(--ds-space-md)",
          // Ciepła linia oprawy TI (styles/tiChrome.css), jak w nagłówkach okien gry.
          borderBottom: "1px solid rgb(var(--ti-gold-rgb) / 0.32)",
        }}
      >
        <ReturnControl />
        <Title
          order={1}
          size="h3"
          style={{
            fontFamily: "var(--ti-font-title)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "color-mix(in oklab, var(--ti-gold-hi) 18%, var(--ds-ink-hi))",
          }}
        >
          Rules
        </Title>
      </Group>

      {/* Stały baner atrybucji — zawsze widoczny (Req 8.1). */}
      <Box style={{ padding: "var(--ds-space-sm) var(--ds-space-md) 0" }}>
        <AttributionNotice />
      </Box>

      {/* Obszar główny: dwa panele (kolumny na szerokich, stack na wąskich ≤768px). */}
      <Box
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: isNarrow ? "column" : "row",
          gap: "var(--ds-space-md)",
          padding: "var(--ds-space-md)",
        }}
      >
        <Paper
          withBorder
          style={{
            // Na wąskich ekranach indeks dostaje ograniczoną, przewijalną wysokość;
            // na szerokich — stała szerokość kolumny i pełna wysokość (Req 9.5).
            flex: isNarrow ? "0 0 auto" : "0 0 320px",
            maxHeight: isNarrow ? "40vh" : undefined,
            minHeight: 0,
            overflow: "hidden",
            padding: "var(--ds-space-sm)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {indexPanel}
        </Paper>

        <Paper
          withBorder
          style={{
            flex: 1,
            minHeight: isNarrow ? "40vh" : 0,
            overflow: "hidden",
          }}
        >
          {contentPanel}
        </Paper>
      </Box>
    </Box>
  );
}

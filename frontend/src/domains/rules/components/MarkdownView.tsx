/**
 * Widok treści tematu renderowany z surowego Markdown (Req 3.1/3.7, 4.x, 7.4).
 *
 * Renderuje Markdown przez `react-markdown` + `remark-gfm` (tabele, listy zadań,
 * przekreślenia) z nadpisanymi komponentami:
 * - `a` — parsuje `href` przez `mapLink(href, knownSlugs)` i deleguje render do
 *   `InternalLink` (Internal_Link → nawigacja react-router bez przeładowania;
 *   External_Link → trwały wskaźnik + bezpieczne otwarcie w nowej karcie).
 * - `blockquote` — cytat ostylowany design systemem (blok źródła tematu).
 * - `li` — pozycja listy; jeśli zawiera marker rulingu Dane Beltramiego
 *   (`_[Dane ruling]_`), renderuje TRWAŁĄ etykietę „ruling Dane Beltramiego"
 *   odróżniającą ją od pozostałych pozycji not (Req 7.4). Sam marker jest
 *   usuwany z treści, bo zastępuje go czytelna etykieta.
 *
 * Bezpieczeństwo: `react-markdown` jest bezpieczny domyślnie (brak
 * `dangerouslySetInnerHTML`/rawHTML) — nieobsługiwane konstrukcje renderują się
 * jako tekst, bez przerywania renderowania pozostałej treści (Req 3.7).
 *
 * Reset scrolla: po zmianie `slug` (wejście w inny temat, np. przez Internal_Link)
 * widok przewija obszar treści na początek (offset 0 od góry — Req 4.5). Scroll
 * container to opcjonalny `scrollViewportRef` dostarczany przez stronę/panel
 * (`TopicContentPanel`/`RulesBrowserPage`, zadania 9.2/10.1). Gdy ref nie jest
 * podany, reset scrolla pozostaje w gestii strony — komponent nie trzyma wtedy
 * własnego kontenera przewijania.
 *
 * Elementy wizualne wyłącznie z design systemu (`@/ds`).
 */

import { useEffect, type ReactNode, type Ref } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Anchor, Box, Text } from "@/ds";
import { mapLink } from "@/domains/rules/linkMapper";
import { InternalLink } from "@/domains/rules/components/InternalLink";

/** Marker rulingu Dane Beltramiego w treści pozycji listy (lustro `DANE_MARKER`). */
const DANE_MARKER = "_[Dane ruling]_";

/** Trwała etykieta prezentowana przy pozycjach oznaczonych jako ruling Dane. */
const DANE_LABEL = "ruling Dane Beltramiego";

export type MarkdownViewProps = {
  /** Surowa treść Markdown tematu do wyrenderowania. */
  markdown: string;
  /**
   * Zbiór znanych lokalnych slugów (z indeksu) — pozwala `mapLink` klasyfikować
   * hiperłącza na Internal/External spójnie z backendowym `map_link`.
   */
  knownSlugs: Set<string> | ReadonlySet<string>;
  /**
   * Slug aktualnie renderowanego tematu. Zmiana wartości resetuje scroll obszaru
   * treści na początek (Req 4.5). Opcjonalny — gdy brak, reset scrolla leży po
   * stronie wywołującego.
   */
  slug?: string;
  /**
   * Ref viewportu przewijanego obszaru treści (np. `ScrollArea` z `@/ds`).
   * Gdy podany wraz ze `slug`, komponent przewija go do góry przy zmianie tematu.
   */
  scrollViewportRef?: Ref<HTMLDivElement>;
};

/**
 * Spłaszcza dzieci węzła Markdown do czystego tekstu, by wykryć marker rulingu
 * Dane w dowolnie zagnieżdżonej strukturze (np. `<li><p>…</p></li>`).
 */
function childrenToText(children: ReactNode): string {
  if (children === null || children === undefined || children === false) {
    return "";
  }
  if (typeof children === "string" || typeof children === "number") {
    return String(children);
  }
  if (Array.isArray(children)) {
    return children.map(childrenToText).join("");
  }
  // Węzeł React z własnymi dziećmi (np. element akapitu) — zejdź w głąb.
  if (
    typeof children === "object" &&
    "props" in children &&
    children.props !== null &&
    typeof children.props === "object" &&
    "children" in children.props
  ) {
    return childrenToText((children.props as { children: ReactNode }).children);
  }
  return "";
}

/**
 * Buduje mapę nadpisanych komponentów Markdown dla danego zbioru znanych slugów.
 *
 * Wydzielone do czystej funkcji, aby `knownSlugs` było jedyną zależnością mapy
 * (react-markdown odczytuje `components` przy każdym renderze).
 */
function buildComponents(
  knownSlugs: Set<string> | ReadonlySet<string>,
): Components {
  return {
    // Hiperłącze: klasyfikacja przez Link_Mapper → InternalLink (internal/external).
    a({ href, children }) {
      // Brak href (teoretycznie) → zwykły, nieaktywny odnośnik (bezpieczny fallback).
      if (href === undefined || href === null || href === "") {
        return <Anchor>{children}</Anchor>;
      }
      return (
        <InternalLink target={mapLink(href, knownSlugs)}>
          {children}
        </InternalLink>
      );
    },

    // Cytat (blok źródła tematu) — styl DS przez lewą krawędź akcentu i wcięcie.
    blockquote({ children }) {
      return (
        <Box
          component="blockquote"
          style={{
            margin: "var(--ds-space-sm) 0",
            paddingLeft: "var(--ds-space-md)",
            borderLeft: "3px solid var(--ds-h28)",
            color: "var(--ds-ink-lo)",
          }}
        >
          {children}
        </Box>
      );
    },

    // Pozycja listy: wykryj marker rulingu Dane i zastąp go trwałą etykietą.
    li({ children }) {
      const text = childrenToText(children);
      if (!text.includes(DANE_MARKER)) {
        return <li>{children}</li>;
      }
      // Usuń surowy marker z treści — zastępuje go czytelna etykieta DS.
      const cleaned = stripDaneMarker(children);
      return (
        <li>
          {cleaned}{" "}
          <Text
            span
            size="xs"
            style={{
              display: "inline-block",
              marginLeft: 4,
              padding: "0 6px",
              borderRadius: "var(--ds-radius-sm)",
              background: "var(--ds-socket)",
              color: "var(--ds-ink-hi)",
              boxShadow: "inset 0 0 0 1px var(--ds-h28)",
              verticalAlign: "middle",
            }}
          >
            {DANE_LABEL}
          </Text>
        </li>
      );
    },
  };
}

/**
 * Usuwa marker `_[Dane ruling]_` z tekstowych dzieci pozycji listy, zachowując
 * strukturę pozostałych węzłów. Działa płytko na stringach (marker występuje w
 * treści tekstowej pozycji), co wystarcza dla formatu zrzutu tirules.
 */
function stripDaneMarker(children: ReactNode): ReactNode {
  if (typeof children === "string") {
    return children.replace(DANE_MARKER, "").replace(/\s{2,}/g, " ").trimEnd();
  }
  if (Array.isArray(children)) {
    const items = children as ReactNode[];
    return items.map((child, index) =>
      typeof child === "string" ? (
        <span key={index}>
          {child.replace(DANE_MARKER, "").replace(/\s{2,}/g, " ")}
        </span>
      ) : (
        child
      ),
    );
  }
  return children;
}

/**
 * Renderuje treść tematu z Markdown i resetuje scroll przy zmianie tematu.
 */
export function MarkdownView({
  markdown,
  knownSlugs,
  slug,
  scrollViewportRef,
}: MarkdownViewProps) {
  // Reset scrolla obszaru treści na początek po zmianie tematu (Req 4.5).
  useEffect(() => {
    if (slug === undefined) {
      return;
    }
    const viewport =
      scrollViewportRef !== undefined &&
      scrollViewportRef !== null &&
      typeof scrollViewportRef === "object" &&
      "current" in scrollViewportRef
        ? scrollViewportRef.current
        : null;
    viewport?.scrollTo({ top: 0 });
  }, [slug, scrollViewportRef]);

  return (
    <Markdown remarkPlugins={[remarkGfm]} components={buildComponents(knownSlugs)}>
      {markdown}
    </Markdown>
  );
}

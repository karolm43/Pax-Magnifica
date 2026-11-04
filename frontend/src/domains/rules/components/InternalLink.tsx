/**
 * Renderer pojedynczego hiperłącza z treści tematu (Link_Mapper w UI).
 *
 * Komponent dostaje już sklasyfikowany cel (`LinkTarget` z `mapLink`) i renderuje:
 * - Internal_Link → odnośnik lokalny, który na kliknięcie wykonuje nawigację
 *   react-router (`navigate`) z `preventDefault`, BEZ przeładowania strony i bez
 *   żądania do hosta zewnętrznego (Req 4.2/4.4). Ścieżka docelowa to
 *   `/rules/<slug>`; jeśli w adresie obecny jest parametr `?from=...`, jest on
 *   propagowany na docelową ścieżkę, aby kontekst powrotu przetrwał głęboką
 *   nawigację między tematami.
 * - External_Link → zwykły odnośnik otwierany w nowej karcie
 *   (`target="_blank" rel="noopener noreferrer"`) z TRWAŁYM wskaźnikiem
 *   wizualnym (ikona + `aria-label`) odróżniającym go od Internal_Link (Req 4.3).
 *
 * Elementy wizualne pochodzą wyłącznie z design systemu (`@/ds`).
 */

import type { ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { IconExternalLink } from "@tabler/icons-react";
import { Anchor } from "@/ds";
import type { LinkTarget } from "@/domains/rules/types";

export type InternalLinkProps = {
  /** Sklasyfikowany cel hiperłącza (wynik `mapLink`). */
  target: LinkTarget;
  /** Treść odnośnika (tekst renderowany przez react-markdown). */
  children: ReactNode;
};

/**
 * Renderuje hiperłącze treści tematu zgodnie z jego klasyfikacją.
 *
 * Internal_Link nawiguje lokalnie (bez przeładowania); External_Link otwiera się
 * w nowej karcie z trwałym wskaźnikiem i bezpiecznymi atrybutami `rel`.
 */
export function InternalLink({ target, children }: InternalLinkProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  if (target.kind === "internal") {
    // Zachowaj kontekst powrotu (`?from=...`) na docelowej ścieżce, jeśli obecny.
    const from = searchParams.get("from");
    const to = from
      ? `/rules/${target.slug}?from=${encodeURIComponent(from)}`
      : `/rules/${target.slug}`;

    return (
      <Anchor
        href={to}
        onClick={(event: React.MouseEvent<HTMLAnchorElement>) => {
          // Pozwól przeglądarce obsłużyć modyfikatory (nowa karta) i środkowy klik.
          if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
          ) {
            return;
          }
          event.preventDefault();
          navigate(to);
        }}
      >
        {children}
      </Anchor>
    );
  }

  // External_Link — trwały wskaźnik wizualny + bezpieczne otwarcie w nowej karcie.
  return (
    <Anchor
      href={target.url}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
      <IconExternalLink
        size={14}
        aria-label="external link (opens in a new tab)"
        role="img"
        style={{ display: "inline-block", verticalAlign: "middle", marginLeft: 3 }}
      />
    </Anchor>
  );
}

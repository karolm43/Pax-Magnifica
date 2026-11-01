/**
 * Stały baner atrybucji i licencji treści Zasad (Attribution_Notice, Req 8).
 *
 * Prezentuje ciągle widoczną, niewymagającą akcji użytkownika informację opartą na
 * `docs/rules_tirules/SOURCE.md`:
 * - treść reguł Twilight Imperium jest © Fantasy Flight Games (Req 8.1),
 * - zrzut pochodzi z repozytorium tirules na licencji GPL-3.0 (Req 8.1),
 * - zawiera odnośnik, którego tekst zawiera ciąg „tirules2.com", oznaczony jako
 *   External_Link (otwarcie w nowej karcie, trwały wskaźnik, bezpieczne `rel`;
 *   Req 8.2/8.3).
 *
 * Baner nie wymaga żadnej akcji użytkownika i nie przesłania widoku — otwarcie
 * odnośnika nie zmienia aktualnego ekranu Rules_Browser (nowa karta). Wszystkie
 * elementy wizualne pochodzą wyłącznie z design systemu (`@/ds`).
 */

import { IconExternalLink } from "@tabler/icons-react";
import { Anchor, Paper, Text } from "@/ds";

/** Adres źródła reguł — link atrybucji (External_Link w nowej karcie). */
const TIRULES_URL = "https://www.tirules2.com/";

/**
 * Renderuje trwały baner atrybucji z linkiem „tirules2.com" jako External_Link.
 *
 * Komponent jest czysto prezentacyjny i bezstanowy — montowany raz w układzie
 * strony (`RulesBrowserPage`, zadanie 10.1), aby był widoczny przez cały czas
 * korzystania z przeglądarki Zasad.
 */
export function AttributionNotice() {
  return (
    <Paper
      withBorder
      role="contentinfo"
      aria-label="Atrybucja i licencja treści Zasad"
      style={{ padding: "var(--ds-space-xs) var(--ds-space-sm)" }}
    >
      <Text size="xs" style={{ color: "var(--ds-ink-lo)" }}>
        Treść reguł © Fantasy Flight Games. Zrzut pochodzi z repozytorium{" "}
        <Anchor
          href="https://github.com/dangothemango/tirules"
          target="_blank"
          rel="noopener noreferrer"
        >
          tirules
        </Anchor>{" "}
        na licencji GPL-3.0, pobrany ze strony{" "}
        <Anchor href={TIRULES_URL} target="_blank" rel="noopener noreferrer">
          tirules2.com
          <IconExternalLink
            size={13}
            aria-label="odnośnik zewnętrzny (otwiera się w nowej karcie)"
            role="img"
            style={{
              display: "inline-block",
              verticalAlign: "middle",
              marginLeft: 3,
            }}
          />
        </Anchor>
        .
      </Text>
    </Paper>
  );
}

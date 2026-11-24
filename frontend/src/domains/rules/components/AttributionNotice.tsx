/**
 * Rules content attribution and license (Attribution_Notice, Req 8): one quiet line under the
 * topic index — the user removed the banner above the rules (2026-11-24).
 *
 * Based on `docs/rules_tirules/SOURCE.md`: rules text © Fantasy Flight Games; the dump comes
 * from the tirules repository (GPL-3.0), scraped from tirules2.com. Links open in a new tab.
 */

import { Anchor, Text } from "@/ds";

/** Rules source site (attribution link, opens in a new tab). */
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
    <Text
      size="xs"
      role="contentinfo"
      aria-label="Rules content attribution and license"
      style={{ color: "var(--ds-ink-lo)", paddingTop: "var(--ds-space-xs)", opacity: 0.8 }}
    >
      Rules © Fantasy Flight Games · via{" "}
      <Anchor href={TIRULES_URL} target="_blank" rel="noopener noreferrer">
        tirules2.com
      </Anchor>{" "}
      (
      <Anchor
        href="https://github.com/dangothemango/tirules"
        target="_blank"
        rel="noopener noreferrer"
      >
        GPL-3.0
      </Anchor>
      )
    </Text>
  );
}

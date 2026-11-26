import { useState } from "react";
import { IconBook2 } from "@tabler/icons-react";
import { Button } from "@/ds";
import { getFactionLore, loreToBlocks } from "@/entities/lore/factionLore";
import { attribution, quoted } from "@/entities/lore/typography";
import { AppModal } from "@/shared/ui/AppModal";
import styles from "./LoreButton.module.css";

/** The faction quote without pasted-in quotation marks or a leading dash (added on render). */
export function factionQuote(faction: string): { quote?: string; author?: string } {
  const lore = getFactionLore(faction);
  const quote = lore?.quote?.trim().replace(/^["“”„«»]+|["“”„«»]+$/g, "").trim() || undefined;
  const author = lore?.quoteAuthor?.trim().replace(/^[—–-]\s*/, "") || undefined;
  return { quote, author: quote ? author : undefined };
}

/** Full faction lore in a window - read mid-game without leaving the table. */
export function LoreButton({ faction, factionName }: { faction: string; factionName: string }) {
  const [opened, setOpened] = useState(false);
  const blocks = loreToBlocks(getFactionLore(faction)?.lore);
  if (blocks.length === 0) return null;
  const { quote, author } = factionQuote(faction);
  return (
    <>
      <Button
        variant="subtle"
        size="xs"
        leftSection={<IconBook2 size={14} aria-hidden="true" />}
        onClick={() => setOpened(true)}
      >
        Lore
      </Button>
      <AppModal opened={opened} onClose={() => setOpened(false)} title={factionName} size="lg">
        <article className={styles.lore} lang="en">
          {quote && <blockquote className={styles.loreQuote}>{quoted(quote)}</blockquote>}
          {author && <p className={styles.loreAuthor}>{attribution(author)}</p>}
          {blocks.map((block, i) =>
            block.kind === "heading" ? (
              <h3 key={i}>{block.text}</h3>
            ) : block.kind === "quote" ? (
              <blockquote key={i} className={styles.loreQuote}>
                {block.text}
              </blockquote>
            ) : (
              <p key={i} data-tone={block.tone}>
                {block.text}
              </p>
            ),
          )}
        </article>
      </AppModal>
    </>
  );
}

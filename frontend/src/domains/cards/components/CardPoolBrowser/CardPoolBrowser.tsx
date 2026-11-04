import type { CSSProperties } from "react";
import type { PoolGroup } from "@/domains/cards/model/cardPoolBrowser";
import {
  DeckGroup,
  DeckList,
} from "@/domains/cards/components/CardDetailsModal/CardDetailsModal";
import styles from "./CardPoolBrowser.module.css";

const NOTE = /(\[Note:[^\]]*\])/i;

/** Rulingi w nawiasach kwadratowych czytają się jako ciche dopiski. */
function CardText({ text }: { text: string }) {
  const parts = text.split(NOTE);
  return parts.map((part, index) =>
    NOTE.test(part) ? <i key={index}>{part}</i> : part,
  );
}

type Props = {
  /** Grupy całej puli kart (np. Prawa/Dyrektywy, Etap I/II). */
  groups: PoolGroup[];
};

/**
 * Przegląd CAŁEJ puli kart danego typu (nie stanu gry): pełna lista kart z
 * aktywnych źródeł, w stylu AsyncTI4. Każda pozycja renderuje się jak karta —
 * kolorowy pasek nagłówka (nazwa + liczba kopii), okno/metadane, treść reguł i
 * oddzielony stopką tekst klimatyczny (flavor) kursywą.
 */
export function CardPoolBrowser({ groups }: Props) {
  const visible = groups.filter((group) => group.entries.length > 0);

  return (
    <DeckList>
      {visible.map((group) => {
        const style = group.tone
          ? ({ "--dk": group.tone } as CSSProperties)
          : undefined;
        return (
          <DeckGroup
            key={group.title}
            title={group.title}
            count={group.entries.reduce((n, e) => n + (e.copies ?? 1), 0)}
            tone={group.tone}
          >
            <div className={styles.grid}>
              {group.entries.map((entry) => (
                <article key={entry.alias} className={styles.card} style={style}>
                  <header className={styles.header}>
                    <span className={styles.name}>{entry.name}</span>
                    {entry.copies && entry.copies > 1 && (
                      <span className={styles.copies}>×{entry.copies}</span>
                    )}
                  </header>
                  {entry.meta && <div className={styles.meta}>{entry.meta}</div>}
                  <p className={styles.text}>
                    <CardText text={entry.text} />
                  </p>
                  {entry.flavor && (
                    <p className={styles.flavor}>{entry.flavor}</p>
                  )}
                </article>
              ))}
            </div>
          </DeckGroup>
        );
      })}
    </DeckList>
  );
}

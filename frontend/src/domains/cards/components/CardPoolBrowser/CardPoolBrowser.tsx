import type { CSSProperties, ReactNode } from "react";
import type { PoolEntry, PoolGroup } from "@/domains/cards/model/cardPoolBrowser";
import {
  DeckGroup,
  DeckList,
} from "@/domains/cards/components/CardDetailsModal/CardDetailsModal";
import { cardSearchKey, searchTarget } from "@/domains/search/searchKeys";
import { FanSourceBadge } from "@/shared/ui/FanSourceBadge";
import styles from "./CardPoolBrowser.module.css";

const NOTE = /(\[Note:[^\]]*\])/i;

/** Rulingi w nawiasach kwadratowych czytają się jako ciche dopiski. */
function CardText({ text }: { text: string }) {
  const parts = text.split(NOTE);
  return parts.map((part, index) =>
    NOTE.test(part) ? <i key={index}>{part}</i> : part,
  );
}

/** Procent z rozsądną precyzją: 12.5% , 5%, <0.1%. */
function formatChance(percent: number): string {
  if (percent > 0 && percent < 0.1) return "<0.1%";
  const rounded = Math.round(percent * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}%`;
}

type Props = {
  /** Grupy całej puli kart (np. Prawa/Dyrektywy, Etap I/II). */
  groups: PoolGroup[];
  /** Dodatkowe przyciski pod kartą (np. ruchy debug między stosami). */
  renderActions?: (entry: PoolEntry) => ReactNode;
  /** Id talii - karty dostają znacznik wyszukiwarki planszy (podświetlenie). */
  deckId?: string;
};

/**
 * Przegląd CAŁEJ puli kart danego typu (nie stanu gry): pełna lista kart z
 * aktywnych źródeł, w stylu AsyncTI4. Każda pozycja renderuje się jak karta —
 * kolorowy pasek nagłówka (nazwa + liczba kopii), okno/metadane, treść reguł i
 * oddzielony stopką tekst klimatyczny (flavor) kursywą.
 */
export function CardPoolBrowser({ groups, renderActions, deckId }: Props) {
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
                <article
                  key={entry.alias}
                  className={styles.card}
                  style={style}
                  {...(deckId ? searchTarget(cardSearchKey(deckId, entry.name)) : {})}
                >
                  <header className={styles.header}>
                    <span className={styles.name}>{entry.name}</span>
                    <FanSourceBadge source={entry.source} />
                    {entry.copies && entry.copies > 1 && (
                      <span className={styles.copies}>×{entry.copies}</span>
                    )}
                    {entry.chance !== undefined && (
                      <span
                        className={styles.chance}
                        title="Chance this is the next card drawn"
                      >
                        {formatChance(entry.chance)}
                      </span>
                    )}
                  </header>
                  {entry.meta && <div className={styles.meta}>{entry.meta}</div>}
                  <p className={styles.text}>
                    <CardText text={entry.text} />
                  </p>
                  {entry.flavor && (
                    <p className={styles.flavor}>{entry.flavor}</p>
                  )}
                  {entry.next && <div className={styles.next}>Next card</div>}
                  {renderActions && (
                    <div className={styles.actions}>{renderActions(entry)}</div>
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

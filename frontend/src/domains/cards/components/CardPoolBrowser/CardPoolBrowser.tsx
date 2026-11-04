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
 * aktywnych źródeł, w stylu AsyncTI4 — te same „teczki" co w podglądzie talii,
 * z nazwą, oknem/metadanymi i treścią. Bez liczności egzemplarzy i procentów.
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
            count={group.entries.length}
            tone={group.tone}
          >
            {group.entries.map((entry) => (
              <div key={entry.alias} className={styles.entry} style={style}>
                <div className={styles.head}>
                  <b className={styles.name}>{entry.name}</b>
                  {entry.meta && <span className={styles.meta}>{entry.meta}</span>}
                </div>
                <p className={styles.text}>
                  <CardText text={entry.text} />
                </p>
              </div>
            ))}
          </DeckGroup>
        );
      })}
    </DeckList>
  );
}

// Warstwy „sceny" wyboru frakcji: duży portret postaci (tło po lewej) oraz lore
// nałożone na ten portret w dwóch kolumnach.
//
// Oba komponenty są renderowane z `key={faction.id}` przez wywołującego (Step_Faction),
// więc KAŻDA zmiana frakcji odtwarza animacje wejścia: portret wjeżdża z lewej, a
// kolejne bloki lore pojawiają się kaskadowo (opóźnienie z indeksu bloku).

import { useEffect, useMemo, useState } from "react";
import type { FactionInfo } from "@/api/useNewGame";
import { getLeaderById } from "@/entities/lookup/leaders";
import {
  defaultPortraitCandidates,
  getFactionLore,
  loreToBlocks,
} from "./factionLore";
import styles from "./FactionBackdrop.module.css";

/** Id lidera-bohatera (hero) frakcji — do domyślnego portretu, gdy brak własnego pliku. */
function heroLeaderId(faction: FactionInfo): string | undefined {
  return faction.leaders.find((id) => getLeaderById(id)?.type === "hero");
}

/**
 * Warstwa portretu: łańcuch źródeł LOKALNYCH (pierwsze istniejące):
 *   1. własny plik `/faction_portraits/<id>.{png,jpg,jpeg,webp}` (lub `lore.portrait`),
 *   2. portret BOHATERA frakcji `/leaders/<heroId>.webp`,
 *   3. lokalna ikona frakcji `/static/factions/<id>.png` (placeholder, rysowany mniejszy).
 * Bez zewnętrznego CDN. Degraduje bez błędu (onError → następne źródło).
 */
export function FactionPortraitLayer({ faction }: { faction: FactionInfo }) {
  const lore = getFactionLore(faction.id);
  const candidates = useMemo(() => {
    const own = lore?.portrait
      ? [lore.portrait]
      : defaultPortraitCandidates(faction.id);
    const hero = heroLeaderId(faction);
    return [
      ...own,
      ...(hero ? [`/leaders/${hero}.webp`] : []),
      `/static/factions/${faction.id}.png`,
    ];
  }, [faction, lore?.portrait]);

  const [index, setIndex] = useState(0);
  // Reset źródła przy zmianie frakcji (inaczej zostałby wyczerpany index).
  useEffect(() => setIndex(0), [candidates]);

  if (index >= candidates.length) return null;
  // Ostatni kandydat to ikona frakcji — pokazujemy ją jako symbol, nie jako postać.
  const isIconFallback = index === candidates.length - 1;
  return (
    <div className={styles.portraitLayer} aria-hidden>
      <img
        key={candidates[index]}
        src={candidates[index]}
        alt=""
        className={isIconFallback ? styles.portraitIcon : styles.portrait}
        onError={() => setIndex((i) => i + 1)}
      />
    </div>
  );
}

/**
 * Lore nałożone na portret: nazwa (krój Ambroise) + cytat + tekst w DWÓCH kolumnach,
 * małą czcionką, bez przewijania. Każdy blok wchodzi z opóźnieniem `--i`.
 */
export function FactionLore({ faction }: { faction: FactionInfo }) {
  const data = getFactionLore(faction.id);
  const blocks = loreToBlocks(data?.lore);

  return (
    <article className={styles.lore}>
      <h2 className={styles.loreName} style={{ ["--i" as string]: 0 }}>
        {faction.name}
      </h2>
      {data?.quote && (
        <p className={styles.loreQuote} style={{ ["--i" as string]: 1 }}>
          „{data.quote}”
        </p>
      )}
      {blocks.length === 0 ? (
        <p className={styles.loreEmpty} style={{ ["--i" as string]: 2 }}>
          Brak lore — uzupełnij w factionLore.ts (klucz „{faction.id}").
        </p>
      ) : (
        <div className={styles.loreColumns}>
          {blocks.map((block, i) => {
            const style = { ["--i" as string]: i + 2 };
            if (block.kind === "heading") {
              return (
                <h3 key={i} className={styles.loreHeading} style={style}>
                  {block.text}
                </h3>
              );
            }
            if (block.kind === "quote") {
              return (
                <blockquote key={i} className={styles.loreBlockQuote} style={style}>
                  {block.text}
                </blockquote>
              );
            }
            return (
              <p key={i} className={styles.loreParagraph} style={style}>
                {block.text}
              </p>
            );
          })}
        </div>
      )}
    </article>
  );
}

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

  // Przezroczysty margines PNG (ułamek wymiaru obrazka) od lewej i od dołu — mierzony
  // po załadowaniu, żeby sylwetka dotykała krawędzi ekranu niezależnie od pliku.
  const [inset, setInset] = useState({ left: 0, bottom: 0 });
  useEffect(() => setInset({ left: 0, bottom: 0 }), [index, candidates]);

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
        style={
          isIconFallback
            ? undefined
            : {
                transform: `translate(${-inset.left * 100}%, ${inset.bottom * 100}%)`,
              }
        }
        onLoad={(e) => {
          if (!isIconFallback) {
            const measured = measureAlphaInset(e.currentTarget);
            if (measured) setInset(measured);
          }
        }}
        onError={() => setIndex((i) => i + 1)}
      />
    </div>
  );
}

/**
 * Mierzy przezroczysty margines obrazka od lewej i od dołu (jako ułamek szerokości /
 * wysokości). Rysuje pomniejszoną kopię na canvasie i szuka pierwszych pikseli o
 * alfie > 16. Zwraca `null`, gdy się nie da (brak kontekstu, obraz pusty).
 */
function measureAlphaInset(
  img: HTMLImageElement,
): { left: number; bottom: number } | null {
  const w = img.naturalWidth;
  const h = img.naturalHeight;
  if (!w || !h) return null;
  const scale = Math.min(1, 256 / Math.max(w, h));
  const cw = Math.max(1, Math.round(w * scale));
  const ch = Math.max(1, Math.round(h * scale));
  const canvas = document.createElement("canvas");
  canvas.width = cw;
  canvas.height = ch;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.drawImage(img, 0, 0, cw, ch);
  let data: Uint8ClampedArray;
  try {
    data = ctx.getImageData(0, 0, cw, ch).data;
  } catch {
    return null;
  }
  let minX = cw;
  let maxY = -1;
  for (let y = 0; y < ch; y++) {
    for (let x = 0; x < cw; x++) {
      if (data[(y * cw + x) * 4 + 3] > 16) {
        if (x < minX) minX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (maxY < 0) return null;
  return { left: minX / cw, bottom: (ch - 1 - maxY) / ch };
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

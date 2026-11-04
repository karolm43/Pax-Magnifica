// Warstwy „sceny" wyboru frakcji: duży portret postaci (tło po lewej) oraz lore
// nałożone na ten portret w dwóch kolumnach.
//
// Oba komponenty są renderowane z `key={faction.id}` przez wywołującego (Step_Faction),
// więc KAŻDA zmiana frakcji odtwarza animacje wejścia: portret wjeżdża z lewej, a
// kolejne bloki lore pojawiają się kaskadowo (opóźnienie z indeksu bloku).

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { FactionInfo } from "@/api/useNewGame";
import { getLeaderById } from "@/entities/lookup/leaders";
import {
  defaultPortraitCandidates,
  getFactionLore,
  loreToBlocks,
  type LoreBlock,
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
export function FactionPortraitLayer({
  faction,
  onFigureCenter,
}: {
  faction: FactionInfo;
  /** Środek widocznej sylwetki w px od lewej krawędzi strefy (`null` = brak/nieznany). */
  onFigureCenter?: (centerPx: number | null) => void;
}) {
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
  const [inset, setInset] = useState({ left: 0, bottom: 0, width: 1 });
  useEffect(() => setInset({ left: 0, bottom: 0, width: 1 }), [index, candidates]);
  const imgRef = useRef<HTMLImageElement>(null);

  const isIconFallback = index === candidates.length - 1;
  const exhausted = index >= candidates.length;

  // Zgłasza środek WIDOCZNEJ sylwetki (px od lewej krawędzi strefy), żeby nagłówek
  // (nazwa + cytat) centrował się dokładnie nad postacią, a nie nad całym pasem portretu.
  useEffect(() => {
    const img = imgRef.current;
    if (!onFigureCenter || exhausted || isIconFallback || !img) {
      onFigureCenter?.(null);
      return;
    }
    const report = () => onFigureCenter((inset.width / 2) * img.offsetWidth);
    report();
    const observer = new ResizeObserver(report);
    observer.observe(img);
    return () => {
      observer.disconnect();
      onFigureCenter(null);
    };
  }, [inset, index, exhausted, isIconFallback, onFigureCenter]);

  if (exhausted) return null;
  // Ostatni kandydat to ikona frakcji — pokazujemy ją jako symbol, nie jako postać.
  return (
    <div className={styles.portraitLayer} aria-hidden>
      <img
        ref={imgRef}
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
 * Mierzy przezroczysty margines obrazka od lewej i od dołu oraz szerokość widocznej
 * sylwetki (jako ułamki wymiarów obrazka). Rysuje pomniejszoną kopię na canvasie i szuka pierwszych pikseli o
 * alfie > 16. Zwraca `null`, gdy się nie da (brak kontekstu, obraz pusty).
 */
function measureAlphaInset(
  img: HTMLImageElement,
): { left: number; bottom: number; width: number } | null {
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
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < ch; y++) {
    for (let x = 0; x < cw; x++) {
      if (data[(y * cw + x) * 4 + 3] > 16) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (maxY < 0) return null;
  // `width` = szerokość widocznej sylwetki jako ułamek szerokości obrazka.
  return {
    left: minX / cw,
    bottom: (ch - 1 - maxY) / ch,
    width: (maxX + 1 - minX) / cw,
  };
}

/**
 * Nagłówek sceny nad postacią i lore — pierwszy punkt uwagi: nazwa frakcji (Handel
 * Gothic), pod nią cytat w cudzysłowie, pod nim autor cytatu. Dopiero potem lore.
 */
export function FactionHeader({ faction }: { faction: FactionInfo }) {
  const data = getFactionLore(faction.id);
  // Cudzysłowy dokłada komponent — w danych cytat wklejasz BEZ nich. Jeśli jednak
  // zostały wklejone, zdejmujemy je z brzegów, żeby nie dublować.
  const quote = data?.quote?.trim().replace(/^["“”„«»]+|["“”„«»]+$/g, "").trim();
  // Autor jest poza cudzysłowem, w osobnej linii; wiodący myślnik usuwamy (dodajemy swój).
  const author = data?.quoteAuthor?.trim().replace(/^[—–-]\s*/, "");

  return (
    <header className={styles.head}>
      <h2 className={styles.headName}>{faction.name}</h2>
      {quote && <blockquote className={styles.headQuote}>“{quote}”</blockquote>}
      {quote && author && <p className={styles.headAuthor}>— {author}</p>}
    </header>
  );
}

/** Czy frakcja ma cytat (steruje rezerwacją paska nad postacią i lore). */
export function hasFactionQuote(factionId: string): boolean {
  return Boolean(getFactionLore(factionId)?.quote);
}

/** Znaczniki końców zdań (pozycja PO zdaniu i spacji) — do podziału długiego akapitu. */
function sentenceEnds(text: string): number[] {
  const ends: number[] = [];
  const re = /[.!?]["”')]?\s+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) ends.push(m.index + m[0].length);
  return ends;
}

/**
 * Dzieli bloki lore na DWIE kolumny o zbliżonej długości, każda wyrównana od góry.
 * Cięcie wypada na granicy bloku albo — gdy środek tekstu trafia w długi akapit — na
 * końcu zdania wewnątrz akapitu (żeby jeden olbrzymi akapit nie rozpychał kolumny).
 * Śródtytuł nigdy nie zostaje samotnie na końcu pierwszej kolumny.
 */
function splitLoreColumns(blocks: LoreBlock[]): [LoreBlock[], LoreBlock[]] {
  const weight = (b: LoreBlock) => (b.kind === "heading" ? 80 : b.text.length);
  const total = blocks.reduce((sum, b) => sum + weight(b), 0);
  const target = total / 2;

  const cutAt = (cut: number): [LoreBlock[], LoreBlock[]] => {
    let adjusted = cut;
    while (adjusted > 0 && blocks[adjusted - 1].kind === "heading") adjusted--;
    if (adjusted === 0) adjusted = cut;
    return [blocks.slice(0, adjusted), blocks.slice(adjusted)];
  };

  let cumulative = 0;
  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    const w = weight(block);
    if (cumulative + w >= target) {
      const inside = target - cumulative;
      if (block.kind === "paragraph" && inside > w * 0.2 && inside < w * 0.8) {
        let best = -1;
        let bestDist = Infinity;
        for (const end of sentenceEnds(block.text)) {
          const dist = Math.abs(end - inside);
          if (end < block.text.length && dist < bestDist) {
            best = end;
            bestDist = dist;
          }
        }
        if (best > 0) {
          const head = { ...block, text: block.text.slice(0, best).trim() };
          const tail = { ...block, text: block.text.slice(best).trim() };
          return [[...blocks.slice(0, i), head], [tail, ...blocks.slice(i + 1)]];
        }
      }
      return cutAt(inside < w / 2 ? i : i + 1);
    }
    cumulative += w;
  }
  return [blocks, []];
}

/**
 * Lore obok portretu: nazwa (krój Ambroise) + tekst w DWÓCH kolumnach, bez przewijania —
 * rozmiar czcionki dopasowuje się do boxa i okna. Każdy blok wchodzi z opóźnieniem `--i`.
 */
export function FactionLore({ faction }: { faction: FactionInfo }) {
  const data = getFactionLore(faction.id);
  const blocks = loreToBlocks(data?.lore);
  const articleRef = useRef<HTMLElement>(null);

  // Dopasowanie rozmiaru czcionki do boxa: największy rozmiar (do limitu zależnego od
  // rozmiaru okna), przy którym lore mieści się bez przewijania. Skaluje się z oknem.
  useLayoutEffect(() => {
    const article = articleRef.current;
    const slot = article?.parentElement;
    const zone = slot?.parentElement;
    if (!article || !slot || !zone) return;

    const fit = () => {
      const style = getComputedStyle(slot);
      const padV = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
      // Limit rośnie z oknem (szerokość i wysokość), nie przekracza czytelnych granic.
      const max = Math.min(
        19,
        Math.max(13, Math.min(window.innerWidth * 0.0105, window.innerHeight * 0.019)),
      );
      const min = 10.5;
      const fits = (size: number) => {
        article.style.fontSize = `${size}px`;
        // Tylko wysokość: scrim (.lore::before) wystaje poza article, więc test
        // szerokości zawsze zawodził i zbijał czcionkę do minimum.
        return article.offsetHeight + padV <= slot.clientHeight + 1;
      };
      if (fits(max)) return;
      let lo = min;
      let hi = max;
      for (let i = 0; i < 8; i++) {
        const mid = (lo + hi) / 2;
        if (fits(mid)) lo = mid;
        else hi = mid;
      }
      article.style.fontSize = `${lo}px`;
    };

    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(zone);
    // Po wczytaniu fontów (Ambroise) metryki się zmieniają — dopasuj ponownie.
    void document.fonts?.ready.then(fit);
    return () => observer.disconnect();
  }, [faction.id]);

  return (
    <article className={styles.lore} ref={articleRef} lang="en">
      {blocks.length === 0 ? (
        <p className={styles.loreEmpty} style={{ ["--i" as string]: 2 }}>
          Brak lore — uzupełnij w factionLore.ts (klucz „{faction.id}").
        </p>
      ) : (
        <div className={styles.loreColumns}>
          {splitLoreColumns(blocks).map((column, c) => (
            <div key={c} className={styles.loreCol}>
              {column.map((block, i) => {
                // Indeks animacji liczony w obrębie kolumny: obie kolumny odsłaniają
                // się równolegle od góry, a nie jedna po drugiej.
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
          ))}
        </div>
      )}
    </article>
  );
}

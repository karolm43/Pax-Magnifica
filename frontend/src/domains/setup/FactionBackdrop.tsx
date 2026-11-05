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
import { DecodedText, useDecode } from "./GlyphText";
import styles from "./FactionBackdrop.module.css";

/** Id lidera-bohatera (hero) frakcji — do domyślnego portretu, gdy brak własnego pliku. */
function heroLeaderId(faction: FactionInfo): string | undefined {
  return faction.leaders.find((id) => getLeaderById(id)?.type === "hero");
}

/**
 * Łańcuch źródeł portretu frakcji (pierwsze istniejące wygrywa): własny plik →
 * portret bohatera → ikona frakcji (ostatni element = placeholder). Wspólny dla sceny
 * wyboru frakcji i planszy otwierającej grę (`GameIntro`).
 */
export function portraitCandidates(faction: FactionInfo): string[] {
  const lore = getFactionLore(faction.id);
  const own = lore?.portrait
    ? [lore.portrait]
    : defaultPortraitCandidates(faction.id);
  const hero = heroLeaderId(faction);
  return [
    ...own,
    ...(hero ? [`/leaders/${hero}.webp`] : []),
    `/static/factions/${faction.id}.png`,
  ];
}

/**
 * Delikatne przesunięcie portretu w PRAWO (w % szerokości obrazka), nakładane na dosunięcie
 * do lewej krawędzi z pomiaru alfy. Dodatni = w prawo. Mały margines, żeby sylwetka nie
 * dotykała samej krawędzi ekranu.
 */
const PORTRAIT_NUDGE_X = 4;

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
  const candidates = useMemo(() => portraitCandidates(faction), [faction]);

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
    // Środek sylwetki uwzględnia to samo przesunięcie w prawo co inline `transform`
    // obrazka, żeby nagłówek nadal centrował się dokładnie nad postacią.
    const report = () =>
      onFigureCenter(
        (inset.width / 2 + PORTRAIT_NUDGE_X / 100) * img.offsetWidth,
      );
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
  const img = (
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
              // Dosuwamy sylwetkę do lewej krawędzi (pomiar alfy), ale zostawiamy mały
              // margines oddechu w prawo (PORTRAIT_NUDGE_X), żeby postać nie kleiła się
              // do samej krawędzi ekranu.
              transform: `translate(${-inset.left * 100 + PORTRAIT_NUDGE_X}%, ${
                inset.bottom * 100
              }%)`,
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
  );
  return (
    <div className={styles.portraitLayer} aria-hidden>
      {/*
       * Delikatny „oddech" postaci jest na OSOBNEJ warstwie (`.portraitFloat`), a nie na
       * samym <img>. Obrazek ma własny inline `transform` (dosuwa sylwetkę do krawędzi po
       * pomiarze alfa) — animacja transformu na img NADPISYWAŁABY ten inline, przez co
       * postać przeskakiwała po wjeździe. Wrapper składa oba ruchy bez kolizji.
       */}
      {isIconFallback ? img : <div className={styles.portraitFloat}>{img}</div>}
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
  const accent = useFactionAccent(faction.id);
  const data = getFactionLore(faction.id);
  // Cudzysłowy dokłada komponent — w danych cytat wklejasz BEZ nich. Jeśli jednak
  // zostały wklejone, zdejmujemy je z brzegów, żeby nie dublować.
  const quote = data?.quote?.trim().replace(/^["“”„«»]+|["“”„«»]+$/g, "").trim();
  // Autor jest poza cudzysłowem, w osobnej linii; wiodący myślnik usuwamy (dodajemy swój).
  const author = data?.quoteAuthor?.trim().replace(/^[—–-]\s*/, "");

  return (
    <header
      className={styles.head}
      style={{ ["--accent" as string]: accent } as React.CSSProperties}
    >
      <div className={styles.headInner}>
        <img
          src={`/static/factions/${faction.id}.png`}
          alt=""
          className={styles.headIcon}
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
        <div className={styles.headText}>
          <h2 className={styles.headName}>{faction.name}</h2>
          {quote && (
            <blockquote className={styles.headQuote}>“{quote}”</blockquote>
          )}
          {quote && author && <p className={styles.headAuthor}>— {author}</p>}
        </div>
      </div>
    </header>
  );
}

/** Akcent, gdy ikony nie da się odczytać (ciepły bursztyn TI4). */
const DEFAULT_ACCENT = "hsl(33 96% 58%)";
const accentCache = new Map<string, string>();

/**
 * Kolor akcentu frakcji wyliczony z jej LOKALNEJ ikony (`/static/factions/<id>.png`):
 * średnia z nasyceniem jako wagą (tło i szarości prawie nie liczą się), potem
 * normalizacja do żywego, czytelnego odcienia. Zero kolorów wpisanych na sztywno —
 * nowa frakcja dostaje akcent automatycznie. Wynik jest cache'owany po id.
 */
export function useFactionAccent(factionId: string): string {
  const [accent, setAccent] = useState(accentCache.get(factionId) ?? DEFAULT_ACCENT);

  useEffect(() => {
    const cached = accentCache.get(factionId);
    if (cached) {
      setAccent(cached);
      return;
    }
    setAccent(DEFAULT_ACCENT);
    let cancelled = false;
    const img = new Image();
    img.onload = () => {
      const color = extractAccent(img) ?? DEFAULT_ACCENT;
      accentCache.set(factionId, color);
      if (!cancelled) setAccent(color);
    };
    img.src = `/static/factions/${factionId}.png`;
    return () => {
      cancelled = true;
    };
  }, [factionId]);

  return accent;
}

/** Dominujący, nasycony kolor ikony jako `hsl(...)` albo `null` (ikona szara/pusta). */
function extractAccent(img: HTMLImageElement): string | null {
  const size = 48;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.drawImage(img, 0, 0, size, size);
  let data: Uint8ClampedArray;
  try {
    data = ctx.getImageData(0, 0, size, size).data;
  } catch {
    return null;
  }
  let r = 0;
  let g = 0;
  let b = 0;
  let weight = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 128) continue;
    const max = Math.max(data[i], data[i + 1], data[i + 2]);
    const min = Math.min(data[i], data[i + 1], data[i + 2]);
    const sat = max === 0 ? 0 : (max - min) / max;
    const w = sat * sat * (max / 255) + 0.0001;
    r += data[i] * w;
    g += data[i + 1] * w;
    b += data[i + 2] * w;
    weight += w;
  }
  if (weight <= 0.01) return null;
  r /= weight;
  g /= weight;
  b /= weight;
  const max = Math.max(r, g, b) / 255;
  const min = Math.min(r, g, b) / 255;
  const delta = max - min;
  // Praktycznie szara ikona — odcień nie ma znaczenia, zostaje domyślny akcent.
  if (delta < 0.08) return null;
  let hue: number;
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  if (max === rn) hue = ((gn - bn) / delta) % 6;
  else if (max === gn) hue = (bn - rn) / delta + 2;
  else hue = (rn - gn) / delta + 4;
  hue = Math.round(((hue * 60 + 360) % 360));
  // Stała, żywa saturacja i jasność: akcent czytelny na ciemnej płycie niezależnie
  // od tego, jak ciemna lub wyblakła jest sama ikona.
  return `hsl(${hue} 72% 58%)`;
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
  // Lore w piśmie z gry: domyślnie glify, przycisk „Przetłumacz" rozszyfrowuje tekst.
  const isGlyph = data?.glyphLore === true;
  const decode = useDecode();

  // Dopasowanie rozmiaru czcionki do boxa: największy rozmiar (do limitu zależnego od
  // rozmiaru okna), przy którym lore mieści się bez przewijania. Skaluje się z oknem.
  useLayoutEffect(() => {
    const article = articleRef.current;
    const slot = article?.parentElement;
    const zone = slot?.parentElement;
    if (!article || !slot || !zone) return;
    // W trakcie rozszyfrowywania szerokości znaków zmieniają się co klatkę — dopasowanie
    // robimy dopiero po zakończeniu przejścia (efekt uruchomi się ponownie, gdy `busy` = false).
    if (decode.busy) return;

    const fit = () => {
      const style = getComputedStyle(slot);
      const padV = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
      // Limit rośnie z oknem (szerokość i wysokość), nie przekracza czytelnych granic.
      const max = Math.min(
        21,
        Math.max(14, Math.min(window.innerWidth * 0.0115, window.innerHeight * 0.021)),
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
  }, [faction.id, decode.busy, decode.mode]);

  // Groza Obsidiana (tylko `glyphLore`): losowe glitche akapitów, przygasanie światła i
  // krótkie błyski ukrytych fraz. Zdarzenia lecą z timerów (nie z renderu), więc losowość
  // nie psuje czystości komponentu. Wstrzymane na czas rozszyfrowywania (ma własny glitch)
  // i przy `prefers-reduced-motion`.
  const [flash, setFlash] = useState<{
    text: string;
    x: number;
    y: number;
    size: number;
  } | null>(null);

  useEffect(() => {
    const article = articleRef.current;
    if (!isGlyph || decode.busy || !article) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const phrases = getFactionLore(faction.id)?.glitchPhrases ?? [];
    const timers: number[] = [];

    const rand = (min: number, max: number) => min + Math.random() * (max - min);

    const fire = () => {
      const paragraphs = article.querySelectorAll<HTMLElement>(
        `.${styles.loreParagraph}`,
      );
      const target = paragraphs[Math.floor(Math.random() * paragraphs.length)];
      // Akapit „rwie się": przesunięcie z skosem, rozdwojenie kolorów i ucięte pasy.
      // UWAGA: `easing` ustawiamy W KAŻDEJ KLATCE KLUCZOWEJ (skok skokowy do następnej).
      // Opcja `easing` na poziomie animate() działa na cały przebieg i trzymałaby
      // animację w pierwszej klatce aż do końca — efekt byłby niewidoczny.
      const jump = "steps(1, end)";
      target?.animate(
        [
          { transform: "none", clipPath: "inset(0 0 0 0)", easing: jump, offset: 0 },
          {
            transform: "translate(-6px, 0) skewX(-8deg)",
            textShadow: "4px 0 #ff2a2a, -4px 0 #2ae0ff",
            clipPath: "inset(8% 0 62% 0)",
            filter: "brightness(1.6)",
            easing: jump,
            offset: 0.15,
          },
          {
            transform: "translate(7px, 1px) skewX(6deg)",
            textShadow: "-4px 0 #ff2a2a, 4px 0 #2ae0ff",
            clipPath: "inset(58% 0 6% 0)",
            filter: "brightness(0.6)",
            easing: jump,
            offset: 0.4,
          },
          {
            transform: "translate(-3px, -1px)",
            textShadow: "3px 0 #ff2a2a",
            clipPath: "inset(30% 0 30% 0)",
            easing: jump,
            offset: 0.65,
          },
          { transform: "none", clipPath: "inset(0 0 0 0)", offset: 1 },
        ],
        { duration: 600 },
      );
      // Czasem światło „przygasa" na ułamek sekundy.
      if (Math.random() < 0.4) {
        article.animate(
          [
            { opacity: 1, easing: jump, offset: 0 },
            { opacity: 0.1, easing: jump, offset: 0.18 },
            { opacity: 1, easing: jump, offset: 0.3 },
            { opacity: 0.4, easing: jump, offset: 0.5 },
            { opacity: 1, offset: 1 },
          ],
          { duration: 420 },
        );
      }
      // Często coś „przebija" przez tekst: krótki błysk frazy w losowym miejscu.
      if (phrases.length > 0 && Math.random() < 0.65) {
        setFlash({
          text: phrases[Math.floor(Math.random() * phrases.length)],
          x: rand(2, 55),
          y: rand(8, 82),
          size: rand(2, 3.4),
        });
        timers.push(window.setTimeout(() => setFlash(null), rand(160, 340)));
      }
      schedule();
    };

    const schedule = (first = false) => {
      // Pierwszy glitch krótko po odsłonięciu lore (wejście trwa ok. 6–10 s), potem co
      // kilka sekund.
      timers.push(window.setTimeout(fire, first ? rand(6000, 9000) : rand(2500, 6500)));
    };
    schedule(true);

    return () => {
      timers.forEach((id) => window.clearTimeout(id));
      setFlash(null);
    };
  }, [faction.id, isGlyph, decode.busy]);

  const columns = splitLoreColumns(blocks);
  const total = columns[0].length + columns[1].length;

  return (
    <article
      className={`${styles.lore} ${isGlyph ? styles.loreGlyph : ""} ${
        decode.busy ? styles.decoding : ""
      }`}
      ref={articleRef}
      lang="en"
    >
      {isGlyph && blocks.length > 0 && (
        <div className={styles.loreTools} style={{ ["--i" as string]: 1 }}>
          <button
            type="button"
            className={styles.translateBtn}
            disabled={decode.busy}
            onClick={decode.toggle}
          >
            {decode.busy
              ? "Decoding…"
              : decode.mode === "glyph"
                ? "Translate"
                : "Show original"}
          </button>
        </div>
      )}
      {blocks.length === 0 ? (
        <p className={styles.loreEmpty} style={{ ["--i" as string]: 2 }}>
          No lore — add it in factionLore.ts (key "{faction.id}").
        </p>
      ) : (
        <div className={styles.loreColumns}>
          {columns.map((column, c) => (
            <div key={c} className={styles.loreCol}>
              {column.map((block, i) => {
                // Indeks animacji liczony w obrębie kolumny: obie kolumny odsłaniają
                // się równolegle od góry, a nie jedna po drugiej.
                const style = { ["--i" as string]: i + 2 };
                // Numer bloku w kolejności czytania (kolumna 1, potem 2) — dla fali
                // rozszyfrowania.
                const readingIndex = (c === 0 ? 0 : columns[0].length) + i;
                const content = isGlyph ? (
                  <DecodedText
                    text={block.text}
                    mode={decode.mode}
                    progress={decode.progress}
                    index={readingIndex}
                    total={total}
                  />
                ) : (
                  block.text
                );
                if (block.kind === "heading") {
                  return (
                    <h3 key={i} className={styles.loreHeading} style={style}>
                      {content}
                    </h3>
                  );
                }
                if (block.kind === "quote") {
                  return (
                    <blockquote key={i} className={styles.loreBlockQuote} style={style}>
                      {content}
                    </blockquote>
                  );
                }
                const variant = [
                  block.tone === "red" ? styles.toneRed : "",
                  block.tone === "dark-red" ? styles.toneDarkRed : "",
                  block.size === "large" ? styles.sizeLarge : "",
                  block.size === "small" ? styles.sizeSmall : "",
                ].join(" ");
                return (
                  <p key={i} className={`${styles.loreParagraph} ${variant}`} style={style}>
                    {content}
                  </p>
                );
              })}
            </div>
          ))}
        </div>
      )}
      {flash && (
        <span
          aria-hidden
          className={`${styles.flash} ${decode.mode === "glyph" ? styles.flashGlyph : ""}`}
          style={{ left: `${flash.x}%`, top: `${flash.y}%`, fontSize: `${flash.size}em` }}
        >
          {flash.text}
        </span>
      )}
    </article>
  );
}

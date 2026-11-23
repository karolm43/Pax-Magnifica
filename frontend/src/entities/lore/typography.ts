/**
 * Typografia tekstów lore (cytaty, flavour kart, kronika) — jedno miejsce, żeby łamanie linii
 * wyglądało dobrze niezależnie od szerokości okna: bez samotnego myślnika/cudzysłowu na początku
 * lub końcu linii i bez jednoliterowego „a”/„I” wiszącego na końcu wiersza.
 */

/** Twarda spacja: nie pozwala przełamać linii w tym miejscu. */
export const NBSP = " ";
/** Word joiner: niewidoczny, skleja sąsiednie znaki (cudzysłów z ostatnim słowem). */
export const WORD_JOINER = "⁠";

const OPEN_CONTEXT = /[\s([{—–“‘]/;

/** Prosty cudzysłów → drukarski (otwierający po początku/spacji/nawiasie, inaczej zamykający). */
function curlyQuotes(text: string): string {
  let out = "";
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const prev = i === 0 ? "" : text[i - 1];
    const opens = i === 0 || OPEN_CONTEXT.test(prev);
    if (ch === '"') out += opens ? "“" : "”";
    // Apostrof w środku słowa (don't, Emperor's) i zamykający pojedynczy → ’; otwierający → ‘.
    else if (ch === "'") out += opens ? "‘" : "’";
    else out += ch;
  }
  return out;
}

/**
 * Wygładza tekst do wyświetlenia: `--` → `—`, `...` → `…`, drukarskie cudzysłowy,
 * twarda spacja przed myślnikiem i po jednoliterowych słowach (a, I). Idempotentna.
 */
export function typeset(text: string): string {
  return curlyQuotes(text)
    .replace(/\s*--\s*/g, " — ")
    .replace(/\.{3}/g, "…")
    .replace(/\s+([—–])/g, `${NBSP}$1`)
    .replace(/(^|\s)([aAI])\s+/g, `$1$2${NBSP}`);
}

/**
 * Cytat w drukarskich cudzysłowach: zamykający `”` sklejony z ostatnim słowem. Ewentualne
 * cudzysłowy z brzegów danych zdejmujemy, żeby ich nie dublować.
 */
export function quoted(text: string): string {
  const inner = text.trim().replace(/^["“”„«»]+|["“”„«»]+$/g, "").trim();
  return `“${typeset(inner)}${WORD_JOINER}”`;
}

/** Podpis autora: `—` + twarda spacja, żeby kreska nie została sama na końcu linii. */
export function attribution(author: string): string {
  return `—${NBSP}${author.trim().replace(/^[—–-]\s*/, "")}`;
}

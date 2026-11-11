/*
 * Ostatnie błędy JS / konsoli tej karty — dołączane do zgłoszenia „Report bug", żeby raport
 * mówił nie tylko „co widać", ale też „co się wywaliło". Bufor kołowy (MAX_ENTRIES), instalowany
 * raz przy starcie (`main.tsx`). Oryginalne `console.error` działa dalej bez zmian.
 */
const MAX_ENTRIES = 30;
const entries: string[] = [];
let installed = false;

function push(kind: string, text: string): void {
  const stamp = new Date().toISOString().slice(11, 19);
  entries.push(`${stamp} ${kind}: ${text.slice(0, 800)}`);
  if (entries.length > MAX_ENTRIES) entries.shift();
}

function describe(value: unknown): string {
  if (value instanceof Error) return `${value.name}: ${value.message}`;
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function installConsoleCapture(): void {
  if (installed || typeof window === "undefined") return;
  installed = true;
  const original = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    push("console", args.map(describe).join(" "));
    original(...args);
  };
  window.addEventListener("error", (event) => {
    push("error", event.error ? describe(event.error) : event.message);
  });
  window.addEventListener("unhandledrejection", (event) => {
    push("rejection", describe(event.reason));
  });
}

/** Kopia bufora (najstarsze pierwsze). */
export function recentConsoleErrors(): string[] {
  return [...entries];
}

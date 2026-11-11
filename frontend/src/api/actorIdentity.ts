/*
 * Tożsamość aktora (RULES.md 44.1a) — JEDYNY punkt, w którym front mówi backendowi,
 * KTO wykonuje żądanie. Nagłówek `X-Actor-Id` trafia do każdego żądania backendu (`/bot…`).
 *
 * - Tryb lokalny (domyślny, jedno okno): brak miejsca → brak nagłówka → backend działa
 *   w trybie zaufanym, jak dotychczas (operator klika za wszystkich).
 * - Test „kilku graczy": otwórz grę z `?seat=p2` — okno działa jako gracz p2, a backend
 *   odrzuca (403) akcje, do których p2 nie jest uprawniony. Wybór pamiętany w sessionStorage
 *   (osobno dla każdej karty), `?seat=` (puste) go czyści.
 * - Etap N1 (RULES.md 44.2): w tym samym miejscu zamiast `seat` pójdzie token miejsca.
 */

export const ACTOR_HEADER = "X-Actor-Id";
const STORAGE_KEY = "custodian.seat";
const BACKEND_PREFIX = "/bot";

/** Odczytuje miejsce z `?seat=` (i zapamiętuje) albo z sessionStorage. */
export function readActingSeat(search: string = window.location.search): string | null {
  const fromUrl = new URLSearchParams(search).get("seat");
  try {
    if (fromUrl !== null) {
      const seat = fromUrl.trim();
      if (seat) sessionStorage.setItem(STORAGE_KEY, seat);
      else sessionStorage.removeItem(STORAGE_KEY);
      return seat || null;
    }
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return fromUrl?.trim() || null;
  }
}

let actingSeat: string | null = null;

/** Gracz, jako który działa to okno (`null` = tryb lokalny, bez kontroli tożsamości). */
export function getActingSeat(): string | null {
  return actingSeat;
}

function isBackendUrl(input: RequestInfo | URL): boolean {
  const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (raw.startsWith(BACKEND_PREFIX)) return true;
  try {
    const url = new URL(raw, window.location.origin);
    return url.origin === window.location.origin && url.pathname.startsWith(BACKEND_PREFIX);
  } catch {
    return false;
  }
}

/** Dokłada nagłówek aktora do żądania backendu; pozostałe (CDN, assety) bez zmian. */
export function withActorHeader(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  seat: string | null,
): RequestInit | undefined {
  if (!seat || !isBackendUrl(input)) return init;
  const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
  headers.set(ACTOR_HEADER, seat);
  return { ...init, headers };
}

/** Instaluje opakowanie `fetch` (raz, przy starcie aplikacji). */
export function installActorIdentity(): void {
  actingSeat = readActingSeat();
  if (!actingSeat) return;
  const original = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
    original(input, withActorHeader(input, init, actingSeat));
}

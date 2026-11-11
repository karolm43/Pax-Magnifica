/*
 * Tożsamość aktora (RULES.md 44.1a) — JEDYNY punkt, w którym front mówi backendowi,
 * KTO wykonuje żądanie. Nagłówek `X-Actor-Id` trafia do każdego żądania backendu (`/bot…`).
 *
 * - Tryb lokalny (domyślny, jedno okno): brak miejsca → brak nagłówka → backend działa
 *   w trybie zaufanym, jak dotychczas (operator klika za wszystkich).
 * - Test „kilku graczy": otwórz grę z `?seat=p2` — okno działa jako gracz p2, a backend
 *   odrzuca (403) akcje, do których p2 nie jest uprawniony. Wybór pamiętany w sessionStorage
 *   (osobno dla każdej karty), `?seat=` (puste) go czyści.
 * - Gra sieciowa (RULES.md 44.2): link zaproszenia `?token=…` — token miejsca trafia do nagłówka
 *   `X-Seat-Token` (i do adresu WebSocketu). Tożsamość ustala wtedy backend z tokenu, a `seat`
 *   jest ignorowany. Token pamiętany w sessionStorage i usuwany z paska adresu (nie wycieknie
 *   przy udostępnianiu ekranu / zrzucie).
 */

export const ACTOR_HEADER = "X-Actor-Id";
export const SEAT_TOKEN_HEADER = "X-Seat-Token";
const STORAGE_KEY = "custodian.seat";
const TOKEN_KEY = "custodian.token";
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

/** Token miejsca z `?token=` (zapamiętany w karcie); `?token=` puste go czyści. */
export function readSeatToken(search: string = window.location.search): string | null {
  const fromUrl = new URLSearchParams(search).get("token");
  try {
    if (fromUrl !== null) {
      const token = fromUrl.trim();
      if (token) sessionStorage.setItem(TOKEN_KEY, token);
      else sessionStorage.removeItem(TOKEN_KEY);
      return token || null;
    }
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return fromUrl?.trim() || null;
  }
}

/**
 * Zapamiętuje token otrzymany w trakcie (dołączenie do lobby) i od razu go używa — bez
 * przeładowania strony (opakowanie `fetch` czyta bieżący token przy każdym żądaniu).
 */
export function storeSeatToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // brak storage (tryb prywatny) — token żyje do zamknięcia karty
  }
  seatToken = token;
}

/** Usuwa `token` z paska adresu (bez przeładowania). */
function stripTokenFromUrl(): void {
  const url = new URL(window.location.href);
  if (!url.searchParams.has("token")) return;
  url.searchParams.delete("token");
  window.history.replaceState(window.history.state, "", url.toString());
}

let actingSeat: string | null = null;
let seatToken: string | null = null;

/** Token miejsca tej karty (`null` = brak, np. tryb lokalny). */
export function getSeatToken(): string | null {
  return seatToken;
}

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
  token: string | null = null,
): RequestInit | undefined {
  if ((!seat && !token) || !isBackendUrl(input)) return init;
  const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
  if (seat) headers.set(ACTOR_HEADER, seat);
  if (token) headers.set(SEAT_TOKEN_HEADER, token);
  return { ...init, headers };
}

/** Instaluje opakowanie `fetch` (raz, przy starcie aplikacji; zawsze — token może dojść później). */
export function installActorIdentity(): void {
  actingSeat = readActingSeat();
  seatToken = readSeatToken();
  stripTokenFromUrl();
  const original = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const response = await original(input, withActorHeader(input, init, actingSeat, seatToken));
    if (response.status === 403 && isBackendUrl(input)) notifyForbidden(response);
    return response;
  };
}

/** Zdarzenie okna: backend odmówił (403 — „nie twój ruch" / nie host). Słucha `NetworkPanel`. */
export const FORBIDDEN_EVENT = "custodian:forbidden";

function notifyForbidden(response: Response): void {
  void response
    .clone()
    .json()
    .then((body: { detail?: unknown }) =>
      typeof body.detail === "string" ? body.detail : "Not allowed.",
    )
    .catch(() => "Not allowed.")
    .then((detail) => window.dispatchEvent(new CustomEvent(FORBIDDEN_EVENT, { detail })));
}

/** Adres WebSocketu backendu (przez proxy `/bot`), z tokenem miejsca w sieci. */
export function backendSocketUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const query = seatToken ? `?token=${encodeURIComponent(seatToken)}` : "";
  return `${proto}//${window.location.host}${BACKEND_PREFIX}/ws${query}`;
}

/**
 * Czytelny komunikat z odpowiedzi błędu backendu (FastAPI: ``{"detail": ...}``).
 *
 * Backend zwraca ``detail`` jako tekst (reguły gry, 403) albo listę błędów walidacji. Gracz
 * nigdy nie powinien zobaczyć surowego JSON-a ani „[object Object]", więc tu wszystko
 * sprowadzamy do jednego zdania.
 */
export function parseErrorDetail(raw: string, status: number): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const { detail } = parsed;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => {
          const entry = item as { msg?: unknown; loc?: unknown };
          const msg = typeof entry.msg === "string" ? entry.msg : "Invalid value";
          const field = Array.isArray(entry.loc)
            ? entry.loc.filter((p) => p !== "body").join(".")
            : "";
          return field ? `${field}: ${msg}` : msg;
        })
        .join("; ");
    }
  } catch {
    // nie-JSON - użyj surowego tekstu niżej
  }
  if (raw.trim()) return raw;
  return fallbackForStatus(status);
}

/** Zdanie dla odpowiedzi bez treści (serwer padł, brak uprawnień...). */
function fallbackForStatus(status: number): string {
  if (status === 401) return "Join the game from your invite link first.";
  if (status === 403) return "You are not allowed to do that right now.";
  if (status === 404) return "The server does not know that action - refresh the page.";
  if (status >= 500) return "The server hit an unexpected error - try again.";
  return `The request was rejected (error ${status}).`;
}

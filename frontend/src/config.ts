/*
 * Konfiguracja adresów backendu. Custodian Engine działa WYŁĄCZNIE lokalnie
 * (jeden backend FastAPI, jedna gra), więc nie ma rozbicia dev/prod jak w
 * oryginalnym AsyncTI4 — zostaje jeden zestaw adresów.
 *
 * Ścieżki względne (/bot, /static) są przepuszczane przez proxy Vite do backendu
 * na :8000 (patrz vite.config.ts), dzięki czemu front używa adresów względnych.
 */
export const config = {
  api: {
    // GET {gameDataUrl}/{gameId}/web-data  -> dokument PlayerDataResponse.
    // GET {gameDataUrl}/{gameId}/events    -> log zdarzeń gry.
    gameDataUrl: "/bot/api/public/game",
    // Baza REST bota (ręka gracza, uwierzytelnianie). Proxy /bot -> backend.
    botApiUrl: "/bot/api",
    // STOMP WebSocket (live-sync). Backend NIE wystawia go jeszcze — viewer działa
    // przez refetch; adres lokalny tylko po to, by klient nie łączył się z produkcją.
    websocketUrl: "ws://127.0.0.1:8000/ws-stomp",
    // OAuth Discorda: logowanie jest w UI, ale lokalnie nieużywane (brak serwera auth).
    discordRedirectUri: "http://localhost:5173/login",
  },
};

/*
 * Push stanu w grze sieciowej (RULES.md 44.3): WebSocket `/bot/ws?token=…`.
 *
 * Backend po każdej zmianie wysyła TEJ karcie jej własną projekcję stanu. Nie składamy UI
 * z tej wiadomości — traktujemy ją jako sygnał „coś się zmieniło" i odświeżamy aktywne
 * zapytania (web-data, oferty, walka…), które serwer i tak rzutuje z perspektywy tokenu.
 * Dzięki temu widać ruchy INNYCH graczy bez klikania. Tryb lokalny: hook nic nie robi
 * (zachowanie jak dotąd: odświeżanie po własnych akcjach).
 */
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { backendSocketUrl } from "@/api/actorIdentity";

const DEBOUNCE_MS = 200;
const RECONNECT_MS = 2000;

export function useBackendPush(enabled: boolean): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;
    let socket: WebSocket | null = null;
    let closed = false;
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const refresh = () => {
      clearTimeout(refreshTimer);
      // Akcja wysyła kilka wiadomości (stan + mapa) — jedno odświeżenie na serię.
      refreshTimer = setTimeout(() => {
        void queryClient.invalidateQueries({ refetchType: "active" });
      }, DEBOUNCE_MS);
    };

    const connect = () => {
      socket = new WebSocket(backendSocketUrl());
      socket.onmessage = refresh;
      socket.onclose = () => {
        if (!closed) reconnectTimer = setTimeout(connect, RECONNECT_MS);
      };
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(refreshTimer);
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [enabled, queryClient]);
}

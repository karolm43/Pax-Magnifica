/*
 * Kreator nowej gry na żywo — synchronizacja z lobby na serwerze (RULES.md 44.5a).
 *
 * Kreator (`useSetupStore`) zostaje tym samym, graficznym kreatorem; ten moduł spina go ze
 * wspólnym szkicem na serwerze (`/lobby/draft`, backend `lobby_draft.py`):
 *
 * - lokalna zmiana → po 250 ms łatka z RÓŻNICĄ względem ostatnio zsynchronizowanego stanu
 *   (host: mapa, krok, dowolne sloty; zmiana liczby graczy = pełny szkic; gość: tylko swój slot);
 * - co sekundę odczyt lobby → nowsza wersja szkicu trafia do kreatora (cudze wybory na żywo),
 *   chyba że właśnie wysyłamy własną zmianę (żeby nie „cofać" pisanego tekstu);
 * - odmowa serwera (zajęta frakcja, cudzy slot) → komunikat i powrót do stanu z serwera.
 *
 * `useLobbyRole` mówi krokom kreatora, kto patrzy: host prowadzi, gość edytuje tylko swój slot.
 */
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { create } from "zustand";
import { FORBIDDEN_EVENT } from "@/api/actorIdentity";
import { useSetupStore, type SetupSlot } from "@/domains/setup/useSetupStore";
import { useLobby, type LobbyView } from "./useLobby";
import { useNetworkMe } from "./useNetworkMe";

export type LobbyDraft = {
  slots: SetupSlot[];
  owners: (string | null)[];
  ownerNames: (string | null)[];
  mapString: string;
  step: number;
  version: number;
};

/** Pola slotu, które gość może zmieniać (jak `GUEST_FIELDS` w backendzie). */
const GUEST_FIELDS = new Set(["factionId", "startingTech", "color", "seat", "name"]);
const DEBOUNCE_MS = 250;

type LobbyRole = {
  /** Kreator działa jako lobby sieciowe. */
  active: boolean;
  isGuest: boolean;
  /** Mój slot w szkicu (host lub gość). */
  mySlot: number | null;
  owners: (string | null)[];
  ownerNames: (string | null)[];
  /** Adresy do podania znajomym (tylko host). */
  links: string[];
};

export const useLobbyRole = create<LobbyRole>(() => ({
  active: false,
  isGuest: false,
  mySlot: null,
  owners: [],
  ownerNames: [],
  links: [],
}));

/** Czy ta osoba może edytować slot `index` (lokalnie / host: zawsze; gość: tylko swój). */
export function canEditSlot(role: LobbyRole, index: number): boolean {
  return !role.active || !role.isGuest || role.mySlot === index;
}

type Snapshot = { slots: SetupSlot[]; mapString: string; step: number };

function snapshot(): Snapshot {
  const s = useSetupStore.getState();
  return { slots: s.slots, mapString: s.mapString, step: s.currentStepIndex };
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

async function send(method: "PUT" | "PATCH", body: unknown): Promise<LobbyView> {
  const res = await fetch("/bot/lobby/draft", {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let message = `Error ${res.status}`;
    try {
      const parsed = (await res.json()) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // nie-JSON
    }
    // 403 ogłasza już opakowanie fetch; 422 (np. zajęta frakcja) — tutaj.
    if (res.status !== 403) {
      window.dispatchEvent(new CustomEvent(FORBIDDEN_EVENT, { detail: message }));
    }
    throw new Error(message);
  }
  return (await res.json()) as LobbyView;
}

/**
 * Spina kreator z lobby. `enabled` = lobby otwarte (gra sieciowa). Host przy wejściu wysyła
 * pełny szkic (świeże lobby po „Play"), gość od razu przyjmuje szkic hosta.
 */
export function useSetupSync(enabled: boolean): void {
  const navigate = useNavigate();
  const { data: me } = useNetworkMe();
  const { data: lobby, refetch } = useLobby(enabled);
  const synced = useRef<Snapshot | null>(null);
  const version = useRef(0);
  const applying = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inFlight = useRef(false);
  const putting = useRef(false);
  const hasDraft = useRef(false);

  const isHost = lobby?.you === "host";
  const draft = (lobby?.draft ?? null) as LobbyDraft | null;

  // Rola dla kroków kreatora.
  useEffect(() => {
    if (!enabled || !lobby) {
      useLobbyRole.setState({ active: false, isGuest: false, mySlot: null });
      return;
    }
    const port = window.location.port ? `:${window.location.port}` : "";
    const owners = draft?.owners ?? [];
    const mine = owners.indexOf(lobby.you ?? "");
    useLobbyRole.setState({
      active: true,
      isGuest: !isHost,
      mySlot: mine >= 0 ? mine : null,
      owners,
      ownerNames: draft?.ownerNames ?? [],
      // Protokół strony (nie stały adres) — strażnik lokalności zabrania literałów URL.
      links: lobby.addresses.map((ip) => `${window.location.protocol}//${ip}${port}`),
    });
  }, [enabled, lobby, draft, isHost]);

  useEffect(() => () => useLobbyRole.setState({ active: false, isGuest: false }), []);

  const apply = (d: LobbyDraft) => {
    applying.current = true;
    useSetupStore.setState({
      slots: d.slots,
      playerCount: d.slots.length,
      mapString: d.mapString,
      currentStepIndex: d.step,
    });
    applying.current = false;
    synced.current = snapshot();
    version.current = d.version;
  };

  // Brak szkicu na serwerze (świeże lobby po „Play") → host wysyła pełny kreator; gość czeka.
  // Jest szkic → nowsza wersja trafia do kreatora (gdy nie wysyłamy własnej zmiany).
  useEffect(() => {
    hasDraft.current = draft != null;
    if (!enabled || !lobby) return;
    if (!draft) {
      synced.current = null;
      version.current = 0;
      if (!isHost || putting.current) return;
      putting.current = true;
      const s = snapshot();
      void send("PUT", {
        draft: { slots: s.slots, owners: ["host"], mapString: s.mapString, step: s.step },
      })
        .then((view) => {
          if (view.draft) apply(view.draft as LobbyDraft);
        })
        .catch(() => undefined)
        .finally(() => {
          putting.current = false;
          void refetch();
        });
      return;
    }
    if (synced.current && draft.version <= version.current) return;
    if (timer.current || inFlight.current) return;
    apply(draft);
    // Reagujemy tylko na szkic z serwera (apply/refetch są stabilne w czasie życia hooka).
  }, [enabled, lobby, draft, isHost]);

  // Gość: host wystartował grę i posadził mnie przy stole → do gry.
  useEffect(() => {
    if (enabled && !isHost && me?.player_id && lobby?.game_started) navigate("/game");
  }, [enabled, isHost, me?.player_id, lobby?.game_started, navigate]);

  // Lokalne zmiany → łatki do serwera.
  useEffect(() => {
    if (!enabled) return;
    const flush = async () => {
      timer.current = undefined;
      const before = synced.current;
      if (!before || !hasDraft.current) return; // szkic dopiero powstaje — wyśle go PUT
      const now = snapshot();
      const role = useLobbyRole.getState();
      let request: Promise<LobbyView> | null = null;
      if (!role.isGuest && now.slots.length !== before.slots.length) {
        request = send("PUT", {
          draft: { slots: now.slots, owners: role.owners, mapString: now.mapString, step: now.step },
        });
      } else {
        const patch: Record<string, unknown> = {};
        const slots: Record<string, Partial<SetupSlot>> = {};
        now.slots.forEach((slot, i) => {
          if (role.isGuest && i !== role.mySlot) return;
          const prev = before.slots[i] ?? ({} as SetupSlot);
          const changed: Record<string, unknown> = {};
          for (const key of Object.keys(slot) as (keyof SetupSlot)[]) {
            if (role.isGuest && !GUEST_FIELDS.has(key)) continue;
            if (!same(slot[key], prev[key])) changed[key] = slot[key];
          }
          if (Object.keys(changed).length > 0) slots[String(i)] = changed as Partial<SetupSlot>;
        });
        if (Object.keys(slots).length > 0) patch.slots = slots;
        if (!role.isGuest && now.mapString !== before.mapString) patch.mapString = now.mapString;
        if (!role.isGuest && now.step !== before.step) patch.step = now.step;
        if (Object.keys(patch).length > 0) request = send("PATCH", patch);
      }
      if (!request) return;
      inFlight.current = true;
      try {
        const view = await request;
        if (view.draft) apply(view.draft as LobbyDraft);
      } catch {
        // odmowa: wróć do szkicu z serwera
        const fresh = await refetch();
        const d = fresh.data?.draft as LobbyDraft | null | undefined;
        if (d) apply(d);
      } finally {
        inFlight.current = false;
      }
    };
    const unsubscribe = useSetupStore.subscribe(() => {
      if (applying.current || !synced.current) return;
      clearTimeout(timer.current);
      timer.current = setTimeout(() => void flush(), DEBOUNCE_MS);
    });
    return () => {
      unsubscribe();
      clearTimeout(timer.current);
      timer.current = undefined;
    };
  }, [enabled, refetch]);
}

/** Po utworzeniu gry z lobby: właściciele slotów siadają na swoich miejscach. */
export async function seatLobbyPlayers(): Promise<void> {
  const res = await fetch("/bot/lobby/seat", { method: "POST" });
  if (!res.ok) throw new Error(`Seating players failed (${res.status})`);
}

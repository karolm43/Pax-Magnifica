import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import type { ActionCardInput } from "@/api/useActionCard";

/*
 * Komponenty frakcji (RULES.md 61): liderzy, zdolności frakcji, przełom — formularz „ACTION:" i
 * stan lidera; promissory notes z ręki — zagrywalność i formularz. Legalne opcje liczy silnik,
 * gracz zawsze decyduje. Front nie zna efektów — renderuje opis z backendu.
 */
const BOT_ROOT = "/bot";

export type FactionComponentKind = "leader" | "ability" | "breakthrough" | "technology";

export type FactionComponentForm = {
  kind: FactionComponentKind;
  component_id: string;
  name: string;
  text: string;
  /**
   * `action` = „ACTION:" (akcja komponentu), `window` = „During X: you may…" — gracz używa w danym
   * kroku bez zużycia akcji (RULES.md 62.0), `passive` = działa sam / przez oferty.
   */
  mode: "action" | "window" | "passive";
  implemented: boolean;
  inputs: ActionCardInput[];
  /** Lider: locked | unlocked | exhausted | purged; przełom: unlocked | exhausted. */
  status: string;
  leader_type: string | null;
  unlock_condition: string | null;
  /** Lider zablokowany, a silnik nie sprawdza jeszcze jego warunku — gracz odblokowuje sam. */
  can_claim_unlock: boolean;
};

/** Formularz komponentu frakcji gracza (422, gdy gracz go nie ma). */
export function useFactionComponentForm(
  kind: FactionComponentKind | null,
  componentId: string | null,
  playerId: string | null,
) {
  return useQuery({
    queryKey: ["factionComponentForm", kind, componentId, playerId],
    enabled: Boolean(kind && componentId && playerId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async () =>
      fetchJson<FactionComponentForm>(
        `${BOT_ROOT}/faction-component/${kind}/${encodeURIComponent(componentId ?? "")}/form?player_id=${encodeURIComponent(playerId ?? "")}`,
        "factionComponentForm",
      ),
  });
}

export type PromissoryPlayability = {
  note_id: string;
  template: string;
  owner_id: string | null;
  playable: boolean;
  reason: string | null;
  implemented: boolean;
  /** Notka grana w odpowiedzi na okno (nie ACTION) - sygnał przy zwiniętej ręce. */
  reaction?: boolean;
};

export type PromissoryForm = {
  note_id: string;
  template: string;
  owner_id: string | null;
  name: string;
  text: string;
  action: boolean;
  implemented: boolean;
  inputs: ActionCardInput[];
};

/** Notki z ręki gracza i które można zagrać TERAZ (po ``note_id``); odświeżane co 3 s. */
export function usePromissoryPlayability(playerId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["promissoryPlayable", playerId],
    enabled: Boolean(playerId) && enabled,
    staleTime: 0,
    refetchInterval: 3000,
    retry: false,
    queryFn: async (): Promise<Record<string, PromissoryPlayability>> => {
      const data = await fetchJson<{ notes: PromissoryPlayability[] }>(
        `${BOT_ROOT}/promissory/playable?player_id=${encodeURIComponent(playerId ?? "")}`,
        "promissoryPlayable",
      );
      return Object.fromEntries(data.notes.map((note) => [note.note_id, note]));
    },
  });
}

/** Formularz zagrania notki (tekst z kolorem właściciela + wybory). */
export function usePromissoryForm(noteId: string | null, playerId: string | null) {
  return useQuery({
    queryKey: ["promissoryForm", noteId, playerId],
    enabled: Boolean(noteId && playerId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async () =>
      fetchJson<PromissoryForm>(
        `${BOT_ROOT}/promissory/${encodeURIComponent(noteId ?? "")}/form?player_id=${encodeURIComponent(playerId ?? "")}`,
        "promissoryForm",
      ),
  });
}

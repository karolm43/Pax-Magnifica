import { useQuery } from "@tanstack/react-query";
import { parseErrorDetail } from "@/api/apiError";

/*
 * Formularz zagrania karty akcji (RULES.md 53). Backend opisuje, jakich decyzji wymaga karta
 * i jakie są legalne opcje na bieżącym stanie gry — front nie zna kart, tylko renderuje opis.
 */

/** Korzeń proxy do backendu silnika (jak w ``useBoardEditor``; NIE ``/bot/api``). */
const BOT_ROOT = "/bot";

/** Jedna opcja wyboru: ``id`` jest unikalne w obrębie wejścia, ``value`` trafia do parametrów. */
export type ActionCardOption = {
  id: string;
  value: unknown;
  label: string;
  /** Dane strukturalne dla graficznych formularzy (np. Transit Diodes). */
  meta?: Record<string, unknown>;
};

type InputBase = { key: string; label: string; hint: string };

export type ActionCardInput =
  | (InputBase & {
      kind: "choice";
      /** Gdy true, słownik z wybranej opcji jest wklejany do parametrów (np. cel Lucky Shot). */
      merge: boolean;
      options: ActionCardOption[];
    })
  | (InputBase & {
      kind: "multi";
      min: number;
      max: number;
      options: ActionCardOption[];
      /** Wejście jest płatnością: koszt, czym się płaci i które pole liczbowe to TG. */
      payment?: { cost: number; valueKind: string; tradeGoods: string };
    })
  | (InputBase & { kind: "number"; min: number; max: number })
  /** Tylko informacja (bez wyboru); ``options`` = legalne cele, pusta lista blokuje zagranie. */
  | (InputBase & { kind: "info"; options: ActionCardOption[] })
  /** „Zbadaj technologię”: pełne okno badania (``TechnologyOverlay``) z opisem ``research``. */
  | (InputBase & { kind: "research"; research: Record<string, unknown> });

/** Wejście z opcjami do wyboru (choice / multi / info). */
function optionCount(input: ActionCardInput): number | null {
  return "options" in input ? input.options.length : null;
}

/**
 * Czy któreś wejście nie ma dość legalnych opcji (formularz nie do rozstrzygnięcia). Ta sama
 * reguła co ``action_cards._has_legal_choices`` w silniku.
 */
export function hasNoLegalOption(inputs: ActionCardInput[]): boolean {
  return inputs.some((input) => {
    const count = optionCount(input);
    if (count === null) return false;
    return count < (input.kind === "multi" ? input.min : 1);
  });
}

export type ActionCardForm = {
  card_id: string;
  name: string;
  text: string;
  /** Czego dotyczy karta teraz i co da (podgląd z silnika) — null, gdy brak. */
  summary?: string | null;
  /** False = silnik nie automatyzuje karty: zagranie ją odrzuca, skutek rozstrzyga operator. */
  implemented: boolean;
  inputs: ActionCardInput[];
};

/** Pobiera formularz karty dla gracza (karta musi być w jego ręce, inaczej 422). */
export function useActionCardForm(
  cardId: string | null,
  playerId: string | null,
  /** Migawka historii (hold-rewind): formularz liczony na stanie z tamtej chwili. */
  seq?: number,
) {
  return useQuery({
    queryKey: ["actionCardForm", cardId, playerId, seq ?? null],
    enabled: Boolean(cardId && playerId),
    // Opcje zależą od bieżącego stanu gry — nie cache'ujemy między otwarciami.
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async () => {
      const id = encodeURIComponent(cardId ?? "");
      const player = encodeURIComponent(playerId ?? "");
      const url =
        seq === undefined
          ? `${BOT_ROOT}/action-card/${id}/inputs?player_id=${player}`
          : `${BOT_ROOT}/hold/${id}/inputs?player_id=${player}&seq=${seq}`;
      const response = await fetch(url);
      if (!response.ok) {
        // 422 niesie powód z silnika (np. karty nie ma w ręce); inne kody = błąd serwera/trasy.
        const raw = await response.text().catch(() => "");
        let detail = `Error ${response.status}`;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed.detail === "string") detail = parsed.detail;
        } catch {
          // nie-JSON - zostaje kod statusu
        }
        throw new Error(detail);
      }
      return (await response.json()) as ActionCardForm;
    },
  });
}

/** Wartość pola formularza: wybrane id opcji / lista id / liczba. */
export type FormValue = string | null | string[] | number;

/**
 * Składa parametry żądania z wartości formularza. ``ready`` = wszystkie wymagane pola
 * wypełnione w dozwolonych zakresach (przycisk „Play” wolno nacisnąć).
 */
export function buildActionCardParams(
  inputs: ActionCardInput[],
  values: Record<string, FormValue>,
): { params: Record<string, unknown>; ready: boolean } {
  const params: Record<string, unknown> = {};
  let ready = true;
  for (const input of inputs) {
    const value = values[input.key];
    if (input.kind === "choice") {
      const option = input.options.find((o) => o.id === value);
      if (!option) {
        ready = false;
        continue;
      }
      if (input.merge && typeof option.value === "object" && option.value !== null) {
        Object.assign(params, option.value);
      } else {
        params[input.key] = option.value;
      }
    } else if (input.kind === "multi") {
      const ids = Array.isArray(value) ? value : [];
      if (ids.length < input.min || ids.length > input.max) ready = false;
      params[input.key] = ids
        .map((id) => input.options.find((o) => o.id === id)?.value)
        .filter((v) => v !== undefined);
    } else if (input.kind === "number") {
      const amount = typeof value === "number" ? value : input.min;
      if (amount < input.min || amount > input.max) ready = false;
      params[input.key] = amount;
    }
  }
  // Płatność (planety + TG oznaczone przez backend jako ``payment``): gotowe dopiero, gdy
  // wybrane planety i trade goods pokrywają koszt - inaczej silnik i tak odrzuci odpowiedź.
  for (const input of inputs) {
    if (input.kind !== "multi" || !input.payment) continue;
    const ids = Array.isArray(values[input.key]) ? (values[input.key] as string[]) : [];
    const fromPlanets = input.options
      .filter((o) => ids.includes(o.id))
      .reduce((sum, o) => sum + (typeof o.meta?.value === "number" ? o.meta.value : 0), 0);
    const tg = params[input.payment.tradeGoods];
    if (fromPlanets + (typeof tg === "number" ? tg : 0) < input.payment.cost) ready = false;
  }
  return { params, ready };
}

/** Czy karta z ręki jest zagrywalna TERAZ jako akcja (decyzja silnika, nie UI). */
export type ActionCardPlayability = {
  card_id: string;
  playable: boolean;
  /** Powód, gdy nie - pokazywany w podpowiedzi karty. */
  reason: string | null;
  implemented: boolean;
  /** Karta reakcji (okno inne niż ACTION): dok sygnalizuje ją także zwinięty (RULES.md 54.8). */
  reaction?: boolean;
  /**
   * Okno minęło ostatnim krokiem (np. Public Disgrace po wyborze rywala): zagranie cofa grę do
   * tej migawki (hold-rewind, RULES.md 53.7).
   */
  hold_seq?: number | null;
};

/**
 * Zagrywalność kart akcji z ręki gracza (po ``card_id``). Odświeżana co kilka sekund, bo zależy
 * od tury, fazy, okien i celów na planszy; dok ręki pozwala podnieść tylko karty zagrywalne.
 */
/** Odpowiedź ``/action-card/playable``: karty + limit ręki (R_action_cards, RULES.md 53.8). */
type PlayableResponse = {
  cards: ActionCardPlayability[];
  /** Ile kart gracz musi odrzucić do limitu ręki (0 = w limicie). */
  discard?: number;
  handLimit?: number | null;
};

function playableQuery(playerId: string | null, enabled: boolean) {
  return {
    queryKey: ["actionCardPlayable", playerId],
    enabled: Boolean(playerId) && enabled,
    staleTime: 0,
    refetchInterval: 3000,
    retry: false,
    queryFn: async (): Promise<PlayableResponse> => {
      const url = `${BOT_ROOT}/action-card/playable?player_id=${encodeURIComponent(playerId ?? "")}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Error ${response.status}`);
      return (await response.json()) as PlayableResponse;
    },
  };
}

const byCardId = (data: PlayableResponse): Record<string, ActionCardPlayability> =>
  Object.fromEntries(data.cards.map((card) => [card.card_id, card]));

const handLimitOf = (data: PlayableResponse): { discard: number; handLimit: number | null } => ({
  discard: data.discard ?? 0,
  handLimit: data.handLimit ?? null,
});

export function useActionCardPlayability(playerId: string | null, enabled: boolean) {
  return useQuery({ ...playableQuery(playerId, enabled), select: byCardId });
}

/**
 * Limit ręki kart akcji: ile kart gracz musi odrzucić (to samo zapytanie co zagrywalność — jeden
 * fetch). Nadwyżkę odrzuca się przeciągnięciem karty na stos odrzuconych.
 */
export function useHandLimit(playerId: string | null, enabled: boolean) {
  return useQuery({ ...playableQuery(playerId, enabled), select: handLimitOf });
}

/** Odrzuca wybraną kartę akcji ponad limit ręki; zwraca komunikat błędu albo null. */
export async function postDiscardExcess(actorId: string, cardId: string): Promise<string | null> {
  const response = await fetch(`${BOT_ROOT}/action-card/discard-excess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, card_id: cardId }),
  });
  if (response.ok) return null;
  const raw = await response.text().catch(() => "");
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // nie-JSON — zostaje kod statusu
  }
  return `Error ${response.status}`;
}

/** Krok historii, do którego można się cofnąć kartą (HOLD, RULES.md 53.7). */
export type HoldStep = {
  seq: number;
  label: string;
  nextLabel?: string | null;
  /** Numer cofanego kroku (wpis feedu Activity o tym `seq` opisuje go po ludzku). */
  nextSeq?: number | null;
  round: number;
  phase: string;
  stepsBack: number;
  cards: { card_id: string; name: string; window: string }[];
};

export type HoldCandidates = { steps: HoldStep[]; limitReason: string | null };

/** Kroki, do których gracz może się cofnąć z kartą (od najnowszego); odświeżane przy otwartym panelu. */
export function useHoldCandidates(playerId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["holdCandidates", playerId],
    enabled: Boolean(playerId) && enabled,
    staleTime: 0,
    refetchInterval: 3000,
    retry: false,
    queryFn: async (): Promise<HoldCandidates> => {
      const response = await fetch(
        `${BOT_ROOT}/hold/candidates?player_id=${encodeURIComponent(playerId ?? "")}`,
      );
      if (!response.ok) throw new Error(`Error ${response.status}`);
      const data = (await response.json()) as Partial<HoldCandidates>;
      return { steps: data.steps ?? [], limitReason: data.limitReason ?? null };
    },
  });
}

/** Pas / zwolnienie okna Sabotage (``held_play``). Błędy (np. za wcześnie) są ignorowane. */
/** Pas / zwolnienie pauzy ochronnej w kluczowym oknie reakcji (RULES.md 54.10). */
export async function postReactionPause(action: "pass" | "release" | "wait", actorId: string): Promise<void> {
  await fetch(`${BOT_ROOT}/reaction-pause/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId }),
  }).catch(() => undefined);
}

/** „Skip all reactions” gracza (RULES.md 54.11): silnik pasuje za niego w każdym oknie reakcji. */
export async function postAutoPass(actorId: string, enabled: boolean): Promise<void> {
  const response = await fetch(`${BOT_ROOT}/reaction-settings/auto-pass`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, enabled }),
  });
  if (!response.ok) throw new Error(`Failed to change auto-pass (${response.status}).`);
}

/** Host ustawia stałą długość okien reakcji w trwającej grze (RULES.md 54.11). */
export async function postReactionWindowSeconds(seconds: number): Promise<void> {
  const response = await fetch(`${BOT_ROOT}/reaction-settings/window`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seconds }),
  });
  if (!response.ok) throw new Error(`Failed to set reaction windows (${response.status}).`);
}

export async function postHeld(action: "pass" | "release" | "wait", actorId: string): Promise<void> {
  await fetch(`${BOT_ROOT}/action-card/held/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId }),
  }).catch(() => undefined);
}

/** Undo gracza (RULES.md 44.7): czy mogę teraz cofnąć swój ostatni krok, a jeśli nie — dlaczego. */
export type PlayerUndoStatus = {
  available: boolean;
  reason: string | null;
  label: string | null;
  undone_seq: number | null;
};

export function usePlayerUndo(playerId: string | null) {
  return useQuery({
    queryKey: ["playerUndo", playerId],
    enabled: Boolean(playerId),
    staleTime: 0,
    refetchInterval: 2500,
    retry: false,
    queryFn: async (): Promise<PlayerUndoStatus> => {
      const response = await fetch(
        `${BOT_ROOT}/undo/mine?player_id=${encodeURIComponent(playerId ?? "")}`,
      );
      if (!response.ok) throw new Error(`Error ${response.status}`);
      return (await response.json()) as PlayerUndoStatus;
    },
  });
}

/** Cofa ostatni krok gracza; zwraca komunikat błędu (422) albo ``null``. */
export async function postPlayerUndo(playerId: string): Promise<string | null> {
  const response = await fetch(`${BOT_ROOT}/undo/mine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_id: playerId }),
  }).catch(() => null);
  if (response === null) return "The server is not responding.";
  if (response.ok) return null;
  const raw = await response.text().catch(() => "");
  return parseErrorDetail(raw, response.status);
}

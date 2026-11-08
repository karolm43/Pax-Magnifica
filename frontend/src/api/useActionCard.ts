import { useQuery } from "@tanstack/react-query";
import { getBotApiUrl } from "@/api/auth";
import { fetchJson } from "@/api/fetchJson";

/*
 * Formularz zagrania karty akcji (RULES.md 53). Backend opisuje, jakich decyzji wymaga karta
 * i jakie są legalne opcje na bieżącym stanie gry — front nie zna kart, tylko renderuje opis.
 */

/** Jedna opcja wyboru: ``id`` jest unikalne w obrębie wejścia, ``value`` trafia do parametrów. */
export type ActionCardOption = { id: string; value: unknown; label: string };

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
    })
  | (InputBase & { kind: "number"; min: number; max: number });

export type ActionCardForm = {
  card_id: string;
  name: string;
  text: string;
  /** False = silnik nie automatyzuje karty: zagranie ją odrzuca, skutek rozstrzyga operator. */
  implemented: boolean;
  inputs: ActionCardInput[];
};

/** Pobiera formularz karty dla gracza (karta musi być w jego ręce, inaczej 422). */
export function useActionCardForm(cardId: string | null, playerId: string | null) {
  return useQuery({
    queryKey: ["actionCardForm", cardId, playerId],
    enabled: Boolean(cardId && playerId),
    // Opcje zależą od bieżącego stanu gry — nie cache'ujemy między otwarciami.
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: () =>
      fetchJson<ActionCardForm>(
        getBotApiUrl(
          `/action-card/${encodeURIComponent(cardId ?? "")}/inputs?player_id=${encodeURIComponent(
            playerId ?? "",
          )}`,
        ),
        "action card form",
      ),
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
    } else {
      const amount = typeof value === "number" ? value : input.min;
      if (amount < input.min || amount > input.max) ready = false;
      params[input.key] = amount;
    }
  }
  return { params, ready };
}

import type { OfferView } from "@/api/useOffers";
import type { FormValue } from "@/api/useActionCard";
import type { ShipEntity } from "./battleAssign";

type Input = OfferView["inputs"][number];
type UnitInput = Extract<Input, { kind: "choice" | "multi" }>;
type ChoiceOption = UnitInput["options"][number];

/**
 * Zaznaczenia jednej decyzji na polu bitwy: pole oferty → (id okrętu → id opcji). Trzymamy
 * KONKRETNY egzemplarz, który gracz kliknął (podświetlenie, odznaczenie ponownym klikiem), a
 * silnik dostaje id opcji.
 */
export type PickState = Record<string, Record<string, string>>;

/** Bieżący stan decyzji „wskaż jednostkę” w tej bitwie. */
export type ShipPickStep = {
  offer: OfferView;
  /** Pole, które teraz zbiera kliknięcia (``null`` = wszystko wybrane, czeka na Confirm). */
  input: UnitInput | null;
  /** Gracze, których jednostki występują w polach tej decyzji (obie strony - Viscount Unlenn). */
  owners: string[];
  state: PickState;
};

/** Gracz-właściciel opcji (``meta.player``) albo ``null``. */
function playerOf(option: ChoiceOption): string | null {
  const player = option.meta?.player;
  return typeof player === "string" ? player : null;
}

/**
 * Pole wskazuje jednostki tej bitwy: wybór (jeden/wiele), KAŻDA opcja to jednostka
 * (``meta.unit``) jednej ze stron walki. Strony mogą się mieszać (Viscount Unlenn: dowolny
 * statek w systemie, Evelyn DeLouis: dowolna siła naziemna).
 */
function isUnitInput(input: Input, playerIds: string[]): input is UnitInput {
  if (input.kind !== "choice" && input.kind !== "multi") return false;
  if (input.options.length === 0) return false;
  return input.options.every(
    (o) => typeof o.meta?.unit === "string" && playerIds.includes(playerOf(o) ?? ""),
  );
}

/** Czy opcja opisuje ten egzemplarz: typ i — gdy silnik go podał — stan uszkodzenia. */
export function optionMatchesShip(option: ChoiceOption, ship: ShipEntity): boolean {
  if (String(option.meta?.unit) !== ship.baseType) return false;
  const damaged = option.meta?.damaged;
  return typeof damaged !== "boolean" || damaged === ship.damaged;
}

const minOf = (input: UnitInput) => (input.kind === "multi" ? input.min : 1);
const maxOf = (input: UnitInput) => (input.kind === "multi" ? input.max : 1);
const picksIn = (state: PickState, input: UnitInput) => state[input.key] ?? {};

/** Pole ma komplet minimum (wybór pojedynczy: 1 okręt; wielokrotny: ``min``). */
export function satisfied(input: UnitInput, state: PickState): boolean {
  return Object.keys(picksIn(state, input)).length >= minOf(input);
}

/**
 * Pole zbierające teraz kliknięcia: pierwsze bez minimum, a gdy wszystkie mają minimum - ostatnie
 * pole wielokrotne, do którego można jeszcze dołożyć; inaczej ``null`` (gotowe do Confirm).
 */
export function currentInput(offer: OfferView, state: PickState): UnitInput | null {
  const inputs = offer.inputs as UnitInput[];
  const open = inputs.find((input) => !satisfied(input, state));
  if (open) return open;
  const last = inputs[inputs.length - 1];
  return last && last.kind === "multi" && Object.keys(picksIn(state, last)).length < maxOf(last)
    ? last
    : null;
}

/** Wszystkie pola mają minimum - decyzję można zatwierdzić. */
export function complete(offer: OfferView, state: PickState): boolean {
  return (offer.inputs as UnitInput[]).every((input) => satisfied(input, state));
}

/** Wartości formularza dla silnika (pojedynczy: id opcji, wielokrotny: lista id). */
export function pickValues(offer: OfferView, state: PickState): Record<string, FormValue> {
  const values: Record<string, FormValue> = {};
  for (const input of offer.inputs as UnitInput[]) {
    const ids = Object.values(picksIn(state, input));
    if (input.kind === "multi") values[input.key] = ids;
    else if (ids[0]) values[input.key] = ids[0];
  }
  return values;
}

/** Pole i opcja, które zajmuje ten okręt (do podświetlenia i odznaczenia), albo ``null``. */
export function pickedAs(
  offer: OfferView,
  state: PickState,
  ship: ShipEntity,
): { input: string; option: string } | null {
  for (const input of offer.inputs) {
    const option = state[input.key]?.[ship.id];
    if (option) return { input: input.key, option };
  }
  return null;
}

/** Wolna opcja bieżącego pola pasująca do okrętu strony ``owner`` (``null`` = nie do kliknięcia). */
function freeOption(
  offer: OfferView,
  state: PickState,
  ship: ShipEntity,
  owner: string,
): { input: UnitInput; option: ChoiceOption } | null {
  // Wszystko wybrane: ostatnie pole pojedyncze przyjmuje ZAMIANĘ (klik w inny okręt).
  const last = offer.inputs[offer.inputs.length - 1] as UnitInput | undefined;
  const input = currentInput(offer, state) ?? (last?.kind === "choice" ? last : null);
  if (!input) return null;
  const used = new Set(Object.values(picksIn(state, input)));
  const option = input.options.find(
    (o) => playerOf(o) === owner && optionMatchesShip(o, ship) && (input.kind === "choice" || !used.has(o.id)),
  );
  return option ? { input, option } : null;
}

/** Okręt można kliknąć: jest zaznaczony (odznaczenie) albo pasuje do bieżącego pola. */
export function canPick(offer: OfferView, state: PickState, ship: ShipEntity, owner: string): boolean {
  return pickedAs(offer, state, ship) !== null || freeOption(offer, state, ship, owner) !== null;
}

/**
 * Klik w okręt: zaznaczony → odznacz (także z wcześniejszego pola - „wybór od nowa” bez
 * osobnego przycisku); inaczej zaznacz w bieżącym polu (pojedynczy wybór zastępuje poprzedni).
 */
export function togglePick(
  offer: OfferView,
  state: PickState,
  ship: ShipEntity,
  owner: string,
): PickState {
  const picked = pickedAs(offer, state, ship);
  if (picked) {
    const rest = { ...state[picked.input] };
    delete rest[ship.id];
    return { ...state, [picked.input]: rest };
  }
  const free = freeOption(offer, state, ship, owner);
  if (!free) return state;
  const { input, option } = free;
  const now = input.kind === "choice" ? {} : { ...picksIn(state, input) };
  if (Object.keys(now).length >= maxOf(input)) return state;
  return { ...state, [input.key]: { ...now, [ship.id]: option.id } };
}

/**
 * Decyzje „wskaż jednostkę w tej bitwie” (ofiara Assault Cannon, Duranium Armor, Devotion,
 * Viscount Unlenn, Evelyn DeLouis, Ambush…): KAŻDE pole oferty wskazuje jednostki stron walki.
 * Gracz klika jednostki na polu bitwy (ponowny klik odznacza) i zatwierdza decyzję. Obie
 * strony mogą decydować NARAZ; jeden gracz ma jedną decyzję naraz (następna po rozstrzygnięciu).
 * Mapa: właściciel klikalnych jednostek → decyzja (decyzja z jednostkami obu stron jest pod
 * oboma; pierwsza wygrywa).
 */
export function shipPickSteps(
  offers: OfferView[] | undefined,
  playerIds: string[],
  states: Record<string, PickState> = {},
): Map<string, ShipPickStep> {
  const found = new Map<string, ShipPickStep>();
  const busy = new Set<string>();
  for (const offer of offers ?? []) {
    if (offer.inputs.length === 0 || !offer.inputs.every((i) => isUnitInput(i, playerIds))) continue;
    if (busy.has(offer.player_id)) continue;
    busy.add(offer.player_id);
    const state = states[offer.id] ?? {};
    const owners = [
      ...new Set(
        offer.inputs.flatMap((i) => i.options.map(playerOf)).filter(
          (p): p is string => p !== null,
        ),
      ),
    ];
    const step = { offer, input: currentInput(offer, state), owners, state };
    for (const owner of owners) if (!found.has(owner)) found.set(owner, step);
  }
  return found;
}

/** Zgodność wstecz: mapa właściciel jednostek → oferta. */
export function shipPickOffers(
  offers: OfferView[] | undefined,
  playerIds: string[],
): Map<string, OfferView> {
  const steps = shipPickSteps(offers, playerIds);
  return new Map([...steps].map(([owner, step]) => [owner, step.offer]));
}

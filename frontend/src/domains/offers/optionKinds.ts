import type { ActionCardOption } from "@/api/useActionCard";

/*
 * Rozpoznanie, CZEGO dotyczy wybór (silnik opisuje wejścia ogólnie: choice/multi + opcje).
 * Jedno miejsce dla wszystkich formularzy (karty akcji, relikty, technologie, liderzy, notki,
 * oferty): planeta/system => klik NA MAPIE, technologia => kafelki technologii, gracz => ikony
 * frakcji. Bez tego każda karta pokazywała tekstową listę.
 */

export type OptionKind = "technology" | "player" | "planet" | "system";

export type OptionLookups = {
  isTech: (id: string) => boolean;
  isPlayer: (id: string) => boolean;
  isPlanet: (id: string) => boolean;
  isSystem: (position: string) => boolean;
};

export type Classified = {
  kind: OptionKind;
  /** id opcji → cel (id technologii / gracza / planety / pozycja systemu). */
  targets: Map<string, string>;
  /**
   * Kilka opcji wskazuje TEN SAM cel (np. „PDS / mech na planecie X”, statki w systemie): klik
   * w cel na mapie otwiera wybór tego, co na nim (``GroupedMapField``), zamiast listy wszystkich.
   */
  grouped?: boolean;
};

function str(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

/** Części wartości złożonej silnika („pozycja|planeta”, „planeta>cel”). */
function parts(value: string): string[] {
  const split = value.split(/[|>]/).filter(Boolean);
  return split.length > 1 ? split : [value];
}

/**
 * Pola opcji, w których silnik podaje miejsce: ``meta`` oraz wartość-słownik (Mercenary
 * Contract ``{position, planet}``, Lucky Shot ``{position, owner, base_type}``).
 */
function fieldsOf(option: ActionCardOption): Record<string, unknown> {
  const value = option.value;
  const fromValue =
    value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
  return { ...fromValue, ...(option.meta ?? {}) };
}

/** Id komponentu z ``meta.ref`` silnika, gdy jest danego rodzaju (``planet``, ``tech``). */
export function refOf(option: ActionCardOption, kind: string): string | null {
  const ref = option.meta?.ref;
  if (!ref || typeof ref !== "object") return null;
  const r = ref as Record<string, unknown>;
  return r.kind === kind ? str(r.id) : null;
}

/** Odnośniki, które same są celem wyboru (planeta na mapie, technologia w drzewie). */
const TARGET_REFS = new Set(["planet", "tech"]);

export function planetOf(option: ActionCardOption, look: OptionLookups): string | null {
  const meta = fieldsOf(option);
  const fromRef = refOf(option, "planet");
  if (fromRef && look.isPlanet(fromRef)) return fromRef;
  const fromMeta = str(meta.planet);
  if (fromMeta && look.isPlanet(fromMeta)) return fromMeta;
  const value = str(option.value);
  if (!value) return null;
  return parts(value).find((p) => look.isPlanet(p)) ?? null;
}

export function systemOf(option: ActionCardOption, look: OptionLookups): string | null {
  const meta = fieldsOf(option);
  for (const key of ["position", "system"]) {
    const v = str(meta[key]);
    if (v && look.isSystem(v)) return v;
  }
  const value = str(option.value);
  if (!value) return null;
  return parts(value).find((p) => look.isSystem(p)) ?? null;
}

/** Wszystkie opcje muszą wskazywać RÓŻNE cele tego samego rodzaju - inaczej zwykłe kafelki. */
function all(
  options: ActionCardOption[],
  pick: (option: ActionCardOption) => string | null,
): Map<string, string> | null {
  const targets = new Map<string, string>();
  const seen = new Set<string>();
  for (const option of options) {
    const target = pick(option);
    if (!target || seen.has(target)) return null;
    seen.add(target);
    targets.set(option.id, target);
  }
  return targets;
}

/** Opcja bez celu na mapie, ale też bez innego obiektu gry („Do not place”, „Decline”). */
function isLoose(option: ActionCardOption, look: OptionLookups): boolean {
  const v = str(option.value);
  if (v === null) return option.value === null || typeof option.value !== "object";
  return !look.isTech(v) && !look.isPlayer(v) && !look.isPlanet(v) && !look.isSystem(v);
}

/** Najwyżej tyle opcji bez celu (odmowa, „nic”) obok celów na mapie. */
const MAX_LOOSE = 2;

/**
 * Cele planet / systemów, gdy KILKA opcji może wskazywać to samo miejsce (``grouped``), a do
 * ``MAX_LOOSE`` opcji nie ma celu (zwykłe kafelki obok mapy). Jeden cel z wieloma opcjami to
 * nie wybór miejsca - wtedy ``null`` (kafelki / liczniki jednostek).
 */
function located(
  options: ActionCardOption[],
  pick: (option: ActionCardOption) => string | null,
  look: OptionLookups,
): { targets: Map<string, string>; grouped: boolean } | null {
  const targets = new Map<string, string>();
  const perTarget = new Map<string, number>();
  let loose = 0;
  for (const option of options) {
    const target = pick(option);
    if (!target) {
      // Space area of a system next to planets (Yin Spinner, a board source „pozycja|space”):
      // still a map target - ``GroupedMapField.targetsOf`` maps it to the hex, never a tile.
      if (systemOf(option, look)) continue;
      if (!isLoose(option, look)) return null;
      loose += 1;
      continue;
    }
    targets.set(option.id, target);
    perTarget.set(target, (perTarget.get(target) ?? 0) + 1);
  }
  if (targets.size === 0 || loose > MAX_LOOSE) return null;
  const grouped = [...perTarget.values()].some((n) => n > 1);
  if (grouped && perTarget.size < 2) return null;
  return { targets, grouped };
}

/** Rodzaj wyboru albo ``null`` (zwykłe kafelki: jednostki, kości, karty, tryby…). */
export function classifyOptions(
  options: ActionCardOption[],
  look: OptionLookups,
): Classified | null {
  if (options.length === 0) return null;
  // Kości i opcje z odnośnikiem do innego komponentu (``meta.ref`` karty / reliktu - opis i
  // pełna karta, patrz ``describeOption``) mają własny wygląd. Odnośnik do PLANETY lub
  // TECHNOLOGII to nadal wybór planety (mapa) / technologii (drzewo) - decyzja użytkownika:
  // nigdy lista planet ani technologii. Jednostka NA PLANECIE / W SYSTEMIE to wybór miejsca.
  const otherRef = (o: ActionCardOption) => {
    const ref = o.meta?.ref as Record<string, unknown> | undefined;
    return ref !== undefined && !TARGET_REFS.has(String(ref?.kind));
  };
  if (options.some((o) => o.meta && ("die" in o.meta || otherRef(o)))) return null;
  const units = options.some((o) => o.meta && "unit" in o.meta);
  const plain = (test: (id: string) => boolean, refKind?: string) => (o: ActionCardOption) => {
    const fromRef = refKind ? refOf(o, refKind) : null;
    if (fromRef && test(fromRef)) return fromRef;
    const v = str(o.value);
    return v && test(v) ? v : null;
  };
  if (!units) {
    const exact: [OptionKind, (o: ActionCardOption) => string | null][] = [
      ["technology", plain(look.isTech, "tech")],
      ["player", plain(look.isPlayer)],
    ];
    for (const [kind, pick] of exact) {
      const targets = all(options, pick);
      if (targets) return { kind, targets };
    }
  }
  const places: [OptionKind, (o: ActionCardOption) => string | null][] = [
    ["planet", (o) => planetOf(o, look)],
    ["system", (o) => systemOf(o, look)],
  ];
  for (const [kind, pick] of places) {
    const found = located(options, pick, look);
    if (found) return { kind, targets: found.targets, grouped: found.grouped || undefined };
  }
  if (units) return null;
  // Gracze z dodatkową opcją bez celu (Carth of Golden Sands: „Gain 2 commodities” obok
  // „Replenish <gracz>…”): gracze dalej z ikoną frakcji i kolorem, reszta zwykłym kafelkiem.
  const players = some(options, plain(look.isPlayer));
  if (players) return { kind: "player", targets: players };
  return null;
}

/** Jak ``all``, ale część opcji może nie mieć celu (zostają zwykłymi kafelkami); min. 1 cel. */
function some(
  options: ActionCardOption[],
  pick: (option: ActionCardOption) => string | null,
): Map<string, string> | null {
  const targets = new Map<string, string>();
  const seen = new Set<string>();
  for (const option of options) {
    const target = pick(option);
    if (!target) continue;
    if (seen.has(target)) return null;
    seen.add(target);
    targets.set(option.id, target);
  }
  return targets.size > 0 ? targets : null;
}

/** Wejście silnika (pole formularza) - minimalny kształt potrzebny do rozpoznania slotów. */
type SlotInput = { key: string; kind: string; options?: ActionCardOption[] };

/**
 * Jednakowe SLOTY: kolejne pola ``choice`` z identycznymi opcjami (bohater Yin: „Infantry 1/2/3
 * commits to”, każde z „No infantry” i tymi samymi planetami). Dla gracza to jedna decyzja
 * „rozdziel do N sztuk” - formularz pokazuje je jako jedno pole. Mapa: klucz pierwszego pola →
 * klucze wszystkich pól grupy (w kolejności silnika).
 */
export function slotGroups(inputs: SlotInput[]): Map<string, string[]> {
  const groups = new Map<string, string[]>();
  const sig = (input: SlotInput) =>
    input.kind === "choice" && input.options && input.options.length > 1
      ? input.options.map((o) => o.id).join("\u0001")
      : null;
  let run: SlotInput[] = [];
  const flush = () => {
    if (run.length > 1) groups.set(run[0].key, run.map((i) => i.key));
    run = [];
  };
  for (const input of inputs) {
    const s = sig(input);
    if (s !== null && run.length > 0 && sig(run[0]) === s) {
      run.push(input);
      continue;
    }
    flush();
    if (s !== null) run = [input];
  }
  flush();
  return groups;
}

/** Stos jednakowych opcji: ta sama jednostka tego samego gracza w tym samym miejscu. */
export type OptionStack = { key: string; options: ActionCardOption[] };

/**
 * Opcje pogrupowane w stosy (kolejność jak u silnika). Silnik daje JEDNĄ opcję na sztukę
 * (Xxekir Grom: „Mech on X”, „Mech on X #2”; agendy: „carrier #1”, „carrier #2”) - w multi to
 * jeden licznik −/+ zamiast rzędu identycznych kafelków. Bez ``meta.unit`` każda opcja osobno.
 */
export function stacksOf(options: ActionCardOption[]): OptionStack[] {
  const stacks: OptionStack[] = [];
  const byKey = new Map<string, OptionStack>();
  for (const option of options) {
    const meta = option.meta ?? {};
    const key =
      typeof meta.unit === "string"
        ? ["unit", meta.unit, meta.player, meta.planet, meta.position, meta.zone]
            .map((part) => (typeof part === "string" ? part : ""))
            .join("|")
        : `option|${option.id}`;
    const found = byKey.get(key);
    if (found) {
      found.options.push(option);
    } else {
      const stack = { key, options: [option] };
      byKey.set(key, stack);
      stacks.push(stack);
    }
  }
  return stacks;
}

/** Wybór multi po ustawieniu licznika stosu na ``count`` (w limicie ``max`` całego pola). */
export function withStackCount(
  picked: string[],
  stack: ActionCardOption[],
  count: number,
  max: number,
): string[] {
  const ids = stack.map((o) => o.id);
  const others = picked.filter((id) => !ids.includes(id));
  const room = Math.max(0, max - others.length);
  return [...others, ...ids.slice(0, Math.max(0, Math.min(count, room)))];
}

/** Ile sztuk stosu jest wybranych i ile najwyżej można (rozmiar stosu, wolne miejsce pola). */
export function stackRange(
  picked: string[],
  stack: ActionCardOption[],
  max: number,
): { value: number; max: number } {
  const value = stack.filter((o) => picked.includes(o.id)).length;
  return { value, max: Math.min(stack.length, value + Math.max(0, max - picked.length)) };
}

/** Etykiety silnika oznaczające „nie rób tego” („Do not place”, „Decline - …”, „- none -”). */
const DECLINE_LABEL = /^\s*(?:(?:do not|don['’]t|decline|skip|none available)\b|-\s*none\s*-)/i;

/**
 * Opcja odmowy w polu wyboru (punkt 6 planu okien decyzji): pokazywana osobno, za „or”, jako
 * wyraźny kafelek „⊘”, a nie jako kolejny cel obok planet/opcji. Silnik oznacza je id/value
 * ``none`` albo etykietą „Do not …” / „Decline …”.
 */
export function isDeclineOption(option: ActionCardOption): boolean {
  return option.id === "none" || option.value === "none" || DECLINE_LABEL.test(option.label);
}

/** Opcje zwykłe i opcje odmowy (kolejność w obu grupach bez zmian). */
export function splitDeclines(options: ActionCardOption[]): {
  regular: ActionCardOption[];
  declines: ActionCardOption[];
} {
  const regular: ActionCardOption[] = [];
  const declines: ActionCardOption[] = [];
  for (const option of options) (isDeclineOption(option) ? declines : regular).push(option);
  return { regular, declines };
}

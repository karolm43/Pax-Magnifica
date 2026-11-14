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
};

function str(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

/** Części wartości złożonej silnika („pozycja|planeta”, „planeta>cel”). */
function parts(value: string): string[] {
  const split = value.split(/[|>]/).filter(Boolean);
  return split.length > 1 ? split : [value];
}

function planetOf(option: ActionCardOption, look: OptionLookups): string | null {
  const meta = option.meta ?? {};
  const fromMeta = str(meta.planet);
  if (fromMeta && look.isPlanet(fromMeta)) return fromMeta;
  const value = str(option.value);
  if (!value) return null;
  return parts(value).find((p) => look.isPlanet(p)) ?? null;
}

function systemOf(option: ActionCardOption, look: OptionLookups): string | null {
  const meta = option.meta ?? {};
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

/** Rodzaj wyboru albo ``null`` (zwykłe kafelki: jednostki, kości, karty, tryby…). */
export function classifyOptions(
  options: ActionCardOption[],
  look: OptionLookups,
): Classified | null {
  if (options.length === 0) return null;
  // Opcje graficzne (jednostka, kość) mają już własny wygląd.
  if (options.some((o) => o.meta && ("unit" in o.meta || "die" in o.meta))) return null;
  const plain = (test: (id: string) => boolean) => (o: ActionCardOption) => {
    const v = str(o.value);
    return v && test(v) ? v : null;
  };
  const order: [OptionKind, (o: ActionCardOption) => string | null][] = [
    ["technology", plain(look.isTech)],
    ["player", plain(look.isPlayer)],
    ["planet", (o) => planetOf(o, look)],
    ["system", (o) => systemOf(o, look)],
  ];
  for (const [kind, pick] of order) {
    const targets = all(options, pick);
    if (targets) return { kind, targets };
  }
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

/**
 * Kluczowe momenty gry (RULES.md 64) — CZYSTE funkcje: wpis feedu Activity -> lista momentów
 * do animacji oraz zmiana fazy/rundy -> pasek przejścia. Rysowanie: `KeyMomentStage`
 * (momenty) i `PhaseSweep` (przejścia faz / „Your turn”).
 */
import type { ActivityEntry } from "@/api/useBoardEditor";
import { isCreussWormholeToken } from "@/entities/lookup/wormholeTokens";

export type KeyMoment =
  /** Bohater frakcji użyty (purge po rozpatrzeniu — R_leaders). */
  | {
      kind: "hero";
      seq: number;
      player: string;
      leaderId: string;
      replaced?: ReplacedTile[];
      /** Planety, do których bohater dołączył swoją kartę (Ul the Progenitor -> Elysium). */
      planets?: string[];
      /** Gdzie zadziałał (fakty `area`): system, czyje zmiany, rodzaj zmiany. */
      areas?: HeroArea[];
    }
  /** The Fracture weszła do gry (`player` = kto ją wprowadził). */
  | { kind: "fracture"; seq: number; player: string | null }
  /** Przełom frakcji zdobyty. */
  | { kind: "breakthrough"; seq: number; player: string }
  /** Żeton Custodians zdjęty z Mecatol Rex. */
  | { kind: "custodians"; seq: number; player: string | null }
  /**
   * Stellar Converter: the player's BOMBARDMENT ships fire at a planet in an adjacent system and
   * destroy it (fact `planet_destroyed` in the entry that purged the relic).
   */
  | { kind: "converter"; seq: number; player: string | null; planet: string; position: string }
  /**
   * A Creuss wormhole token opened in a system (Wormhole Generator, Creuss IFF, Icarus Drive —
   * RULES.md 62.19), or a unit's wormhole moved with it (Hil Colish's delta, `token` =
   * `whdelta`); `from` = the system it left when it was moved.
   */
  | {
      kind: "wormhole";
      seq: number;
      player: string | null;
      token: string;
      position: string;
      from: string | null;
    }
  /**
   * Empyrean Void Tether token placed / moved onto a border (RULES.md 62.20): `a`-`b` = the two
   * systems it separates; `from` = the border it left when moved.
   */
  | {
      kind: "tether";
      seq: number;
      player: string | null;
      a: string;
      b: string;
      from: [string, string] | null;
    };

/** Relic whose purge + `planet_destroyed` fact is the Stellar Converter moment. */
export const STELLAR_CONVERTER = "stellarconverter";

/** Kafel wymieniony w tym samym wpisie (Nova Seed): mapa pokazuje stary do chwili wybuchu. */
export type ReplacedTile = { position: string; from: string };

/** Miejsce działania bohatera: `self` = jednostki/żetony samego bohatera, inaczej rywala. */
export type HeroArea = {
  position: string;
  self: boolean;
  /** `frontier` / `explore`: frontier token placed / explored (Multiverse Shift, RULES.md 62.20).
   * `time_warp` / `time_warp_token`: the Nomad flagship's system / a system with a Nomad command
   * token under Time Warp (RULES.md 62.21). `kyver`: a rival's home system under Kyver's Guild of
   * Spies (RULES.md 62.22). `benediction_origin` / `benediction`: the system whose space area
   * Benediction moves / the system where its space combat is fought (RULES.md 62.23).
   * `nekro_devour`: the system of the planet Devour World consumes (RULES.md 62.24). */
  kind:
    | "gain"
    | "loss"
    | "token_removed"
    | "frontier"
    | "explore"
    | "time_warp"
    | "time_warp_token"
    | "kyver"
    | "benediction_origin"
    | "benediction"
    | "nekro_devour";
};

/** Rozpoznanie typu lidera (wstrzykiwane — w aplikacji `getLeaderById`). */
export type IsHero = (leaderId: string) => boolean;

/** Momenty jednego NOWEGO wpisu feedu (kolejność = kolejność animacji). */
export function momentsForEntry(entry: ActivityEntry, isHero: IsHero): KeyMoment[] {
  const a = entry.activity;
  const seq = entry.seq;
  // Korekty God-Mode to edycja stanu, nie zagranie — wyjątek: wejście Fracture (RULES.md 64.2).
  const godmode = a.kind === "godmode";
  const out: KeyMoment[] = [];
  for (const f of a.facts) {
    if (f.type === "fracture_entered") {
      out.push({ kind: "fracture", seq, player: f.player_id ?? a.actor_id });
      continue;
    }
    if (godmode) continue;
    // Bohater: purge po użyciu (R_leaders) albo efekt trwający `leaders:<bohater>` (np. Letnev
    // „place this card near the game board”) — jeden moment na bohatera we wpisie.
    const heroId =
      f.type === "leader" && f.detail === "purged"
        ? f.value
        : f.type === "effect" && f.value?.startsWith("leaders:")
          ? f.value.slice("leaders:".length)
          : null;
    if (heroId && f.player_id && isHero(heroId)) {
      if (!out.some((m) => m.kind === "hero" && m.leaderId === heroId)) {
        out.push({ kind: "hero", seq, player: f.player_id, leaderId: heroId });
      }
    } else if (f.type === "attached" && f.value && isHero(f.value) && a.actor_id) {
      // Bohater dołączony do planety zamiast purge (Geoform: karta zostaje przy Elysium).
      const planets = f.detail ? [f.detail] : [];
      const known = out.find((m) => m.kind === "hero" && m.leaderId === f.value);
      if (known?.kind === "hero") known.planets = [...(known.planets ?? []), ...planets];
      else out.push({ kind: "hero", seq, player: f.player_id ?? a.actor_id, leaderId: f.value, planets });
    } else if (f.type === "breakthrough_unlocked" && f.player_id) {
      out.push({ kind: "breakthrough", seq, player: f.player_id });
    } else if (f.type === "custodians_removed") {
      // Kto zdjął: gracz, który w tym samym wpisie zyskał punkt (żeton daje 1 VP), inaczej sprawca.
      const scorer = a.facts.find((x) => x.type === "vp" && (x.delta ?? 0) > 0)?.player_id;
      out.push({ kind: "custodians", seq, player: scorer ?? a.actor_id });
    }
  }
  // Wymiana kafla (fakt `tile_replaced`, detail "<stary>><nowy>") należy do bohatera z wpisu.
  const replaced = a.facts
    .filter((f) => f.type === "tile_replaced" && f.value && f.detail?.includes(">"))
    .map((f) => ({ position: f.value ?? "", from: (f.detail ?? "").split(">")[0] }));
  const hero = out.find((m) => m.kind === "hero");
  if (hero?.kind === "hero" && replaced.length > 0) hero.replaced = replaced;
  // Miejsca działania bohatera (fakty `area` — tylko we wpisie z użyciem bohatera).
  const areas = a.facts
    .filter((f) => f.type === "area" && f.value && AREA_KINDS.has(f.detail ?? ""))
    .map((f) => ({
      position: f.value ?? "",
      self: f.player_id === (hero?.kind === "hero" ? hero.player : null),
      kind: f.detail as HeroArea["kind"],
    }));
  if (hero?.kind === "hero" && areas.length > 0) hero.areas = areas;
  // The exact planet a hero acted on (fact `hero_planet` - Devour World, RULES.md 62.24).
  const heroPlanets = a.facts.filter((f) => f.type === "hero_planet" && f.value).map((f) => f.value ?? "");
  if (hero?.kind === "hero" && heroPlanets.length > 0) {
    hero.planets = [...(hero.planets ?? []), ...heroPlanets];
  }
  // Stellar Converter: zniszczona planeta we wpisie, w którym relikt zszedł z gry (The Silver
  // Flame też niszczy planety — dom gracza — ale to nie ten moment).
  const converterUsed =
    !godmode &&
    a.facts.some((f) => f.type === "relic" && f.value === STELLAR_CONVERTER && f.detail === "lost");
  if (converterUsed) {
    for (const f of a.facts) {
      if (f.type === "planet_destroyed" && f.value) {
        out.push({ kind: "converter", seq, player: a.actor_id, planet: f.value, position: f.detail ?? "" });
      }
    }
  }
  // Creuss wormhole token placed / moved — but not when a hero swap carried it with its tile
  // (the tokens "move" there only because the systems traded places).
  const swapped = a.facts.some((f) => f.type === "tile_replaced");
  if (!godmode && !swapped) {
    for (const f of a.facts) {
      if (f.type !== "faction_token" || !isCreussWormholeToken(f.value) || !f.position) continue;
      const left = a.facts.find(
        (x) => x.type === "faction_token_removed" && x.value === f.value && x.position,
      );
      out.push({
        kind: "wormhole",
        seq,
        player: a.actor_id,
        token: f.value ?? "",
        position: f.position,
        from: left?.position ?? null,
      });
    }
  }
  // A wormhole carried by a unit moved with it (Hil Colish's delta, RULES.md 62.19): the same
  // portal - a vortex opens where it arrived and collapses where it left. Token id of that
  // wormhole type in the token data (`wh<type>`) = its image and its recipe.
  if (!godmode && !swapped) {
    for (const f of a.facts) {
      if (f.type !== "unit_wormhole" || !f.value || !f.position) continue;
      const left = a.facts.find(
        (x) => x.type === "unit_wormhole_removed" && x.value === f.value && x.player_id === f.player_id,
      );
      out.push({
        kind: "wormhole",
        seq,
        player: f.player_id ?? a.actor_id,
        token: unitWormholeToken(f.value),
        position: f.position,
        from: left?.position ?? null,
      });
    }
  }
  // Empyrean Void Tether (RULES.md 62.20): a faction token kept in a BORDER zone
  // (`border:<other system>` of the lower position) - a border effect, not a system one.
  if (!godmode) {
    for (const f of a.facts) {
      const pair = tetherBorder(f);
      if (f.type !== "faction_token" || !pair) continue;
      const left = a.facts.find((x) => x.type === "faction_token_removed" && tetherBorder(x));
      out.push({
        kind: "tether",
        seq,
        player: f.player_id ?? a.actor_id,
        a: pair[0],
        b: pair[1],
        from: left ? tetherBorder(left) : null,
      });
    }
  }
  // Fracture otwiera scenę: jeśli w jednym wpisie jest kilka momentów (przełom -> rzut 1/10),
  // najpierw przełom, potem Fracture.
  return out.sort((x, y) => order(x) - order(y));
}

const AREA_KINDS = new Set([
  "gain",
  "loss",
  "token_removed",
  "frontier",
  "explore",
  "time_warp",
  "time_warp_token",
  "kyver",
  "benediction_origin",
  "benediction",
  "nekro_devour",
]);

/** Void Tether token id (`assets/data/tokens`, backend `faction_tokens.VOID_TETHER`). */
export const VOID_TETHER = "voidtether";
const BORDER_PREFIX = "border:";

/** The two systems of a Void Tether fact (`position` + `detail` "border:<other>"), else null. */
export function tetherBorder(f: {
  value?: string | null;
  detail?: string | null;
  position?: string | null;
}): [string, string] | null {
  if (f.value !== VOID_TETHER || !f.position || !f.detail?.startsWith(BORDER_PREFIX)) return null;
  return [f.position, f.detail.slice(BORDER_PREFIX.length)];
}

/** Token id of a unit-carried wormhole type (`delta` -> `whdelta`, `assets/data/tokens`). */
export function unitWormholeToken(type: string): string {
  return `wh${type.toLowerCase()}`;
}

function order(m: KeyMoment): number {
  return m.kind === "fracture" ? 1 : 0;
}

/** Główne fazy z paskiem przejścia (podfazy `status.*` liczą się jako swoja faza). */
export const PHASE_LABEL: Record<string, string> = {
  strategy: "Strategy Phase",
  action: "Action Phase",
  status: "Status Phase",
  agenda: "Agenda Phase",
};

export type SweepVariant = "round" | "strategy" | "action" | "status" | "agenda" | "turn";

export type Sweep = {
  /** Unikalny klucz (restart animacji). */
  id: string;
  variant: SweepVariant;
  title: string;
  subtitle: string | null;
};

/** Normalizacja fazy do głównej: `"status.scoring"` -> `"status"`. */
export function mainPhaseOf(phase: string | null | undefined): string {
  return (phase ?? "").split(".")[0];
}

/**
 * Pasek przejścia przy zmianie głównej fazy (`null` = brak przejścia / faza bez paska).
 * Wejście w fazę strategii albo wzrost numeru rundy = NOWA RUNDA (mocniejszy akcent).
 */
export function phaseSweep(
  prev: { phase: string; round: number | undefined },
  next: { phase: string; round: number | undefined },
): Sweep | null {
  if (prev.phase === next.phase) return null;
  const label = PHASE_LABEL[next.phase];
  if (!label) return null;
  const round = next.round;
  const newRound =
    next.phase === "strategy" ||
    (round !== undefined && prev.round !== undefined && round > prev.round);
  if (newRound && round !== undefined) {
    return { id: `round-${round}-${next.phase}`, variant: "round", title: `Round ${round}`, subtitle: label };
  }
  return {
    id: `${next.phase}-${round ?? "?"}`,
    variant: next.phase as SweepVariant,
    title: label,
    subtitle: round !== undefined ? `Round ${round}` : null,
  };
}

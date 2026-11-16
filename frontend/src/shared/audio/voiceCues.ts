/**
 * Kiedy co gra — CZYSTE funkcje: wpis feedu Activity -> lista „sygnałów” dźwiękowych.
 *
 * - `combat.start` -> kwestie bitwy (rozstrzyga `battleLines`, bo potrzebuje sił stron i domów):
 *   walka w domu obrońcy = atakujący `homeinvasion` + obrońca `homedefense`; wyraźna przewaga
 *   atakującego = `offensesuperior` (przy miażdżącej obrońca dorzuca `defenseoutnumbered`);
 *   reszta = okrzyk `battle` atakującego (czasem z odpowiedzią obrońcy).
 * - zdolności frakcji z własnymi nagraniami (Pillage, Orbital Drop, Reclamation…) -> ich kwestia,
 *   rozpoznawana po identyfikatorze komponentu we wpisie (działa, gdy mechanika trafi do silnika);
 * - bohater frakcji (leader „hero”) -> `special`;
 * - pas -> czasem żart frakcji; propozycja transakcji do mnie / Rada Galaktyczna -> transmisja;
 * - moja tura -> dźwięk UI „turn”, zmiana fazy -> „transition”.
 */
import type { ActivityEntry } from "@/api/useBoardEditor";
import type { UiSound } from "./uiSounds";

export type Cue =
  | { kind: "voice"; player: string; category: string; fallback?: string }
  | { kind: "transmission" }
  | { kind: "ui"; name: UiSound }
  | { kind: "battle"; attacker: string; defender: string | null; position: string | null };

export type CueContext = {
  /** Gracz tej przeglądarki (null w trybie lokalnym). */
  me: string | null;
  network: boolean;
  isBot: (playerId: string) => boolean;
  /** Frakcja gracza (do wyboru kwestii specjalnych). */
  factionOf: (playerId: string) => string | null;
  random: () => number;
};

/** Szansa na żart frakcji przy pasie (żeby nie spowszedniał). */
export const JOKE_ON_PASS_CHANCE = 0.3;

/**
 * Kwestie specjalne frakcji: kategoria pliku -> wzorzec szukany w identyfikatorach wpisu
 * (komponent, zdolność, efekt, lider, notka). Nazwy kategorii = nazwy plików w `assets/voices`.
 */
export const FACTION_SPECIALS: Record<string, { category: string; match: RegExp }[]> = {
  mentak: [{ category: "pillage", match: /pillage/i }],
  sol: [{ category: "orbitaldrop", match: /orbital.?drop/i }],
  winnu: [{ category: "reclamation", match: /reclamation/i }],
  // Yin `bomb` = Van Hauge (flagowiec ginie i niszczy statki w systemie) — patrz `flagshipCues`.
  yin: [{ category: "yinspin", match: /yin.?spinner/i }],
  naaz: [{ category: "specialforgery", match: /fabrication/i }],
  nomad: [
    { category: "artuno", match: /artuno/i },
    { category: "cavalry", match: /cavalry/i },
  ],
};

/** Identyfikatory komponentów, których dotyczy wpis (dla dopasowania kwestii specjalnych). */
function componentIds(entry: ActivityEntry, player: string): string[] {
  const a = entry.activity;
  const ids: string[] = [];
  if (a.actor_id === player) {
    if (a.subject) ids.push(a.subject);
    if (a.detail) ids.push(a.detail);
  }
  for (const f of a.facts) {
    if (f.player_id !== player) continue;
    if (["ability_used", "effect", "leader", "promissory_in_play", "action_card"].includes(f.type)) {
      if (f.value) ids.push(f.value);
    }
  }
  return ids;
}

const COMPONENT_ACTIONS = new Set([
  "component.use",
  "tactical.component",
  "leader.state",
  "promissory.play",
  "tech.exhaust",
]);

function specialCues(entry: ActivityEntry, ctx: CueContext): Cue[] {
  const a = entry.activity;
  const players = new Set<string>();
  if (a.actor_id) players.add(a.actor_id);
  for (const f of a.facts) if (f.player_id && f.type === "ability_used") players.add(f.player_id);
  const cues: Cue[] = [];
  for (const player of players) {
    const faction = ctx.factionOf(player);
    const ids = componentIds(entry, player);
    const special = (FACTION_SPECIALS[faction ?? ""] ?? []).find((s) =>
      ids.some((id) => s.match.test(id)),
    );
    if (special) {
      cues.push({ kind: "voice", player, category: special.category, fallback: "special" });
      continue;
    }
    // Naaz-Rokha: każdy zdobyty relikt.
    if (faction === "naaz" && a.facts.some((f) => f.type === "relic" && f.player_id === player && (f.delta ?? 1) > 0)) {
      cues.push({ kind: "voice", player, category: "specialrelic", fallback: "special" });
      continue;
    }
    // Bohater frakcji (odblokowanie/użycie) — główny moment frakcji.
    if (a.actor_id === player && COMPONENT_ACTIONS.has(a.action) && ids.some((id) => /hero/i.test(id))) {
      cues.push({ kind: "voice", player, category: "special" });
    }
  }
  return cues;
}

/** Frakcje, których flagowiec przy zniszczeniu ma własną kwestię (Yin: Van Hauge niszczy system). */
const FLAGSHIP_DEATH: Record<string, string> = { yin: "bomb" };

/**
 * Utrata flagowca (fakt `units`, `flagship`, delta < 0). Pomija podsumowanie `combat.end`,
 * które powtarza straty już ogłoszone wpisem `combat.losses`.
 */
function flagshipCues(entry: ActivityEntry, ctx: CueContext): Cue[] {
  const a = entry.activity;
  if (a.action === "combat.end") return [];
  const cues: Cue[] = [];
  for (const f of a.facts) {
    if (f.type !== "units" || f.value !== "flagship" || (f.delta ?? 0) >= 0 || !f.player_id) continue;
    const category = FLAGSHIP_DEATH[ctx.factionOf(f.player_id) ?? ""];
    if (category) cues.push({ kind: "voice", player: f.player_id, category });
  }
  return cues;
}

/** Czy to „ja” (sieć: moje miejsce; lokalnie: każdy człowiek, nie bot). */
function isMe(player: string | null | undefined, ctx: CueContext): boolean {
  if (!player) return false;
  return ctx.network ? player === ctx.me : !ctx.isBot(player);
}

/** Sygnały dźwiękowe jednego NOWEGO wpisu feedu. */
export function cuesForEntry(entry: ActivityEntry, ctx: CueContext): Cue[] {
  const a = entry.activity;
  if (a.kind === "godmode") return [];
  const cues: Cue[] = [];
  switch (a.action) {
    case "combat.start":
      if (a.actor_id) {
        cues.push({ kind: "battle", attacker: a.actor_id, defender: a.target_id, position: a.detail });
      }
      break;
    case "turn.pass":
      if (a.actor_id && ctx.random() < JOKE_ON_PASS_CHANCE) {
        cues.push({ kind: "voice", player: a.actor_id, category: "joke" });
      }
      break;
    case "transaction.proposed":
      if (isMe(a.target_id, ctx) && !isMe(a.actor_id, ctx)) cues.push({ kind: "transmission" });
      break;
    case "phase.start":
      cues.push({ kind: "ui", name: "transition" });
      if ((a.subject ?? "").startsWith("agenda")) cues.push({ kind: "transmission" });
      break;
    default:
      break;
  }
  if (["turn.next", "turn.end", "turn.pass"].includes(a.action) && a.target_id) {
    if (isMe(a.target_id, ctx) && a.target_id !== a.actor_id) cues.push({ kind: "ui", name: "turn" });
  }
  cues.push(...specialCues(entry, ctx));
  cues.push(...flagshipCues(entry, ctx));
  return cues;
}

export type BattleSideStrength = { hp: number; expectedHits: number; unitCount: number };

/** Siła strony do porównania (wytrzymałość + oczekiwane trafienia). */
export function strength(side: BattleSideStrength | null | undefined): number {
  if (!side) return 0;
  return side.hp + side.expectedHits * 2;
}

/** Przewaga od tylu razy wzwyż = „offense superior”; od `CRUSHING` obrońca mówi „outnumbered”. */
export const SUPERIOR = 1.6;
export const CRUSHING = 2.5;

export type BattleLine = { player: string; category: string };

/** Kwestie na początek bitwy (kolejność = kolejność odtwarzania). */
export function battleLines(
  attacker: string,
  defender: string | null,
  opts: {
    defenderHome: boolean;
    attackerSide?: BattleSideStrength | null;
    defenderSide?: BattleSideStrength | null;
    random: () => number;
  },
): BattleLine[] {
  if (defender && opts.defenderHome) {
    return [
      { player: attacker, category: "homeinvasion" },
      { player: defender, category: "homedefense" },
    ];
  }
  const att = strength(opts.attackerSide);
  const dfn = strength(opts.defenderSide);
  if (defender && att > 0 && dfn > 0) {
    const ratio = att / dfn;
    if (ratio >= CRUSHING) {
      return [
        { player: attacker, category: "offensesuperior" },
        { player: defender, category: "defenseoutnumbered" },
      ];
    }
    if (ratio >= SUPERIOR) return [{ player: attacker, category: "offensesuperior" }];
  }
  // Wyrównana walka: okrzyk bojowy atakującego, czasem odpowiedź obrońcy.
  const lines: BattleLine[] = [{ player: attacker, category: "battle" }];
  if (defender && opts.random() < 0.35) lines.push({ player: defender, category: "battle" });
  return lines;
}

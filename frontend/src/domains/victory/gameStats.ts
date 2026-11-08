// Statystyki końcowe graczy do ekranu podsumowania (czyste funkcje nad `PlayerData`).
// Niczego nie liczy z reguł gry — składa liczby, które backend już policzył w web-data.

import type { PlayerData } from "@/entities/data/types";

export interface PlayerSummary {
  player: PlayerData;
  rank: number;
  vp: number;
  planets: number;
  resources: number;
  influence: number;
  techs: number;
  tradeGoods: number;
  relics: number;
  secretsScored: number;
  /** Siła floty (suma zdrowia kosmicznych jednostek) — jak panel Army Strength. */
  fleet: number;
  /** Siła wojsk naziemnych (suma zdrowia). */
  ground: number;
}

export interface Award {
  key: string;
  title: string;
  /** Opis zasługi, np. „7 planets held". */
  detail: string;
  /** Krótka liczba do dużego napisu na karcie (np. „7"). */
  stat: string;
  player: PlayerData;
}

/** Podsumowania wszystkich graczy, posortowane: zwycięzca pierwszy, potem wg VP. */
export function summarize(
  players: PlayerData[],
  winnerId: string | null | undefined,
): PlayerSummary[] {
  const rows = players.map((player) => ({
    player,
    vp: player.totalVps ?? 0,
    planets: player.planets?.length ?? 0,
    resources: player.totResources ?? 0,
    influence: player.totInfluence ?? 0,
    techs: player.techs?.length ?? 0,
    tradeGoods: player.tg ?? 0,
    relics: player.relics?.length ?? 0,
    secretsScored: Object.keys(player.secretsScored ?? {}).length,
    fleet: player.spaceArmyHealth ?? 0,
    ground: player.groundArmyHealth ?? 0,
  }));
  rows.sort((a, b) => {
    if (a.player.discordId === winnerId) return -1;
    if (b.player.discordId === winnerId) return 1;
    return b.vp - a.vp || b.planets - a.planets;
  });
  return rows.map((row, index) => ({ ...row, rank: index + 1 }));
}

/**
 * „Nagrody" za najlepszy wynik w kategorii. Kategoria bez lidera (wszędzie 0) jest
 * pomijana; remis wygrywa gracz wyżej w klasyfikacji.
 */
export function buildAwards(rows: PlayerSummary[]): Award[] {
  const defs: {
    key: string;
    title: string;
    value: (r: PlayerSummary) => number;
    detail: (n: number) => string;
  }[] = [
    {
      key: "planets",
      title: "Master of Worlds",
      value: (r) => r.planets,
      detail: (n) => `${n} planet${n === 1 ? "" : "s"} held`,
    },
    {
      key: "fleet",
      title: "Admiral of the Fleet",
      value: (r) => r.fleet,
      detail: (n) => `${n} fleet strength`,
    },
    {
      key: "ground",
      title: "Iron Legion",
      value: (r) => r.ground,
      detail: (n) => `${n} ground strength`,
    },
    {
      key: "techs",
      title: "Pioneer of Science",
      value: (r) => r.techs,
      detail: (n) => `${n} technologies`,
    },
    {
      key: "tg",
      title: "Merchant Prince",
      value: (r) => r.tradeGoods,
      detail: (n) => `${n} trade goods`,
    },
    {
      key: "economy",
      title: "Economic Titan",
      value: (r) => r.resources + r.influence,
      detail: (n) => `${n} resources and influence`,
    },
    {
      key: "relics",
      title: "Relic Hunter",
      value: (r) => r.relics,
      detail: (n) => `${n} relic${n === 1 ? "" : "s"}`,
    },
    {
      key: "secrets",
      title: "Keeper of Secrets",
      value: (r) => r.secretsScored,
      detail: (n) => `${n} secret objective${n === 1 ? "" : "s"}`,
    },
  ];
  const awards: Award[] = [];
  for (const def of defs) {
    let best: PlayerSummary | null = null;
    for (const row of rows) {
      if (def.value(row) > (best ? def.value(best) : 0)) best = row;
    }
    if (best) {
      awards.push({
        key: def.key,
        title: def.title,
        detail: def.detail(def.value(best)),
        stat: String(def.value(best)),
        player: best.player,
      });
    }
  }
  // Drugie miejsce (to ono rozstrzyga remis w głosowaniu) i ostatnie miejsce.
  const [first, second] = rows;
  if (first && second) {
    const gap = first.vp - second.vp;
    awards.push({
      key: "runner_up",
      title: "The Runner-up",
      detail:
        gap > 0
          ? `${second.vp} VP, ${gap} short of the throne`
          : `${second.vp} VP, level with the throne`,
      player: second.player,
      stat: `${second.vp} VP`,
    });
  }
  const last = rows[rows.length - 1];
  if (rows.length >= 3 && last && second && last.vp < second.vp) {
    awards.push({
      key: "wooden_spoon",
      title: "The Wooden Spoon",
      detail: `${last.vp} VP, last at the table`,
      player: last.player,
      stat: `${last.vp} VP`,
    });
  }
  return awards;
}

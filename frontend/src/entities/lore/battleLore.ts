/*
 * NARRACJA BITEW — generowany opis wyniku walki („co się stało”). Czysta warstwa prezentacyjna:
 * niczego nie zmienia w regułach, a czyta tylko to, co silnik już zapisał (straty, rundy, zwycięzca).
 * Używana w ekranie wyniku bitwy (BattleSummary) i w historii bitew w teczce systemu
 * (SystemDossier) — ten sam tekst w obu miejscach dla tej samej bitwy (wariant wybiera ziarno).
 *
 * Teksty możesz dopisywać/zmieniać w `POOLS` poniżej. Znaczniki w tekście:
 *   {W} zwycięzca  {L} przegrany  {A} atakujący  {D} obrońca  {where} miejsce (system/planeta)
 *   {lostL} straty przegranego („4 ships”)  {lostW} straty zwycięzcy  {typesL} z czego
 *   („2 dreadnoughts and a carrier”)  {rounds} („a single round” / „3 rounds”)
 * Zestawy `attacker` / `defender` są losowane tylko, gdy wygrała ta strona.
 */

export type BattleKind = "space" | "ground";

export type BattleClass =
  | "crushing"
  | "decisive"
  | "hard_fought"
  | "pyrrhic"
  | "skirmish"
  | "annihilation"
  | "standoff";

export type BattleLoreInput = {
  kind: BattleKind;
  /** Nazwa miejsca: system (walka kosmiczna) albo planeta (naziemna). */
  where: string;
  attacker: string;
  defender: string;
  /** Strona, która utrzymała pole; `null` = remis / odwrót. */
  winner: "attacker" | "defender" | null;
  rounds: number;
  attackerLost: number;
  defenderLost: number;
  /** Straty wg typu bazowego (np. `{ dreadnought: 2 }`) — do „z czego”. */
  attackerTypes?: Record<string, number>;
  defenderTypes?: Record<string, number>;
  /** Pełna nazwa jednostki (liczba pojedyncza) z typu bazowego; brak = pomijamy „z czego”. */
  typeName?: (baseType: string) => string;
  /** Stabilne ziarno (np. id bitwy) — ta sama bitwa zawsze dostaje ten sam tekst. */
  seed: string | number;
};

export type BattleLore = {
  cls: BattleClass;
  headline: string;
  text: string;
};

type Pool = { any: string[]; attacker?: string[]; defender?: string[] };

const POOLS: Record<BattleKind, Record<BattleClass, Pool>> = {
  space: {
    crushing: {
      any: [
        "{W} tore through the fleet of {L} above {where} and left only debris behind: {lostL} gone, not one ship of {W} lost.",
        "It was over before the sensors had finished counting. {typesL} of {L} burned above {where}, and {W} did not lose a single hull.",
        "{L} had expected a battle. What came to {where} was an execution: {lostL} destroyed without a scratch on {W}.",
        "Above {where} the void filled with the wreckage of {L}. {W} flew through it untouched.",
        "No flares, no retreat, no mercy. {W} erased {typesL} of {L} at {where} and sailed on with every ship intact.",
        "The logs of {W} will call it routine. The survivors of {L} will remember {where} for the rest of their lives.",
      ],
      attacker: [
        "{A} came out of the dark above {where} already firing. By the time {D} raised shields, {lostL} were lost.",
        "The assault of {A} on {where} was a hammer on glass: {typesL} of {D} shattered, none of the attackers fell.",
      ],
      defender: [
        "{D} met the invaders of {A} above {where} with a perfect wall of fire. {lostL} of {A} died, {D} lost nothing.",
        "{A} flew into the guns of {D} at {where} and learned why the locals sleep soundly.",
      ],
    },
    decisive: {
      any: [
        "{W} broke {L} above {where} in {rounds}, paying {lostW} for {lostL} of the enemy.",
        "{where} fell silent after {rounds} of fire. {typesL} of {L} were gone; {W} counted its own losses ({lostW}) and held the field.",
        "A clean victory for {W} at {where}: {lostL} destroyed against {lostW} lost.",
        "The line of {L} buckled above {where} and never recovered. {W} kept the void.",
        "{W} out-fought {L} at {where} in {rounds}. The wreckage drifts there still.",
        "Cold, quick and efficient: {W} took {where} from {L}, losing {lostW} and destroying {typesL}.",
      ],
      attacker: [
        "{A} forced the approach to {where} and shattered the defence of {D}: {lostL} destroyed, {lostW} lost.",
      ],
      defender: [
        "{D} held {where}. {A} left {typesL} in the void and counted the cost of the attempt.",
      ],
    },
    hard_fought: {
      any: [
        "{rounds} of fire above {where}, and neither side gave an inch until {W} finally broke {L}. Losses: {lostW} for {W}, {lostL} for {L}.",
        "Both fleets bled at {where}. {W} won, but the victory was measured in wreckage: {lostW} lost, {lostL} destroyed.",
        "It could have gone either way. For {rounds} {W} and {L} traded hits above {where}, until the last shield of {L} failed.",
        "{where} will be remembered as a slugging match. {W} stood at the end, with {lostW} lost and {typesL} of {L} destroyed.",
        "Shields flickered, hulls split, and still they fired. {W} outlasted {L} at {where} by the width of a single volley.",
        "Neither admiral blinked at {where}. {W} won by refusing to stop firing.",
      ],
    },
    pyrrhic: {
      any: [
        "{W} holds {where}, but at what price: {lostW} lost, more than {L} could take with it. The victory feels like a defeat.",
        "The fleet of {W} limped out of {where} with {lostW} gone. {L} lost {lostL}, and still the cost was higher for the victor.",
        "Historians will call {where} a triumph of {W}. The crews who watched {lostW} burn will call it something else.",
        "{W} won at {where}, if you can call it that. {lostW} destroyed, {lostL} of {L} destroyed, and the void is richer for the wreckage.",
        "A victory that no one will want to repeat. {W} took {where}; {L} took {lostW} with it.",
      ],
    },
    skirmish: {
      any: [
        "A brief exchange of fire above {where}. {W} prevailed against {L} in {rounds}; {lostW} and {lostL} were lost.",
        "Little more than a skirmish at {where}: {W} drove off {L} with minimal loss.",
        "{where} saw a quick, ugly flare of weapons fire. {W} kept the field; the galaxy hardly noticed.",
        "\nScouts and screens clashed above {where}. {W} came out ahead, and everyone went back to the ledgers.",
      ],
    },
    annihilation: {
      any: [
        "Nothing was left above {where}. {A} and {D} destroyed each other utterly: {lostW} against {lostL}, and the void keeps both.",
        "{rounds} of fire, and no flag still flying. The fleets of {A} and {D} died together at {where}.",
        "{where} is now a graveyard for the ships of {A} and {D}. No victor, no survivors, only drifting wreckage.",
        "They fought until there was nothing left to fight with. {A} and {D} both lost everything at {where}.",
        "Mutual annihilation: the sensors of {where} registered {typesL} destroyed, and then silence.",
      ],
    },
    standoff: {
      any: [
        "{A} and {D} circled each other above {where} and neither fleet broke. When the smoke cleared nobody had lost a ship.",
        "A tense standoff at {where}: shields up, guns hot, and nobody willing to be the first to fall.",
        "No ship was lost above {where}. The captains of {A} and {D} would later claim the other blinked first.",
      ],
    },
  },
  ground: {
    crushing: {
      any: [
        "The ground of {where} belonged to {W} within the hour: {lostL} of {L} fell, and not one soldier of {W} was lost.",
        "{L} dug in on {where}. It was not enough. {typesL} were swept aside, and {W} counted no dead of its own.",
        "{W} walked over the defence of {L} on {where}. {lostL} down, no losses on the winning side.",
        "No trenches, no walls, no luck held against {W} on {where}. {typesL} of {L} were wiped out.",
        "The battle for {where} went one way from the first volley. {W} lost nothing and {L} lost {lostL}.",
      ],
      attacker: [
        "{A} landed on {where} like a wave against a sandcastle. The defenders of {D} lost {lostL}; the landing force lost none.",
      ],
      defender: [
        "{A} stormed {where} into a wall of fire. {D} threw them back, {lostL} of the invaders dead and no defender fallen.",
      ],
    },
    decisive: {
      any: [
        "{W} took the ground of {where} from {L} in {rounds}, losing {lostW} while destroying {lostL}.",
        "Smoke rose over {where}. {L} lost {typesL}; {W} lost {lostW} and held the field.",
        "A decisive victory on {where}: {lostL} of {L} destroyed against {lostW} for {W}.",
        "{L} was driven from the ground of {where} in {rounds}. The banners of {W} now fly there.",
        "The line of {L} broke on {where}. {W} paid {lostW} and gained the world.",
      ],
      attacker: [
        "{A} fought its way across {where} and broke the defenders of {D}: {lostL} destroyed, {lostW} lost.",
      ],
      defender: [
        "{D} held {where} against the landing of {A}. {typesL} of the attackers did not leave the surface.",
      ],
    },
    hard_fought: {
      any: [
        "{rounds} of bitter fighting on {where}. {W} won, with {lostW} lost and {lostL} of {L} destroyed. Neither side asked for mercy.",
        "Every metre of {where} was paid for. {W} prevailed over {L}, but the ground drank {lostW} of its own.",
        "It was a battle of inches and bodies. {W} outlasted {L} on {where} at the cost of {lostW}.",
        "The fighting at {where} went on for {rounds}. When it ended, {W} stood on ground littered with {typesL} of {L}.",
        "Nobody who fought on {where} will describe it kindly. {W} won, and that is all the survivors will say.",
      ],
    },
    pyrrhic: {
      any: [
        "{W} holds {where}, but buried {lostW} to do it. Whoever comes next will find the garrison thin.",
        "A bitter win: {L} lost {lostL} on {where}, and {W} lost even more ({lostW}).",
        "{where} is taken, and the victors hardly have anyone left to stand on it. {W} lost {lostW}.",
        "The conquest of {where} was celebrated for about a minute. Then the casualty lists arrived: {lostW} for {W}.",
      ],
    },
    skirmish: {
      any: [
        "A short, ugly fight on {where}. {W} prevailed over {L} with {lostW} lost and {lostL} destroyed.",
        "Little more than a skirmish on {where}: {W} secured the ground and moved on.",
        "{L} resisted briefly on {where}. {W} did not need long.",
        "A handful of troops, a handful of shots, and {W} owned {where}.",
      ],
    },
    annihilation: {
      any: [
        "No one walked away from {where}. {A} and {D} destroyed each other down to the last soldier: {lostW} against {lostL}.",
        "{rounds} of close fighting, and the ground of {where} was left to the dead of both {A} and {D}.",
        "{where} swallowed both armies. {A} and {D} left nothing but craters and silence.",
        "Mutual annihilation on {where}: {typesL} destroyed, no one left to claim the victory.",
      ],
    },
    standoff: {
      any: [
        "Troops of {A} and {D} faced each other across the ground of {where}. Nobody fired the first decisive shot.",
        "A tense stalemate on {where}: no losses, and no one willing to give the ground.",
      ],
    },
  },
};

const HEADLINES: Record<BattleClass, string[]> = {
  crushing: ["A Crushing Victory", "Total Domination", "Without a Scratch"],
  decisive: ["A Decisive Victory", "The Field Is Taken", "Clean and Quick"],
  hard_fought: ["A Hard-Fought Victory", "Won by Inches", "Blood on Both Sides"],
  pyrrhic: ["A Pyrrhic Victory", "A Bitter Win", "Won at Terrible Cost"],
  skirmish: ["A Brief Skirmish", "A Short Clash", "A Quick Exchange"],
  annihilation: ["Mutual Annihilation", "Nobody Left", "Two Armies, No Victor"],
  standoff: ["A Tense Standoff", "Nobody Fired", "The Line Held"],
};

/** Deterministyczny skrót tekstu → liczba (wybór wariantu bez losowania). */
function hash(value: string | number): number {
  const text = String(value);
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

const pick = <T>(items: T[], seed: number): T => items[seed % items.length];

/** „1 ship”, „4 ships” — rzeczownik wg rodzaju walki. */
function count(n: number, kind: BattleKind): string {
  const noun = kind === "space" ? "ship" : "unit";
  return `${n} ${noun}${n === 1 ? "" : "s"}`;
}

const NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight"];

/** „2 dreadnoughts and a carrier” z mapy strat; pusty string, gdy brak danych o typach. */
function describeTypes(
  types: Record<string, number> | undefined,
  typeName: ((base: string) => string) | undefined,
): string {
  if (!types || !typeName) return "";
  const parts = Object.entries(types)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([base, n]) => {
      const name = typeName(base).toLowerCase();
      if (n === 1) return `a ${name}`;
      return `${NUMBER_WORDS[n] ?? n} ${name}s`;
    });
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0];
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

/** Rodzaj rozstrzygnięcia z samych strat i długości walki (progi stałe, patrz testy). */
export function classifyBattle(input: Pick<
  BattleLoreInput,
  "winner" | "rounds" | "attackerLost" | "defenderLost"
>): BattleClass {
  const { winner, rounds, attackerLost, defenderLost } = input;
  const total = attackerLost + defenderLost;
  if (winner === null) return total === 0 ? "standoff" : "annihilation";
  const winnerLost = winner === "attacker" ? attackerLost : defenderLost;
  const loserLost = winner === "attacker" ? defenderLost : attackerLost;
  if (winnerLost === 0 && loserLost >= 4) return "crushing";
  if (total <= 2) return "skirmish";
  if (winnerLost >= 3 && winnerLost >= loserLost) return "pyrrhic";
  if (winnerLost === 0) return "decisive";
  if (rounds >= 3 || winnerLost * 2 >= loserLost) return "hard_fought";
  return "decisive";
}

/** Ziarno wyboru wariantu z danych bitwy — to samo w ekranie wyniku i w historii systemu. */
export function battleSeed(
  position: string | null,
  planet: string | null,
  rounds: number,
  attackerLost: number,
  defenderLost: number,
): string {
  return `${position ?? ""}:${planet ?? ""}:${rounds}:${attackerLost}:${defenderLost}`;
}

/** Opis bitwy: rodzaj, nagłówek i tekst — deterministyczny dla danego ziarna. */
export function describeBattle(input: BattleLoreInput): BattleLore {
  const cls = classifyBattle(input);
  const seed = hash(`${input.seed}|${input.where}|${input.attacker}|${input.defender}`);
  const pool = POOLS[input.kind][cls];
  const rolePool =
    input.winner === "attacker" ? pool.attacker : input.winner === "defender" ? pool.defender : undefined;
  const variants = [...pool.any, ...(rolePool ?? [])];
  const winnerName = input.winner === "attacker" ? input.attacker : input.defender;
  const loserName = input.winner === "attacker" ? input.defender : input.attacker;
  const winnerLost = input.winner === "defender" ? input.defenderLost : input.attackerLost;
  const loserLost = input.winner === "defender" ? input.attackerLost : input.defenderLost;
  const loserTypes = input.winner === "defender" ? input.attackerTypes : input.defenderTypes;
  // Remis: {lostW} = straty atakującego, {lostL} = straty obrońcy; {typesL} = obie strony razem.
  const lostL = count(input.winner === null ? input.defenderLost : loserLost, input.kind);
  const typesL =
    describeTypes(
      input.winner === null ? mergeTypes(input.attackerTypes, input.defenderTypes) : loserTypes,
      input.typeName,
    ) || lostL;
  const values: Record<string, string> = {
    W: winnerName,
    L: loserName,
    A: input.attacker,
    D: input.defender,
    where: input.where,
    lostL,
    lostW: count(input.winner === null ? input.attackerLost : winnerLost, input.kind),
    typesL,
    rounds: input.rounds === 1 ? "a single round" : `${input.rounds} rounds`,
  };
  const text = pick(variants, seed).replace(/\{(\w+)\}/g, (_, key: string) => values[key] ?? "");
  return { cls, headline: pick(HEADLINES[cls], seed >>> 3), text };
}

function mergeTypes(
  a: Record<string, number> | undefined,
  b: Record<string, number> | undefined,
): Record<string, number> {
  const merged: Record<string, number> = { ...(a ?? {}) };
  for (const [base, n] of Object.entries(b ?? {})) merged[base] = (merged[base] ?? 0) + n;
  return merged;
}

import type { BombardGroup, InvasionUnit } from "./useInvasion";

/**
 * Logika przygotowania lądowania i bombardowania w oknie inwazji (RULES.md 40) — czysta, bez UI.
 *
 * Lądowanie (Commit Ground Forces) i przydział bombardowania gracz układa LOKALNIE, a do silnika
 * idzie jedno żądanie. Silnik i tak waliduje (422 z powodem), więc tu pilnujemy tylko, żeby
 * nie dało się ułożyć więcej, niż jest w przestrzeni / niż ma statków.
 */

/** Lądowanie: planeta → baseType → liczba. */
export type Stage = Record<string, Record<string, number>>;

/** Ile sztuk danego typu już rozdzielono po planetach. */
export function stagedOf(stage: Stage, baseType: string): number {
  return Object.values(stage).reduce((sum, p) => sum + (p[baseType] ?? 0), 0);
}

/** Ile sztuk danego typu zostaje jeszcze w przestrzeni (ładunek minus rozdzielone). */
export function remainingOf(
  cargo: InvasionUnit[],
  stage: Stage,
  baseType: string,
): number {
  const owned = cargo.find((u) => u.baseType === baseType)?.count ?? 0;
  return Math.max(0, owned - stagedOf(stage, baseType));
}

/** Zmienia liczbę ``baseType`` lądowaną na ``planet`` o ``delta`` (przycięte do 0..dostępne). */
export function bumpStage(
  stage: Stage,
  cargo: InvasionUnit[],
  planet: string,
  baseType: string,
  delta: number,
): Stage {
  const current = stage[planet]?.[baseType] ?? 0;
  const next = Math.max(
    0,
    Math.min(current + delta, current + remainingOf(cargo, stage, baseType)),
  );
  if (next === current) return stage;
  const planetStage = { ...(stage[planet] ?? {}) };
  if (next > 0) planetStage[baseType] = next;
  else delete planetStage[baseType];
  const result = { ...stage };
  if (Object.keys(planetStage).length > 0) result[planet] = planetStage;
  else delete result[planet];
  return result;
}

/** Całe pozostałe w przestrzeni siły naziemne ląduje na jednej planecie. */
export function landAll(
  stage: Stage,
  cargo: InvasionUnit[],
  planet: string,
): Stage {
  let result = stage;
  for (const unit of cargo) {
    result = bumpStage(
      result,
      cargo,
      planet,
      unit.baseType,
      remainingOf(cargo, result, unit.baseType),
    );
  }
  return result;
}

/** Sumaryczna liczba rozdzielonych jednostek (wszystkie planety). */
export function stageTotal(stage: Stage): number {
  return Object.values(stage).reduce(
    (sum, p) => sum + Object.values(p).reduce((a, b) => a + b, 0),
    0,
  );
}

/** Płaska lista do żądania `POST /tactical/invasion/commit`. */
export function stageList(
  stage: Stage,
): { planet: string; baseType: string; count: number }[] {
  return Object.entries(stage).flatMap(([planet, byType]) =>
    Object.entries(byType).map(([baseType, count]) => ({
      planet,
      baseType,
      count,
    })),
  );
}

/** Przydział bombardowania: baseType → planeta → liczba statków. */
export type BombardPlan = Record<string, Record<string, number>>;

/** Domyślnie wszystkie statki każdego typu bombardują pierwszy dozwolony cel. */
export function defaultBombardPlan(
  groups: BombardGroup[],
  targets: string[],
): BombardPlan {
  const plan: BombardPlan = {};
  if (targets.length === 0) return plan;
  for (const group of groups) {
    plan[group.baseType] = { [targets[0]]: group.count };
  }
  return plan;
}

/**
 * Przesuwa jedną jednostkę typu ``group`` na ``planet`` (zabiera ją z planety o największym
 * przydziale) albo (``delta`` < 0) zwraca ją na pierwszy inny cel. Suma przydziałów zostaje
 * równa liczbie statków — reguła „użyj każdej jednostki z Bombardment".
 */
export function shiftBombard(
  plan: BombardPlan,
  group: BombardGroup,
  targets: string[],
  planet: string,
  delta: 1 | -1,
): BombardPlan {
  const row = { ...(plan[group.baseType] ?? {}) };
  const others = targets.filter((t) => t !== planet);
  if (others.length === 0) return plan;
  if (delta === 1) {
    const donor = others
      .filter((t) => (row[t] ?? 0) > 0)
      .sort((a, b) => (row[b] ?? 0) - (row[a] ?? 0))[0];
    if (!donor) return plan;
    row[donor] = (row[donor] ?? 0) - 1;
    row[planet] = (row[planet] ?? 0) + 1;
  } else {
    if ((row[planet] ?? 0) <= 0) return plan;
    row[planet] = (row[planet] ?? 0) - 1;
    row[others[0]] = (row[others[0]] ?? 0) + 1;
  }
  return { ...plan, [group.baseType]: row };
}

/**
 * Przeciągnięcie statków typu ``baseType`` na planetę ``to``: z planety ``from`` albo (gdy
 * ``from`` = null) z planet o największym przydziale. Domyślnie 1 statek, ``all`` = cały stos.
 * Suma przydziałów zostaje równa liczbie statków („użyj każdej jednostki z Bombardment").
 */
export function moveBombard(
  plan: BombardPlan,
  baseType: string,
  targets: string[],
  to: string,
  from: string | null,
  all: boolean,
): BombardPlan {
  if (!targets.includes(to)) return plan;
  const row = { ...(plan[baseType] ?? {}) };
  const sources = (from ? [from] : targets)
    .filter((t) => t !== to && (row[t] ?? 0) > 0)
    .sort((a, b) => (row[b] ?? 0) - (row[a] ?? 0));
  let budget = all ? Number.POSITIVE_INFINITY : 1;
  let moved = 0;
  for (const source of sources) {
    if (budget <= 0) break;
    const take = Math.min(row[source] ?? 0, budget);
    row[source] = (row[source] ?? 0) - take;
    budget -= take;
    moved += take;
  }
  if (moved === 0) return plan;
  row[to] = (row[to] ?? 0) + moved;
  return { ...plan, [baseType]: row };
}

/** Płaska lista przydziałów do żądania `POST /tactical/invasion/bombard`. */
export function bombardList(
  plan: BombardPlan,
): { baseType: string; planet: string; count: number }[] {
  return Object.entries(plan).flatMap(([baseType, row]) =>
    Object.entries(row)
      .filter(([, count]) => count > 0)
      .map(([planet, count]) => ({ baseType, planet, count })),
  );
}

/** Rozdział żetonów dowodzenia w pulach (taktyczna / floty / strategii). */
export type Alloc = { t: number; f: number; s: number };

/**
 * „Auto” w kroku 5 fazy statusu (szybki domyślny rozdział, gracz nadal zatwierdza):
 * obecne pule zostają, nowe żetony najpierw dopełniają pulę floty do największej floty
 * w jednym systemie (żeby nie trzeba było niszczyć statków — RULES.md 42), reszta trafia
 * do puli taktycznej.
 *
 * @param base Pule przed rozdziałem (bez nowych żetonów).
 * @param gained Żetony zdobyte w kroku 5, jeszcze nieprzydzielone.
 * @param ships Statki liczone do puli floty per system (`{pozycja: ile}`).
 */
export function autoAlloc(base: Alloc, gained: number, ships: Record<string, number>): Alloc {
  const largest = Math.max(0, ...Object.values(ships));
  const toFleet = Math.min(gained, Math.max(0, largest - base.f));
  return { t: base.t + gained - toFleet, f: base.f + toFleet, s: base.s };
}

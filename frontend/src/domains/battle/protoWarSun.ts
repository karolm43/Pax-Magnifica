/**
 * Prototype War Sun (Embers of Muaat) — war sun FRAKCYJNY z danych (`muaat_warsun`, ulepszenie
 * `muaat_warsun2`, warianty modów z tym rdzeniem id, `tf-pws`): 1 / 2 = poziom, null = zwykły
 * war sun. Jednostki bez frakcji (np. `baldrick_muaat_warsun` — ogólny war sun wariantu) nie
 * dostają oprawy. Oprawa: kuźnia gwiazdy zamiast wormhole, korona plazmy, gorętsza salwa.
 */
export function protoWarSunLevel(
  unit:
    | { id: string; faction?: string | null; upgradesFromUnitId?: string | null }
    | null
    | undefined,
): 1 | 2 | null {
  if (!unit?.faction) return null;
  if (!unit.id.includes("muaat_warsun") && unit.id !== "tf-pws") return null;
  return unit.upgradesFromUnitId || unit.id.endsWith("2") ? 2 : 1;
}

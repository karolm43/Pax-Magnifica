// Portrety i lore frakcji — TREŚĆ DO UZUPEŁNIENIA PRZEZ CIEBIE.
//
// ───────────────────────────────────────────────────────────────────────────
// GDZIE CO WKLEJAĆ:
//
// 1) LORE (tekst) — wpisujesz TUTAJ, w mapie `FACTION_LORE` poniżej. Kluczem jest
//    identyfikator frakcji (`faction.id`, np. "ghost", "argent", "sol"). Tekst może
//    być dowolnie długi (panel ma własne przewijanie). Zachowaj znaki nowej linii —
//    puste linie rozdzielą akapity.
//
// 2) PORTRET (obrazek) — wrzucasz plik do katalogu:
//        frontend/public/faction_portraits/<id>.<rozszerzenie>
//    np. frontend/public/faction_portraits/ghost.jpg
//    Obsługiwane rozszerzenia (próbowane po kolei): jpg → png → webp. Nie musisz nic
//    tu wpisywać dla domyślnego portretu — komponent sam spróbuje tych ścieżek.
//    Jeśli chcesz podać WŁASNĄ ścieżkę (np. z CDN albo inną nazwę), ustaw `portrait`
//    we wpisie frakcji poniżej — nadpisze domyślne próbowanie.
//
// Brak portretu lub lore NIE jest błędem — panel pokaże placeholder / ukryje sekcję.
// ───────────────────────────────────────────────────────────────────────────

/** Wpis lore jednej frakcji. Oba pola opcjonalne. */
export interface FactionLore {
  /** Pełny tekst lore (może być długi — panel ma scroll). */
  lore?: string;
  /** Opcjonalna własna ścieżka portretu (nadpisuje domyślne /faction_portraits/<id>). */
  portrait?: string;
}

/**
 * Mapa „id frakcji → lore/portret". UZUPEŁNIAJ TUTAJ.
 *
 * Przykład (odkomentuj i wypełnij):
 *
 *   ghost: {
 *     lore: `Ghosts of Creuss przemierzają sieć tuneli czasoprzestrzennych...
 *
 *   ...drugi akapit...`,
 *   },
 *   argent: {
 *     lore: `Argent Flight...`,
 *     portrait: "/faction_portraits/argent_custom.jpg",
 *   },
 */
export const FACTION_LORE: Record<string, FactionLore> = {
  // TODO(user): dodawaj tu wpisy frakcji.
};

/** Domyślne ścieżki portretu próbowane po kolei (pierwsza istniejąca wygrywa). */
export function defaultPortraitCandidates(factionId: string): string[] {
  return [
    `/faction_portraits/${factionId}.jpg`,
    `/faction_portraits/${factionId}.png`,
    `/faction_portraits/${factionId}.webp`,
  ];
}

/** Lore frakcji (lub undefined, gdy nie uzupełniono). */
export function getFactionLore(factionId: string): FactionLore | undefined {
  return FACTION_LORE[factionId];
}

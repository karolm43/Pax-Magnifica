// Przełomy (breakthroughs) Thunder's Edge, które WRAZ ze sobą wprowadzają do gry osobny
// KOMPONENT frakcji — planetę albo jednostkę — poza standardowymi planetami domowymi i
// generycznymi jednostkami startowymi. Pokazujemy te komponenty w osobnej, jasno nazwanej
// sekcji „Breakthrough component" podglądu frakcji, żeby nie myliły się z planetami
// domowymi ani z resztą jednostek frakcyjnych.
//
// CZTERY takie frakcje (potwierdzone w głównym źródle reguł — docs/rules_tirules/F_muaat.md,
// F_keleres.md oraz treści kart przełomów w assets/data/breakthroughs/te_breakthroughs.json):
//   • Muaat — „Stellar Genesis" (muaatbt): legendarna planeta AVERNUS („The Nucleus").
//   • Keleres — „I.I.H.Q. Modernization" (keleresbt): legendarna planeta CUSTODIA VIGILIA.
//   • Mentak — „The Table's Grace" (mentakbt): jednostka CORSAIR (``mentak_cruiser3``).
//   • Naaz-Rokha — „Absolute Synergy" (naazbt): jednostka EIDOLON MAXIMUM (``naaz_voltron``).
//
// To świadoma decyzja warstwy UI (stąd mapa po id przełomu tutaj, a nie flaga w danych
// AsyncTI4): dane przełomu opisują grant tylko w wolnym tekście karty. Id planety/jednostki
// wskazuje na istniejący wpis w danych (``avernus``, ``custodiavigilia``, ``mentak_cruiser3``,
// ``naaz_voltron``), więc karta renderuje się z pełnymi danymi bez dopisywania statystyk tutaj.

/** Komponenty nadawane przez przełom: id planet i/lub id jednostek (istniejące wpisy danych). */
export interface BreakthroughComponents {
  planetIds: string[];
  unitIds: string[];
}

/** Mapa: id przełomu → komponenty, które wprowadza (tylko przełomy dające komponent). */
const BREAKTHROUGH_COMPONENTS: Record<string, BreakthroughComponents> = {
  muaatbt: { planetIds: ["avernus"], unitIds: [] },
  keleresbt: { planetIds: ["custodiavigilia"], unitIds: [] },
  mentakbt: { planetIds: [], unitIds: ["mentak_cruiser3"] },
  naazbt: { planetIds: [], unitIds: ["naaz_voltron"] },
};

/**
 * Komponenty (planety + jednostki) nadawane przez dany przełom. Zwraca `null`, gdy przełom
 * nie wprowadza osobnego komponentu (większość przełomów to tylko zdolność).
 */
export function breakthroughComponents(
  breakthroughId: string | null | undefined,
): BreakthroughComponents | null {
  if (!breakthroughId) return null;
  return BREAKTHROUGH_COMPONENTS[breakthroughId] ?? null;
}

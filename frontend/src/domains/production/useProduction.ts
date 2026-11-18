import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";

/*
 * Okno PRODUKCJI (RULES.md 33.3): odczyt liczbowy kroku PRODUCTION
 * (`GET /tactical/production/view`). Samo zamawianie idzie przez `useBoardEditor().produce`
 * (silnik waliduje i płaci; 422 z powodem trafia do panelu komunikatów).
 */

export type ProductionUnit = {
  baseType: string;
  asyncId: string;
  name: string;
  /** Cena JEDNEJ produkcji (dla fighter/infantry: para = `unitsPerCost` sztuk). */
  cost: number;
  unitsPerCost: number;
  placement: "space" | "planet";
  /** CAPACITY wariantu jednostki (Bellum Gloriosum). */
  capacity?: number;
  /** Ile sztuk zostało w rezerwie; null = bez limitu (żetony fighter/infantry). */
  reinforcements: number | null;
  /** Ile sztuk tego typu stoi teraz na planszy (przestrzeń + planety, wszystkie systemy). */
  onBoard: number;
  /**
   * Gdy rezerwy zabraknie (R_component_limitations): jednostki, które gracz może zdjąć
   * z systemów bez swojego żetonu i od razu wyprodukować (`value` = "<pozycja>|<strefa>").
   */
  boardSources?: { value: string; label: string }[];
};

export type ProductionPlanet = {
  planet: string;
  name: string;
  position: string;
  resources: number;
  influence: number;
  /** Ile planeta wnosi do płatności (zasoby; przy Freelancers wpływ liczy się jak zasoby). */
  payValue: number;
  planetType: string | null;
  exhausted: boolean;
  inActiveSystem: boolean;
};

export type ProductionProducer = {
  /** "space" albo id planety, na której stoi producent (dok). */
  zone: string;
  baseType: string;
  asyncId: string;
  /** Czym jest producent: "unit" (sprite), "planet", "technology" (np. Magmus Reactor), "other". */
  kind?: string;
  /** Id komponentu dającego zdolność (technologia Magmus Reactor itp.). */
  sourceId?: string | null;
  name: string;
  count: number;
  /** Łączna wartość PRODUCTION tej grupy. */
  value: number;
  /** Wartość PRODUCTION jednej sztuki (value = perUnit × count). */
  perUnit: number;
  /** Typy, których ta zdolność PRODUCTION NIE może produkować (np. dok Arborec → infantry). */
  forbids: string[];
};

/** Jednorazowa produkcja z karty (np. Freelancers) - poza krokiem PRODUCTION. */
export type ProductionGrant = {
  source: string;
  units: number;
  influenceAsResources: boolean;
  /** Integrated Economy: limit ŁĄCZNEGO kosztu (zamiast limitu liczby sztuk); null = brak. */
  maxCost?: number | null;
  /** Sling Relay: tylko statki. */
  shipsOnly?: boolean;
  /** Salvage Operations: tylko te typy (base_type); puste = bez ograniczenia. */
  allowedTypes?: string[];
};

export type ProductionBody = {
  active: true;
  grant: ProductionGrant | null;
  position: string;
  /** Produkcja z karty strategii (Construction / Warfare), poza akcją taktyczną. */
  standalone?: boolean;
  /** Zniżka łącznego kosztu z hooków (np. Sarween Tools) - działa od razu. */
  costReduction?: number;
  /** Źródła zniżki (nazwa karty z danych + ile zdejmuje) - podpis przy koszcie. */
  costReductionSources?: { name: string; amount: number }[];
  /** AI Development Algorithm: gotowy i ile kosztu zdejmie (tylko gdy gracz go wyczerpie). */
  aida?: { ready: boolean; discount: number };
  playerId: string;
  faction: string | null;
  limit: number;
  used: number;
  remaining: number;
  /** Bellum Gloriosum: myśliwce i siły naziemne do capacity produkowanych statków poza limitem. */
  freeCargo?: boolean;
  /** Co już wyprodukowano w tej akcji, wg typu (do rozdziału między osobne zdolności). */
  usedByType: Record<string, number>;
  blockaded: boolean;
  producers: ProductionProducer[];
  /** Strefy, gdzie wolno postawić siły naziemne (planety z producentem / "space"). */
  groundZones: string[];
  planets: ProductionPlanet[];
  tradeGoods: number;
  /** Wartość 1 TG w płatności (Mirror Computing: 2); brak = 1. */
  tradeGoodValue?: number;
  units: ProductionUnit[];
};

export type ProductionView = { active: false } | ProductionBody;

/** Stan okna produkcji; `enabled` = trwa krok PRODUCTION. */
export function useProductionView(enabled: boolean) {
  return useQuery<ProductionView>({
    queryKey: ["production", "view"],
    enabled,
    queryFn: async () =>
      fetchJson<ProductionView>("/bot/tactical/production/view", "production"),
    staleTime: 0,
  });
}

/** Rezygnacja z jednorazowej produkcji z karty (Freelancers: "you may produce"). */
export async function skipProductionGrant(): Promise<void> {
  const response = await fetch("/bot/tactical/production/skip-grant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    let message = raw || `Error ${response.status}`;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // nie-JSON - zostaje surowy tekst
    }
    useAppStore.getState().setNotice(message, "error");
    throw new Error(message);
  }
}

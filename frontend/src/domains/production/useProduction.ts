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
  /** Ile sztuk zostało w rezerwie; null = bez limitu (żetony fighter/infantry). */
  reinforcements: number | null;
  /** Ile sztuk tego typu stoi teraz na planszy (przestrzeń + planety, wszystkie systemy). */
  onBoard: number;
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
};

export type ProductionBody = {
  active: true;
  grant: ProductionGrant | null;
  position: string;
  playerId: string;
  faction: string | null;
  limit: number;
  used: number;
  remaining: number;
  /** Co już wyprodukowano w tej akcji, wg typu (do rozdziału między osobne zdolności). */
  usedByType: Record<string, number>;
  blockaded: boolean;
  producers: ProductionProducer[];
  /** Strefy, gdzie wolno postawić siły naziemne (planety z producentem / "space"). */
  groundZones: string[];
  planets: ProductionPlanet[];
  tradeGoods: number;
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

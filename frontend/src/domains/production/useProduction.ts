import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";

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
};

export type ProductionPlanet = {
  planet: string;
  name: string;
  position: string;
  resources: number;
  influence: number;
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
};

export type ProductionBody = {
  active: true;
  position: string;
  playerId: string;
  faction: string | null;
  limit: number;
  used: number;
  remaining: number;
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

import type { ExtraDie } from "@/shared/ui/ExtraDicePicker";
import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";
import type { BattleAssignPlan } from "@/api/useBoardEditor";

/*
 * Okno INWAZJI (RULES.md 40): odczyt stanu (`GET /tactical/invasion`) i akcje podkroków.
 * Akcje WALIDUJE silnik (422 z powodem → panel komunikatów), okno tylko prowadzi.
 */
const BOT_ROOT = "/bot";

export type InvasionPhase =
  | "BOMBARDMENT"
  | "COMMIT"
  | "SPACE_CANNON_DEFENSE"
  | "GROUND_COMBAT"
  | "ESTABLISH";

export type InvasionUnit = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
  damaged: number;
  sustain: boolean;
  baseHitsOn: number;
};

export type InvasionPlanet = {
  planet: string;
  owner: string | null;
  shielded: boolean;
  /** Tarcza stoi, ale war sun ją łamie (animacja zapadnięcia). */
  hasShield: boolean;
  hasSpaceCannon: boolean;
  /** Siły naziemne per gracz (klucz tożsamości). */
  forces: Record<string, InvasionUnit[]>;
  /** Struktury (PDS, dok) per gracz. */
  structures: Record<string, InvasionUnit[]>;
  committed: Record<string, number>;
  contested: boolean;
  bombardable: boolean;
};

export type BombardGroup = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
  hitsOn: number;
  dicePerUnit: number;
  expectedHits: number;
};

export type BombardPending = {
  planet: string;
  defender: string;
  hits: number;
  required: number;
  /** Ile trafień anuluje jedno użycie Sustain Damage (Non-Euclidean Shielding: 2). */
  cancels?: number;
};

export type DefenseShooter = {
  baseType: string;
  asyncId: string;
  name: string;
  owner: string;
  count: number;
  hitsOn: number;
  dicePerUnit: number;
  /** Klucz grupy - wybór jednostki z dodatkową kością (Plasma Scoring). */
  key: string;
  /** Ile kości dodałby Plasma Scoring jednej jednostce (0 = brak technologii). */
  plasmaDice: number;
};

export type DefensePlanet = {
  planet: string;
  shooters: DefenseShooter[];
  /** Źródła dodatkowych kości obrońcy - każde osobno (RULES.md 62.11). */
  extraDice?: ExtraDie[];
  status: "open" | "pending" | "resolved";
  hits: number;
  required: number;
  /** Ile trafień anuluje jedno użycie Sustain Damage (Non-Euclidean Shielding: 2). */
  cancels?: number;
};

export type InvasionRoll = {
  baseType: string;
  name: string;
  owner?: string;
  count: number;
  hitsOn: number;
  dice: number[];
  hits: number;
  /** Modyfikator wyniku kości celu (Antimass Deflectors: -1). */
  modifier?: number;
  /** Kości dodane przez Plasma Scoring. */
  extraDice?: number;
};

export type InvasionLogEntry = {
  phase: "BOMBARDMENT" | "DEFENSE";
  planet: string;
  defender: string | null;
  rolls: InvasionRoll[];
  hits: number;
  passed?: boolean;
  losses: Record<string, number>;
  sustained: Record<string, number>;
};

export type InvasionResult = {
  planet: string;
  previousOwner: string | null;
  outcome: "captured" | "retained" | "lost" | "already_controlled";
  destroyedStructures: Record<string, Record<string, number>>;
  explore: boolean;
};

/** Żeton Custodians w inwazji na Mecatol Rex (R_custodians_token). */
export type CustodiansView = {
  onBoard: boolean;
  /** Atakujący zdjął żeton w tej inwazji - musi zlądować na Mecatol Rex. */
  claimed: boolean;
  canClaim: boolean;
  /** Powód, dla którego teraz nie można zdjąć żetonu. */
  reason: string | null;
  cost: number;
  /** Gotowe planety atakującego -> wpływ. */
  influence: Record<string, number>;
  tradeGoods: number;
  /** Wartość 1 TG w płatności (Mirror Computing: 2). */
  tradeGoodValue?: number;
  /** Planety zablokowane dla lądowania, dopóki żeton leży. */
  blockedPlanets: string[];
};

export type InvasionView = {
  custodians: CustodiansView | null;
  active: boolean;
  /** Prosta inwazja (brak obrońców/bombardowania) - lądowanie w panelu pomocy. */
  simple: boolean;
  /** Inwazja komponentu (np. `leaders:yinhero`): bez lądowania z orbity i bez Space Cannon Defense. */
  source: string;
  phase: InvasionPhase | null;
  position: string | null;
  attacker: string | null;
  cargo: InvasionUnit[];
  planets: InvasionPlanet[];
  bombard: {
    /** Ile kości dodałby Plasma Scoring jednej bombardującej jednostce (0 = brak). */
    plasmaDice: number;
    /** Źródła dodatkowych kości atakującego - każde osobno (RULES.md 62.11). */
    extraDice?: ExtraDie[];
    groups: BombardGroup[];
    targets: string[];
    done: boolean;
    pending: BombardPending[];
  };
  defense: DefensePlanet[];
  combatPlanets: string[];
  inCombat: boolean;
  results: InvasionResult[];
  log: InvasionLogEntry[];
  combatResults: Record<
    string,
    {
      attacker: string;
      defender: string;
      winner: string | null;
      outcome: "winner" | "draw" | null;
      rounds: number;
    }
  >;
};

/** Stan okna inwazji; `enabled` = trwa inwazja (gameState.activeInvasion). */
export function useInvasion(enabled: boolean) {
  return useQuery<InvasionView>({
    queryKey: ["invasion"],
    enabled,
    queryFn: async () =>
      fetchJson<InvasionView>("/bot/tactical/invasion", "invasion"),
    staleTime: 0,
  });
}

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    let message = raw || `Error ${response.status}`;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // nie-JSON — zostaje surowy tekst
    }
    useAppStore.getState().setNotice(message, "error");
    throw new Error(message);
  }
}

const items = (m: Record<string, number>) =>
  Object.entries(m)
    .filter(([, count]) => count > 0)
    .map(([baseType, count]) => ({ baseType, count }));

/** Akcje podkroków inwazji; po sukcesie oznaczają zapytania jako nieświeże. */
export function useInvasionActions() {
  const queryClient = useQueryClient();
  const refresh = useCallback(() => {
    for (const key of [
      "invasion",
      "battle",
      "playerData",
      "history",
      "moveRange",
      "production",
    ]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }, [queryClient]);

  const bombard = useCallback(
    async (
      assignments: { baseType: string; planet: string; count: number }[],
      extraDice: Record<string, string> | null = null,
    ) => {
      await post("/tactical/invasion/bombard", {
        assignments: assignments.filter((a) => a.count > 0),
        extraDice,
      });
      refresh();
    },
    [refresh],
  );

  const assignBombard = useCallback(
    async (planet: string, faction: string, plan: BattleAssignPlan) => {
      await post("/tactical/invasion/bombard/assign", {
        planet,
        faction,
        sustain: items(plan.sustain),
        destroy: items(plan.destroy),
        destroyDamaged: items(plan.destroyDamaged),
      });
      refresh();
    },
    [refresh],
  );

  const commit = useCallback(
    async (commits: { planet: string; baseType: string; count: number }[]) => {
      await post("/tactical/invasion/commit", {
        commits: commits.filter((c) => c.count > 0),
      });
      refresh();
    },
    [refresh],
  );

  const defenseFire = useCallback(
    async (planet: string, extraDice: Record<string, string> | null = null) => {
      await post("/tactical/invasion/defense/fire", { planet, extraDice });
      refresh();
    },
    [refresh],
  );

  const defensePass = useCallback(
    async (planet: string) => {
      await post("/tactical/invasion/defense/pass", { planet });
      refresh();
    },
    [refresh],
  );

  const assignDefense = useCallback(
    async (planet: string, faction: string, plan: BattleAssignPlan) => {
      await post("/tactical/invasion/defense/assign", {
        planet,
        faction,
        sustain: items(plan.sustain),
        destroy: items(plan.destroy),
        destroyDamaged: items(plan.destroyDamaged),
      });
      refresh();
    },
    [refresh],
  );

  const claimCustodians = useCallback(
    async (planets: string[], tradeGoods: number) => {
      await post("/tactical/invasion/custodians", { planets, tradeGoods });
      refresh();
    },
    [refresh],
  );

  const begin = useCallback(async () => {
    await post("/tactical/invasion/begin", {});
    refresh();
  }, [refresh]);

  const next = useCallback(async () => {
    await post("/tactical/invasion/next", {});
    refresh();
  }, [refresh]);

  return {
    begin,
    bombard,
    assignBombard,
    commit,
    claimCustodians,
    defenseFire,
    defensePass,
    assignDefense,
    next,
  };
}

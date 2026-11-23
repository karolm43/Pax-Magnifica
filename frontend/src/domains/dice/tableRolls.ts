import type { TableRoll } from "@/entities/data/types";

type WithRolls = {
  tableRoll?: TableRoll | null;
  tableRolls?: TableRoll[];
};

/** Lista ostatnich rzutów „na stół”; starszy backend daje tylko ``tableRoll``. */
function allRolls(state: WithRolls | undefined): TableRoll[] {
  if (!state) return [];
  if (state.tableRolls && state.tableRolls.length > 0) return state.tableRolls;
  return state.tableRoll ? [state.tableRoll] : [];
}

/** Najnowszy ``seq`` rzutu w stanie (0 = brak rzutów). */
export function latestTableRollSeq(state: WithRolls | undefined): number {
  return allRolls(state).reduce((max, r) => Math.max(max, r.seq), 0);
}

/** Rzuty nowsze niż ``seen`` w kolejności rzucania (kilka graczy w jednym efekcie). */
export function pendingTableRolls(
  state: WithRolls | undefined,
  seen: number,
): TableRoll[] {
  return allRolls(state)
    .filter((r) => r.seq > seen)
    .sort((a, b) => a.seq - b.seq);
}

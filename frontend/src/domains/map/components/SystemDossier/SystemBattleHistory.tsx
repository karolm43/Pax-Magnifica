import { getPlanetData } from "@/entities/lookup/planets";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import { BASE_TYPE_BY_ASYNC } from "@/domains/map/components/UnitStack/cargo";
import { battleSeed, describeBattle } from "@/domains/lore/battleLore";
import { useGameData } from "@/state/useGameContext";
import type { BattleHistoryEntry } from "@/entities/data/types";
import type { FactionHelpers } from "./useFactionHelpers";
import styles from "./SystemDossier.module.css";

const ASYNC_BY_BASE: Record<string, string> = Object.fromEntries(
  Object.entries(BASE_TYPE_BY_ASYNC).map(([asyncId, base]) => [base, asyncId]),
);

const unitFullName = (base: string) =>
  getGenericUnitDataByAsyncId(ASYNC_BY_BASE[base] ?? base)?.name ?? base;

/**
 * Kronika bitew systemu: co i kiedy się tu wydarzyło (warstwa fabularna, niczego nie zmienia
 * w grze). Tekst generuje `describeBattle` z zapisanych strat — ten sam co w ekranie wyniku.
 * Najnowsze na górze; brak bitew = nic nie renderujemy.
 */
export function SystemBattleHistory({
  position,
  helpers,
  history,
}: {
  position: string;
  helpers: FactionHelpers;
  /** Kronika bitew partii (`gameState.battleHistory`). */
  history: BattleHistoryEntry[] | undefined;
}) {
  const players = useGameData()?.playerData ?? [];
  const battles = (history ?? []).filter((b) => b.position === position);
  if (battles.length === 0) return null;

  const factionOf = (playerId: string) =>
    players.find((p) => p.discordId === playerId)?.faction ?? playerId;
  const nameOf = (playerId: string) => helpers.displayName(factionOf(playerId));

  return (
    <section className={styles.chronicle} aria-label="Battle history">
      <h3 className={styles.chronicleHead}>Battle history</h3>
      <ol className={styles.chronicleList}>
        {[...battles].reverse().map((b) => {
          const attackerLost = b.losses[b.attacker] ?? 0;
          const defenderLost = b.losses[b.defender] ?? 0;
          const planet = b.planet ? getPlanetData(b.planet)?.name : undefined;
          const lore = describeBattle({
            kind: b.kind,
            where: planet ?? `System ${position}`,
            attacker: nameOf(b.attacker),
            defender: nameOf(b.defender),
            winner: b.winner === b.attacker ? "attacker" : b.winner === b.defender ? "defender" : null,
            rounds: b.rounds,
            attackerLost,
            defenderLost,
            attackerTypes: b.lostTypes[b.attacker],
            defenderTypes: b.lostTypes[b.defender],
            typeName: unitFullName,
            seed: battleSeed(b.position, b.planet, b.rounds, attackerLost, defenderLost),
          });
          return (
            <li key={b.id} className={styles.chronicleItem}>
              <span className={styles.chronicleMeta}>
                Round {b.round} · {b.kind === "ground" ? (planet ?? "ground battle") : "space battle"}
              </span>
              <p>
                <b>{lore.headline}.</b> {lore.text}
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

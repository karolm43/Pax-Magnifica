import { IconArrowRight, IconPencil, IconRocket, IconTrash } from "@tabler/icons-react";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { lookupUnit } from "@/entities/lookup/units";
import { Unit } from "@/shared/ui/Unit";
import { BOOST_NAMES, neededBoosts, type StagedLeg } from "./flightPlan";
import { asyncOfBase } from "./routeTypes";
import styles from "./FlightPlanList.module.css";

/**
 * Staged legs of the flight plan (RULES.md 32.4): where each group flies from, which ships and
 * cargo, which one-ship bonus it spends, and Edit / Remove. The routes are drawn on the map
 * (``FlightPlanLayer``); clicking a leg's source system on the map also reopens it.
 */
export function FlightPlanList({ legs }: { legs: StagedLeg[] }) {
  const gameData = useGameData();
  const editStagedLeg = useAppStore((s) => s.editStagedLeg);
  const removeStagedLeg = useAppStore((s) => s.removeStagedLeg);
  const editing = useAppStore((s) => s.moveDraft?.legId);
  if (legs.length === 0) return null;

  const systemName = (position: string) => {
    const tile = gameData?.tiles?.[position];
    const name = tile ? getTileById(tile.systemId)?.name : undefined;
    return name ? `${position} · ${name}` : position;
  };

  return (
    <ol className={styles.list} aria-label="Flight plan">
      {legs.map((leg, index) => {
        const player = gameData?.playerData?.find((p) => p.faction === leg.faction);
        const colorAlias = getColorAlias(player?.color);
        const picks = Object.values(leg.picks).filter((p) => p.count > 0);
        const boosts = neededBoosts(leg.route, leg.picks);
        const jumps = (leg.route.route?.length ?? 1) - 1;
        return (
          <li
            key={leg.id}
            className={styles.leg}
            data-editing={leg.id === editing || undefined}
          >
            <header className={styles.head}>
              <span className={styles.index}>{index + 1}</span>
              <span className={styles.from}>
                <IconRocket size={12} aria-hidden="true" /> {systemName(leg.from)}
                <IconArrowRight size={11} aria-hidden="true" />
                <small>
                  {jumps} jump{jumps === 1 ? "" : "s"}
                </small>
              </span>
              {leg.id !== "open" && (
                <span className={styles.tools}>
                  <button
                    type="button"
                    className={styles.tool}
                    aria-label={`Edit the leg from ${systemName(leg.from)}`}
                    onClick={() => editStagedLeg(leg.id)}
                  >
                    <IconPencil size={13} />
                  </button>
                  <button
                    type="button"
                    className={styles.tool}
                    aria-label={`Remove the leg from ${systemName(leg.from)}`}
                    onClick={() => removeStagedLeg(leg.id)}
                  >
                    <IconTrash size={13} />
                  </button>
                </span>
              )}
            </header>
            <div className={styles.units}>
              {picks.map((p) => {
                const asyncId = asyncOfBase(p.baseType);
                const name = lookupUnit(asyncId, leg.faction, player)?.name ?? p.baseType;
                return (
                  <span
                    key={`${p.kind}|${p.position}|${p.zone}|${p.baseType}`}
                    className={styles.unit}
                    data-cargo={p.kind === "cargo" || undefined}
                    title={p.kind === "cargo" ? `${name} (carried)` : name}
                  >
                    <span className={styles.sprite}>
                      <Unit
                        unitType={asyncId}
                        colorAlias={colorAlias}
                        faction={leg.faction}
                        scaleSprite
                      />
                    </span>
                    <b>{p.count}</b>
                  </span>
                );
              })}
            </div>
            {boosts.length > 0 && (
              <div className={styles.boosts}>
                {boosts.map((b) => (
                  <span key={b} className={styles.boost} title="+1 move for one ship of this leg">
                    {BOOST_NAMES[b]} +1
                  </span>
                ))}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}

import type { KeyboardEvent } from "react";
import cx from "clsx";
import { useDisclosure } from "@/hooks/useDisclosure";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { Unit } from "@/shared/ui/Unit";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { StasisInfantryCard } from "@/domains/player/components/StasisInfantryCard";
import { UnitDetails } from "@/domains/player/components/UnitCard/UnitDetails";
import {
  DEFAULT_UNIT_CAPS,
  getUnitModifiers,
} from "@/domains/player/components/UnitCard/unitModifiers";
import { getUnitData, lookupUnit } from "@/entities/lookup/units";
import { getTechData, TECH_PREREQ_ICON } from "@/entities/lookup/tech";
import { getColorAlias } from "@/entities/lookup/colors";
import type { PlayerData } from "@/entities/data/types";
import { useSettingsStore } from "@/state/appStore";
import {
  prerequisiteText,
  statBoxes,
  unitKeywords,
  upgradeStrip,
  type StatBox,
} from "./sheetUnits";
import styles from "./SheetUnit.module.css";

/*
 * One unit box of the faction sheet (also the flagship and the mech slot): printed name,
 * silhouette in the player's colour, ability, keywords, stat bar and UPGRADE strip, plus the
 * live deployed / cap count. Click = the same unit card as everywhere else (`UnitDetails`).
 */

export function StatBar({ stats }: { stats: StatBox[] }) {
  if (stats.length === 0) return null;
  return (
    <dl className={styles.stats}>
      {stats.map((stat) => (
        <div key={stat.label} className={styles.stat}>
          <dd>
            {stat.value}
            {stat.times ? <i>×{stat.times}</i> : null}
          </dd>
          <dt>{stat.label}</dt>
        </div>
      ))}
    </dl>
  );
}

function Prerequisites({ requirements }: { requirements: string }) {
  return (
    <>
      {requirements.split("").map((letter, i) =>
        TECH_PREREQ_ICON[letter] ? (
          <img key={`${letter}-${i}`} src={TECH_PREREQ_ICON[letter]} alt="" />
        ) : null,
      )}
    </>
  );
}

function Silhouette({
  asyncId,
  player,
  faction,
}: {
  asyncId: string;
  player: PlayerData;
  faction?: string;
}) {
  return (
    <span className={styles.art} aria-hidden="true">
      <Unit
        unitType={asyncId}
        colorAlias={getColorAlias(player.color)}
        faction={faction}
        scaleSprite
        showFactionTokens={false}
      />
    </span>
  );
}

/** War Sun nobody has researched yet: the printed box, empty, with what unlocks it. */
function LockedWarSun({ player, className }: { player: PlayerData; className?: string }) {
  const requirements = getTechData("ws")?.requirements ?? "";
  return (
    <article className={cx(styles.box, styles.unavailable, className)} aria-label="War Sun">
      <div className={styles.body}>
        <h4 className={styles.name}>War Sun</h4>
        <Silhouette asyncId="ws" player={player} />
        <p className={styles.ability}>
          Requires War Sun technology{" "}
          <span className={styles.inlineIcons} title={prerequisiteText(requirements)}>
            <Prerequisites requirements={requirements} />
          </span>
        </p>
      </div>
    </article>
  );
}

type Props = {
  asyncId: string;
  player: PlayerData;
  variant?: "unit" | "flagship" | "mech";
  /** Line under the name (flagship: whose it is). */
  subtitle?: string;
  className?: string;
};

export function SheetUnit({ asyncId, player, variant = "unit", subtitle, className }: Props) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const showUpgrades = useSettingsStore((s) => s.settings.showPlayerAreaUnitUpgrades);
  const found = lookupUnit(asyncId, player.faction, player);
  const unit = found ? getUnitData(found.id) : undefined;

  if (!unit || unit.id.toLowerCase() === "nowarsun") {
    if (asyncId === "ws") return <LockedWarSun player={player} className={className} />;
    return null;
  }

  const modifiers = getUnitModifiers(unit, player.unitsOwned);
  const deployed = player.unitCounts?.[asyncId]?.deployedCount ?? 0;
  const cap = player.unitCounts?.[asyncId]?.unitCap ?? DEFAULT_UNIT_CAPS[unit.baseType];
  const strip = upgradeStrip(unit);
  const upgraded =
    showUpgrades &&
    (Boolean(strip?.researched) || modifiers.upgradeFactions.length > 0);
  const keywords = unitKeywords(unit);
  const stasis = asyncId === "gf" ? (player.stasisInfantry ?? 0) : 0;
  const count =
    cap !== undefined ? `${deployed} of ${cap} deployed` : `${deployed} deployed`;
  const factionMark = modifiers.upgradeFactions[0] ?? unit.faction;

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggle();
  };

  return (
    <div className={cx(styles.slot, className)}>
      <SmoothPopover opened={opened} onChange={setOpened}>
        <SmoothPopover.Target>
          <div
            role="button"
            tabIndex={0}
            className={styles.box}
            data-variant={variant}
            data-upgraded={upgraded || undefined}
            aria-label={`${unit.name}, ${count}`}
            aria-expanded={opened}
            onClick={toggle}
            onKeyDown={onKeyDown}
          >
            <div className={styles.body}>
              <header className={styles.head}>
                {factionMark ? (
                  <CircularFactionIcon faction={factionMark} size={18} />
                ) : null}
                <span>
                  <h4 className={styles.name}>{unit.name}</h4>
                  {(subtitle ?? unit.subtitle) && (
                    <small className={styles.subtitle}>{subtitle ?? unit.subtitle}</small>
                  )}
                </span>
              </header>
              <Silhouette asyncId={asyncId} player={player} faction={unit.faction} />
              {unit.ability && <p className={styles.ability}>{unit.ability}</p>}
              {keywords.length > 0 && (
                <ul className={styles.keywords}>
                  {keywords.map((keyword) => (
                    <li key={keyword}>{keyword}</li>
                  ))}
                </ul>
              )}
              <StatBar stats={statBoxes(unit, modifiers)} />
              <span
                className={styles.count}
                data-empty={deployed === cap || undefined}
                title={
                  cap !== undefined
                    ? `${count} · ${cap - deployed} in reinforcements`
                    : count
                }
              >
                <b>{deployed}</b>
                {cap !== undefined ? `/${cap}` : null}
              </span>
            </div>
            {strip && (
              <span
                className={styles.upgrade}
                data-researched={strip.researched || undefined}
                title={
                  strip.researched
                    ? `Upgraded: ${strip.techName}`
                    : `Upgrade ${strip.techName}: ${prerequisiteText(strip.requirements)}`
                }
              >
                <span>{strip.researched ? "Upgraded" : "Upgrade"}</span>
                <Prerequisites requirements={strip.requirements} />
              </span>
            )}
          </div>
        </SmoothPopover.Target>
        <SmoothPopover.Dropdown p={0}>
          <UnitDetails unitId={unit.id} color={player.color} />
        </SmoothPopover.Dropdown>
      </SmoothPopover>
      {stasis > 0 && (
        <div className={styles.stasis}>
          <StasisInfantryCard reviveCount={stasis} color={player.color} />
        </div>
      )}
    </div>
  );
}

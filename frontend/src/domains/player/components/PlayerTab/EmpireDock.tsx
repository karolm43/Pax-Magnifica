import { useState } from "react";
import { IconAlertTriangle, IconBolt, IconBulb, IconStar } from "@tabler/icons-react";
import { ComponentCard } from "@/domains/cards/components/ComponentInfo";
import { Named } from "@/domains/game-shell/components/ActivityPanel/Named";
import { ArmyStats } from "@/domains/player/components/ArmyStats";
import { usePlayerCardComputedData } from "@/domains/player/components/PlayerCardShared/usePlayerCardComputedData";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import type { PlayerData } from "@/entities/data/types";
import { useGameData } from "@/state/useGameContext";
import { useSettingsStore } from "@/state/appStore";
import type { Tip, TipRef, TipTone } from "./commanderTips";
import type { EmpireStats } from "./empireStats";
import { EmpirePanel } from "./EmpirePanel";
import { HandPanel } from "./HandPanel";
import styles from "./PlayerTab.module.css";

/*
 * Under the player zone: what the printed pieces cannot say - the briefing (what to do now /
 * opponent intel), the empire overview with the shipyard, and the hand. No tabs: planets,
 * technologies and cards in play are on the Players tab.
 */

const TONE_ICON: Record<TipTone, typeof IconBolt> = {
  action: IconBolt,
  good: IconStar,
  warn: IconAlertTriangle,
  info: IconBulb,
};

const TONE_LABEL: Record<TipTone, string> = {
  action: "Now",
  good: "Opportunity",
  warn: "Warning",
  info: "Tip",
};

/** Most urgent first: what to do now, then warnings, opportunities and general tips. */
const TONE_ORDER: TipTone[] = ["action", "warn", "good", "info"];

/** A tip reference: name with hover hint; click opens the full card (same as the player panel chips). */
function TipRefLink({ tipRef, idMap }: { tipRef: TipRef; idMap?: Record<number, string> }) {
  const [opened, setOpened] = useState(false);
  const named = <Named kind={tipRef.kind} id={tipRef.id} name={tipRef.name} idMap={idMap} />;
  if (tipRef.kind === "system") return named;
  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="bottom">
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.refLink}
          aria-expanded={opened}
          title="Click for the full card"
          onClick={() => setOpened((o) => !o)}
        >
          {named}
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <ComponentCard componentRef={{ kind: tipRef.kind, id: tipRef.id }} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

function TipRow({ tip, idMap }: { tip: Tip; idMap?: Record<number, string> }) {
  const Icon = TONE_ICON[tip.tone];
  return (
    <li className={styles.tip} data-tone={tip.tone}>
      <Icon size={15} aria-label={TONE_LABEL[tip.tone]} className={styles.tipIcon} />
      <span>
        {tip.text}
        {tip.refs?.map((ref, i) => (
          <span key={`${ref.kind}-${ref.id}`} className={styles.ref}>
            {i === 0 ? " " : ", "}
            <TipRefLink tipRef={ref} idMap={idMap} />
          </span>
        ))}
      </span>
    </li>
  );
}

export function EmpireDock({
  gameId,
  player,
  own,
  scouting,
  tips,
  empire,
}: {
  gameId: string;
  player: PlayerData;
  /** The shown player is the desk player (their hand is visible). */
  own: boolean;
  scouting: boolean;
  tips: Tip[];
  empire?: EmpireStats;
}) {
  const gameData = useGameData();
  const showArmy = useSettingsStore((s) => s.settings.showPlayerAreaArmyStrength);
  const idMap = gameData?.strategyCardIdMap;
  const { armyStats } = usePlayerCardComputedData(player);
  const sorted = [...tips].sort((a, b) => TONE_ORDER.indexOf(a.tone) - TONE_ORDER.indexOf(b.tone));

  return (
    <div className={styles.grid}>
      <div className={styles.column}>
        <section className={styles.panel} aria-label={scouting ? "Opponent intel" : "Briefing"}>
          <h3 className={styles.panelTitle}>{scouting ? "Opponent intel" : "Briefing"}</h3>
          {sorted.length > 0 ? (
            <ul className={styles.tips}>
              {sorted.map((tip) => (
                <TipRow key={tip.id} tip={tip} idMap={idMap} />
              ))}
            </ul>
          ) : (
            <p className={styles.hint}>All clear.</p>
          )}
        </section>
        {empire ? <EmpirePanel player={player} stats={empire} /> : null}
      </div>
      <div className={styles.column}>
        <HandPanel gameId={gameId} player={player} own={own} />
        {showArmy && (
          <section className={styles.panel} aria-label="Army strength">
            <h3 className={styles.panelTitle}>Army strength</h3>
            <ArmyStats stats={armyStats} rank={gameData?.armyRankings?.[player.faction]} />
          </section>
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { IconAlertTriangle, IconBolt, IconBulb, IconStar } from "@tabler/icons-react";
import { Tabs } from "@/ds";
import { ComponentCard } from "@/domains/cards/components/ComponentInfo";
import { Named } from "@/domains/game-shell/components/ActivityPanel/Named";
import { ArmyStats } from "@/domains/player/components/ArmyStats";
import { FragmentsPool } from "@/domains/player/components/FragmentsPool";
import { Nombox } from "@/domains/player/components/composition/Nombox";
import { OmenDice } from "@/domains/player/components/OmenDice";
import { PlayerCardAbilitiesFactionTechsMobile } from "@/domains/player/components/PlayerCardAbilitiesFactionTechs";
import { PlayerCardCounts } from "@/domains/player/components/PlayerCardCounts";
import { PlayerCardPlanetsArea } from "@/domains/player/components/PlayerCardPlanetsArea";
import { ObjectivesRack } from "@/domains/player/components/PlayerCardShared/ObjectivesRack";
import { PlayerCardDeck } from "@/domains/player/components/PlayerCardShared/PlayerCardDeck";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { usePlayerCardComputedData } from "@/domains/player/components/PlayerCardShared/usePlayerCardComputedData";
import { PlotCardsList } from "@/domains/player/components/PlotCardsList";
import { ReinforcementTokensGroup } from "@/domains/player/components/ReinforcementTokensGroup";
import { ResourceInfluenceCompact } from "@/domains/player/components/ResourceInfluenceTable";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { TechSkipIcon, type TechType } from "@/shared/ui/TechSkipIcon";
import type { PlayerData } from "@/entities/data/types";
import { useGameData } from "@/state/useGameContext";
import { useSettingsStore } from "@/state/appStore";
import type { Tip, TipRef, TipTone } from "./commanderTips";
import type { EmpireStats } from "./empireStats";
import { EmpirePanel } from "./EmpirePanel";
import { HandPanel } from "./HandPanel";
import styles from "./PlayerTab.module.css";

/*
 * Lower dock under the player zone: everything that is not on the faction sheet, behind tabs so
 * the board stays uncluttered - hand & briefing, planets, technologies, cards on the table.
 */

const SKIPS: TechType[] = ["biotic", "propulsion", "cybernetic", "warfare"];

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

function Planets({ player, empire }: { player: PlayerData; empire?: EmpireStats }) {
  const settings = useSettingsStore((s) => s.settings);
  const fields = getPlayerCardLayoutFields(player);
  const { planetEconomics } = usePlayerCardComputedData(player);
  return (
    <section className={styles.panel} aria-label="Planets">
      <div className={styles.dockSummary}>
        <ResourceInfluenceCompact
          planetEconomics={planetEconomics}
          showTotalSpend={settings.showPlayerAreaTotalSpend}
        />
        {empire && (
          <span className={styles.hint}>
            {empire.planets.ready} of {empire.planets.total} planets ready
          </span>
        )}
      </div>
      <div className={styles.dockFlow}>
        <PlayerCardPlanetsArea
          planets={fields.planets}
          exhaustedPlanetAbilities={player.exhaustedPlanetAbilities}
          exhaustedPlanets={player.exhaustedPlanets}
          playerId={player.discordId}
        />
        {settings.showPlayerAreaReinforcements && (
          <ReinforcementTokensGroup
            breachTokensReinf={player.breachTokensReinf}
            sleeperTokensReinf={player.sleeperTokensReinf}
            ghostWormholesReinf={player.ghostWormholesReinf}
            galvanizeTokensReinf={player.galvanizeTokensReinf}
            ml="xs"
          />
        )}
      </div>
    </section>
  );
}

function Technologies({ player, empire }: { player: PlayerData; empire?: EmpireStats }) {
  const showFaction = useSettingsStore((s) => s.settings.showPlayerAreaFactionAbilities);
  const { allNotResearchedFactionTechs } = usePlayerCardComputedData(player);
  return (
    <section className={styles.panel} aria-label="Technologies">
      {empire && (
        <span className={styles.iconGroup} aria-label="Tech specialties on ready planets">
          <small>Skips</small>
          {SKIPS.map((c) => (
            <span key={c} className={styles.iconCount} title={`${empire.skips[c]} ready ${c} specialty planets`}>
              <TechSkipIcon techType={c} size={16} />
              <b data-zero={empire.skips[c] === 0 || undefined}>{empire.skips[c]}</b>
            </span>
          ))}
        </span>
      )}
      <PlayerCardDeck playerData={player} sections={["tech"]} />
      {showFaction &&
        (allNotResearchedFactionTechs.length > 0 || (player.customPromissoryNotes?.length ?? 0) > 0) && (
          <>
            <h4 className={styles.subTitle}>Faction technologies and notes</h4>
            <div className={styles.dockFlow}>
              <PlayerCardAbilitiesFactionTechsMobile
                notResearchedFactionTechs={allNotResearchedFactionTechs}
                customPromissoryNotes={player.customPromissoryNotes}
                showBreakthrough={false}
                groupClassName={styles.dockFlow}
              />
            </div>
          </>
        )}
    </section>
  );
}

function Holdings({ player }: { player: PlayerData }) {
  const fields = getPlayerCardLayoutFields(player);
  const { promissoryNotes } = usePlayerCardComputedData(player);
  const captured = fields.nombox && Object.keys(fields.nombox).length > 0;
  const plots = Array.isArray(fields.plotCards) ? fields.plotCards : [];
  return (
    <section className={styles.panel} aria-label="Objectives and cards">
      <h4 className={styles.subTitle}>Secrets, relics, laws and promissory notes</h4>
      <ObjectivesRack
        flow
        secretsScored={player.secretsScored ?? {}}
        knownUnscoredSecrets={player.knownUnscoredSecrets}
        soCount={player.soCount}
        promissoryNotes={promissoryNotes}
        relics={player.relics ?? []}
        laws={player.lawsOwned}
        exhaustedRelics={player.exhaustedRelics}
      />
      <h4 className={styles.subTitle}>Relic fragments</h4>
      <FragmentsPool fragments={player.fragments ?? []} reserveSpace />
      {plots.length > 0 && (
        <>
          <h4 className={styles.subTitle}>Plots</h4>
          <PlotCardsList plotCards={plots} faction={player.faction} keyPrefix="tab-plot" />
        </>
      )}
      {captured && <Nombox capturedUnits={fields.nombox} ownerFaction={player.faction} />}
      <OmenDice dice={player.omenDice} />
    </section>
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
  const [view, setView] = useState<string>("hand");
  const gameData = useGameData();
  const showArmy = useSettingsStore((s) => s.settings.showPlayerAreaArmyStrength);
  const idMap = gameData?.strategyCardIdMap;
  const { armyStats, planetEconomics } = usePlayerCardComputedData(player);
  const limit = player.actionCardLimit;
  const overLimit = typeof limit === "number" && player.acCount > limit;
  const { total } = planetEconomics;

  return (
    <Tabs value={view} onChange={(v) => v && setView(v)}>
      <Tabs.List className={styles.viewTabs}>
        <Tabs.Tab value="hand">
          {scouting ? "Hand & intel" : "Hand & briefing"}
          <span
            className={styles.tabMeta}
            data-warn={overLimit || undefined}
            title={`Action cards${typeof limit === "number" ? ` (limit ${limit})` : ""} · secret objectives · promissory notes`}
          >
            {player.acCount}
            {typeof limit === "number" ? `/${limit}` : ""} AC · {player.soCount ?? 0} SO ·{" "}
            {player.pnCount ?? 0} PN
          </span>
        </Tabs.Tab>
        <Tabs.Tab value="planets">
          Planets
          <span className={styles.tabMeta} title="Ready resources · ready influence">
            {Math.floor(total.currentResources)} R · {Math.floor(total.currentInfluence)} I
          </span>
        </Tabs.Tab>
        <Tabs.Tab value="tech">Technologies</Tabs.Tab>
        <Tabs.Tab value="holdings">Objectives & cards</Tabs.Tab>
      </Tabs.List>

      <Tabs.Panel value="hand" keepMounted={false} className={styles.view}>
        <div className={styles.grid}>
          <div className={styles.column}>
            <section className={styles.panel} aria-label={scouting ? "Opponent intel" : "Briefing"}>
              <h3 className={styles.panelTitle}>{scouting ? "Opponent intel" : "Briefing"}</h3>
              {tips.length > 0 ? (
                <ul className={styles.tips}>
                  {tips.map((tip) => (
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
            <section className={styles.panel} aria-label="Cards held">
              <PlayerCardCounts pnCount={player.pnCount ?? 0} acCount={player.acCount ?? 0} />
            </section>
            <HandPanel gameId={gameId} player={player} own={own} />
            {showArmy && (
              <section className={styles.panel} aria-label="Army strength">
                <ArmyStats stats={armyStats} rank={gameData?.armyRankings?.[player.faction]} />
              </section>
            )}
          </div>
        </div>
      </Tabs.Panel>

      <Tabs.Panel value="planets" keepMounted={false} className={styles.view}>
        <Planets player={player} empire={empire} />
      </Tabs.Panel>
      <Tabs.Panel value="tech" keepMounted={false} className={styles.view}>
        <Technologies key={player.color} player={player} empire={empire} />
      </Tabs.Panel>
      <Tabs.Panel value="holdings" keepMounted={false} className={styles.view}>
        <Holdings player={player} />
      </Tabs.Panel>
    </Tabs>
  );
}

import { Nombox } from "@/domains/player/components/composition/Nombox";
import { OmenDice } from "@/domains/player/components/OmenDice";
import { PlayerCardAbilitiesFactionTechsMobile } from "@/domains/player/components/PlayerCardAbilitiesFactionTechs";
import { PlayerCardPlanetsArea } from "@/domains/player/components/PlayerCardPlanetsArea";
import { ObjectivesRack } from "@/domains/player/components/PlayerCardShared/ObjectivesRack";
import { PlayerCardDeck } from "@/domains/player/components/PlayerCardShared/PlayerCardDeck";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { usePlayerCardComputedData } from "@/domains/player/components/PlayerCardShared/usePlayerCardComputedData";
import { PlotCardsList } from "@/domains/player/components/PlotCardsList";
import { TechSkipIcon, type TechType } from "@/shared/ui/TechSkipIcon";
import type { PlayerData } from "@/entities/data/types";
import { useSettingsStore } from "@/state/appStore";
import type { EmpireStats } from "./empireStats";
import styles from "./PlayerTab.module.css";

/*
 * What lies on the table in front of the player besides the printed pieces: technologies,
 * planet cards, and the cards in play (scored secrets, relics, laws, promissory notes, plots,
 * captured units). Always open, no tabs - the same components as the Players tab, so every chip
 * opens the same full card on click.
 */

const SKIPS: TechType[] = ["biotic", "propulsion", "cybernetic", "warfare"];

export function TechnologiesPanel({ player, empire }: { player: PlayerData; empire?: EmpireStats }) {
  const showFaction = useSettingsStore((s) => s.settings.showPlayerAreaFactionAbilities);
  const { allNotResearchedFactionTechs } = usePlayerCardComputedData(player);
  const researched = player.techs?.length ?? 0;
  const factionLeft =
    showFaction &&
    (allNotResearchedFactionTechs.length > 0 || (player.customPromissoryNotes?.length ?? 0) > 0);
  return (
    <section className={styles.panel} aria-label="Technologies">
      <header className={styles.panelHead}>
        <h3 className={styles.panelTitle}>
          Technologies <span className={styles.count}>{researched}</span>
        </h3>
        {empire && (
          <span className={styles.iconGroup} aria-label="Tech specialties on ready planets">
            <small>Skips on ready planets</small>
            {SKIPS.map((c) => (
              <span key={c} className={styles.iconCount} title={`${empire.skips[c]} ready ${c} specialty planets`}>
                <TechSkipIcon techType={c} size={16} />
                <b data-zero={empire.skips[c] === 0 || undefined}>{empire.skips[c]}</b>
              </span>
            ))}
          </span>
        )}
      </header>
      <PlayerCardDeck key={player.color} playerData={player} sections={["tech"]} />
      {factionLeft && (
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

export function PlanetsPanel({ player, empire }: { player: PlayerData; empire?: EmpireStats }) {
  const fields = getPlayerCardLayoutFields(player);
  return (
    <section className={styles.panel} aria-label="Planets">
      <header className={styles.panelHead}>
        <h3 className={styles.panelTitle}>
          Planets <span className={styles.count}>{fields.planets.length}</span>
        </h3>
        {empire && (
          <span className={styles.hint}>
            {empire.planets.ready} ready · {empire.planets.total - empire.planets.ready} exhausted
          </span>
        )}
      </header>
      {fields.planets.length === 0 ? (
        <p className={styles.hint}>No planets controlled.</p>
      ) : (
        <div className={styles.dockFlow}>
          <PlayerCardPlanetsArea
            planets={fields.planets}
            exhaustedPlanetAbilities={player.exhaustedPlanetAbilities}
            exhaustedPlanets={player.exhaustedPlanets}
            playerId={player.discordId}
          />
        </div>
      )}
    </section>
  );
}

export function CardsInPlayPanel({ player }: { player: PlayerData }) {
  const fields = getPlayerCardLayoutFields(player);
  const { promissoryNotes } = usePlayerCardComputedData(player);
  const captured = Boolean(fields.nombox && Object.keys(fields.nombox).length > 0);
  const plots = Array.isArray(fields.plotCards) ? fields.plotCards : [];
  const hasRack =
    (fields.lawsOwned?.length ?? 0) > 0 ||
    Object.keys(fields.secretsScored ?? {}).length > 0 ||
    (fields.soCount ?? 0) > 0 ||
    (fields.relics?.length ?? 0) > 0 ||
    promissoryNotes.length > 0;
  const omen = (player.omenDice?.length ?? 0) > 0;
  return (
    <section className={styles.panel} aria-label="Cards in play">
      <h3 className={styles.panelTitle}>Cards in play</h3>
      {!hasRack && plots.length === 0 && !captured && !omen && (
        <p className={styles.hint}>No secrets, relics, laws or promissory notes in play.</p>
      )}
      {hasRack && (
        <ObjectivesRack
          flow
          secretsScored={fields.secretsScored ?? {}}
          knownUnscoredSecrets={fields.knownUnscoredSecrets}
          soCount={fields.soCount}
          promissoryNotes={promissoryNotes}
          relics={fields.relics ?? []}
          laws={fields.lawsOwned}
          exhaustedRelics={fields.exhaustedRelics}
        />
      )}
      {plots.length > 0 && (
        <>
          <h4 className={styles.subTitle}>Plots</h4>
          <PlotCardsList plotCards={plots} faction={player.faction} keyPrefix="tab-plot" />
        </>
      )}
      {captured && (
        <>
          <h4 className={styles.subTitle}>Captured units</h4>
          <Nombox capturedUnits={fields.nombox} ownerFaction={player.faction} />
        </>
      )}
      <OmenDice dice={player.omenDice} />
    </section>
  );
}

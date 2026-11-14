/*
 * Pasek zasobów „jak w strategiach" — dyskretny odczyt MOICH zapasów w pasku zakładek:
 * resources/influence (niewyczerpane planety / wszystkie), trade goods, commodities, karty
 * akcji i notki, żetony dowodzenia, fragmenty, dług. To ten sam `StoresStrip`, co w strefie
 * gracza (spójność), tylko z dołożonym blokiem ekonomii planet. Gracz = biurko (`useDeskPlayer`).
 */
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { StoresStrip } from "@/domains/player/components/PlayerCardShared/StoresStrip";
import styles from "./ResourceBar.module.css";

export function ResourceBar() {
  const desk = useDeskPlayer();
  if (!desk) return null;
  const player = getPlayerCardLayoutFields(desk);
  return (
    <div className={styles.bar} role="group" aria-label="Your stores">
      <StoresStrip
        economy={{
          resources: { current: desk.resources ?? 0, total: desk.totResources ?? 0 },
          influence: { current: desk.influence ?? 0, total: desk.totInfluence ?? 0 },
        }}
        tg={player.tg}
        commodities={player.commodities}
        commoditiesTotal={player.commoditiesTotal}
        acCount={player.acCount}
        pnCount={player.pnCount}
        fragments={player.fragments}
        debtTokens={player.debtTokens}
        tacticalCC={player.tacticalCC}
        fleetCC={player.fleetCC + (desk.mahactEdict?.length ?? 0)}
        strategicCC={player.strategicCC}
      />
    </div>
  );
}

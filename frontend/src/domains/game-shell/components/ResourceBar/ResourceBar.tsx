/*
 * Pasek zasobów „jak w strategiach" — odczyt MOICH zapasów w pasku zakładek: resources /
 * influence (niewyczerpane planety / wszystkie), trade goods, commodities, karty akcji,
 * żetony dowodzenia i fragmenty. Ikony to te same assety, co w strefie gracza i szczegółach
 * planety (`/pa_resources.png`, `InfluenceIcon`, `/tg.png`, `/comms.png`, rewers karty akcji).
 * Gracz = biurko (`useDeskPlayer`).
 */
import type { ReactNode } from "react";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { FragmentsPool } from "@/domains/player/components/FragmentsPool";
import InfluenceIcon from "@/shared/ui/InfluenceIcon";
import styles from "./ResourceBar.module.css";

function Stat({
  icon,
  value,
  total,
  title,
  tone,
}: {
  icon: ReactNode;
  value: number;
  total?: number;
  title: string;
  tone?: "res" | "inf" | "tg";
}) {
  return (
    <span className={styles.stat} data-tone={tone} title={title}>
      <span className={styles.icon}>{icon}</span>
      <b data-zero={value === 0 || undefined}>{value}</b>
      {total !== undefined && <i>/{total}</i>}
    </span>
  );
}

export function ResourceBar() {
  const desk = useDeskPlayer();
  if (!desk) return null;
  const player = getPlayerCardLayoutFields(desk);
  const resources = desk.resources ?? 0;
  const totResources = desk.totResources ?? 0;
  const influence = desk.influence ?? 0;
  const totInfluence = desk.totInfluence ?? 0;
  const tg = player.tg ?? 0;
  const comms = player.commodities ?? 0;
  const commsMax = player.commoditiesTotal ?? 0;
  const fleet = player.fleetCC + (desk.mahactEdict?.length ?? 0);

  return (
    <div className={styles.bar} role="group" aria-label="Your stores">
      <Stat
        tone="res"
        icon={<img src="/pa_resources.png" alt="" />}
        value={resources}
        total={totResources}
        title={`Resources: ${resources} available of ${totResources} (unexhausted planets)`}
      />
      <Stat
        tone="inf"
        icon={<InfluenceIcon size={20} />}
        value={influence}
        total={totInfluence}
        title={`Influence: ${influence} available of ${totInfluence} (unexhausted planets)`}
      />
      <span className={styles.sep} aria-hidden="true" />
      <Stat
        tone="tg"
        icon={<img src="/tg.png" alt="" />}
        value={tg}
        title={`Trade goods: ${tg}`}
      />
      <Stat
        icon={<img src="/comms.png" alt="" />}
        value={comms}
        total={commsMax}
        title={`Commodities: ${comms} of ${commsMax}`}
      />
      <Stat
        icon={<img className={styles.card} src="/cardback/cardback_action.png" alt="" />}
        value={player.acCount}
        title={`Action cards in hand: ${player.acCount}`}
      />
      <span className={styles.sep} aria-hidden="true" />
      <span
        className={styles.cc}
        title={`Command tokens: ${player.tacticalCC} tactic · ${fleet} fleet · ${player.strategicCC} strategy`}
      >
        <b>{player.tacticalCC}</b>
        <em>T</em>
        <b>{fleet}</b>
        <em>F</em>
        <b>{player.strategicCC}</b>
        <em>S</em>
      </span>
      {player.fragments.length > 0 && <FragmentsPool fragments={player.fragments} />}
    </div>
  );
}

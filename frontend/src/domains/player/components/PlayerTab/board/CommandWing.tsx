import type { CSSProperties, ReactNode } from "react";
import { IconAlertTriangle } from "@tabler/icons-react";
import { DebtTokens } from "@/domains/player/components/DebtTokens";
import { useFactionTokenImage } from "@/hooks/useFactionTokenImage";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { Unit } from "@/shared/ui/Unit";
import { getColorAlias } from "@/entities/lookup/colors";
import type { PlayerData } from "@/entities/data/types";
import styles from "./CommandWing.module.css";

/*
 * Right wing of the player zone: the command sheet - TACTIC / FLEET / STRATEGY pools and the
 * TRADE GOODS hex, with the reinforcement tokens on the bottom edge.
 */

const COMMAND_TOKEN_SUPPLY = 16;

function CommandToken({ player }: { player: PlayerData }) {
  const factionUrl = useFactionTokenImage(player.faction);
  return (
    <span className={styles.token} aria-hidden="true">
      <img src={assetUrl(`/command_token/command_${getColorAlias(player.color)}.png`)} alt="" />
      {player.faction && <img className={styles.tokenFaction} src={factionUrl} alt="" />}
    </span>
  );
}

function Pool({
  kind,
  label,
  count,
  title,
  warn,
  children,
}: {
  kind: "tactic" | "fleet" | "strategy" | "tg";
  label: string;
  count: ReactNode;
  title: string;
  warn?: boolean;
  children?: ReactNode;
}) {
  return (
    <div
      className={styles.pool}
      data-kind={kind}
      data-warn={warn || undefined}
      role="group"
      aria-label={title}
      title={title}
    >
      <div className={styles.plate} aria-hidden="true" />
      <span className={styles.poolLabel}>{label}</span>
      <span className={styles.poolValue}>{count}</span>
      {children}
    </div>
  );
}

export function CommandWing({
  player,
  largestFleet,
}: {
  player: PlayerData;
  /** Most non-fighter ships in one system; null while the board is unknown. */
  largestFleet: number | null;
}) {
  const edict = player.mahactEdict?.length ?? 0;
  const fleet = player.fleetCC + edict;
  const fleetFull = largestFleet !== null && fleet > 0 && largestFleet >= fleet;
  const tg = player.tg ?? 0;
  const debts = player.debtTokens ?? {};
  const hasDebts = Object.values(debts).some((n) => n > 0);

  return (
    <section className={styles.wing} aria-label="Command sheet">
      <Pool
        kind="tactic"
        label="Tactic"
        count={player.tacticalCC}
        title={`Tactic pool: ${player.tacticalCC} command tokens`}
      >
        <CommandToken player={player} />
      </Pool>

      <Pool
        kind="fleet"
        label="Fleet"
        count={`${fleet}${edict > 0 ? "*" : ""}`}
        title={`Fleet pool: ${fleet} command tokens${edict > 0 ? ` (${edict} from Edict)` : ""}`}
        warn={fleetFull}
      >
        <span className={styles.ship} style={{ "--unit-fit": "84px" } as CSSProperties} aria-hidden="true">
          <Unit
            unitType="dn"
            colorAlias={getColorAlias(player.color)}
            faction={player.faction}
            scaleSprite
            showFactionTokens={false}
          />
        </span>
        {largestFleet !== null && (
          <span
            className={styles.fleetUse}
            title="Largest fleet (non-fighter ships in one system) vs. fleet pool tokens"
          >
            {fleetFull && <IconAlertTriangle size={12} aria-label="Fleet pool full" />}
            Largest {largestFleet}/{fleet}
          </span>
        )}
      </Pool>

      <p className={styles.motto} lang="la">
        Pax Magnifica Bellum Gloriosum
      </p>

      <div className={styles.bottom}>
        <Pool kind="tg" label="Trade goods" count={tg} title={`Trade goods: ${tg}`}>
          <img className={styles.tgIcon} src="/tg.png" alt="" />
        </Pool>
        <Pool
          kind="strategy"
          label="Strategy"
          count={player.strategicCC}
          title={`Strategy pool: ${player.strategicCC} command tokens`}
        >
          <CommandToken player={player} />
        </Pool>
      </div>

      {hasDebts && <DebtTokens debts={debts} compact />}

      {player.ccReinf !== undefined && (
        <p className={styles.reinforcements}>
          Reinforcements <b>{player.ccReinf}</b>/{COMMAND_TOKEN_SUPPLY} command tokens
        </p>
      )}
    </section>
  );
}

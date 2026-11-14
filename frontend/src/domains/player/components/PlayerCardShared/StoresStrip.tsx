import type { PlayerData } from "@/entities/data/types";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { FragmentsPool } from "@/domains/player/components/FragmentsPool";
import { DebtTokens } from "@/domains/player/components/DebtTokens";
import { EconomyGlyph } from "@/domains/player/components/ResourceInfluenceTable";
import styles from "./StoresStrip.module.css";

/** Dostępne / wszystkie (planety niewyczerpane / wszystkie) — pasek zasobów w nagłówku. */
export type StoresEconomy = {
  resources: { current: number; total: number };
  influence: { current: number; total: number };
};

type Props = {
  tg?: number | null;
  commodities?: number | null;
  commoditiesTotal?: number | null;
  acCount: number;
  pnCount: number;
  fragments: string[];
  debtTokens?: PlayerData["debtTokens"];
  tacticalCC: number;
  fleetCC: number;
  strategicCC: number;
  showCommandTokens?: boolean;
  /** Opcjonalnie resources/influence planet na początku paska (pasek zasobów). */
  economy?: StoresEconomy;
};

/** Stores as one row of keyed readouts, for the narrow Panels dossier. */
export function StoresStrip({
  tg,
  commodities,
  commoditiesTotal,
  acCount,
  pnCount,
  fragments,
  debtTokens,
  tacticalCC,
  fleetCC,
  strategicCC,
  showCommandTokens = true,
  economy,
}: Props) {
  const tradeGoods = tg ?? 0;
  const comms = commodities ?? 0;

  return (
    <div className={styles.strip}>
      {economy && (
        <>
          <span
            className={styles.sx}
            title={`${economy.resources.current} of ${economy.resources.total} resources available (unexhausted planets)`}
          >
            <EconomyGlyph kind="resource" />
            <b className={economy.resources.current === 0 ? styles.zero : undefined}>
              {economy.resources.current}
              <i>/{economy.resources.total}</i>
            </b>
          </span>
          <span
            className={styles.sx}
            title={`${economy.influence.current} of ${economy.influence.total} influence available (unexhausted planets)`}
          >
            <EconomyGlyph kind="influence" />
            <b className={economy.influence.current === 0 ? styles.zero : undefined}>
              {economy.influence.current}
              <i>/{economy.influence.total}</i>
            </b>
          </span>
        </>
      )}
      <span className={`${styles.sx} ${styles.tg}`} title={`${tradeGoods} trade goods`}>
        <img src="/tg.png" alt="" />
        <b className={tradeGoods === 0 ? styles.zero : undefined}>{tradeGoods}</b>
      </span>
      <span className={styles.sx} title={`${comms} of ${commoditiesTotal ?? 0} commodities`}>
        <img src="/comms.png" alt="" />
        <b className={comms === 0 ? styles.zero : undefined}>
          {comms}
          <i>/{commoditiesTotal ?? 0}</i>
        </b>
      </span>
      <span className={`${styles.sx} ${styles.card}`} title={`${acCount} action cards`}>
        <img src="/cardback/cardback_action.png" alt="" />
        <b>{acCount}</b>
      </span>
      <span className={`${styles.sx} ${styles.card}`} title={`${pnCount} promissory notes`}>
        <img src={assetUrl("/player_area/pa_cardbacks_pn.png")} alt="" />
        <b>{pnCount}</b>
      </span>
      {showCommandTokens && (
        <span
          className={`${styles.sx} ${styles.cc}`}
          title={`${tacticalCC} tactic · ${fleetCC} fleet · ${strategicCC} strategy`}
        >
          {tacticalCC}
          <em>T</em>
          {fleetCC}
          <em>F</em>
          {strategicCC}
          <em>S</em>
        </span>
      )}
      <FragmentsPool fragments={fragments} />
      {debtTokens && <DebtTokens debts={debtTokens} compact />}
    </div>
  );
}

import { useState } from "react";
import { IconCheck } from "@tabler/icons-react";
import { Switch } from "@/ds";
import type { ObjectivePaymentBody, ObjectiveSpend } from "@/entities/data/types";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getPlanetData } from "@/entities/lookup/planets";
import { PaymentPicker, paymentTotal } from "@/domains/strategy/PromptParts";
import { AutoButton } from "@/shared/ui/AutoButton/AutoButton";
import { Stepper } from "@/shared/ui/Stepper/Stepper";
import styles from "./ObjectiveSpendForm.module.css";

/*
 * Okno płatności za cel „Spend…" (RULES.md 41.4): gracz sam wskazuje, co wydaje - planety,
 * trade goods, pule żetonów, karty akcji, fragmenty reliktów. Startuje od podpowiedzi
 * silnika (`spend.suggested`). Formularz niczego nie rozstrzyga: legalność sprawdza backend (422).
 */

const FRAGMENT_NAMES: Record<string, string> = {
  c: "Cultural fragment",
  h: "Hazardous fragment",
  i: "Industrial fragment",
  u: "Frontier fragment",
};

const POOL_LABELS: Record<string, string> = {
  tactical: "Tactic",
  fleet: "Fleet",
  strategic: "Strategy",
};

const fragmentName = (id: string) => FRAGMENT_NAMES[id.charAt(0)] ?? id;
const planetName = (id: string) => getPlanetData(id)?.name ?? id;

function toggled(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
}

/** Chipy do wyboru dokładnie `goal` elementów (karty akcji / fragmenty). */
function PickChips({
  ids,
  picked,
  onToggle,
  label,
  busy,
}: {
  ids: string[];
  picked: string[];
  onToggle: (id: string) => void;
  label: (id: string) => string;
  busy: boolean;
}) {
  if (ids.length === 0) return <span className={styles.empty}>Nothing to choose from.</span>;
  return (
    <div className={styles.chips}>
      {ids.map((id) => (
        <button
          key={id}
          type="button"
          className={styles.chip}
          data-on={picked.includes(id) || undefined}
          aria-pressed={picked.includes(id)}
          disabled={busy}
          onClick={() => onToggle(id)}
        >
          {label(id)}
        </button>
      ))}
    </div>
  );
}

export function ObjectiveSpendForm({
  spend,
  busy,
  onConfirm,
}: {
  spend: ObjectiveSpend;
  busy: boolean;
  onConfirm: (payment: ObjectivePaymentBody) => void;
}) {
  const start = spend.suggested ?? {};
  const [planets, setPlanets] = useState<string[]>(start.planets ?? []);
  const [tradeGoods, setTradeGoods] = useState<number>(start.trade_goods ?? 0);
  const [resPlanets, setResPlanets] = useState<string[]>(start.resource_planets ?? []);
  const [infPlanets, setInfPlanets] = useState<string[]>(start.influence_planets ?? []);
  const [tokens, setTokens] = useState<Record<string, number>>(start.tokens ?? {});
  const [scepter, setScepter] = useState<boolean>(start.scepter ?? false);
  const [cards, setCards] = useState<string[]>(start.cards ?? []);
  const [fragments, setFragments] = useState<string[]>(start.fragments ?? []);

  const { goal, kind } = spend;
  let body: ObjectivePaymentBody = {};
  let ok = false;
  let summary = "";
  let controls: React.ReactNode = null;

  if (kind === "trade_goods") {
    body = { trade_goods: goal };
    ok = spend.tradeGoods >= goal;
    summary = `Spend ${goal} trade goods (you have ${spend.tradeGoods}).`;
  } else if (kind === "tokens") {
    const pools = spend.pools ?? {};
    const used = Object.values(tokens).reduce((n, v) => n + v, 0);
    // Scepter of Emelpar (C_relics): 1 żeton strategiczny schodzi z rezerwy zamiast z puli.
    const useScepter = Boolean(spend.scepter) && scepter;
    const available = (pool: string) =>
      (pools[pool] ?? 0) + (useScepter && pool === "strategic" ? 1 : 0);
    body = { tokens: Object.fromEntries(Object.entries(tokens).filter(([, v]) => v > 0)) };
    if (useScepter) body.scepter = true;
    ok = used === goal && (!useScepter || (tokens.strategic ?? 0) >= 1);
    summary = `Spend ${goal} command tokens from your pools: ${used}/${goal}.`;
    controls = (
      <div className={styles.pools}>
        {spend.suggested && (
          <AutoButton
            disabled={busy}
            onClick={() => {
              setTokens(start.tokens ?? {});
              setScepter(start.scepter ?? false);
            }}
          />
        )}
        {spend.scepter && (
          <Switch
            checked={scepter}
            onChange={(e) => setScepter(e.currentTarget.checked)}
            disabled={busy}
            label="Exhaust Scepter of Emelpar to spend a strategy token from your reinforcements instead"
          />
        )}
        {Object.keys(pools).map((pool) => {
          const value = tokens[pool] ?? 0;
          return (
            <div className={styles.poolRow} key={pool}>
              <span>
                {POOL_LABELS[pool] ?? pool} pool <small>now {pools[pool]}</small>
              </span>
              <Stepper
                bare
                value={value}
                max={Math.min(available(pool), value + (goal - used))}
                onChange={(next) => setTokens({ ...tokens, [pool]: next })}
                disabled={busy}
                label={`${POOL_LABELS[pool] ?? pool} tokens`}
              />
            </div>
          );
        })}
      </div>
    );
  } else if (kind === "resources" || kind === "influence") {
    const values = spend.planets ?? {};
    const total = paymentTotal(values, { planets, tradeGoods }, spend.tradeGoodValue ?? 1);
    body = { planets, trade_goods: tradeGoods };
    ok = total >= goal;
    summary = `Spend ${goal} ${kind}: ${total}/${goal}.`;
    controls = (
      <PaymentPicker
        values={values}
        tradeGoodsAvailable={spend.tradeGoods}
        tradeGoodValue={spend.tradeGoodValue ?? 1}
        value={{ planets, tradeGoods }}
        onChange={(next) => {
          setPlanets(next.planets);
          setTradeGoods(next.tradeGoods);
        }}
        unit={kind}
        busy={busy}
        target={goal}
      />
    );
  } else if (kind === "mixed") {
    const resValues = spend.resourcePlanets ?? {};
    const infValues = spend.influencePlanets ?? {};
    const res = resPlanets.reduce((n, id) => n + (resValues[id] ?? 0), 0);
    const inf = infPlanets.reduce((n, id) => n + (infValues[id] ?? 0), 0);
    // Braki wpływu/zasobów pokrywa TG po swojej wartości (Mirror Computing), wymóg TG — sztukami.
    const worth = spend.tradeGoodValue ?? 1;
    const neededTg =
      goal + Math.ceil(Math.max(0, goal - res) / worth) + Math.ceil(Math.max(0, goal - inf) / worth);
    body = { resource_planets: resPlanets, influence_planets: infPlanets, trade_goods: tradeGoods };
    ok = tradeGoods >= neededTg;
    summary =
      `Spend ${goal} resources (${res}), ${goal} influence (${inf}) and ${goal} trade goods. ` +
      `Trade goods needed: ${neededTg}, chosen: ${tradeGoods}.`;
    const ids = [...new Set([...Object.keys(resValues), ...Object.keys(infValues)])];
    controls = (
      <>
        {spend.suggested && (
          <AutoButton
            disabled={busy}
            onClick={() => {
              setResPlanets(start.resource_planets ?? []);
              setInfPlanets(start.influence_planets ?? []);
              setTradeGoods(start.trade_goods ?? 0);
            }}
          />
        )}
        <div className={styles.planetRows}>
          {ids.map((id) => (
            <div className={styles.planetRow} key={id}>
              <span>{planetName(id)}</span>
              <span className={styles.toggle}>
                <button
                  type="button"
                  className={styles.chip}
                  data-on={resPlanets.includes(id) || undefined}
                  disabled={busy || !(id in resValues)}
                  onClick={() => {
                    setInfPlanets(infPlanets.filter((x) => x !== id));
                    setResPlanets(toggled(resPlanets, id));
                  }}
                >
                  Resources {resValues[id] ?? 0}
                </button>
                <button
                  type="button"
                  className={styles.chip}
                  data-on={infPlanets.includes(id) || undefined}
                  disabled={busy || !(id in infValues)}
                  onClick={() => {
                    setResPlanets(resPlanets.filter((x) => x !== id));
                    setInfPlanets(toggled(infPlanets, id));
                  }}
                >
                  Influence {infValues[id] ?? 0}
                </button>
              </span>
            </div>
          ))}
          {ids.length === 0 && <span className={styles.empty}>No ready planets.</span>}
        </div>
        <div className={styles.poolRow}>
          <span>
            Trade goods <small>you have {spend.tradeGoods}</small>
          </span>
          <Stepper
            bare
            value={tradeGoods}
            max={spend.tradeGoods}
            onChange={setTradeGoods}
            disabled={busy}
            label="trade goods"
          />
        </div>
      </>
    );
  } else if (kind === "cards") {
    body = { cards };
    ok = cards.length === goal;
    summary = `Discard ${goal} action cards: ${cards.length}/${goal}.`;
    controls = (
      <PickChips
        ids={spend.cards ?? []}
        picked={cards}
        onToggle={(id) => setCards(toggled(cards, id))}
        label={(id) => getActionCard(id)?.name ?? id}
        busy={busy}
      />
    );
  } else {
    body = { fragments };
    ok = fragments.length === goal;
    summary = `Purge ${goal} relic fragments: ${fragments.length}/${goal}.`;
    controls = (
      <PickChips
        ids={spend.fragments ?? []}
        picked={fragments}
        onToggle={(id) => setFragments(toggled(fragments, id))}
        label={fragmentName}
        busy={busy}
      />
    );
  }

  return (
    <div className={styles.form}>
      <p className={styles.summary} data-ok={ok || undefined}>
        {summary}
      </p>
      {controls}
      <button
        type="button"
        className={styles.confirm}
        disabled={busy || !ok}
        onClick={() => onConfirm(body)}
      >
        <IconCheck size={15} aria-hidden="true" />
        <span>Pay and score</span>
      </button>
    </div>
  );
}

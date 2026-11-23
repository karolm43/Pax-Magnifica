import type { CSSProperties, ReactNode } from "react";
import { Button } from "@/ds";
import { getPlanetData } from "@/entities/lookup/planets";
import { PaymentTiles } from "@/domains/offers/PaymentTiles";
import { CommandPools } from "@/shared/ui/CommandPools/CommandPools";
import { autoPay } from "@/domains/technology/techModel";
import {
  splitTotal,
  type PoolSplit,
  type PromptPlayer,
} from "./strategyPrompt";
import styles from "./StrategyPrompt.module.css";

/** Oprawa okna karty: nagłówek z kolorem karty, treść i stopka z akcjami. */
export function PromptShell({
  hue,
  initiative,
  title,
  badge,
  subtitle,
  children,
  footer,
}: {
  hue: string;
  initiative: number;
  title: string;
  badge: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className={styles.shell} style={{ "--sc-hue": hue } as CSSProperties}>
      <div className={styles.head}>
        <span className={styles.disc}>{initiative}</span>
        <span className={styles.headText}>
          <span className={styles.headTitle}>{title}</span>
          {subtitle ? <span className={styles.headSub}>{subtitle}</span> : null}
        </span>
        <span className={styles.badge}>{badge}</span>
      </div>
      {children}
      {footer ? <div className={styles.footer}>{footer}</div> : null}
    </div>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <h4 className={styles.sectionTitle}>{title}</h4>
      {children}
    </section>
  );
}

export function Hint({ children }: { children: ReactNode }) {
  return <p className={styles.hint}>{children}</p>;
}

export type Payment = { planets: string[]; tradeGoods: number };

/**
 * Wybór płatności planetami (wyczerpanie karty) i trade goods — wspólny dla kart, które
 * każą coś wydać (Leadership: wpływ; Technology: zasoby). `values` = gotowe planety i ich
 * wartość z backendu; TG zastępują wpływ/zasób po `tradeGoodValue` (bazowo 1:1, R_trade_goods;
 * Mirror Computing 1:2 — RULES.md 62.8).
 */
export function PaymentPicker({
  values,
  tradeGoodsAvailable,
  value,
  onChange,
  unit,
  busy,
  tradeGoodValue = 1,
  target,
}: {
  values: Record<string, number>;
  tradeGoodsAvailable: number;
  tradeGoodValue?: number;
  value: Payment;
  onChange: (next: Payment) => void;
  unit: string;
  busy?: boolean;
  /** Kwota do zapłaty: przycisk „Auto” dobiera najtańszą płatność (planety, potem TG). */
  target?: number;
}) {
  const ids = Object.keys(values).sort((a, b) => values[b] - values[a] || a.localeCompare(b));
  const planets = ids.map((id) => ({
    id,
    value: id,
    label: getPlanetData(id)?.name ?? id,
    meta: { planet: id, value: values[id], valueKind: unit },
  }));
  const toggle = (id: string) =>
    onChange({
      ...value,
      planets: value.planets.includes(id)
        ? value.planets.filter((p) => p !== id)
        : [...value.planets, id],
    });
  return (
    <PaymentTiles
      unit={unit}
      planets={planets}
      picked={value.planets}
      onTogglePlanet={toggle}
      tradeGoods={value.tradeGoods}
      tradeGoodsMax={tradeGoodsAvailable}
      tradeGoodValue={tradeGoodValue}
      onTradeGoods={(tradeGoods) => onChange({ ...value, tradeGoods })}
      onAuto={
        target !== undefined && target > 0
          ? () => onChange(autoPay(values, [], tradeGoodsAvailable, target, tradeGoodValue))
          : undefined
      }
      disabled={busy}
    />
  );
}

/** Suma wartości wybranych planet + TG (``tgValue`` = wartość 1 TG; Mirror Computing: 2). */
export function paymentTotal(
  values: Record<string, number>,
  payment: Payment,
  tgValue = 1,
): number {
  return (
    payment.planets.reduce((sum, id) => sum + (values[id] ?? 0), 0) +
    payment.tradeGoods * tgValue
  );
}

/** Rozdział zdobytych żetonów dowodzenia po pulach (suma musi dać `total`); „Auto” = `auto`. */
export function PoolDistributor({
  total,
  value,
  onChange,
  player,
  busy,
  auto,
}: {
  total: number;
  value: PoolSplit;
  onChange: (next: PoolSplit) => void;
  player?: PromptPlayer;
  busy?: boolean;
  /** Podpowiedziany rozdział („Auto”); brak = bez przycisku. */
  auto?: PoolSplit;
}) {
  const used = splitTotal(value);
  return (
    <Section title="Place the command tokens in your pools">
      <CommandPools
        alloc={{ t: value.tactical, f: value.fleet, s: value.strategic }}
        total={total}
        disabled={busy}
        onChange={(next) => onChange({ tactical: next.t, fleet: next.f, strategic: next.s })}
        onAuto={auto ? () => onChange(auto) : undefined}
        current={{ t: player?.tacticalCC, f: player?.fleetCC, s: player?.strategicCC }}
      />
      <div className={styles.total} data-ok={used === total || undefined} data-bad={used !== total || undefined}>
        Placed <b>{used}</b> of <b>{total}</b>
      </div>
    </Section>
  );
}

/** Przycisk potwierdzenia z ujednoliconą stopką. */
export function ConfirmButton({
  children,
  onClick,
  disabled,
  icon,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  icon?: ReactNode;
}) {
  return (
    <Button disabled={disabled} leftSection={icon} onClick={onClick}>
      {children}
    </Button>
  );
}

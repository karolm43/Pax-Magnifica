import type { CSSProperties, ReactNode } from "react";
import { IconMinus, IconPlus, IconWand } from "@tabler/icons-react";
import { Button } from "@/ds";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
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

export function Stepper({
  value,
  min = 0,
  max,
  onChange,
  disabled,
  label,
}: {
  value: number;
  min?: number;
  max: number;
  onChange: (next: number) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <span className={styles.stepper}>
      <button
        type="button"
        className={styles.stepBtn}
        disabled={disabled || value <= min}
        onClick={() => onChange(value - 1)}
        aria-label={`Less ${label}`}
      >
        <IconMinus size={16} />
      </button>
      <b className={styles.stepVal}>{value}</b>
      <button
        type="button"
        className={styles.stepBtn}
        disabled={disabled || value >= max}
        onClick={() => onChange(value + 1)}
        aria-label={`More ${label}`}
      >
        <IconPlus size={16} />
      </button>
    </span>
  );
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
  const toggle = (id: string) =>
    onChange({
      ...value,
      planets: value.planets.includes(id)
        ? value.planets.filter((p) => p !== id)
        : [...value.planets, id],
    });
  return (
    <>
      {target !== undefined && target > 0 && (
        <Button
          variant="subtle"
          size="compact-sm"
          leftSection={<IconWand size={14} aria-hidden="true" />}
          disabled={busy}
          onClick={() => onChange(autoPay(values, [], tradeGoodsAvailable, target, tradeGoodValue))}
        >
          Auto
        </Button>
      )}
      <Section title={`Planets to exhaust (${unit})`}>
        {ids.length === 0 ? (
          <span className={styles.empty}>No ready planets.</span>
        ) : (
          <div className={styles.planets}>
            {ids.map((id) => (
              <div className={styles.planetSlot} key={id}>
                <PlanetCard
                  planetId={id}
                  picked={value.planets.includes(id)}
                  onPick={busy ? undefined : () => toggle(id)}
                />
                <span className={styles.planetValue}>
                  {values[id]} {unit}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>
      <div className={styles.row}>
        <span className={styles.rowLabel}>
          <img className={styles.tgIcon} src="/tg.png" alt="" aria-hidden="true" /> Trade goods
          <small>
            1 trade good = {tradeGoodValue} {unit} · you have {tradeGoodsAvailable}
          </small>
        </span>
        <Stepper
          value={value.tradeGoods}
          max={tradeGoodsAvailable}
          onChange={(tradeGoods) => onChange({ ...value, tradeGoods })}
          disabled={busy || tradeGoodsAvailable === 0}
          label="trade goods"
        />
      </div>
    </>
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

const POOL_LABELS: { key: keyof PoolSplit; label: string }[] = [
  { key: "tactical", label: "Tactic" },
  { key: "fleet", label: "Fleet" },
  { key: "strategic", label: "Strategy" },
];

/** Rozdział zdobytych żetonów dowodzenia po pulach (suma musi dać `total`). */
export function PoolDistributor({
  total,
  value,
  onChange,
  player,
  busy,
}: {
  total: number;
  value: PoolSplit;
  onChange: (next: PoolSplit) => void;
  player?: PromptPlayer;
  busy?: boolean;
}) {
  const used = splitTotal(value);
  const current: Record<keyof PoolSplit, number | undefined> = {
    tactical: player?.tacticalCC,
    fleet: player?.fleetCC,
    strategic: player?.strategicCC,
  };
  return (
    <Section title="Place the command tokens in your pools">
      {POOL_LABELS.map(({ key, label }) => (
        <div className={styles.row} key={key}>
          <span className={styles.rowLabel}>
            {label} pool
            {current[key] != null ? <small>now {current[key]}</small> : null}
          </span>
          <Stepper
            value={value[key]}
            max={value[key] + (total - used)}
            onChange={(next) => onChange({ ...value, [key]: next })}
            disabled={busy}
            label={`${label} tokens`}
          />
        </div>
      ))}
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

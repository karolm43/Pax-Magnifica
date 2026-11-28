import { IconCoins } from "@tabler/icons-react";
import type { ActionCardOption } from "@/api/useActionCard";
import { AutoButton } from "@/shared/ui/AutoButton/AutoButton";
import { Stepper } from "@/shared/ui/Stepper/Stepper";
import { Tile } from "./DecisionTiles";
import tileStyles from "./DecisionFields.module.css";
import styles from "./PaymentTiles.module.css";

/** Planeta do wyczerpania: opcja kafelka z `meta.value` (wartość do zapłaty). */
export type PaymentPlanet = ActionCardOption;

/**
 * JEDEN widżet płatności w całej grze (decyzja użytkownika, plan U2): kafelki planet z wartością,
 * licznik trade goods, pasek „zapłacono X / Y” (gdy znana kwota) i „Auto”. Adaptery:
 * `DecisionFields` (płatność z opisu backendu) i `PaymentPicker` (okna kart/technologii/ekspedycji).
 */
export function PaymentTiles({
  title,
  hint,
  cost,
  unit,
  planets,
  picked,
  onTogglePlanet,
  tradeGoods,
  tradeGoodsMin = 0,
  tradeGoodsMax,
  tradeGoodValue = 1,
  onTradeGoods,
  onAuto,
  paid,
  disabled,
}: {
  /** Nagłówek (domyślnie „Pay N unit” albo „Planets to exhaust (unit)”). */
  title?: string;
  hint?: string;
  /** Kwota do zapłaty — włącza pasek postępu. */
  cost?: number;
  /** „influence” / „resources” — jednostka wartości. */
  unit: string;
  planets: PaymentPlanet[];
  picked: string[];
  onTogglePlanet: (id: string) => void;
  tradeGoods: number;
  tradeGoodsMin?: number;
  tradeGoodsMax: number;
  /** Ile jednostek daje 1 trade good (bazowo 1; Mirror Computing 2). */
  tradeGoodValue?: number;
  onTradeGoods: (next: number) => void;
  /** „Auto” = najtańsza płatność; brak = bez przycisku. */
  onAuto?: () => void;
  /** Suma już wybrana (do paska). */
  paid?: number;
  disabled?: boolean;
}) {
  const bar = cost !== undefined && cost > 0 && paid !== undefined;
  return (
    <div className={styles.payment}>
      <div className={styles.head}>
        <span className={styles.title}>{title ?? (cost ? `Pay ${cost} ${unit}` : `Planets to exhaust (${unit})`)}</span>
        {onAuto && <AutoButton disabled={disabled} onClick={onAuto} />}
      </div>
      {hint && <p className={styles.hint}>{hint}</p>}
      {bar && (
        <div className={styles.bar} data-ok={paid >= cost || undefined} aria-live="polite">
          <span>
            Paid <b>{paid}</b> / {cost}
            {paid > cost ? " · overpaying" : ""}
          </span>
          <i aria-hidden="true">
            <em style={{ width: `${Math.min(100, (paid / Math.max(1, cost)) * 100)}%` }} />
          </i>
        </div>
      )}
      {planets.length > 0 ? (
        <div className={tileStyles.tiles}>
          {planets.map((option) => (
            <Tile
              key={option.id}
              option={option}
              multi
              selected={picked.includes(option.id)}
              disabled={!!disabled}
              onClick={() => onTogglePlanet(option.id)}
            />
          ))}
        </div>
      ) : (
        <p className={styles.hint}>No ready planets{tradeGoodsMax > 0 ? " — pay with trade goods." : "."}</p>
      )}
      {tradeGoodsMax > 0 && (
        <Stepper
          label="Trade goods"
          icon={<IconCoins size={16} aria-hidden="true" />}
          hint={tradeGoodValue !== 1 ? `1 trade good = ${tradeGoodValue} ${unit}` : undefined}
          value={tradeGoods}
          min={tradeGoodsMin}
          max={tradeGoodsMax}
          disabled={disabled}
          onChange={onTradeGoods}
        />
      )}
    </div>
  );
}

import { useState, type CSSProperties, type ReactNode } from "react";
import {
  IconArrowsExchange,
  IconCheck,
  IconCircleFilled,
  IconCoins,
  IconDoorExit,
  IconMinus,
  IconPlus,
  IconRefresh,
} from "@tabler/icons-react";
import { Button, Group } from "@/ds";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import {
  useBoardEditor,
  type TransactionSide,
  type TransactionTableView,
} from "@/api/useBoardEditor";
import {
  FragmentIcon,
  TradeCard,
  TradeSummary,
  isEmptySide,
  planetName,
} from "./transactionItems";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { playerRgb } from "@/domains/strategy/PlayerChip";
import { useMapPick } from "@/domains/strategy/mapPick";
import styles from "./TransactionModal.module.css";

/** Mała liczba z przyciskami −/+ (zakres min..max). */
export function Stepper({
  label,
  icon,
  value,
  max,
  min = 0,
  hint,
  disabled,
  onChange,
}: {
  label: string;
  icon: ReactNode;
  value: number;
  max: number;
  min?: number;
  /** Nadpisuje domyślny podpis „N available". */
  hint?: string;
  disabled?: boolean;
  onChange: (next: number) => void;
}) {
  return (
    <div className={styles.stepper}>
      <span className={styles.stepperLabel}>
        {icon}
        {label}
        <small>{hint ?? `${max} available`}</small>
      </span>
      <span className={styles.stepperCtl}>
        <button
          type="button"
          aria-label={`Less ${label}`}
          disabled={disabled || value <= min}
          onClick={() => onChange(value - 1)}
        >
          <IconMinus size={14} aria-hidden="true" />
        </button>
        <output aria-live="polite">{value}</output>
        <button
          type="button"
          aria-label={`More ${label}`}
          disabled={disabled || value >= max}
          onClick={() => onChange(value + 1)}
        >
          <IconPlus size={14} aria-hidden="true" />
        </button>
      </span>
    </div>
  );
}

/** Pusta strona stołu. */
export const EMPTY_SIDE: TransactionSide = {
  tradeGoods: 0,
  commodities: 0,
  promissoryNote: null,
  relicFragments: [],
  actionCards: [],
  planets: [],
  debtTokens: 0,
  tradeSecondary: false,
  wash: null,
};

type Props = {
  gameId: string;
  /** Ja — kładę wyłącznie własne rzeczy (widzę tylko swoją rękę). */
  me: PlayerData;
  partner: PlayerData;
  table: TransactionTableView;
  /** Planety, których kartę mogę oddać (Pride of Kenara). */
  myPlanets: string[];
};

/** Kolor gracza jako zmienna CSS ``--pc`` (obwódka miejsca i połowy stołu). */
const seatStyle = (player: PlayerData): CSSProperties =>
  ({ "--pc": playerRgb(player.color) }) as CSSProperties;

/** Nagłówek miejsca przy stole: kto to (logo + kolor jak na planszy) i czy dał Ready. */
function SeatHeader({
  player,
  label,
  ready,
}: {
  player: PlayerData;
  label: string;
  ready: boolean;
}) {
  return (
    <header className={styles.seatHead}>
      <small>{label}</small>
      <PlayerTag playerId={player.discordId} size={22} />
      {ready ? (
        <b className={styles.readyBadge}>
          <IconCheck size={12} aria-hidden="true" /> Ready
        </b>
      ) : (
        <span className={styles.notReady}>not ready</span>
      )}
    </header>
  );
}

/**
 * Stół transakcji (RULES.md 47.1b). Każda strona kładzie WYŁĄCZNIE własne rzeczy — rękę
 * partnera widać dopiero, gdy coś z niej wyłoży. Każda zmiana trafia od razu na stół (partner
 * widzi ją na żywo) i zdejmuje oba Ready; wymiana następuje, gdy obie strony dadzą Ready.
 * Żetony długu (47.3) to zwykły przedmiot na stole — z nie-sąsiadem tylko one. W kroku 3 Trade
 * (47.4) posiadacz karty kładzie „darmowe secondary", a drugi gracz cenę (dług / wash −N).
 */
/**
 * Pride of Kenara: dokąd przenieść własne jednostki z oddawanej planety - klik NA MAPIE na
 * świecącej planecie (decyzja użytkownika: nigdy lista planet), nie lista rozwijana.
 */
function UnitsDestination({
  current,
  choices,
  disabled,
  onPick,
}: {
  current: string;
  choices: string[];
  disabled: boolean;
  onPick: (planet: string) => void;
}) {
  const [picking, setPicking] = useState(false);
  useMapPick(
    "planet",
    choices,
    (target) => {
      onPick(target);
      setPicking(false);
    },
    { enabled: picking && !disabled, selected: current || null },
  );
  return (
    <span className={styles.tradeCardText}>
      Your units move to <b>{current ? planetName(current) : "—"}</b>{" "}
      <button
        type="button"
        className={styles.mapPickButton}
        aria-pressed={picking}
        disabled={disabled}
        onClick={() => setPicking((v) => !v)}
      >
        {picking ? "Click a glowing planet on the map…" : "Change on map"}
      </button>
    </span>
  );
}

export function TradingTable({ gameId, me, partner, table, myPlanets }: Props) {
  const { setTableSide, setTableReady, closeTable } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  const { data: myHand } = usePlayerHand(gameId, { ignoreAuthGate: true, player: me.discordId });
  const mine: TransactionSide = { ...EMPTY_SIDE, ...table.mine };
  const meId = me.discordId;
  const partnerId = partner.discordId;
  const partnerName = getPlayerFactionDisplayName(partner);

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn()
      .catch(() => undefined) // komunikat błędu pokazuje już useBoardEditor.post
      .finally(() => setBusy(false));
  };
  const put = (next: TransactionSide) => run(() => setTableSide(meId, partnerId, next));

  // Umowa Trade: komponenty i wash przejdą po uzupełnieniu (tylko z sąsiadem / Guild Ships).
  const tradeDeal = table.tradeHolder || table.tradePartner;
  const components = table.components || (tradeDeal && table.dealComponents);
  const myNotes = myHand?.promissoryNotes ?? [];
  const myCards = table.actionCards ? (myHand?.actionCards ?? []) : [];
  const fragments = me.relicFragmentCards ?? [];
  const planets = table.components ? myPlanets : [];
  const theirsEmpty = isEmptySide(table.theirs);

  const toggleFragment = (id: string) =>
    put({
      ...mine,
      relicFragments: mine.relicFragments.includes(id)
        ? mine.relicFragments.filter((f) => f !== id)
        : [...mine.relicFragments, id],
    });
  const toggleCard = (id: string) => {
    const picked = mine.actionCards ?? [];
    const at = picked.indexOf(id);
    put({
      ...mine,
      actionCards: at >= 0 ? picked.filter((_, i) => i !== at) : [...picked, id],
    });
  };
  const togglePlanet = (planet: string) => {
    const list = mine.planets ?? [];
    const entry = list.find((e) => e.split(">")[0] === planet);
    const others = (me.planets ?? []).filter((p) => p !== planet);
    put({
      ...mine,
      planets: entry
        ? list.filter((e) => e !== entry)
        : [...list, `${planet}>${others[0] ?? ""}`],
    });
  };

  return (
    <div className={styles.table} aria-label={`Trading table with ${partnerName}`}>
      {table.prefilled && (
        <p className={styles.notice}>
          <IconRefresh size={14} aria-hidden="true" />
          Your Trade deal, filled in after replenishing. It is not binding — both of you
          still confirm with Ready.
        </p>
      )}
      <div className={styles.board}>
        <section
          className={styles.seat}
          style={seatStyle(me)}
          aria-label="Your things"
        >
          <SeatHeader player={me} label="You" ready={table.myReady} />
          <span className={styles.seatHint}>Pick what you put on the table</span>
          {table.tradeHolder && (
            <button
              type="button"
              className={styles.dealToggle}
              aria-pressed={Boolean(mine.tradeSecondary)}
              disabled={busy}
              onClick={() => put({ ...mine, tradeSecondary: !mine.tradeSecondary })}
            >
              <IconRefresh size={15} aria-hidden="true" />
              Free Trade secondary
              <small>they replenish commodities without a command token</small>
            </button>
          )}
          {table.tradePartner && table.dealComponents && (
            <div className={styles.group}>
              <button
                type="button"
                className={styles.dealToggle}
                aria-pressed={mine.wash != null}
                disabled={busy}
                onClick={() => put({ ...mine, wash: mine.wash == null ? 1 : null })}
              >
                <IconArrowsExchange size={15} aria-hidden="true" />
                Wash after replenishing
                <small>all your commodities for their trade goods</small>
              </button>
              {mine.wash != null && (
                <Stepper
                  label="Wash discount"
                  icon={<IconCoins size={15} aria-hidden="true" />}
                  value={mine.wash}
                  max={9}
                  hint={`they give ${mine.wash} trade good${mine.wash === 1 ? "" : "s"} less`}
                  disabled={busy}
                  onChange={(v) => put({ ...mine, wash: v })}
                />
              )}
            </div>
          )}
          {components && (
            <>
              <Stepper
                label="Trade goods"
                icon={<IconCoins size={15} aria-hidden="true" />}
                value={mine.tradeGoods}
                max={Math.max(me.tg, mine.tradeGoods)}
                disabled={busy}
                onChange={(v) => put({ ...mine, tradeGoods: v })}
              />
              <Stepper
                label="Commodities"
                icon={<IconCoins size={15} aria-hidden="true" />}
                value={mine.commodities}
                max={Math.max(me.commodities, mine.commodities)}
                disabled={busy}
                onChange={(v) => put({ ...mine, commodities: v })}
              />
              <div className={styles.group}>
                <span className={styles.groupLabel}>
                  Promissory note <small>(max 1, from your hand)</small>
                </span>
                {myNotes.length === 0 ? (
                  <span className={styles.none}>No notes in hand</span>
                ) : (
                  <div className={styles.cardList}>
                    {myNotes.map((id) => (
                      <TradeCard
                        key={id}
                        kind="note"
                        id={id}
                        selected={mine.promissoryNote === id}
                        onToggle={() =>
                          put({
                            ...mine,
                            promissoryNote: mine.promissoryNote === id ? null : id,
                          })
                        }
                      />
                    ))}
                  </div>
                )}
              </div>
              {fragments.length > 0 && (
                <div className={styles.group}>
                  <span className={styles.groupLabel}>Relic fragments</span>
                  <div className={styles.chips}>
                    {fragments.map((f) => (
                      <button
                        key={f.id}
                        type="button"
                        className={styles.fragChip}
                        aria-pressed={mine.relicFragments.includes(f.id)}
                        data-selected={mine.relicFragments.includes(f.id) || undefined}
                        disabled={busy}
                        onClick={() => toggleFragment(f.id)}
                      >
                        <FragmentIcon id={f.id} />
                        {f.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {myCards.length > 0 && (
                <div className={styles.group}>
                  <span className={styles.groupLabel}>
                    Action cards <small>(Arbiters / Black Market Dealings)</small>
                  </span>
                  <div className={styles.cardList}>
                    {myCards.map((id, i) => (
                      <TradeCard
                        key={`${i}:${id}`}
                        kind="action"
                        id={id}
                        selected={(mine.actionCards ?? []).includes(id)}
                        onToggle={() => toggleCard(id)}
                      />
                    ))}
                  </div>
                </div>
              )}
              {planets.length > 0 && (
                <div className={styles.group}>
                  <span className={styles.groupLabel}>
                    Planet cards <small>(Pride of Kenara)</small>
                  </span>
                  {planets.map((planet) => {
                    const entry = (mine.planets ?? []).find((e) => e.split(">")[0] === planet);
                    const others = (me.planets ?? []).filter((p) => p !== planet);
                    return (
                      <div
                        key={planet}
                        className={styles.tradeCard}
                        data-selected={entry ? true : undefined}
                      >
                        <label className={styles.tradeCardHead}>
                          <input
                            type="checkbox"
                            checked={Boolean(entry)}
                            disabled={busy || others.length === 0}
                            onChange={() => togglePlanet(planet)}
                          />
                          <b>{planetName(planet)}</b>
                        </label>
                        {entry && (
                          <UnitsDestination
                            current={entry.split(">")[1] ?? ""}
                            choices={others}
                            disabled={busy}
                            onPick={(target) =>
                              put({
                                ...mine,
                                planets: (mine.planets ?? []).map((x) =>
                                  x === entry ? `${planet}>${target}` : x,
                                ),
                              })
                            }
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
          <Stepper
            label="Debt tokens"
            icon={<IconCircleFilled size={13} aria-hidden="true" />}
            value={mine.debtTokens ?? 0}
            max={20}
            hint="your tokens as a promise (table custom)"
            disabled={busy}
            onChange={(v) => put({ ...mine, debtTokens: v })}
          />
          {!components && (
            <span className={styles.none}>
              {tradeDeal
                ? `${partnerName} is not your neighbor — agree on debt tokens.`
                : "No transaction with this player now — only debt tokens."}
            </span>
          )}
        </section>
        <section className={styles.center} aria-label="On the table">
          <h4 className={styles.centerTitle}>On the table</h4>
          <div className={styles.half} style={seatStyle(me)}>
            <span className={styles.halfWho}>
              <PlayerTag playerId={meId} size={16} /> gives
            </span>
            <TradeSummary title="You give" side={mine} issuerColor={me.color} />
          </div>
          <IconArrowsExchange className={styles.swap} size={22} aria-hidden="true" />
          <div className={styles.half} style={seatStyle(partner)}>
            <span className={styles.halfWho}>
              <PlayerTag playerId={partnerId} size={16} /> gives
            </span>
            <TradeSummary
              title={`${partnerName} gives`}
              side={table.theirs}
              issuerColor={partner.color}
            />
          </div>
        </section>
        <section
          className={styles.seat}
          style={seatStyle(partner)}
          aria-label={`${partnerName}'s seat`}
        >
          <SeatHeader player={partner} label="Partner" ready={table.theirReady} />
          <span className={styles.seatHint}>
            {theirsEmpty
              ? "Their hand stays hidden until they put something on the table."
              : "What they put down is shown on the table."}
          </span>
          <dl className={styles.seatStats}>
            <dt>Trade goods</dt>
            <dd>{partner.tg ?? 0}</dd>
            <dt>Commodities</dt>
            <dd>
              {partner.commodities ?? 0}/{partner.commoditiesTotal ?? 0}
            </dd>
          </dl>
        </section>
      </div>
      <Group justify="space-between" gap="sm">
        <Button
          variant="default"
          disabled={busy}
          leftSection={<IconDoorExit size={16} />}
          onClick={() => run(() => closeTable(meId, partnerId))}
        >
          Leave the table
        </Button>
        {table.myReady ? (
          <Button
            variant="default"
            disabled={busy}
            onClick={() => run(() => setTableReady(meId, partnerId, false))}
          >
            Not ready — waiting for {partnerName}
          </Button>
        ) : (
          <Button
            disabled={busy || (isEmptySide(mine) && theirsEmpty)}
            leftSection={<IconCheck size={16} />}
            onClick={() => run(() => setTableReady(meId, partnerId, true))}
          >
            Ready
          </Button>
        )}
      </Group>
    </div>
  );
}

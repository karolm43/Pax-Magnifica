import { useState, type CSSProperties } from "react";
import {
  IconArrowsExchange,
  IconCircleFilled,
  IconCoins,
  IconHandStop,
  IconMinus,
  IconPlus,
  IconDiamond,
  IconInfoCircle,
} from "@tabler/icons-react";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import type { PlayerData } from "@/entities/data/types";
import {
  useBoardEditor,
  useTransactionState,
  type TransactionSide,
} from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import { TradeCard, TradeSummary, isEmptySide, planetName } from "./transactionItems";
import styles from "./TransactionModal.module.css";

type Tab = "trade" | "promises";

const EMPTY_SIDE: TransactionSide = {
  tradeGoods: 0,
  commodities: 0,
  promissoryNote: null,
  relicFragments: [],
  actionCards: [],
};

type Props = {
  opened: boolean;
  onClose: () => void;
  gameId: string;
  /** Aktywny gracz (ten, którego jest tura) — strona „You". */
  me: PlayerData;
  /** Wszyscy posadzeni gracze (partnerzy wybierani spośród nich). */
  players: PlayerData[];
  /** Czy wolno teraz rozstrzygać transakcje (faza akcji + tura gracza). */
  canTrade: boolean;
};

/** Mała liczba z przyciskami −/+ (zakres 0..max). */
function Stepper({
  label,
  icon,
  value,
  max,
  hint,
  onChange,
}: {
  label: string;
  icon: React.ReactNode;
  value: number;
  max: number;
  /** Nadpisuje domyślny podpis „N available" (np. dla żetonów bez zasobu). */
  hint?: string;
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
          disabled={value <= 0}
          onClick={() => onChange(value - 1)}
        >
          <IconMinus size={14} aria-hidden="true" />
        </button>
        <output aria-live="polite">{value}</output>
        <button
          type="button"
          aria-label={`More ${label}`}
          disabled={value >= max}
          onClick={() => onChange(value + 1)}
        >
          <IconPlus size={14} aria-hidden="true" />
        </button>
      </span>
    </div>
  );
}

/** Żeton obietnicy w barwie wystawcy (do N kropek + „×N" przy większej liczbie). */
function PromiseDots({ color, count }: { color: string; count: number }) {
  const rgb = resolvePrimaryRgb(color);
  const style = rgb
    ? ({ "--tk": `${rgb.red}, ${rgb.green}, ${rgb.blue}` } as CSSProperties)
    : undefined;
  const shown = Math.min(count, 8);
  return (
    <span className={styles.dots} style={style} aria-label={`${count} tokens`}>
      {Array.from({ length: shown }, (_, i) => (
        <IconCircleFilled key={i} size={13} aria-hidden="true" />
      ))}
      {count > shown && <b>×{count}</b>}
    </span>
  );
}

function PlayerPick({
  player,
  selected,
  disabled,
  note,
  onPick,
}: {
  player: PlayerData;
  selected: boolean;
  disabled?: boolean;
  note?: string;
  onPick: () => void;
}) {
  return (
    <button
      type="button"
      className={styles.pick}
      data-selected={selected || undefined}
      disabled={disabled}
      onClick={onPick}
    >
      {player.faction && (
        <CircularFactionIcon faction={player.faction} size={22} />
      )}
      <span>{getPlayerFactionDisplayName(player)}</span>
      {note && <small>{note}</small>}
    </button>
  );
}

/**
 * Transakcje między graczami (RULES.md 47) + nieformalne żetony długu (debt).
 *
 * Dwie zakładki:
 *  - „Transaction": do jednej transakcji z każdym SĄSIADEM w turze (Guild Ships / Trade Convoys:
 *    także z nie-sąsiadem) — oddaję TG/commodities, jedną promissory note, fragmenty reliktów
 *    i (Arbiters / Black Market Dealings) karty akcji, w zamian dostaję to samo od partnera.
 *    Notki i karty pokazują pełny tekst. To PROPOZYCJA: wymiana następuje, gdy partner ją
 *    przyjmie (RULES.md 47.1a, okno ``TransactionOfferPrompt``); do tego czasu można ją wycofać.
 *    Reguły egzekwuje backend (422 z powodem).
 *  - „Debt tokens": zwyczajowe żetony kontroli jako niewiążące długi — bez sąsiedztwa.
 */
export function TransactionModal({
  opened,
  onClose,
  gameId,
  me,
  players,
  canTrade,
}: Props) {
  const {
    proposeTransaction,
    cancelTransaction,
    giveDebtTokens,
    returnDebtTokens,
  } = useBoardEditor();
  const { data: gameState } = useGameState(gameId);
  const [tab, setTab] = useState<Tab>("trade");
  const [busy, setBusy] = useState(false);
  const [partnerId, setPartnerId] = useState<string | null>(null);
  const [give, setGive] = useState<TransactionSide>(EMPTY_SIDE);
  const [receive, setReceive] = useState<TransactionSide>(EMPTY_SIDE);
  const [promisePartnerId, setPromisePartnerId] = useState<string | null>(null);
  const [promiseCount, setPromiseCount] = useState(1);

  const others = players.filter((p) => p.discordId !== me.discordId);
  // Partnerzy z silnika (sąsiedzi + Guild Ships / Trade Convoys, flaga kart akcji). Odświeżenie
  // wymusza publiczny skrót propozycji i sąsiedztwo z web-data.
  const offerStamp = JSON.stringify([
    gameState?.transactionOffer ?? null,
    me.neighbors,
    me.transactedWith ?? [],
  ]);
  const { data: tradeState } = useTransactionState(offerStamp);
  const partnerViews = tradeState?.partners;
  const neighbors = partnerViews
    ? others.filter((p) => partnerViews.some((v) => v.playerId === p.discordId))
    : others.filter((p) => me.neighbors.includes(p.color));
  const viewOf = (id: string | null) =>
    partnerViews?.find((v) => v.playerId === id) ?? null;
  const done = new Set(me.transactedWith ?? []);
  const partner = neighbors.find((p) => p.discordId === partnerId) ?? null;
  const cardsAllowed = viewOf(partnerId)?.actionCards ?? false;
  const myOffer =
    tradeState?.offer && tradeState.offer.proposer === me.discordId
      ? tradeState.offer
      : null;
  const offerPartner = myOffer
    ? (players.find((p) => p.discordId === myOffer.partner) ?? null)
    : null;
  const promisePartner =
    others.find((p) => p.discordId === promisePartnerId) ?? null;

  // Ręce (promissory notes): moja i partnera. Tryb lokalny — operator widzi wszystko.
  const { data: myHand } = usePlayerHand(gameId, {
    ignoreAuthGate: true,
    player: me.discordId,
  });
  const { data: partnerHand } = usePlayerHand(gameId, {
    ignoreAuthGate: true,
    player: partner?.discordId ?? null,
  });
  const myNotes = myHand?.promissoryNotes ?? [];
  const partnerNotes = partner ? (partnerHand?.promissoryNotes ?? []) : [];
  const myCards = cardsAllowed ? (myHand?.actionCards ?? []) : [];
  // Pride of Kenara: planety, których kartę strona może oddać (z mechem Hacan).
  const myTradePlanets = tradeState?.myPlanets ?? [];
  const partnerTradePlanets = viewOf(partnerId)?.planets ?? [];
  const partnerCards =
    cardsAllowed && partner ? (partnerHand?.actionCards ?? []) : [];
  const myFragments = me.relicFragmentCards ?? [];
  const partnerFragments = partner?.relicFragmentCards ?? [];

  const canConfirm =
    canTrade &&
    partner != null &&
    myOffer == null &&
    !(isEmptySide(give) && isEmptySide(receive));

  const reset = () => {
    setGive(EMPTY_SIDE);
    setReceive(EMPTY_SIDE);
  };
  const pickPartner = (id: string) => {
    setPartnerId(id);
    reset();
  };
  const run = (fn: () => Promise<void>, after?: () => void) => {
    if (busy) return;
    setBusy(true);
    void fn()
      .then(after)
      .catch(() => undefined) // komunikat błędu pokazuje już useBoardEditor.post
      .finally(() => setBusy(false));
  };

  const toggleFragment = (
    side: TransactionSide,
    set: (s: TransactionSide) => void,
    id: string,
  ) =>
    set({
      ...side,
      relicFragments: side.relicFragments.includes(id)
        ? side.relicFragments.filter((f) => f !== id)
        : [...side.relicFragments, id],
    });

  const toggleCard = (
    side: TransactionSide,
    set: (s: TransactionSide) => void,
    index: number,
    id: string,
  ) => {
    // Karty mogą się powtarzać (kopie) — zaznaczamy po indeksie w ręce, wysyłamy identyfikatory.
    const key = `${index}:${id}`;
    const picked = side.actionCards ?? [];
    set({
      ...side,
      actionCards: picked.includes(key)
        ? picked.filter((c) => c !== key)
        : [...picked, key],
    });
  };
  // ``actionCards`` w formularzu trzyma klucze ``indeks:id``; do silnika idą same identyfikatory.
  const forEngine = (side: TransactionSide): TransactionSide => ({
    ...side,
    actionCards: (side.actionCards ?? []).map((k) => k.slice(k.indexOf(":") + 1)),
  });

  const renderSide = (
    title: string,
    owner: PlayerData,
    side: TransactionSide,
    set: (s: TransactionSide) => void,
    notes: string[],
    fragments: { id: string; name: string }[],
    cards: string[],
    tradePlanets: string[],
    /** Moja strona: cel jednostek wybieram ja; stronę partnera wskazuje on przy akceptacji. */
    chooseDestination: boolean,
  ) => (
    <section className={styles.side} aria-label={title}>
      <h4 className={styles.sideTitle}>
        {title}
        <small>{getPlayerFactionDisplayName(owner)}</small>
      </h4>
      <Stepper
        label="Trade goods"
        icon={<IconCoins size={15} aria-hidden="true" />}
        value={side.tradeGoods}
        max={owner.tg}
        onChange={(v) => set({ ...side, tradeGoods: v })}
      />
      <Stepper
        label="Commodities"
        icon={<IconCoins size={15} aria-hidden="true" />}
        value={side.commodities}
        max={owner.commodities}
        onChange={(v) => set({ ...side, commodities: v })}
      />
      <div className={styles.group}>
        <span className={styles.groupLabel}>
          Promissory note <small>(max 1)</small>
        </span>
        {notes.length === 0 ? (
          <span className={styles.none}>No notes in hand</span>
        ) : (
          <div className={styles.cardList}>
            {notes.map((id) => (
              <TradeCard
                key={id}
                kind="note"
                id={id}
                selected={side.promissoryNote === id}
                onToggle={() =>
                  set({
                    ...side,
                    promissoryNote: side.promissoryNote === id ? null : id,
                  })
                }
              />
            ))}
          </div>
        )}
      </div>
      <div className={styles.group}>
        <span className={styles.groupLabel}>Relic fragments</span>
        {fragments.length === 0 ? (
          <span className={styles.none}>No fragments</span>
        ) : (
          <div className={styles.chips}>
            {fragments.map((f) => (
              <button
                key={f.id}
                type="button"
                className={styles.fragChip}
                data-selected={side.relicFragments.includes(f.id) || undefined}
                onClick={() => toggleFragment(side, set, f.id)}
              >
                <IconDiamond size={13} aria-hidden="true" />
                {f.name}
              </button>
            ))}
          </div>
        )}
      </div>
      {tradePlanets.length > 0 && (
        <div className={styles.group}>
          <span className={styles.groupLabel}>
            Planet cards <small>(Pride of Kenara)</small>
          </span>
          <div className={styles.cardList}>
            {tradePlanets.map((planet) => {
              const entry = (side.planets ?? []).find(
                (e) => e === planet || e.startsWith(`${planet}>`),
              );
              const others = (owner.planets ?? []).filter((p) => p !== planet);
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
                      disabled={others.length === 0}
                      onChange={() =>
                        set({
                          ...side,
                          planets: entry
                            ? (side.planets ?? []).filter((e) => e !== entry)
                            : [
                                ...(side.planets ?? []),
                                chooseDestination ? `${planet}>${others[0]}` : planet,
                              ],
                        })
                      }
                    />
                    <b>{planetName(planet)}</b>
                  </label>
                  {entry && !chooseDestination && (
                    <span className={styles.tradeCardText}>
                      Their units move to a planet they choose when accepting.
                    </span>
                  )}
                  {entry && chooseDestination && (
                    <label className={styles.tradeCardText}>
                      Units move to{" "}
                      <select
                        value={entry.split(">")[1]}
                        onChange={(e) =>
                          set({
                            ...side,
                            planets: (side.planets ?? []).map((x) =>
                              x === entry ? `${planet}>${e.target.value}` : x,
                            ),
                          })
                        }
                      >
                        {others.map((p) => (
                          <option key={p} value={p}>
                            {planetName(p)}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {cardsAllowed && (
        <div className={styles.group}>
          <span className={styles.groupLabel}>
            Action cards <small>(Arbiters)</small>
          </span>
          {cards.length === 0 ? (
            <span className={styles.none}>No action cards to show</span>
          ) : (
            <div className={styles.cardList}>
              {cards.map((id, i) => (
                <TradeCard
                  key={`${i}:${id}`}
                  kind="action"
                  id={id}
                  selected={(side.actionCards ?? []).includes(`${i}:${id}`)}
                  onToggle={() => toggleCard(side, set, i, id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );

  // --- Zakładka obietnic: stan stołu ---
  const heldByMe = Object.entries(me.debtTokens ?? {});
  const myTokensElsewhere = others
    .map((o) => ({ holder: o, count: o.debtTokens?.[me.color] ?? 0 }))
    .filter((e) => e.count > 0);
  const issuerOf = (color: string) => players.find((p) => p.color === color);

  return (
    <AppModal
      floating
      minimizable
      opened={opened}
      onClose={onClose}
      title="Transaction"
      size={760}
    >
      <Stack gap="md">
        <div className={styles.tabs} role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "trade"}
            className={styles.tab}
            data-active={tab === "trade" || undefined}
            onClick={() => setTab("trade")}
          >
            <IconArrowsExchange size={16} aria-hidden="true" />
            Transaction
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "promises"}
            className={styles.tab}
            data-active={tab === "promises" || undefined}
            onClick={() => setTab("promises")}
          >
            <IconCircleFilled size={14} aria-hidden="true" />
            Debt tokens
            {heldByMe.length + myTokensElsewhere.length > 0 && (
              <b className={styles.tabBadge}>
                {heldByMe.reduce((n, [, c]) => n + c, 0) +
                  myTokensElsewhere.reduce((n, e) => n + e.count, 0)}
              </b>
            )}
          </button>
        </div>

        {tab === "trade" && (
          <>
            <Text size="sm" c="dimmed">
              One transaction per neighbor each turn, any time during your turn
              (even in combat). You make an offer — nothing changes hands until
              the other player accepts it. Commodities you hand over become trade
              goods for the receiver. It does not have to be even — and once
              accepted it can't be undone.
            </Text>

            {!canTrade && (
              <p className={styles.notice}>
                <IconInfoCircle size={14} aria-hidden="true" />
                Transactions are resolved on the active player's turn in the
                action phase.
              </p>
            )}

            <div className={styles.picks} role="group" aria-label="Neighbors">
              {neighbors.length === 0 ? (
                <span className={styles.none}>
                  You have no neighbors right now — you need a unit or planet in
                  or next to a system where they have one.
                </span>
              ) : (
                neighbors.map((p) => (
                  <PlayerPick
                    key={p.discordId}
                    player={p}
                    selected={p.discordId === partnerId}
                    disabled={done.has(p.color)}
                    note={
                      done.has(p.color)
                        ? "done this turn"
                        : viewOf(p.discordId)?.neighbor === false
                          ? "not a neighbor"
                          : undefined
                    }
                    onPick={() => pickPartner(p.discordId)}
                  />
                ))
              )}
            </div>

            {myOffer && (
              <div className={styles.waiting} role="status">
                <span className={styles.waitingHead}>
                  <IconArrowsExchange size={16} aria-hidden="true" />
                  Waiting for{" "}
                  <b>
                    {offerPartner
                      ? getPlayerFactionDisplayName(offerPartner)
                      : myOffer.partner}
                  </b>{" "}
                  to accept your offer.
                </span>
                {myOffer.give && myOffer.receive && (
                  <div className={styles.summaryPair}>
                    <TradeSummary title="You give" side={myOffer.give} />
                    <TradeSummary title="You receive" side={myOffer.receive} />
                  </div>
                )}
                <Group justify="flex-end">
                  <Button
                    variant="default"
                    disabled={busy}
                    onClick={() => run(() => cancelTransaction(me.discordId))}
                  >
                    Withdraw offer
                  </Button>
                </Group>
              </div>
            )}

            {partner && !myOffer && (
              <div className={styles.sides}>
                {renderSide(
                  "You give",
                  me,
                  give,
                  setGive,
                  myNotes,
                  myFragments,
                  myCards,
                  myTradePlanets,
                  true,
                )}
                <IconArrowsExchange
                  className={styles.swap}
                  size={26}
                  aria-hidden="true"
                />
                {renderSide(
                  "You receive",
                  partner,
                  receive,
                  setReceive,
                  partnerNotes,
                  partnerFragments,
                  partnerCards,
                  partnerTradePlanets,
                  false,
                )}
              </div>
            )}

            <Group justify="flex-end" gap="sm">
              <Button variant="default" disabled={busy} onClick={onClose}>
                Cancel
              </Button>
              <Button
                disabled={busy || !canConfirm}
                leftSection={<IconArrowsExchange size={16} />}
                onClick={() =>
                  partner &&
                  run(
                    () =>
                      proposeTransaction({
                        partnerId: partner.discordId,
                        give: forEngine(give),
                        receive: forEngine(receive),
                      }),
                    () => {
                      reset();
                      setPartnerId(null);
                    },
                  )
                }
              >
                Offer the deal
              </Button>
            </Group>
          </>
        )}

        {tab === "promises" && (
          <>
            <Text size="sm" c="dimmed">
              Table custom, not a rule: hand over small control tokens as a
              non-binding promise (3 trade goods owed = 3 tokens). No neighbors
              needed. The tokens go back when the debt is settled.
            </Text>

            <div className={styles.picks} role="group" aria-label="Players">
              {others.map((p) => (
                <PlayerPick
                  key={p.discordId}
                  player={p}
                  selected={p.discordId === promisePartnerId}
                  onPick={() => setPromisePartnerId(p.discordId)}
                />
              ))}
            </div>

            {promisePartner && (
              <div className={styles.promiseBox}>
                <Stepper
                  label="Tokens"
                  icon={<IconCircleFilled size={13} aria-hidden="true" />}
                  value={promiseCount}
                  max={20}
                  hint="one per trade good owed"
                  onChange={(v) => setPromiseCount(Math.max(1, v))}
                />
                <Group gap="sm">
                  <Button
                    disabled={busy || promiseCount < 1}
                    onClick={() =>
                      run(() =>
                        giveDebtTokens(
                          me.discordId,
                          promisePartner.discordId,
                          promiseCount,
                        ),
                      )
                    }
                  >
                    I promise — give {promiseCount} of mine
                  </Button>
                  <Button
                    variant="default"
                    disabled={busy || promiseCount < 1}
                    onClick={() =>
                      run(() =>
                        giveDebtTokens(
                          promisePartner.discordId,
                          me.discordId,
                          promiseCount,
                        ),
                      )
                    }
                  >
                    They promise — take {promiseCount} of theirs
                  </Button>
                </Group>
              </div>
            )}

            <div className={styles.ledger}>
              <h4 className={styles.sideTitle}>Tokens you hold</h4>
              {heldByMe.length === 0 ? (
                <span className={styles.none}>
                  Nobody owes you anything on the table.
                </span>
              ) : (
                heldByMe.map(([color, count]) => {
                  const issuer = issuerOf(color);
                  if (!issuer) return null;
                  return (
                    <div key={color} className={styles.ledgerRow}>
                      <PromiseDots color={color} count={count} />
                      <span className={styles.ledgerWho}>
                        {getPlayerFactionDisplayName(issuer)} owes you
                      </span>
                      <Button
                        size="xs"
                        variant="default"
                        disabled={busy}
                        onClick={() =>
                          run(() =>
                            returnDebtTokens(me.discordId, issuer.discordId, 1),
                          )
                        }
                      >
                        Return 1
                      </Button>
                      <Button
                        size="xs"
                        variant="default"
                        disabled={busy}
                        leftSection={<IconHandStop size={14} />}
                        onClick={() =>
                          run(() =>
                            returnDebtTokens(
                              me.discordId,
                              issuer.discordId,
                              count,
                            ),
                          )
                        }
                      >
                        Return all
                      </Button>
                    </div>
                  );
                })
              )}

              <h4 className={styles.sideTitle}>Your tokens held by others</h4>
              {myTokensElsewhere.length === 0 ? (
                <span className={styles.none}>You owe nothing.</span>
              ) : (
                myTokensElsewhere.map(({ holder, count }) => (
                  <div key={holder.discordId} className={styles.ledgerRow}>
                    <PromiseDots color={me.color} count={count} />
                    <span className={styles.ledgerWho}>
                      You owe {getPlayerFactionDisplayName(holder)}
                    </span>
                    <Button
                      size="xs"
                      variant="default"
                      disabled={busy}
                      onClick={() =>
                        run(() =>
                          returnDebtTokens(holder.discordId, me.discordId, 1),
                        )
                      }
                    >
                      Repaid 1
                    </Button>
                    <Button
                      size="xs"
                      variant="default"
                      disabled={busy}
                      onClick={() =>
                        run(() =>
                          returnDebtTokens(
                            holder.discordId,
                            me.discordId,
                            count,
                          ),
                        )
                      }
                    >
                      Repaid all
                    </Button>
                  </div>
                ))
              )}
            </div>

            <Group justify="flex-end">
              <Button variant="default" onClick={onClose}>
                Close
              </Button>
            </Group>
          </>
        )}
      </Stack>
    </AppModal>
  );
}

import { useState } from "react";
import { IconBolt, IconX } from "@tabler/icons-react";
import { Button, NumberInput, Tooltip } from "@/ds";
import type { PlayerData } from "@/entities/data/types";
import { useBoostActions, useBoosts, type BoostRow } from "@/api/useBoosts";
import { LeaderChip } from "@/domains/player/components/Leader/LeaderChip";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import holdStyles from "./HoldControls.module.css";
import styles from "./BoostsButton.module.css";
import { ToolHint } from "./ToolHint";

/*
 * "Boosts" (RULES.md 54.15): other players' cooperative agents you could get RIGHT NOW (Captain
 * Mendosa when you activate, Trilossa Aun Mirik when you produce, Viscount Unlenn in your
 * combat...). They never interrupt anyone: the button appears only while something is available
 * or a request of yours is open. Asking may include a payment; the owner accepts or declines, or
 * their standing offer accepts at once. The payment and the effect resolve together - a binding
 * deal - and nothing is paid when it is declined or lapses.
 */

function leaderId(source: string): string | null {
  const [category, id] = source.split(":");
  return category === "leaders" && id ? id : null;
}

function BoostItem({ row, me, busy, onRequest }: {
  row: BoostRow;
  me: PlayerData;
  busy: boolean;
  onRequest: (tradeGoods: number, commodities: number) => void;
}) {
  // "Auto" = the owner's standing price paid in trade goods (0 when free or when asking).
  const auto = row.mode === "standing" && !row.free ? (row.price ?? 0) : 0;
  const [tg, setTg] = useState<number | null>(null);
  const [comm, setComm] = useState(0);
  const tradeGoods = tg ?? Math.min(auto, me.tg ?? 0);
  const paid = tradeGoods + comm;
  const covered = row.mode === "standing" && (row.free || paid >= (row.price ?? 0));
  const leader = leaderId(row.source);
  return (
    <li className={styles.item}>
      <div className={styles.itemHead}>
        {leader ? (
          <LeaderChip id={leader} type="agent" exhausted={false} locked={false} active={false} playerId={row.owner} />
        ) : null}
        <div className={styles.itemText}>
          <b>{row.name}</b>
          <small>
            <PlayerTag playerId={row.owner} size={14} />
            {row.mode === "standing"
              ? row.free
                ? " · free for you"
                : ` · standing offer: ${row.price ?? 0}`
              : " · asks the owner"}
          </small>
        </div>
      </div>
      {row.text && <p className={styles.text}>{row.text}</p>}
      {row.pending ? (
        <p className={styles.waiting}>Waiting for the owner…</p>
      ) : (
        <div className={styles.pay}>
          {row.payable ? (
            <>
              <NumberInput
                label="Trade goods"
                size="xs"
                min={0}
                max={me.tg ?? 0}
                disabled={busy}
                value={tradeGoods}
                onChange={(v) => setTg(typeof v === "number" ? v : 0)}
              />
              <NumberInput
                label="Commodities"
                size="xs"
                min={0}
                max={me.commodities ?? 0}
                disabled={busy}
                value={comm}
                onChange={(v) => setComm(typeof v === "number" ? v : 0)}
              />
              <Button size="xs" variant="subtle" disabled={busy} onClick={() => { setTg(null); setComm(0); }}>
                Auto
              </Button>
            </>
          ) : (
            <small className={styles.note}>
              No payment possible now (not neighbours, or you already traded this turn) - ask for
              free.
            </small>
          )}
          <Button size="xs" disabled={busy} onClick={() => onRequest(row.payable ? tradeGoods : 0, row.payable ? comm : 0)}>
            {covered ? "Take the offer" : paid > 0 ? `Ask, paying ${paid}` : "Ask for free"}
          </Button>
        </div>
      )}
    </li>
  );
}

export function BoostsButton({ player }: { player: PlayerData }) {
  const me = player.discordId ?? null;
  const { data } = useBoosts(me);
  const actions = useBoostActions();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const available = data?.available ?? [];
  const outgoing = data?.outgoing ?? [];
  // Contextual: nothing to request and nothing open = no button at all.
  if (!me || (available.length === 0 && outgoing.length === 0)) return null;

  const run = (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    fn()
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <Tooltip
        position="top"
        multiline
        maw={300}
        disabled={open}
        label={
          <ToolHint title="Boosts" status={`${available.length} available now`}>
            Other players&apos; agents that could help you right now. Ask for one, optionally
            offering trade goods - nobody is interrupted unless you ask.
          </ToolHint>
        }
      >
        <button
          type="button"
          className={holdStyles.toolBtn}
          data-tone="boost"
          data-open={open || undefined}
          aria-expanded={open}
          aria-label={`Boosts: ${available.length} available`}
          onClick={() => setOpen((v) => !v)}
        >
          <IconBolt size={15} aria-hidden="true" />
          <span className={holdStyles.toolLabel}>Boosts</span>
          <b className={styles.count}>{available.length}</b>
        </button>
      </Tooltip>

      {open && (
        <aside className={holdStyles.panel} aria-label="Available boosts">
          <header className={holdStyles.head}>
            <b>Available boosts</b>
            <button
              type="button"
              className={holdStyles.close}
              aria-label="Close"
              onClick={() => setOpen(false)}
            >
              <IconX size={14} aria-hidden="true" />
            </button>
          </header>
          <p className={holdStyles.note}>
            Accepted = paid and used in the same moment. Declined or unanswered = nothing is paid.
          </p>
          {outgoing.length > 0 && (
            <ul className={styles.list} aria-label="Your requests">
              {outgoing.map((deal) => (
                <li key={deal.offerId} className={styles.item}>
                  <span>
                    <b>{deal.name}</b> from <PlayerTag playerId={deal.owner} size={14} />
                    {deal.tradeGoods + deal.commodities > 0
                      ? ` · offering ${deal.tradeGoods + deal.commodities}`
                      : " · for free"}
                  </span>
                  <Button
                    size="xs"
                    variant="default"
                    disabled={busy}
                    onClick={() => run(() => actions.withdraw(me, deal.offerId))}
                  >
                    Withdraw
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <ul className={styles.list} aria-label="Boosts you can ask for">
            {available.map((row) => (
              <BoostItem
                key={row.id}
                row={row}
                me={player}
                busy={busy}
                onRequest={(tg, comm) => run(() => actions.request(me, row.id, tg, comm))}
              />
            ))}
          </ul>
          {error && <p className={styles.error} role="alert">{error}</p>}
        </aside>
      )}
    </>
  );
}

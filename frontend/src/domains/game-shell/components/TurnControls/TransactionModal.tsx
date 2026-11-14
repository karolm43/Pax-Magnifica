import { useState } from "react";
import { IconHandStop } from "@tabler/icons-react";
import { Button, Group, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import { useBoardEditor, useTransactionState } from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import { PromiseDots } from "./transactionItems";
import { TradingTable } from "./TradingTable";
import styles from "./TransactionModal.module.css";

type Props = {
  opened: boolean;
  onClose: () => void;
  gameId: string;
  /** Ja — gracz przy tym ekranie (kładę własne rzeczy). */
  me: PlayerData;
  /** Wszyscy posadzeni gracze (partnerzy wybierani spośród nich). */
  players: PlayerData[];
};

/** Publiczny skrót stołów z web-data — odświeża widok, gdy ktoś coś położy. */
export function useTableStamp(gameId: string, extra: unknown[] = []): string {
  const { data: gameState } = useGameState(gameId);
  return JSON.stringify([gameState?.transactionTables ?? [], ...extra]);
}

function PlayerPick({
  player,
  selected,
  note,
  onPick,
}: {
  player: PlayerData;
  selected: boolean;
  note?: string;
  onPick: () => void;
}) {
  return (
    <button
      type="button"
      className={styles.pick}
      data-selected={selected || undefined}
      aria-pressed={selected}
      onClick={onPick}
    >
      {player.faction && <CircularFactionIcon faction={player.faction} size={22} />}
      <span>{getPlayerFactionDisplayName(player)}</span>
      {note && <small>{note}</small>}
    </button>
  );
}

/**
 * Transakcje między graczami (RULES.md 47.1b) — STÓŁ. Wybierasz gracza i siadasz z nim do
 * stołu; każdy kładzie wyłącznie swoje rzeczy (rękę partnera widać dopiero, gdy coś wyłoży),
 * wymiana następuje po Ready obu stron. Do stołu może usiąść każda strona; z nie-sąsiadem
 * (albo poza turą aktywnego) na stole lądują tylko żetony długu (47.3). Niżej rejestr długów.
 */
export function TransactionModal({ opened, onClose, gameId, me, players }: Props) {
  const { openTable, returnDebtTokens } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  const [partnerId, setPartnerId] = useState<string | null>(null);
  const stamp = useTableStamp(gameId, [me.neighbors, me.transactedWith ?? []]);
  const { data: tradeState } = useTransactionState(stamp, me.discordId);

  const others = players.filter((p) => p.discordId !== me.discordId);
  const tables = tradeState?.tables ?? [];
  const tableWith = (id: string) => tables.find((t) => t.partner === id) ?? null;
  const viewOf = (id: string) =>
    tradeState?.partners.find((v) => v.playerId === id) ?? null;
  // Domyślnie pierwszy stół, przy którym już siedzę (np. ktoś mnie zaprosił).
  const selectedId = partnerId ?? tables[0]?.partner ?? null;
  const partner = others.find((p) => p.discordId === selectedId) ?? null;
  const table = selectedId ? tableWith(selectedId) : null;

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn()
      .catch(() => undefined) // komunikat błędu pokazuje już useBoardEditor.post
      .finally(() => setBusy(false));
  };
  const pick = (id: string) => {
    setPartnerId(id);
    if (!tableWith(id)) run(() => openTable(me.discordId, id));
  };
  const noteFor = (id: string): string | undefined => {
    const view = viewOf(id);
    if (tableWith(id)) return "at the table";
    if (view?.done) return "traded this turn";
    if (view && !view.components) return "debt only";
    return undefined;
  };

  // --- Rejestr długów (żetony 47.3) ---
  const heldByMe = Object.entries(me.debtTokens ?? {});
  const myTokensElsewhere = others
    .map((o) => ({ holder: o, count: o.debtTokens?.[me.color] ?? 0 }))
    .filter((e) => e.count > 0);
  const issuerOf = (color: string) => players.find((p) => p.color === color);

  return (
    <AppModal floating minimizable opened={opened} onClose={onClose} title="Transaction" size={780}>
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Sit down at the table with another player. Each of you puts down only your own
          things — you see theirs once they put them on the table. The deal happens when
          both of you are Ready; any change clears Ready. One transaction per neighbor each
          active player's turn. With anyone else only debt tokens (a promise) can go on the
          table.
        </Text>

        <div className={styles.picks} role="group" aria-label="Players">
          {others.map((p) => (
            <PlayerPick
              key={p.discordId}
              player={p}
              selected={p.discordId === selectedId}
              note={noteFor(p.discordId)}
              onPick={() => pick(p.discordId)}
            />
          ))}
        </div>

        {partner && table && (
          <TradingTable
            gameId={gameId}
            me={me}
            partner={partner}
            table={table}
            myPlanets={tradeState?.myPlanets ?? []}
          />
        )}

        <div className={styles.ledger}>
          <h4 className={styles.sideTitle}>Debt tokens you hold</h4>
          {heldByMe.length === 0 ? (
            <span className={styles.none}>Nobody owes you anything on the table.</span>
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
                    onClick={() => run(() => returnDebtTokens(me.discordId, issuer.discordId, 1))}
                  >
                    Return 1
                  </Button>
                  <Button
                    size="xs"
                    variant="default"
                    disabled={busy}
                    leftSection={<IconHandStop size={14} />}
                    onClick={() =>
                      run(() => returnDebtTokens(me.discordId, issuer.discordId, count))
                    }
                  >
                    Return all
                  </Button>
                </div>
              );
            })
          )}
          <h4 className={styles.sideTitle}>Your debt tokens held by others</h4>
          {myTokensElsewhere.length === 0 ? (
            <span className={styles.none}>You owe nothing.</span>
          ) : (
            myTokensElsewhere.map(({ holder, count }) => (
              <div key={holder.discordId} className={styles.ledgerRow}>
                <PromiseDots color={me.color} count={count} />
                <span className={styles.ledgerWho}>
                  You owe {getPlayerFactionDisplayName(holder)}
                </span>
              </div>
            ))
          )}
        </div>

        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Close
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}

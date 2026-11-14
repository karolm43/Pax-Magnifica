import { useState } from "react";
import { useParams } from "react-router-dom";
import { IconArrowsExchange, IconCheck } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useBoardEditor, useTransactionState } from "@/api/useBoardEditor";
import { usePlayerData } from "@/api/usePlayerData";
import {
  EMPTY_SIDE,
  TradingTable,
} from "@/domains/game-shell/components/TurnControls/TradingTable";
import { useTableStamp } from "@/domains/game-shell/components/TurnControls/TransactionModal";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import { PlayerChip } from "../PlayerChip";
import styles from "../StrategyPrompt.module.css";
import type { PrimaryViewProps } from "./types";

/*
 * Trade (RULES.md 30.6, 47.4): +3 trade goods i uzupełnienie commodities dzieją się same;
 * aktywny gracz wybiera, kto robi secondary ZA DARMO. Wybór można zwyczajnie zaznaczyć albo
 * WYNEGOCJOWAĆ przy stole transakcji: posiadacz kładzie „darmowe secondary", drugi gracz cenę
 * (żetony długu, „wash −N" po uzupełnieniu). Gracze z zawartą umową są wskazani na pewno.
 * Wskazani rozstrzygają secondary AUTOMATYCZNIE (bez okna i bez żetonu).
 */
export function TradePrimary({ shell, players, owner, busy, submit }: PrimaryViewProps) {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const [chosen, setChosen] = useState<string[]>([]);
  const [talking, setTalking] = useState<string | null>(null);
  const { openTable, setTableSide } = useBoardEditor();
  const ownerId = owner?.discordId ?? null;
  const stamp = useTableStamp(gameId);
  const { data: tradeState } = useTransactionState(stamp, ownerId);
  const { data: webData } = usePlayerData(gameId);
  const others = players.filter((p) => p.discordId !== ownerId);
  const deals = tradeState?.dealPlayers ?? [];
  const tableWith = (id: string) => tradeState?.tables.find((t) => t.partner === id) ?? null;
  const dataOf = (id: string | null) =>
    webData?.playerData?.find((p) => p.discordId === id) ?? null;
  const toggle = (id: string) =>
    setChosen((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  const negotiate = (id: string) => {
    if (!ownerId) return;
    setTalking(id);
    if (tableWith(id)) return;
    void openTable(ownerId, id)
      .then(() => setTableSide(ownerId, id, { ...EMPTY_SIDE, tradeSecondary: true }))
      .catch(() => undefined); // powód 422 pokazuje panel komunikatów
  };
  const picked = [...new Set([...chosen, ...deals])];
  const meData = dataOf(ownerId);
  const partnerData = dataOf(talking);
  const table = talking ? tableWith(talking) : null;
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="+3 trade goods, replenish commodities"
      footer={
        <ConfirmButton
          disabled={busy}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ players: chosen.filter((id) => !deals.includes(id)) })}
        >
          {picked.length === 0 ? "Choose nobody" : `Confirm (${picked.length})`}
        </ConfirmButton>
      }
    >
      <Hint>
        You gain <b>3 trade goods</b> and replenish your commodities. Choose the players who
        replenish their commodities <b>for free</b> — or <b>negotiate</b> a price at the
        trading table: debt tokens, or a <b>wash</b> after they replenish (their commodities
        for your trade goods, minus a cut). A wash is not binding — after replenishing the
        table opens filled in and you both confirm it.
      </Hint>
      <Section title="Replenish for free">
        <div className={styles.chips}>
          {others.map((p) => {
            const deal = deals.includes(p.discordId);
            return (
              <span key={p.discordId} className={styles.chipRow}>
                <PlayerChip
                  player={p}
                  selected={picked.includes(p.discordId)}
                  disabled={busy || deal}
                  onClick={() => toggle(p.discordId)}
                  badge={deal ? "deal" : chosen.includes(p.discordId) ? "free" : undefined}
                />
                {!deal && (
                  <button
                    type="button"
                    className={styles.ghostBtn}
                    aria-pressed={talking === p.discordId}
                    disabled={busy}
                    onClick={() => negotiate(p.discordId)}
                  >
                    <IconArrowsExchange size={14} aria-hidden="true" /> Negotiate
                  </button>
                )}
              </span>
            );
          })}
        </div>
      </Section>
      {table && meData && partnerData && (
        <Section title="Trading table">
          <TradingTable
            gameId={gameId}
            me={meData}
            partner={partnerData}
            table={table}
            myPlanets={tradeState?.myPlanets ?? []}
          />
        </Section>
      )}
    </PromptShell>
  );
}

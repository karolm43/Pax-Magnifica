import { useState } from "react";
import { useParams } from "react-router-dom";
import { IconArrowsExchange, IconCheck } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useBoardEditor, useTransactionState } from "@/api/useBoardEditor";
import { usePlayerData } from "@/api/usePlayerData";
import {
  TradeSummary,
  isEmptySide,
} from "@/domains/game-shell/components/TurnControls/transactionItems";
import { TransactionModal } from "@/domains/game-shell/components/TurnControls/TransactionModal";
import type { GameState } from "@/entities/data/types";
import styles from "./AbilityPrompts.module.css";

/*
 * Zaproszenie do stołu transakcji (RULES.md 47.1b): wyskakuje SAMO u gracza, z którym ktoś usiadł
 * do stołu (albo gdy silnik otworzył stół z umowy Trade po uzupełnieniu — 47.4). Pokazuje, co
 * partner już położył, i otwiera to samo okno stołu co przycisk Transaction.
 */
export function TransactionOfferPrompt({
  gameState,
  handOwners,
  nameOf,
}: {
  gameState: GameState | undefined;
  /** Ludzie przy tym ekranie (sieć: tylko ja; lokalnie: wszyscy ludzie). */
  handOwners: string[];
  nameOf: (playerId: string) => string;
}) {
  const invites = (gameState?.transactionTables ?? []).filter(
    (t) => handOwners.includes(t.partner) || (t.prefilled && handOwners.includes(t.opener)),
  );
  // Kto jest zaproszony (właściciel ręki przy ekranie) -> przez kogo.
  const invited = new Map<string, string[]>();
  for (const t of invites) {
    const owner = handOwners.includes(t.partner) ? t.partner : t.opener;
    const from = owner === t.partner ? t.opener : t.partner;
    invited.set(owner, [...(invited.get(owner) ?? []), from]);
  }
  return (
    <>
      {[...invited].map(([owner, from]) => (
        <OwnerInvites
          key={owner}
          owner={owner}
          from={from}
          stamp={JSON.stringify(gameState?.transactionTables ?? [])}
          nameOf={nameOf}
          several={handOwners.length > 1}
        />
      ))}
    </>
  );
}

function OwnerInvites({
  owner,
  from: inviters,
  stamp,
  nameOf,
  several,
}: {
  owner: string;
  /** Partnerzy, którzy zaprosili (albo stół z umowy Trade). */
  from: string[];
  stamp: string;
  nameOf: (playerId: string) => string;
  several: boolean;
}) {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: tradeState } = useTransactionState(stamp, owner);
  const { data: webData } = usePlayerData(gameId);
  const { closeTable } = useBoardEditor();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const players = (webData?.playerData ?? []).filter((p) => p.faction && p.faction !== "neutral");
  const me = players.find((p) => p.discordId === owner);
  const tables = (tradeState?.tables ?? []).filter((t) => inviters.includes(t.partner));
  if (!me || tables.length === 0) return null;
  const leave = (partner: string) => {
    if (busy) return;
    setBusy(true);
    void closeTable(owner, partner)
      .catch(() => undefined) // powód 422 pokazuje panel komunikatów
      .finally(() => setBusy(false));
  };
  return (
    <>
      {tables.map((t) => {
        const from = nameOf(t.partner);
        return (
          <section key={t.partner} className={styles.card} aria-label={`Trading table with ${from}`}>
            <header className={styles.head}>
              <IconArrowsExchange size={16} aria-hidden="true" className={styles.icon} />
              <span className={styles.titleBox}>
                <small className={styles.kind}>
                  {t.prefilled ? "Trade deal · wash" : "Trading table"}
                  {several ? ` · for ${nameOf(owner)}` : ""}
                </small>
                <b className={styles.title}>
                  {t.prefilled
                    ? `Confirm your Trade deal with ${from}`
                    : `${from} sat down to trade with you`}
                </b>
              </span>
            </header>
            {!isEmptySide(t.theirs) && (
              <TradeSummary
                title={`${from} puts down${t.theirReady ? " · Ready" : ""}`}
                side={t.theirs}
                issuerColor={t.partnerColor ?? undefined}
              />
            )}
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.ghost}
                disabled={busy}
                onClick={() => leave(t.partner)}
              >
                Leave
              </button>
              <button type="button" className={styles.primary} onClick={() => setOpen(true)}>
                <IconCheck size={14} aria-hidden="true" /> Open the table
              </button>
            </div>
          </section>
        );
      })}
      {open && (
        <TransactionModal
          opened
          onClose={() => setOpen(false)}
          gameId={gameId}
          me={me}
          players={players}
        />
      )}
    </>
  );
}

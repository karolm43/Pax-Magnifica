import { useState } from "react";
import { IconArrowsExchange } from "@tabler/icons-react";
import { useBoardEditor, useTransactionState } from "@/api/useBoardEditor";
import { TradeSummary } from "@/domains/game-shell/components/TurnControls/transactionItems";
import type { GameState } from "@/entities/data/types";
import styles from "./AbilityPrompts.module.css";

/*
 * Propozycja transakcji dla PARTNERA (RULES.md 47.1a): wymiana nie dzieje się bez jego zgody.
 * Okno wyskakuje samo u gracza, któremu złożono ofertę, z pełną treścią (notki i karty akcji
 * z tekstem) i przyciskami Accept / Decline. Proponujący widzi oczekiwanie w oknie transakcji.
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
  const pub = gameState?.transactionOffer ?? null;
  const partner = pub && handOwners.includes(pub.partner) ? pub.partner : null;
  const { data } = useTransactionState(JSON.stringify(pub), partner);
  const { respondTransaction } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  const offer = data?.offer;
  if (!partner || !offer || offer.partner !== partner || !offer.give || !offer.receive) {
    return null;
  }
  const answer = (accept: boolean) => {
    if (busy) return;
    setBusy(true);
    void respondTransaction(partner, accept)
      .catch(() => undefined) // powód 422 pokazuje panel komunikatów
      .finally(() => setBusy(false));
  };
  const from = nameOf(offer.proposer);
  return (
    <section className={styles.card} aria-label={`Deal offered by ${from}`}>
      <header className={styles.head}>
        <IconArrowsExchange size={16} aria-hidden="true" className={styles.icon} />
        <span className={styles.titleBox}>
          <small className={styles.kind}>
            Transaction offer
            {handOwners.length > 1 ? ` · for ${nameOf(partner)}` : ""}
          </small>
          <b className={styles.title}>{from} offers you a deal</b>
        </span>
      </header>
      {/* Strony z perspektywy partnera: dostaje „give” proponującego, oddaje jego „receive”. */}
      <TradeSummary title="You receive" side={offer.give} />
      <TradeSummary title="You give" side={offer.receive} />
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.ghost}
          disabled={busy}
          onClick={() => answer(false)}
        >
          Decline
        </button>
        <button
          type="button"
          className={styles.primary}
          disabled={busy}
          onClick={() => answer(true)}
        >
          Accept deal
        </button>
      </div>
    </section>
  );
}

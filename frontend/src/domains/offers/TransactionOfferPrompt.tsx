import { useState } from "react";
import { IconArrowsExchange } from "@tabler/icons-react";
import { useBoardEditor, useTransactionState } from "@/api/useBoardEditor";
import {
  TradeSummary,
  planetName,
} from "@/domains/game-shell/components/TurnControls/transactionItems";
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
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const offer = data?.offer;
  if (!partner || !offer || offer.partner !== partner || !offer.give || !offer.receive) {
    return null;
  }
  // Pride of Kenara: cel moich jednostek z oddawanej planety wybieram ja (domyślnie pierwszy).
  const destinations = Object.entries(offer.unitDestinations ?? {});
  const destOf = (planet: string, options: string[]) => chosen[planet] ?? options[0] ?? "";
  const answer = (accept: boolean) => {
    if (busy) return;
    setBusy(true);
    const picked = Object.fromEntries(destinations.map(([p, opts]) => [p, destOf(p, opts)]));
    void respondTransaction(partner, accept, accept ? picked : {})
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
      {destinations.map(([planet, options]) => (
        <label key={planet} className={styles.text}>
          Your units on {planetName(planet)} move to{" "}
          <select
            value={destOf(planet, options)}
            onChange={(e) => setChosen({ ...chosen, [planet]: e.target.value })}
          >
            {options.map((p) => (
              <option key={p} value={p}>
                {planetName(p)}
              </option>
            ))}
          </select>
        </label>
      ))}
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

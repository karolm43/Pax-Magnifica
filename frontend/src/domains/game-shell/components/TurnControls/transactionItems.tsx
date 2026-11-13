import {
  IconCards,
  IconCoins,
  IconDiamond,
  IconFileText,
  IconPlanet,
} from "@tabler/icons-react";
import { getPlanetData } from "@/entities/lookup/planets";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { useFactionColors } from "@/hooks/useFactionColors";
import type { TransactionSide } from "@/api/useBoardEditor";
import styles from "./TransactionModal.module.css";

/*
 * Elementy transakcji z PEŁNYM tekstem (RULES.md 47.1a): gracz musi wiedzieć, co robi notka albo
 * karta akcji, zanim ją odda lub przyjmie. Wspólne dla okna transakcji i okna zgody partnera.
 */

type CardKind = "note" | "action";

/** Nazwa i tekst notki / karty akcji z danych (assety AsyncTI4). */
export function useTradeCardInfo() {
  const colors = useFactionColors();
  return (kind: CardKind, id: string): { name: string; text: string; owner?: string } => {
    if (kind === "note") {
      const note = getPromissoryNoteData(id, colors);
      return {
        name: note?.displayName || id,
        text: note?.noteData.text ?? "",
        owner: note?.faction,
      };
    }
    const card = getActionCard(id);
    const text = card ? [card.window, card.text].filter(Boolean).join(" ") : "";
    return { name: card?.name ?? id, text };
  };
}

/** Karta do wyboru (albo tylko do odczytu, gdy brak ``onToggle``) z nazwą i pełnym tekstem. */
export function TradeCard({
  kind,
  id,
  selected,
  onToggle,
}: {
  kind: CardKind;
  id: string;
  selected?: boolean;
  onToggle?: () => void;
}) {
  const info = useTradeCardInfo()(kind, id);
  const Icon = kind === "note" ? IconFileText : IconCards;
  const body = (
    <>
      <span className={styles.tradeCardHead}>
        <Icon size={13} aria-hidden="true" />
        <b>{info.name}</b>
        {info.owner && <small>{info.owner}</small>}
      </span>
      {info.text && <span className={styles.tradeCardText}>{info.text}</span>}
    </>
  );
  if (!onToggle) {
    return (
      <div className={styles.tradeCard} data-kind={kind}>
        {body}
      </div>
    );
  }
  return (
    <button
      type="button"
      className={styles.tradeCard}
      data-kind={kind}
      data-selected={selected || undefined}
      aria-pressed={selected}
      aria-label={`${kind === "note" ? "Promissory note" : "Action card"}: ${info.name}`}
      onClick={onToggle}
    >
      {body}
    </button>
  );
}

/** Nazwa planety z danych (id, gdy brak). */
export const planetName = (id: string | undefined): string =>
  (id ? getPlanetData(id)?.name : undefined) ?? id ?? "";

/** Czy strona nic nie oddaje. */
export function isEmptySide(s: TransactionSide): boolean {
  return (
    s.tradeGoods === 0 &&
    s.commodities === 0 &&
    s.promissoryNote === null &&
    s.relicFragments.length === 0 &&
    (s.actionCards ?? []).length === 0 &&
    (s.planets ?? []).length === 0
  );
}

/** Podsumowanie jednej strony (do okna zgody): zasoby + karty z tekstem. */
export function TradeSummary({
  title,
  side,
  fragmentName,
}: {
  title: string;
  side: TransactionSide;
  fragmentName?: (id: string) => string;
}) {
  const goods = [
    side.tradeGoods > 0 && `${side.tradeGoods} trade good${side.tradeGoods === 1 ? "" : "s"}`,
    side.commodities > 0 &&
      `${side.commodities} commodit${side.commodities === 1 ? "y" : "ies"} (become trade goods)`,
  ].filter(Boolean);
  return (
    <section className={styles.summary} aria-label={title}>
      <h5 className={styles.summaryTitle}>{title}</h5>
      {isEmptySide(side) && <span className={styles.none}>Nothing</span>}
      {goods.length > 0 && (
        <span className={styles.summaryGoods}>
          <IconCoins size={14} aria-hidden="true" />
          {goods.join(", ")}
        </span>
      )}
      {side.relicFragments.map((f, i) => (
        <span key={`${f}-${i}`} className={styles.summaryGoods}>
          <IconDiamond size={13} aria-hidden="true" />
          {fragmentName?.(f) ?? f}
        </span>
      ))}
      {(side.planets ?? []).map((entry) => {
        const [planet, dest] = entry.split(">");
        return (
          <span key={entry} className={styles.summaryGoods}>
            <IconPlanet size={13} aria-hidden="true" />
            Planet {planetName(planet)} (units move to {planetName(dest)})
          </span>
        );
      })}
      {side.promissoryNote && <TradeCard kind="note" id={side.promissoryNote} />}
      {(side.actionCards ?? []).map((c, i) => (
        <TradeCard key={`${c}-${i}`} kind="action" id={c} />
      ))}
    </section>
  );
}

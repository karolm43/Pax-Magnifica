import { useState } from "react";
import {
  IconCards,
  IconCheck,
  IconCoins,
  IconDiamond,
  IconPlanet,
  IconPlus,
} from "@tabler/icons-react";
import { getPlanetData } from "@/entities/lookup/planets";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { useFactionColors } from "@/hooks/useFactionColors";
import type { TransactionSide } from "@/api/useBoardEditor";
import { PromissoryNote } from "@/domains/player/components/PromissoryNote";
import { ActionCardDetailsCard } from "@/domains/cards/components/ActionCardDetailsCard";
import {
  ObjectLabel,
  ObjectShell,
} from "@/domains/player/components/silhouettes/ObjectShell";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { assetUrl } from "@/shared/assets/resolveAsset";
import styles from "./TransactionModal.module.css";

/*
 * Elementy transakcji (RULES.md 47.1a). Notki i karty akcji to TE SAME chipy co w panelu gracza
 * (``PromissoryNote``) i w ręce: nazwa + znak wystawcy, pełny tekst karty dopiero po kliknięciu
 * (popover z kartą). Wybór do transakcji = osobny przycisk obok chipa. Wspólne dla okna
 * transakcji i okna zgody partnera.
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

/** Chip karty akcji: nazwa w ramce obiektu, pełna karta w popoverze po kliknięciu. */
function ActionCardChip({ id }: { id: string }) {
  const [opened, setOpened] = useState(false);
  const name = getActionCard(id)?.name ?? id;
  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <ObjectShell
          className={styles.acChip}
          label={`${name} · action card`}
          onClick={() => setOpened((o) => !o)}
        >
          <IconCards size={14} aria-hidden="true" />
          <ObjectLabel>{name}</ObjectLabel>
        </ObjectShell>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <ActionCardDetailsCard actionCardId={id} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

/**
 * Notka / karta akcji w transakcji: chip jak w panelu gracza (klik = pełny opis), a przy
 * wyborze (``onToggle``) obok przycisk "Add" / "In deal".
 */
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
  const chip =
    kind === "note" ? <PromissoryNote promissoryNoteId={id} /> : <ActionCardChip id={id} />;
  return (
    <div className={styles.tradePick} data-selected={selected || undefined}>
      {chip}
      {onToggle && (
        <button
          type="button"
          className={styles.pickBtn}
          aria-pressed={selected}
          aria-label={`${selected ? "Remove from deal" : "Add to deal"}: ${info.name}`}
          onClick={onToggle}
        >
          {selected ? (
            <>
              <IconCheck size={13} aria-hidden="true" /> In deal
            </>
          ) : (
            <>
              <IconPlus size={13} aria-hidden="true" /> Add
            </>
          )}
        </button>
      )}
    </div>
  );
}

/** Sprite fragmentu reliktu (jak ``FragmentStack`` w panelu gracza); id z prefiksem typu. */
export function FragmentIcon({ id }: { id: string }) {
  const type = id.slice(0, 3);
  if (!["crf", "hrf", "irf", "urf"].includes(type)) {
    return <IconDiamond size={13} aria-hidden="true" />;
  }
  return (
    <img
      className={styles.fragIcon}
      src={assetUrl(`/player_area/pa_fragment_${type}.png`)}
      alt=""
      loading="lazy"
    />
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
          <FragmentIcon id={f} />
          {fragmentName?.(f) ?? f}
        </span>
      ))}
      {(side.planets ?? []).map((entry) => {
        const [planet, dest] = entry.split(">");
        return (
          <span key={entry} className={styles.summaryGoods}>
            <IconPlanet size={13} aria-hidden="true" />
            Planet {planetName(planet)}
            {dest ? ` (units move to ${planetName(dest)})` : " (owner picks where units move)"}
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

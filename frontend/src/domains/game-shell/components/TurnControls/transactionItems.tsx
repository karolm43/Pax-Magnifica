import { useState, type CSSProperties } from "react";
import {
  IconArrowsExchange,
  IconCards,
  IconCheck,
  IconCircleFilled,
  IconCoins,
  IconDiamond,
  IconPlanet,
  IconPlus,
  IconRefresh,
  IconSkull,
} from "@tabler/icons-react";
import { units } from "@/entities/data/units";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { getPlanetData } from "@/entities/lookup/planets";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getRelicData } from "@/entities/lookup/relics";
import { Relic } from "@/domains/player/components/Relic/Relic";
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
 * Elementy stołu transakcji (RULES.md 47.1b). Notki i karty akcji to TE SAME chipy co w panelu gracza
 * (``PromissoryNote``) i w ręce: nazwa + znak wystawcy, pełny tekst karty dopiero po kliknięciu
 * (popover z kartą). Wybór do transakcji = osobny przycisk obok chipa. Wspólne dla okna
 * transakcji i okna zgody partnera.
 */

type CardKind = "note" | "action" | "relic";

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
    if (kind === "relic") {
      const relic = getRelicData(id);
      return { name: relic?.name ?? id, text: relic?.text ?? "" };
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
    kind === "note" ? (
      <PromissoryNote promissoryNoteId={id} />
    ) : kind === "relic" ? (
      <Relic relicId={id} />
    ) : (
      <ActionCardChip id={id} />
    );
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

/** Pełne nazwy typów bazowych przechwytywanych jednostek (nigdy id AsyncTI4). */
const UNIT_NAMES: Record<string, string> = {
  warsun: "War Sun",
  flagship: "Flagship",
  dreadnought: "Dreadnought",
  carrier: "Carrier",
  cruiser: "Cruiser",
  destroyer: "Destroyer",
  mech: "Mech",
  fighter: "Fighter",
  infantry: "Infantry",
};
export const unitName = (baseType: string): string => UNIT_NAMES[baseType] ?? baseType;

/** Id sprite'u (AsyncTI4) dla typu bazowego — tylko do komponentu ``Unit``. */
export const unitSpriteId = (baseType: string): string =>
  units.find((u) => u.baseType === baseType)?.asyncId ?? baseType;

/** Lista typów bazowych => posortowane pary [typ, sztuki]. */
export function capturedCounts(list: string[] | undefined): [string, number][] {
  const counts = new Map<string, number>();
  for (const t of list ?? []) counts.set(t, (counts.get(t) ?? 0) + 1);
  return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
}

/** Czy strona stołu jest pusta (nic, także bez długu i umowy Trade). */
export function isEmptySide(s: TransactionSide): boolean {
  return (
    s.tradeGoods === 0 &&
    s.commodities === 0 &&
    s.promissoryNote === null &&
    s.relicFragments.length === 0 &&
    (s.actionCards ?? []).length === 0 &&
    (s.relics ?? []).length === 0 &&
    (s.secretObjectives ?? []).length === 0 &&
    (s.planets ?? []).length === 0 &&
    (s.capturedUnits ?? []).length === 0 &&
    !(s.debtTokens ?? 0) &&
    !s.tradeSecondary &&
    s.wash == null
  );
}

/** Żetony długu w barwie wystawcy (do 8 kropek + „×N" przy większej liczbie). */
export function PromiseDots({ color, count }: { color: string; count: number }) {
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

/** Podsumowanie jednej strony stołu: zasoby, dług, umowa Trade + karty z tekstem. */
export function TradeSummary({
  title,
  side,
  fragmentName,
  issuerColor,
}: {
  title: string;
  side: TransactionSide;
  fragmentName?: (id: string) => string;
  /** Barwa właściciela strony — kolor jego żetonów długu. */
  issuerColor?: string;
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
      {capturedCounts(side.capturedUnits).map(([baseType, count]) => (
        <span key={baseType} className={styles.summaryGoods}>
          <IconSkull size={13} aria-hidden="true" />
          Returns captured {unitName(baseType)}
          {count > 1 ? ` ×${count}` : ""}
        </span>
      ))}
      {(side.debtTokens ?? 0) > 0 && (
        <span className={styles.summaryGoods}>
          {issuerColor ? (
            <PromiseDots color={issuerColor} count={side.debtTokens ?? 0} />
          ) : (
            <IconCircleFilled size={13} aria-hidden="true" />
          )}
          {side.debtTokens} debt token{side.debtTokens === 1 ? "" : "s"} (a promise)
        </span>
      )}
      {side.tradeSecondary && (
        <span className={styles.summaryGoods}>
          <IconRefresh size={13} aria-hidden="true" />
          Free Trade secondary (replenish without a command token)
        </span>
      )}
      {side.wash != null && (
        <span className={styles.summaryGoods}>
          <IconArrowsExchange size={13} aria-hidden="true" />
          Wash after replenishing{side.wash > 0 ? ` (−${side.wash})` : ""}
        </span>
      )}
      {side.promissoryNote && <TradeCard kind="note" id={side.promissoryNote} />}
      {(side.actionCards ?? []).map((c, i) => (
        <TradeCard key={`${c}-${i}`} kind="action" id={c} />
      ))}
      {(side.relics ?? []).map((r) => (
        <TradeCard key={r} kind="relic" id={r} />
      ))}
    </section>
  );
}

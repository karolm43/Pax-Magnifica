import { useState, type CSSProperties } from "react";
import {
  IconCards,
  IconCpu,
  IconDiamond,
  IconTarget,
  IconTicket,
} from "@tabler/icons-react";
import { useFactionColors } from "@/hooks/useFactionColors";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { getRelicData } from "@/entities/lookup/relics";
import { CardLore } from "@/shared/ui/DetailsCard/CardLore";
import { getExploration } from "@/entities/lookup/explorations";
import { RelicCard } from "@/domains/player/components/Relic/RelicCard";
import { ActionCardDetailsCard } from "@/domains/cards/components/ActionCardDetailsCard";
import { SecretObjectiveCard } from "@/domains/cards/components/SecretObjectiveCard";
import { PromissoryNoteCard } from "@/domains/cards/components/PromissoryNoteCard";
import { getOwnerRgb } from "@/domains/player/components/PromissoryNote";
import styles from "./BottomHandDock.module.css";

/*
 * Kafelek karty z ręki (rewers + nazwa + znacznik, klik = pełna karta). JEDEN komponent dla
 * paska ręki na mapie (``BottomHandDock``: przeciąganie = zagranie) i zakładki Player
 * (``PlayerTab``: tylko podgląd - bez ``onDragChange`` karty nie da się podnieść).
 */

export type HandTab = "actions" | "secrets" | "notes" | "relics" | "techs";

/** Zakładki z kartami w wachlarzu (technologie mają własny widok kafelków). */
export type CardTab = Exclude<HandTab, "techs">;

/** Minimalny kształt decyzji silnika o zagrywalności (karta akcji albo relikt). */
export type PlayInfo = { playable: boolean; reason: string | null };

export const TABS: {
  key: HandTab;
  label: string;
  tone: string;
  icon: typeof IconCards;
}[] = [
  { key: "actions", label: "Action cards", tone: "239, 68, 68", icon: IconCards },
  { key: "secrets", label: "Secrets", tone: "239, 68, 68", icon: IconTarget },
  { key: "notes", label: "Notes", tone: "6, 182, 212", icon: IconTicket },
  { key: "relics", label: "Relics", tone: "234, 179, 8", icon: IconDiamond },
  { key: "techs", label: "Techs", tone: "110, 168, 255", icon: IconCpu },
];

export const BACKS: Record<CardTab, string> = {
  actions: assetUrl("/player_area/cardback_action.jpg"),
  secrets: assetUrl("/player_area/cardback_secret.jpg"),
  notes: assetUrl("/player_area/pa_cardbacks_pn.png"),
  relics: assetUrl("/player_area/cardback_relic.jpg"),
};

/** Karty, które można przeciągnąć na strefę zagrania (karta akcji albo relikt z ACTION). */
export const PLAYABLE_TABS: ReadonlySet<HandTab> = new Set(["actions", "relics", "notes"]);

/** Typ przeciąganego elementu w `dataTransfer` (strefa zagrania rozróżnia kartę i relikt). */
export const DRAG_TYPE: Partial<Record<HandTab, string>> = {
  actions: "text/x-actioncard",
  relics: "text/x-relic",
  notes: "text/x-promissory",
};

/** Typ przeciąganej karty frontier (Enigmatic Device) w `dataTransfer`. */
export const FRONTIER_DRAG_TYPE = "text/x-frontier";

/** Nazwa/etykieta karty wg kategorii (z wbudowanych danych AsyncTI4). */
export function useCardLabel(
  tab: CardTab,
  id: string,
  /** Tylko relikty: znacznik z decyzji silnika (rodzaj + wyczerpanie). */
  relicTag?: string,
  /** Karta frontier (Enigmatic Device) leżąca w zakładce Action cards. */
  frontier?: boolean,
): { name: string; tag?: string; ownerRgb?: string } {
  const factionColorMap = useFactionColors();
  if (tab === "actions" && frontier) {
    return { name: getExploration(id)?.name ?? id, tag: "Frontier · Action" };
  }
  if (tab === "actions") {
    const card = getActionCard(id);
    return { name: card?.name ?? id, tag: card?.window };
  }
  if (tab === "relics") {
    return { name: getRelicData(id)?.name ?? id, tag: relicTag };
  }
  if (tab === "secrets") {
    const secret = getSecretObjectiveData(id);
    return {
      name: secret?.name ?? id,
      tag: secret ? `${secret.points} VP` : undefined,
    };
  }
  const note = getPromissoryNoteData(id, factionColorMap);
  return {
    name: note?.displayName || id,
    tag: note?.faction,
    // Nota w kolorze gracza, do którego należy (także gdy leży w cudzej ręce).
    ownerRgb: note
      ? getOwnerRgb(note.faction, note.color, factionColorMap)
      : undefined,
  };
}

/** Pełna karta (treść + grafika) do odsłonięcia w popoverze po kliknięciu. */
export function CardDetails({
  tab,
  id,
  frontier,
}: {
  tab: CardTab;
  id: string;
  frontier?: boolean;
}) {
  if (tab === "actions" && frontier) {
    const card = getExploration(id);
    return (
      <div style={{ maxWidth: 320, padding: 14, whiteSpace: "pre-line" }}>
        <b>{card?.name ?? id}</b>
        <p style={{ margin: "8px 0 0" }}>{card?.text ?? ""}</p>
        <CardLore kind="exploration" id={id} />
      </div>
    );
  }
  if (tab === "actions") return <ActionCardDetailsCard actionCardId={id} />;
  if (tab === "secrets") return <SecretObjectiveCard secretId={id} />;
  if (tab === "relics") return <RelicCard relicId={id} />;
  return <PromissoryNoteCard promissoryNoteId={id} />;
}

/** Jeden kafelek karty w wachlarzu: rewers + nazwa + znacznik; klik = podgląd, drag = zagranie. */
export function HandCard({
  tab,
  id,
  play,
  relicTag,
  passive,
  frontier,
  reaction,
  discardable,
  onDragChange,
  onPlay,
}: {
  tab: CardTab;
  id: string;
  /** Ręka ponad limitem (R_action_cards): kartę akcji przeciąga się na stos odrzuconych. */
  discardable?: boolean;
  /** Karta frontier w zakładce Action cards (przeciągana jak karta akcji). */
  frontier?: boolean;
  /** Decyzja silnika o zagrywalności (karty akcji i relikty z ACTION); brak = jeszcze nie wiadomo. */
  play?: PlayInfo;
  /** Relikt: znacznik rodzaju/wyczerpania pod nazwą. */
  relicTag?: string;
  /** Relikt pasywny: działa sam, nie ma co zagrywać (nie przyciemniamy go jak zablokowanej karty). */
  passive?: boolean;
  /** Okno reakcji tej karty jest otwarte TERAZ (RULES.md 54.8) - karta miga. */
  reaction?: boolean;
  /** Brak = tylko podgląd (zakładka Player): karty nie da się podnieść. */
  onDragChange?: (cardId: string | null) => void;
  /** Zagranie / odrzucenie KLIKIEM (przycisk w podglądzie) - druga droga obok przeciągnięcia. */
  onPlay?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const { name, tag, ownerRgb } = useCardLabel(tab, id, relicTag, frontier);
  const playableTab = PLAYABLE_TABS.has(tab);
  const canDrag =
    onDragChange !== undefined &&
    (discardable === true || (playableTab && play?.playable === true));
  const locked =
    !discardable && playableTab && !passive && play !== undefined && !play.playable;
  const hint = discardable
    ? `${name} - drag onto the discard pile or click and choose Discard (hand limit)`
    : canDrag
    ? reaction
      ? `${name} - its window is open now: drag onto the play zone, or click and choose Play`
      : `${name} - drag onto the play zone, or click and choose Play`
    : locked
      ? `${name} - can't be played now: ${play?.reason ?? "not available"}`
      : passive
        ? `${name} - passive, works on its own`
        : name;
  const tone =
    ownerRgb ?? TABS.find((t) => t.key === tab)?.tone ?? "148, 163, 184";
  return (
    // Wrapper (nie sam <button>) jest elementem przeciąganym: Firefox nie przeciąga przycisków.
    <div
      className={styles.cardWrap}
      draggable={canDrag}
      onDragStart={(e) => {
        if (!canDrag) {
          e.preventDefault();
          return;
        }
        e.dataTransfer.setData(
          frontier ? FRONTIER_DRAG_TYPE : (DRAG_TYPE[tab] ?? "text/x-actioncard"),
          id,
        );
        e.dataTransfer.effectAllowed = "move";
        setOpen(false);
        onDragChange?.(id);
      }}
      onDragEnd={() => onDragChange?.(null)}
    >
    <SmoothPopover opened={open} onChange={setOpen} position="top">
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.card}
          style={{ "--hk": tone } as CSSProperties}
          data-open={open || undefined}
          data-tinted={ownerRgb ? true : undefined}
          data-playable={canDrag || undefined}
          data-discard={discardable || undefined}
          data-reaction={(canDrag && reaction) || undefined}
          data-locked={locked || undefined}
          onClick={() => setOpen((v) => !v)}
          title={hint}
        >
          <span
            className={styles.cardArt}
            style={{ backgroundImage: `url("${BACKS[tab]}")` }}
            aria-hidden="true"
          />
          <span className={styles.cardMeta}>
            <b className={styles.cardName}>{name}</b>
            {tag && <small className={styles.cardTag}>{tag}</small>}
          </span>
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <CardDetails tab={tab} id={id} frontier={frontier} />
        {canDrag && onPlay && (
          <div className={styles.cardActions}>
            <button
              type="button"
              className={styles.cardPlayBtn}
              data-discard={discardable || undefined}
              onClick={() => {
                setOpen(false);
                onPlay();
              }}
            >
              {discardable ? `Discard ${name}` : `Play ${name}`}
            </button>
          </div>
        )}
      </SmoothPopover.Dropdown>
    </SmoothPopover>
    </div>
  );
}

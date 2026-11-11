import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import {
  IconArrowsDiagonal,
  IconArrowsDiagonalMinimize2,
  IconChevronDown,
  IconChevronUp,
  IconMinus,
} from "@tabler/icons-react";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { getPortalRoot } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useOfferActions, useOffers, type OfferView } from "@/api/useOffers";
import { buildActionCardParams, type FormValue } from "@/api/useActionCard";
import { InputField } from "@/domains/game-shell/components/TurnControls/ActionCardPlayModal";
import { TransitDiodesPicker } from "./TransitDiodesPicker";
import styles from "./OffersDock.module.css";

/** Czy zdarzenie klawiatury trafia w pole, które samo obsługuje Enter/Esc (formularz, przycisk). */
function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(target.tagName)
  );
}

/**
 * Jedna decyzja gracza: tekst karty z assetów + formularz z opcji policzonych przez silnik.
 * To NIEMODALNY panel przy dolnej krawędzi (bez przyciemnienia): plansza zostaje klikalna, a
 * decyzję zamyka jeden przycisk albo klawisz (Enter = użyj, Esc = pomiń).
 */
function OfferDock({ offer, queued }: { offer: OfferView; queued: number }) {
  const actions = useOfferActions();
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [showText, setShowText] = useState(false);
  const [wide, setWide] = useState(false);
  // Transit Diodes ma własny, graficzny wybór (podnieś → połóż); pozostałe oferty to formularz.
  const graphical = offer.inputs.some((input) => input.key === "unit1") &&
    offer.inputs.some((input) => input.key === "to1");
  const [graphicalReady, setGraphicalReady] = useState(false);
  // Panel da się przesuwać za nagłówek (pozycja zapamiętana) i rozszerzać.
  const drag = useDraggablePanel("offersDock.pos.v1");

  // Nowa oferta → czysty formularz i rozwinięty panel (nie przeoczymy kolejnej decyzji).
  useEffect(() => {
    setValues({});
    setCollapsed(false);
    setShowText(false);
    setGraphicalReady(false);
  }, [offer.id]);

  const { params, ready } = useMemo(
    () => buildActionCardParams(offer.inputs, values),
    [offer.inputs, values],
  );
  const noOptions = offer.inputs.some(
    (input) =>
      input.kind !== "number" &&
      input.options.length < (input.kind === "multi" ? input.min : 1),
  );
  const canUse = !busy && ready && !noOptions && (!graphical || graphicalReady);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód (422) pokazał komunikat; panel zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };
  const use = () => void run(() => actions.accept(offer.player_id, offer.id, params));
  const skip = () => void run(() => actions.decline(offer.player_id, offer.id));

  // Skróty klawiszowe: tylko gdy fokus nie siedzi w polu formularza ani na przycisku.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      if (isInteractiveTarget(event.target)) return;
      if (event.key === "Enter" && canUse) {
        event.preventDefault();
        use();
      } else if (event.key === "Escape" && !offer.mandatory && !busy) {
        event.preventDefault();
        skip();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canUse, busy, offer.id, offer.mandatory, params]);

  if (collapsed) {
    return createPortal(
      <button
        type="button"
        className={styles.pill}
        onClick={() => setCollapsed(false)}
        title="Show the decision"
      >
        <IconChevronUp size={15} aria-hidden="true" />
        <span>{offer.name}</span>
        {queued > 0 && <b>+{queued}</b>}
      </button>,
      getPortalRoot() ?? document.body,
    );
  }

  return createPortal(
    <section
      className={styles.dock}
      role="group"
      aria-label={`Decision: ${offer.name}`}
      data-draggable-panel
      data-wide={wide || undefined}
      data-dragging={drag.isDragging || undefined}
      style={drag.style}
    >
      <header
        className={styles.head}
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move (double-click resets)"
      >
        <b className={styles.title}>{offer.name}</b>
        {offer.mandatory && <span className={styles.tag}>Required</span>}
        {queued > 0 && <span className={styles.tag}>+{queued} more</span>}
        <button
          type="button"
          className={styles.iconBtn}
          data-no-drag
          onClick={() => setWide((w) => !w)}
          aria-label={wide ? "Make smaller" : "Make larger"}
          title={wide ? "Make smaller" : "Make larger"}
        >
          {wide ? (
            <IconArrowsDiagonalMinimize2 size={15} aria-hidden="true" />
          ) : (
            <IconArrowsDiagonal size={15} aria-hidden="true" />
          )}
        </button>
        <button
          type="button"
          className={styles.iconBtn}
          data-no-drag
          onClick={() => setCollapsed(true)}
          aria-label="Minimize to see the board"
          title="Minimize to see the board"
        >
          <IconMinus size={15} aria-hidden="true" />
        </button>
      </header>

      {offer.text && (
        <div className={styles.textBlock}>
          <p className={styles.text} data-open={showText || undefined}>
            {offer.text}
          </p>
          {offer.text.length > 110 && (
            <button
              type="button"
              className={styles.more}
              onClick={() => setShowText((open) => !open)}
            >
              {showText ? "less" : "more"}
              {showText ? (
                <IconChevronUp size={12} aria-hidden="true" />
              ) : (
                <IconChevronDown size={12} aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      )}

      {graphical && (
        <TransitDiodesPicker
          offer={offer}
          disabled={busy}
          onChange={(next, complete) => {
            setValues((prev) => ({ ...prev, ...next }));
            setGraphicalReady(complete);
          }}
        />
      )}
      {!graphical && offer.inputs.length > 0 && (
        <div className={styles.inputs}>
          {offer.inputs.map((input) => (
            <InputField
              key={input.key}
              input={input}
              value={values[input.key]}
              disabled={busy}
              onChange={(next) => setValues((prev) => ({ ...prev, [input.key]: next }))}
            />
          ))}
        </div>
      )}
      {noOptions && <p className={styles.warn}>There is no legal option for this right now.</p>}

      <footer className={styles.actions}>
        {!offer.mandatory && (
          <button type="button" className={styles.skip} disabled={busy} onClick={skip}>
            Skip <kbd>Esc</kbd>
          </button>
        )}
        <button type="button" className={styles.use} disabled={!canUse} onClick={use}>
          {offer.mandatory ? "Confirm" : "Use"} <kbd>Enter</kbd>
        </button>
      </footer>
    </section>,
    getPortalRoot() ?? document.body,
  );
}

/**
 * Decyzje graczy (RULES.md 56): technologie i zdolności z „may" oraz wybory celu (np. ofiara
 * Assault Cannon, cel Magen Defense Grid, naprawa Duranium Armor). Panel pojawia się sam, gdy
 * `gameState.pendingOffers` nie jest puste; pokazuje po jednej decyzji, a gracz zawsze wybiera
 * sam. Nie przyciemnia ekranu i nie blokuje planszy.
 */
export function OffersModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const pending = (gameState?.pendingOffers ?? []).length > 0;
  const { data: offers, refetch } = useOffers(pending);

  // Każda zmiana stanu gry odświeża opcje (zależą od bieżącej planszy).
  useEffect(() => {
    if (pending) void refetch();
  }, [gameState, pending, refetch]);

  if (!pending || !offers || offers.length === 0) return null;
  return <OfferDock key={offers[0].id} offer={offers[0]} queued={offers.length - 1} />;
}

export default OffersModal;

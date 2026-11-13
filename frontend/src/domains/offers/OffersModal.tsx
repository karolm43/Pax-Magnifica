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
import { useGameData } from "@/state/useGameContext";
import { Tech } from "@/domains/player/components/Tech";
import {
  CommandPools,
  poolsLeft,
  type PoolAlloc,
} from "@/shared/ui/CommandPools/CommandPools";
import { DecisionFields } from "./DecisionFields";
import { TransitDiodesPicker } from "./TransitDiodesPicker";
import styles from "./OffersDock.module.css";

/** Opisy krótsze niż tyle znaków pokazujemy w całości (bez „more”). */
const LONG_TEXT = 420;

/** Wejścia rozdziału żetonów (Predictive Intelligence): trzy liczby o tych kluczach. */
const POOL_KEYS = { t: "tactical", f: "fleet", s: "strategic" } as const;

function isPoolsOffer(offer: OfferView): boolean {
  const keys = new Set(
    offer.inputs.filter((i) => i.kind === "number").map((i) => i.key),
  );
  return Object.values(POOL_KEYS).every((k) => keys.has(k));
}

/** Kafelek komponentu źródłowego (dziś: technologia = ten sam Tech co w panelu gracza). */
function SourceTile({ source }: { source: string | undefined }) {
  if (!source?.startsWith("technologies:")) return null;
  return (
    <span className={styles.source} data-no-drag>
      <Tech techId={source.slice("technologies:".length)} />
    </span>
  );
}

/** Czy zdarzenie klawiatury trafia w pole, które samo obsługuje Enter/Esc (formularz, przycisk). */
function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(target.tagName)
  );
}

/** Przycisk „Use”, a gdy etykieta hooka mówi, co się stanie („…: spend 2 TG …”) — ta treść. */
function acceptLabel(offer: OfferView): string {
  const at = offer.label.indexOf(": ");
  const action = at >= 0 ? offer.label.slice(at + 2).trim() : "";
  if (!action || action.length > 42) return "Use";
  return action.charAt(0).toUpperCase() + action.slice(1);
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
  // Predictive Intelligence: pule żetonów (− / +) startują od obecnego rozdziału gracza.
  const pools = isPoolsOffer(offer);
  const gameData = useGameData();
  const decider = gameData?.playerData?.find((p) => p.discordId === offer.player_id);
  const tacticInput = offer.inputs.find((i) => i.key === POOL_KEYS.t);
  const poolsTotal = tacticInput?.kind === "number" ? tacticInput.max : 0;
  const num = (key: string, fallback: number) =>
    typeof values[key] === "number" ? values[key] : fallback;
  const alloc: PoolAlloc = {
    t: num(POOL_KEYS.t, decider?.tacticalCC ?? 0),
    f: num(POOL_KEYS.f, decider?.fleetCC ?? 0),
    s: num(POOL_KEYS.s, decider?.strategicCC ?? 0),
  };
  const poolsToPlace = poolsLeft(alloc, poolsTotal);

  // Nowa oferta → czysty formularz i rozwinięty panel (nie przeoczymy kolejnej decyzji).
  useEffect(() => {
    setValues({});
    setCollapsed(false);
    setShowText(false);
    setGraphicalReady(false);
  }, [offer.id]);

  // Pule: wartości startowe (obecny rozdział) idą do parametrów, choć gracz ich nie ruszał.
  const formValues = useMemo(
    () =>
      pools
        ? {
            ...values,
            [POOL_KEYS.t]: alloc.t,
            [POOL_KEYS.f]: alloc.f,
            [POOL_KEYS.s]: alloc.s,
          }
        : values,
    [pools, values, alloc.t, alloc.f, alloc.s],
  );
  const { params, ready } = useMemo(
    () => buildActionCardParams(offer.inputs, formValues),
    [offer.inputs, formValues],
  );
  const noOptions = offer.inputs.some(
    (input) =>
      input.kind !== "number" &&
      input.options.length < (input.kind === "multi" ? input.min : 1),
  );
  const canUse =
    !busy &&
    ready &&
    (!pools || poolsToPlace === 0) &&
    !noOptions &&
    (!graphical || graphicalReady);

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
        <SourceTile source={offer.source} />
        <span className={styles.titleBox}>
          {offer.kind && <small className={styles.kind}>{offer.kind}</small>}
          <b className={styles.title}>{offer.name}</b>
        </span>
        {offer.mandatory && <span className={styles.tag} data-tone="required">Required</span>}
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
          <p
            className={styles.text}
            data-open={showText || offer.text.length <= LONG_TEXT || undefined}
          >
            {offer.text}
          </p>
          {offer.text.length > LONG_TEXT && (
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
      {pools && (
        <div className={styles.poolsBox}>
          <p className={styles.poolsHint}>
            Move tokens between your pools with − / +.{" "}
            <b data-ok={poolsToPlace === 0 || undefined}>
              {poolsToPlace === 0
                ? `All ${poolsTotal} placed`
                : `${poolsToPlace} to place`}
            </b>
          </p>
          <CommandPools
            alloc={alloc}
            total={poolsTotal}
            disabled={busy}
            onChange={(next) =>
              setValues((prev) => ({
                ...prev,
                [POOL_KEYS.t]: next.t,
                [POOL_KEYS.f]: next.f,
                [POOL_KEYS.s]: next.s,
              }))
            }
          />
        </div>
      )}
      {!graphical && !pools && offer.inputs.length > 0 && (
        <DecisionFields
          inputs={offer.inputs}
          values={values}
          disabled={busy}
          onChange={(key, next) => setValues((prev) => ({ ...prev, [key]: next }))}
        />
      )}
      {noOptions && <p className={styles.warn}>There is no legal option for this right now.</p>}

      <footer className={styles.actions}>
        {!offer.mandatory && (
          <button type="button" className={styles.skip} disabled={busy} onClick={skip}>
            Skip <kbd>Esc</kbd>
          </button>
        )}
        <button type="button" className={styles.use} disabled={!canUse} onClick={use}>
          {offer.mandatory ? "Confirm" : acceptLabel(offer)} <kbd>Enter</kbd>
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

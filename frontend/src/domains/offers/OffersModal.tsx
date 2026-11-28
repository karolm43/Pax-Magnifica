import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useOfferActions, useOffers, type OfferView } from "@/api/useOffers";
import {
  buildActionCardParams,
  type FormValue,
  hasNoLegalOption,
  postReactionPrefs,
} from "@/api/useActionCard";
import { useGameData } from "@/state/useGameContext";
import { DecisionFrame } from "@/shared/ui/DecisionFrame";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import type { OfferDeal } from "@/api/useOffers";
import { Tech } from "@/domains/player/components/Tech";
import { getTechData } from "@/entities/lookup/tech";
import {
  CommandPools,
  poolsLeft,
  type PoolAlloc,
} from "@/shared/ui/CommandPools/CommandPools";
import { DecisionFields } from "./DecisionFields";
import { FrameTitleContext } from "./DecisionTiles";
import { TransitDiodesPicker } from "./TransitDiodesPicker";
import { isResearchOffer, ResearchOfferOverlay } from "./ResearchOfferOverlay";
import styles from "./OffersDock.module.css";

/** Wejścia rozdziału żetonów (Predictive Intelligence): trzy liczby o tych kluczach. */
const POOL_KEYS = { t: "tactical", f: "fleet", s: "strategic" } as const;

function isPoolsOffer(offer: OfferView): boolean {
  const keys = new Set(
    offer.inputs.filter((i) => i.kind === "number").map((i) => i.key),
  );
  return Object.values(POOL_KEYS).every((k) => keys.has(k));
}

/** Id technologii źródłowej oferty (``technologies:<id>``) albo ``null``. */
function sourceTech(source: string | undefined): string | null {
  if (!source?.startsWith("technologies:")) return null;
  const id = source.slice("technologies:".length);
  return getTechData(id) ? id : null;
}

/** Przycisk „Use”, a gdy etykieta hooka mówi, co się stanie („…: spend 2 TG …”) — ta treść. */
/** Terms of a requested cooperative effect on its offer card (RULES.md 54.15). */
export function DealLine({ deal, decider }: { deal: OfferDeal; decider: string }) {
  const debt = deal.debtTokens ?? 0;
  const paid = deal.tradeGoods + deal.commodities + debt;
  const price =
    paid === 0
      ? "for free"
      : [
          deal.tradeGoods ? `${deal.tradeGoods} trade good${deal.tradeGoods === 1 ? "" : "s"}` : "",
          deal.commodities ? `${deal.commodities} commodit${deal.commodities === 1 ? "y" : "ies"}` : "",
          debt ? `${debt} debt token${debt === 1 ? "" : "s"}` : "",
        ]
          .filter(Boolean)
          .join(" + ");
  if (decider === deal.requester) {
    return (
      <span data-testid="deal-line">
        <PlayerTag playerId={deal.owner} size={14} /> agreed - you pay {price} when you use it.
      </span>
    );
  }
  return (
    <span data-testid="deal-line">
      <PlayerTag playerId={deal.requester} size={14} /> asks you to use this
      {paid === 0 ? ", for free" : `, paying ${price}`}. Paid only if you accept.
    </span>
  );
}

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
  // Transit Diodes ma własny, graficzny wybór (podnieś → połóż); pozostałe oferty to formularz.
  const graphical = offer.inputs.some((input) => input.key === "unit1") &&
    offer.inputs.some((input) => input.key === "to1");
  const [graphicalReady, setGraphicalReady] = useState(false);
  // Predictive Intelligence: pule żetonów (− / +) startują od obecnego rozdziału gracza.
  const pools = isPoolsOffer(offer);
  const gameData = useGameData();
  const decider = gameData?.playerData?.find((p) => p.discordId === offer.player_id);
  const foreign = Boolean(offer.owner_id) && offer.owner_id !== offer.player_id;
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
  const noOptions = hasNoLegalOption(offer.inputs);
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
  // „Never ask” (RULES.md 54.12): odmowa + wyciszenie ofert tego komponentu (odwołanie w panelu
  // „Reactions” panelu akcji).
  const neverAsk = () =>
    void run(async () => {
      if (!offer.source) return;
      await postReactionPrefs(offer.player_id, { mute_offers: { [offer.source]: true } });
      await actions.decline(offer.player_id, offer.id);
    });

  const techId = sourceTech(offer.source);
  return (
    <DecisionFrame
      ariaLabel={`Decision: ${offer.name}`}
      kind={offer.kind || undefined}
      ownerId={foreign ? offer.owner_id : undefined}
      // Technologia źródłowa = TEN SAM chip co w panelu gracza (pełna karta po kliknięciu)
      // i jest tytułem - bez drugiej, dublującej nazwy obok.
      title={techId ? <Tech techId={techId} /> : offer.name}
      subtitle={offer.deal ? <DealLine deal={offer.deal} decider={offer.player_id} /> : undefined}
      required={offer.mandatory}
      queued={queued}
      text={offer.text || undefined}
      warnings={noOptions ? ["There is no legal option for this right now."] : []}
      busy={busy}
      canUse={canUse}
      onUse={use}
      useLabel={
        offer.deal
          ? offer.deal.requester === offer.player_id
            ? "Use and pay"
            : "Accept deal"
          : offer.mandatory
            ? "Confirm"
            : acceptLabel(offer)
      }
      onSkip={offer.mandatory ? undefined : skip}
      // „Nie używam” wprost (punkt 6 planu): para do przycisku użycia, zamiast ogólnego „Skip”.
      skipLabel={offer.deal ? (offer.deal.requester === offer.player_id ? "Cancel" : "Decline") : "Don't use"}
      onNeverAsk={!offer.mandatory && offer.source && !offer.deal ? neverAsk : undefined}
    >
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
        <FrameTitleContext.Provider value={offer.name}>
          <DecisionFields
            inputs={offer.inputs}
            values={values}
            disabled={busy}
            onChange={(key, next) => setValues((prev) => ({ ...prev, [key]: next }))}
          />
        </FrameTitleContext.Provider>
      )}
    </DecisionFrame>
  );
}

/**
 * Decyzje graczy (RULES.md 56): technologie i zdolności z „may" oraz wybory celu (np. ofiara
 * Assault Cannon, cel Magen Defense Grid, naprawa Duranium Armor). Kolejka z
 * `gameState.pendingOffers`; pierwsza decyzja to karta w centrum decyzji (`DecisionCenter`),
 * a decyzja badania otwiera pełne okno badania. Gracz zawsze wybiera sam.
 */
export function useDecisionOffers(
  forPlayer: string | null = null,
): { first: OfferView | null; queued: number } {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const pending = (gameState?.pendingOffers ?? []).length > 0;
  const { data: offers, refetch } = useOffers(pending);

  // Każda zmiana stanu gry odświeża opcje (zależą od bieżącej planszy).
  useEffect(() => {
    if (pending) void refetch();
  }, [gameState, pending, refetch]);

  // Gra sieciowa: decyzja cudzego gracza nie jest moją - nie pokazujemy jej (`forPlayer` = moje miejsce).
  const mine = forPlayer ? (offers ?? []).filter((o) => o.player_id === forPlayer) : offers;
  if (!pending || !mine || mine.length === 0) return { first: null, queued: 0 };
  // Decyzja badania czeka na końcu: najpierw zdolności „przed zapłatą” (Doctor Sucaban zdejmuje
  // piechotę), potem pełne okno badania z obniżonym kosztem.
  const ordered = [
    ...mine.filter((o) => !isResearchOffer(o)),
    ...mine.filter((o) => isResearchOffer(o)),
  ];
  return { first: ordered[0], queued: ordered.length - 1 };
}

/** Bieżąca decyzja: pełne okno badania albo karta decyzji (formularz). */
export function OfferCard({ offer, queued }: { offer: OfferView; queued: number }) {
  if (isResearchOffer(offer)) return <ResearchOfferOverlay key={offer.id} offer={offer} />;
  return <OfferDock key={offer.id} offer={offer} queued={queued} />;
}

import { useState, type ReactNode } from "react";
import {
  IconBox,
  IconCards,
  IconCheck,
  IconCoins,
  IconFlask,
  IconLock,
  IconMessageCircle,
} from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPlanetData } from "@/entities/lookup/planets";
import { ConfirmButton, Hint, PaymentPicker, Section } from "@/domains/strategy/PromptParts";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import {
  useThundersEdge,
  useThundersEdgeActions,
  type SliceId,
  type SlicePayment,
} from "./useThundersEdge";
import styles from "./ThundersEdge.module.css";

type SliceMeta = { label: string; cost: string; icon: ReactNode };

/** Opis plastrów żetonu ekspedycji (koszty - R_expedition, RULES.md 50.1). */
const SLICE_META: Record<SliceId, SliceMeta> = {
  fiveRes: { label: "Resources", cost: "Spend 5 resources", icon: <IconBox size={18} /> },
  actionCards: {
    label: "Action cards",
    cost: "Discard 2 action cards",
    icon: <IconCards size={18} />,
  },
  fiveInf: {
    label: "Influence",
    cost: "Spend 5 influence",
    icon: <IconMessageCircle size={18} />,
  },
  secret: {
    label: "Secret objective",
    cost: "Discard 1 unscored secret objective",
    icon: <IconLock size={18} />,
  },
  techSkip: {
    label: "Technology specialty",
    cost: "Exhaust a planet with a technology specialty",
    icon: <IconFlask size={18} />,
  },
  tradeGoods: { label: "Trade goods", cost: "Spend 3 trade goods", icon: <IconCoins size={18} /> },
};

const planetName = (id: string) => getPlanetData(id)?.name ?? id;

type Props = {
  opened: boolean;
  onClose: () => void;
  gameId: string;
  /** Aktywny gracz (ID silnika) - jego ręka i planety płacą za plaster. */
  playerId: string | null;
};

/**
 * Ekspedycja Thunder's Edge (RULES.md 50.1): na koniec swojej tury gracz zajmuje jeden wolny
 * plaster żetonu, płacąc jego koszt. Pierwsza ekspedycja daje przełom frakcji i rzut na The
 * Fracture. Legalność (moment, koszt) sprawdza silnik - okno tylko zbiera wybór.
 */
export function ExpeditionModal({ opened, onClose, gameId, playerId }: Props) {
  const { data: view } = useThundersEdge(opened);
  const { data: hand } = usePlayerHand(gameId, { ignoreAuthGate: true, player: playerId });
  const actions = useThundersEdgeActions();
  const look = usePlayerLook();
  const [slice, setSlice] = useState<SliceId | null>(null);
  const [planets, setPlanets] = useState<string[]>([]);
  const [tradeGoods, setTradeGoods] = useState(0);
  const [cards, setCards] = useState<string[]>([]);
  const [secret, setSecret] = useState<string | null>(null);
  const [techPlanet, setTechPlanet] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const choose = (id: SliceId) => {
    setSlice(id);
    setPlanets([]);
    setTradeGoods(0);
    setCards([]);
    setSecret(null);
    setTechPlanet(null);
  };

  // `cards` trzyma klucze "id#indeks" (ta sama karta może być w ręce kilka razy); do API idą id.
  const cardIds = cards.map((c) => c.split("#")[0]);
  const payment: SlicePayment = (() => {
    switch (slice) {
      case "fiveRes":
      case "fiveInf":
        return { planets, trade_goods: tradeGoods };
      case "actionCards":
        return { action_cards: cardIds };
      case "secret":
        return { secret };
      case "techSkip":
        return { tech_planet: techPlanet };
      default:
        return {};
    }
  })();

  const values = view
    ? slice === "fiveInf"
      ? view.payment.influence
      : view.payment.resources
    : {};
  const total = planets.reduce((n, id) => n + (values[id] ?? 0), 0) + tradeGoods;
  const ready = (() => {
    switch (slice) {
      case "fiveRes":
      case "fiveInf":
        return total >= 5;
      case "actionCards":
        return cards.length === 2;
      case "secret":
        return secret != null;
      case "techSkip":
        return techPlanet != null;
      case "tradeGoods":
        return (view?.payment.tradeGoods ?? 0) >= 3;
      default:
        return false;
    }
  })();

  const submit = async () => {
    if (!slice || busy) return;
    setBusy(true);
    try {
      await actions.perform(slice, payment);
      setSlice(null);
      onClose();
    } catch {
      // Powód (422) pokazuje panel komunikatów.
    } finally {
      setBusy(false);
    }
  };

  const toggleCard = (id: string, index: number) => {
    const key = `${id}#${index}`;
    setCards((prev) =>
      prev.includes(key)
        ? prev.filter((c) => c !== key)
        : prev.length >= 2
          ? prev
          : [...prev, key],
    );
  };
  return (
    <AppModal floating opened={opened} onClose={onClose} title="Expedition" minimizable size="lg">
      <div className={styles.body}>
        <Hint>
          At the <b>end of your turn</b> you may claim <b>one</b> free slice of the expedition
          token (one per turn). Your first expedition unlocks your <b>breakthrough</b> and rolls
          for <b>The Fracture</b>. The sixth slice brings <b>Thunder&apos;s Edge</b> into play.
        </Hint>
        {view && !view.canPerform && view.blockReason && (
          <Hint>
            <b>Not now:</b> {view.blockReason}
          </Hint>
        )}
        <div className={styles.slices}>
          {(view?.slices ?? []).map(({ id, claimedBy }) => {
            const meta = SLICE_META[id];
            const owner = claimedBy && view ? view.players[claimedBy] : null;
            return (
              <button
                key={id}
                type="button"
                className={styles.slice}
                data-selected={slice === id || undefined}
                disabled={claimedBy != null || busy}
                onClick={() => choose(id)}
              >
                <span className={styles.sliceIcon}>{meta.icon}</span>
                <span className={styles.sliceText}>
                  <b>{meta.label}</b>
                  <small>{meta.cost}</small>
                </span>
                {owner && (
                  <span className={styles.claimed}>
                    <CircularFactionIcon faction={owner} size={20} />
                    {look(owner).name}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {view && slice && (slice === "fiveRes" || slice === "fiveInf") && (
          <>
            <PaymentPicker
              values={values}
              tradeGoodsAvailable={view.payment.tradeGoods}
              value={{ planets, tradeGoods }}
              onChange={(next) => {
                setPlanets(next.planets);
                setTradeGoods(next.tradeGoods);
              }}
              unit={slice === "fiveInf" ? "influence" : "resources"}
              busy={busy}
            />
            <Hint>
              Selected: <b>{total}</b> of <b>5</b> (overpaying is allowed, the surplus is lost).
            </Hint>
          </>
        )}

        {view && slice === "tradeGoods" && (
          <Hint>
            Spend <b>3 trade goods</b> - you have <b>{view.payment.tradeGoods}</b>.
          </Hint>
        )}

        {slice === "actionCards" && (
          <Section title="Choose 2 action cards to discard">
            <div className={styles.cards}>
              {(hand?.actionCards ?? []).map((id, index) => (
                <button
                  key={`${id}#${index}`}
                  type="button"
                  className={styles.cardPick}
                  data-on={cards.includes(`${id}#${index}`) || undefined}
                  onClick={() => toggleCard(id, index)}
                >
                  {getActionCard(id)?.name ?? id}
                </button>
              ))}
              {(hand?.actionCards ?? []).length === 0 && <Hint>You have no action cards.</Hint>}
            </div>
          </Section>
        )}

        {slice === "secret" && (
          <Section title="Choose an unscored secret objective to discard">
            <div className={styles.cards}>
              {(hand?.secretObjectives ?? []).map((id) => (
                <button
                  key={id}
                  type="button"
                  className={styles.cardPick}
                  data-on={secret === id || undefined}
                  onClick={() => setSecret(secret === id ? null : id)}
                >
                  {getSecretObjectiveData(id)?.name ?? id}
                </button>
              ))}
              {(hand?.secretObjectives ?? []).length === 0 && (
                <Hint>You have no unscored secret objective.</Hint>
              )}
            </div>
          </Section>
        )}

        {view && slice === "techSkip" && (
          <Section title="Planet to exhaust">
            <div className={styles.cards}>
              {view.payment.specialtyPlanets.map((id) => (
                <button
                  key={id}
                  type="button"
                  className={styles.cardPick}
                  data-on={techPlanet === id || undefined}
                  onClick={() => setTechPlanet(techPlanet === id ? null : id)}
                >
                  {planetName(id)}
                </button>
              ))}
              {view.payment.specialtyPlanets.length === 0 && (
                <Hint>You have no ready planet with a technology specialty.</Hint>
              )}
            </div>
          </Section>
        )}

        <div className={styles.footer}>
          <ConfirmButton
            disabled={busy || !slice || !ready || !(view?.canPerform ?? false)}
            icon={<IconCheck size={16} />}
            onClick={() => void submit()}
          >
            Claim slice
          </ConfirmButton>
        </div>
      </div>
    </AppModal>
  );
}

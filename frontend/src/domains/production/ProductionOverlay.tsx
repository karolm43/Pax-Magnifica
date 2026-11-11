import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconInfoCircle,
  IconBuildingFactory2,
  IconCheck,
  IconMinimize,
  IconMinus,
  IconPlus,
  IconSparkles,
  IconTrash,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { Switch } from "@/ds";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { getTileById } from "@/entities/lookup/systems";
import { useGameData } from "@/state/useGameContext";
import { Unit } from "@/shared/ui/Unit";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
import { FleetPoolWarning } from "@/domains/map/components/FleetPoolWarning";
import {
  SPACE,
  autoPay,
  bumpCart,
  cartCost,
  cartCount,
  countOf,
  fundsTotal,
  maxMore,
  paymentTotal,
  whyNotAdd,
  type CartLine,
  type Payment,
} from "./productionMath";
import {
  skipProductionGrant,
  useProductionView,
  type ProductionBody,
  type ProductionUnit,
} from "./useProduction";
import styles from "./ProductionOverlay.module.css";

/* Grafika tła (podmienna, w `assets/extra/`, serwowana pod `/static`); brak pliku = gwiazdy + ciemne tło. */
const BACKDROP = 'url("/static/extra/production_bg.jpg"), url("/static/extra/starfield.png")';

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

function ProductionWindow({ view }: { view: ProductionBody }) {
  const gameData = useGameData();
  const look = usePlayerLook();
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);
  const setHidden = useAppStore((s) => s.setProductionHidden);
  const { produce, tacticalNextStep } = useBoardEditor();
  const queryClient = useQueryClient();
  const grant = view.grant;
  const [busy, setBusy] = useState(false);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [zone, setZone] = useState<string | null>(null);
  // null = płatność automatyczna (liczona z koszyka); ręczny wybór planet/TG ją zastępuje.
  const [manual, setManual] = useState<Payment | null>(null);

  const player = view.faction ? look(view.faction) : null;
  const tile = gameData?.tiles?.[view.position];
  const systemName = tile
    ? (getTileById(tile.systemId)?.name ?? view.position)
    : view.position;
  const nameOf = (id: string) =>
    id === SPACE
      ? "Space"
      : (view.planets.find((p) => p.planet === id)?.name ?? id);

  const activeZone =
    zone && view.groundZones.includes(zone) ? zone : (view.groundZones[0] ?? null);
  const zoneChoices = view.groundZones;

  const queued = cartCount(cart);
  const free = Math.max(0, view.remaining - queued);
  // Zniżki (RULES.md 57): hooki (Sarween Tools) działają od razu, AI Development Algorithm
  // tylko gdy gracz świadomie go wyczerpie przełącznikiem.
  const [useAida, setUseAida] = useState(false);
  const aidaOn = useAida && view.aida?.ready === true && queued > 0;
  const rawCost = cartCost(view.units, cart);
  const cost =
    queued > 0
      ? Math.max(
          0,
          rawCost - (view.costReduction ?? 0) - (aidaOn ? (view.aida?.discount ?? 0) : 0),
        )
      : rawCost;
  const funds = fundsTotal(view);
  const payment = useMemo<Payment>(
    () => manual ?? autoPay(view.planets, view.tradeGoods, cost),
    [manual, view.planets, view.tradeGoods, cost],
  );
  const paid = paymentTotal(view.planets, payment);
  const short = Math.max(0, cost - paid);
  const wasted = Math.max(0, paid - cost);
  const canProduce = queued > 0 && short === 0 && !busy;
  const costState =
    queued === 0 ? "empty" : short > 0 ? "short" : wasted > 0 ? "surplus" : "ok";
  // Myśliwce z koszyka trafiają do przestrzeni i zajmują capacity (dok: do N nie liczy się).
  const queuedFighters = countOf(cart, "fighter");
  // Statki z koszyka liczone do fleet pool (bez myśliwców) - do ostrzeżenia o przekroczeniu.
  const queuedShips = cart.reduce((n, l) => {
    const u = view.units.find((x) => x.baseType === l.baseType);
    return u?.placement === "space" && u.baseType !== "fighter" ? n + l.count : n;
  }, 0);

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód (422) pokazuje panel komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  const add = (unit: ProductionUnit, delta: number) => {
    const target = unit.placement === "space" ? SPACE : activeZone;
    if (!target) return;
    setCart((c) => bumpCart(c, unit.baseType, target, delta));
  };

  const togglePlanet = (planet: string) => {
    const base = payment;
    const has = base.planets.includes(planet);
    setManual({
      planets: has ? base.planets.filter((p) => p !== planet) : [...base.planets, planet],
      tradeGoods: base.tradeGoods,
    });
  };
  const setTradeGoods = (delta: number) => {
    const next = Math.min(view.tradeGoods, Math.max(0, payment.tradeGoods + delta));
    setManual({ planets: payment.planets, tradeGoods: next });
  };

  const submit = () =>
    run(async () => {
      if (!view.faction) return;
      await produce(
        view.faction,
        cart.map((l) => ({ baseType: l.baseType, count: l.count, zone: l.zone })),
        { planets: payment.planets, tradeGoods: payment.tradeGoods },
        aidaOn,
      );
      setCart([]);
      setManual(null);
      setUseAida(false);
    });

  const sorted = [...view.planets].sort(
    (a, b) =>
      Number(a.exhausted) - Number(b.exhausted) ||
      b.payValue - a.payValue ||
      a.name.localeCompare(b.name),
  );
  const readyRes = view.planets
    .filter((p) => !p.exhausted)
    .reduce((n, p) => n + p.payValue, 0);

  const unitName = (baseType: string) =>
    view.units.find((u) => u.baseType === baseType)?.name ?? baseType;

  const ships = view.units.filter((u) => u.placement === "space");
  const ground = view.units.filter((u) => u.placement === "planet");

  const card = (u: ProductionUnit) => {
    const n = countOf(cart, u.baseType);
    const blocked = whyNotAdd(view, cart, u, activeZone);
    const more = maxMore(view, cart, u, activeZone);
    return (
      <div className={styles.unitCard} key={u.baseType} data-active={n > 0 || undefined}>
        <div className={styles.unitSprite}>
          <Unit
            unitType={u.asyncId}
            colorAlias={player?.colorAlias ?? "gry"}
            faction={view.faction ?? undefined}
            scaleSprite
          />
        </div>
        <div className={styles.unitInfo}>
          <b>{u.name}</b>
          <span className={styles.costLine} title="Resource cost">
            <b>{fmt(u.cost)}</b>
            <i>res{u.unitsPerCost > 1 ? ` for ${u.unitsPerCost}` : ""}</i>
          </span>
          <small className={styles.onBoard}>
            On board: {u.onBoard}
            {n > 0 ? ` (+${n})` : ""}
          </small>
          <small className={styles.reinf}>
            {u.reinforcements === null
              ? "Tokens: no limit"
              : `Reserve: ${u.reinforcements - n}/${u.reinforcements}`}
          </small>
        </div>
        <span className={styles.maxBadge} title="How many more you can add right now">
          max +{more}
        </span>
        <div className={styles.stepper}>
          <button
            type="button"
            className={styles.stepBtn}
            disabled={n === 0 || busy}
            onClick={() => add(u, -1)}
            aria-label={`Fewer ${u.name}`}
          >
            <IconMinus size={18} />
          </button>
          <b className={styles.stepVal}>{n}</b>
          <button
            type="button"
            className={styles.stepBtn}
            disabled={blocked !== null || busy}
            title={blocked ?? `Add ${u.name}`}
            onClick={() => add(u, 1)}
            aria-label={`More ${u.name}`}
          >
            <IconPlus size={18} />
          </button>
        </div>
        {blocked && n === 0 && <small className={styles.why}>{blocked}</small>}
      </div>
    );
  };

  return createPortal(
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label={`Production in ${systemName}`}
      style={{ "--att-rgb": player?.rgb ?? "148 163 184" } as CSSProperties}
    >
      <div className={styles.backdrop} style={{ backgroundImage: BACKDROP }} aria-hidden="true" />
      <header className={styles.topBar}>
        <span className={styles.title}>
          <IconBuildingFactory2 size={18} aria-hidden="true" />
          {grant ? grant.source : "Production"}
          <small>
            {view.position} · {systemName}
          </small>
        </span>
        <span className={styles.topStats}>
          <span className={styles.stat}>
            <b>{view.remaining}</b> slots left
          </span>
          <span className={styles.stat} title="Ready resources + trade goods">
            <b>{readyRes}</b> res +{" "}
            <img className={styles.tgIcon} src="/tg.png" alt="Trade goods" />{" "}
            <b>{view.tradeGoods}</b>
          </span>
          <span className={styles.stat} data-kind="cost" data-bad={short > 0 || undefined}>
            Order cost <b>{fmt(cost)}</b>
          </span>
        </span>
        <span className={styles.topActions}>
          {view.faction && (
            <span className={styles.player}>
              <CircularFactionIcon faction={view.faction} size={22} />
              {player?.name}
            </span>
          )}
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => setHidden(true)}
            title="Hide the window and look at the map"
          >
            <IconMinimize size={14} aria-hidden="true" /> Hide
          </button>
        </span>
      </header>

      {notice && (
        <div className={styles.notice} data-kind={notice.kind} role="alert">
          <span>{notice.text}</span>
          <button type="button" onClick={clearNotice} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <p className={styles.hint}>
        {grant
          ? `${grant.source}: produce ${grant.units} unit in this system. ${
              grant.influenceAsResources
                ? "A planet's influence counts as resources (a planet pays with one or the other). "
                : ""
            }Ground forces go on a planet you control here, or to space. This is optional.`
          : "Pay with resources of ready planets and trade goods; overpaying is lost. Total units are capped by the PRODUCTION of your units in this system. Ground forces go only on planets with a producing unit."}
      </p>

      {/* Technologie działające w produkcji (Sarween Tools, AI Development Algorithm...). */}
      <ActiveTechs context="production" faction={view.faction} className={styles.techRow} />
      {(view.costReduction ?? 0) > 0 && (
        <p className={styles.hint}>
          Technology discount applied: <b>-{view.costReduction}</b> to the order cost.
        </p>
      )}

      <div className={styles.grid}>
        {/* --- Pojemność produkcji --- */}
        <section className={styles.panel} aria-label="Production capacity">
          <h3>Capacity</h3>
          <div className={styles.slotsHead}>
            <b>{free}</b>
            <span>more units can be produced</span>
          </div>
          <div className={styles.slots} role="img" aria-label={`${view.used} used, ${queued} queued, ${free} free of ${view.limit}`}>
            {Array.from({ length: view.limit }, (_, i) => {
              const state =
                i < view.used ? "used" : i < view.used + queued ? "queued" : "free";
              return (
                <span className={styles.slot} data-state={state} key={i}>
                  {state === "used" && <IconCheck size={14} aria-hidden="true" />}
                </span>
              );
            })}
          </div>
          <div className={styles.legend}>
            <span data-state="used">built {view.used}</span>
            <span data-state="queued">queued {queued}</span>
            <span data-state="free">free {free}</span>
          </div>

          <FleetPoolWarning extra={queuedShips} extraFighters={queuedFighters} />

          <h4>{grant ? "Granted production" : "Producing units"}</h4>
          <div className={styles.producers}>
            {grant && (
              <span className={styles.empty}>
                Limit comes from the card, not from PRODUCTION values.
              </span>
            )}
            {!grant && view.producers.length === 0 && (
              <span className={styles.empty}>No unit with PRODUCTION in this system.</span>
            )}
            {(grant ? [] : view.producers).map((p) => (
              <div className={styles.producer} key={`${p.zone}-${p.baseType}`}>
                <span className={styles.producerSprite}>
                  <Unit
                    unitType={p.asyncId}
                    colorAlias={player?.colorAlias ?? "gry"}
                    faction={view.faction ?? undefined}
                    scaleSprite
                  />
                </span>
                <span className={styles.producerText}>
                  <b>
                    {p.count > 1 ? `${p.count}× ` : ""}
                    {p.name}
                  </b>
                  <small>
                    {p.zone === SPACE ? "in space" : `on ${nameOf(p.zone)}`}
                    {p.count > 1 ? ` · PRODUCTION ${p.perUnit} each` : ""}
                  </small>
                  {p.forbids.length > 0 && (
                    <span className={styles.forbid}>
                      can&apos;t produce {p.forbids.map(unitName).join(", ")}
                    </span>
                  )}
                </span>
                <span className={styles.producerVal} title="PRODUCTION value">
                  {p.value}
                </span>
              </div>
            ))}
          </div>

          {!grant && view.producers.length > 1 && (
            <p className={styles.producerNote}>
              Each line is a separate PRODUCTION ability. Their values add up to the limit, but
              each keeps its own restrictions.
            </p>
          )}

          {view.blockaded && (
            <p className={styles.warn}>
              Enemy ships in the system: you cannot produce ships, only ground forces.
            </p>
          )}

          {zoneChoices.length > 0 && (
            <>
              <h4>Place ground forces on</h4>
              <div className={styles.zones}>
                {zoneChoices.map((z) => (
                  <button
                    type="button"
                    key={z}
                    className={styles.zoneChip}
                    data-active={z === activeZone || undefined}
                    aria-pressed={z === activeZone}
                    onClick={() => setZone(z)}
                  >
                    {nameOf(z)}
                  </button>
                ))}
              </div>
            </>
          )}
        </section>

        {/* --- Jednostki --- */}
        <section className={styles.panel} aria-label="Units">
          <h3>Units</h3>
          <h4>Ships · space</h4>
          <div className={styles.units}>{ships.map(card)}</div>
          {ground.length > 0 && (
            <>
              <h4>
                Ground forces · {activeZone ? nameOf(activeZone) : "no place"}
              </h4>
              <div className={styles.units}>{ground.map(card)}</div>
            </>
          )}
        </section>

        {/* --- Fundusze --- */}
        <section className={styles.panel} aria-label="Funds">
          <h3>Funds</h3>
          <div className={styles.fundsHead}>
            <b>{funds}</b>
            <span>to spend</span>
            <button
              type="button"
              className={styles.ghostBtn}
              onClick={() => setManual(null)}
              disabled={manual === null}
              title="Let the engine pick the cheapest payment"
            >
              <IconSparkles size={14} aria-hidden="true" /> Auto
            </button>
          </div>
          <div className={styles.planets}>
            {sorted.length === 0 && <span className={styles.empty}>You control no planets.</span>}
            {sorted.map((p) => {
              const chosen = payment.planets.includes(p.planet);
              // Te same karty planet co w strefach graczy; wyczerpanej nie da się wybrać.
              const pickable = !p.exhausted && !busy;
              return (
                <div
                  className={styles.planetSlot}
                  key={p.planet}
                  data-here={p.inActiveSystem || undefined}
                >
                  <PlanetCard
                    planetId={p.planet}
                    isExhausted={p.exhausted}
                    picked={chosen}
                    onPick={pickable ? () => togglePlanet(p.planet) : undefined}
                  />
                  {p.inActiveSystem && <small>here</small>}
                </div>
              );
            })}
          </div>

          <div className={styles.tgRow}>
            <span className={styles.tgLabel}>
              <img className={styles.tgIcon} src="/tg.png" alt="" aria-hidden="true" /> Trade goods
            </span>
            <span className={styles.stepper}>
              <button
                type="button"
                className={styles.stepBtn}
                disabled={payment.tradeGoods === 0 || busy}
                onClick={() => setTradeGoods(-1)}
                aria-label="Spend fewer trade goods"
              >
                <IconMinus size={18} />
              </button>
              <b className={styles.stepVal}>{payment.tradeGoods}</b>
              <button
                type="button"
                className={styles.stepBtn}
                disabled={payment.tradeGoods >= view.tradeGoods || busy}
                onClick={() => setTradeGoods(1)}
                aria-label="Spend more trade goods"
              >
                <IconPlus size={18} />
              </button>
            </span>
            <small>of {view.tradeGoods}</small>
          </div>

          <p className={styles.payLine} data-bad={short > 0 || undefined}>
            Paying <b>{paid}</b> of <b>{fmt(cost)}</b> needed
          </p>
        </section>
      </div>

      <footer className={styles.dock}>
        <section className={styles.queue} aria-label="Order">
          <h4>Order</h4>
          {cart.length === 0 ? (
            <span className={styles.empty}>Nothing queued. Add units above.</span>
          ) : (
            <div className={styles.chips}>
              {cart.map((l) => {
                const u = view.units.find((x) => x.baseType === l.baseType);
                return (
                  <span className={styles.chip} key={`${l.baseType}-${l.zone}`}>
                    <b>{l.count}×</b> {u?.name ?? l.baseType}
                    <small>{l.zone === SPACE ? "space" : nameOf(l.zone)}</small>
                    <button
                      type="button"
                      onClick={() => setCart((c) => bumpCart(c, l.baseType, l.zone, -l.count))}
                      aria-label={`Remove ${u?.name ?? l.baseType} from the order`}
                    >
                      ×
                    </button>
                  </span>
                );
              })}
            </div>
          )}
        </section>
        <div className={styles.costBox} data-state={costState} aria-live="polite">
          <span className={styles.costLabel}>Total cost</span>
          <span className={styles.costValue}>
            <b>{fmt(cost)}</b>
            <i>res</i>
          </span>
          <span className={styles.costStatus}>
            {costState === "short" && <IconAlertTriangle size={14} aria-hidden="true" />}
            {costState === "ok" && <IconCheck size={14} aria-hidden="true" />}
            {costState === "surplus" && <IconInfoCircle size={14} aria-hidden="true" />}
            {costState === "empty" && "Nothing queued"}
            {costState === "short" && `Short by ${fmt(short)}`}
            {costState === "ok" && "Fully covered"}
            {costState === "surplus" && `${fmt(wasted)} surplus is lost`}
          </span>
        </div>
        <div className={styles.dockActions}>
          <button
            type="button"
            className={styles.ghostBtn}
            disabled={cart.length === 0 || busy}
            onClick={() => {
              setCart([]);
              setManual(null);
            }}
          >
            <IconTrash size={14} aria-hidden="true" /> Clear
          </button>
          {view.aida?.ready && !grant && (
            <Switch
              size="xs"
              label={`Exhaust AI Development Algorithm (-${view.aida.discount} cost)`}
              checked={useAida}
              onChange={(event) => setUseAida(event.currentTarget.checked)}
              disabled={busy}
            />
          )}
          <button
            type="button"
            className={styles.primaryBtn}
            disabled={!canProduce}
            onClick={() => void submit()}
          >
            <IconBuildingFactory2 size={14} aria-hidden="true" />
            {queued > 0 ? `Produce ${queued} for ${fmt(cost)}` : "Produce"}
          </button>
          {grant || view.standalone ? (
            <button
              type="button"
              className={styles.ghostBtn}
              disabled={busy || queued > 0}
              title={
                queued > 0
                  ? "Produce or clear the order first"
                  : view.standalone
                    ? "Close the production and continue"
                    : "Do not produce"
              }
              onClick={() =>
                void run(async () => {
                  await skipProductionGrant();
                  void queryClient.invalidateQueries({ queryKey: ["exploration"] });
                })
              }
            >
              {view.standalone ? "Finish production" : "Skip production"}{" "}
              <IconArrowRight size={14} aria-hidden="true" />
            </button>
          ) : (
            <button
              type="button"
              className={styles.ghostBtn}
              disabled={busy || queued > 0}
              title={queued > 0 ? "Produce or clear the order first" : "Finish the tactical action"}
              onClick={() => void run(tacticalNextStep)}
            >
              Finish action <IconArrowRight size={14} aria-hidden="true" />
            </button>
          )}
        </div>
      </footer>
    </div>,
    document.body,
  );
}

/**
 * Okno PRODUKCJI (RULES.md 33.3) - pełnoekranowe, otwiera się samo w kroku PRODUCTION akcji
 * taktycznej. Pokazuje ile jednostek można zbudować (sloty), czym płacić (planety, TG) i prowadzi
 * zamówienie; walidację i płatność wykonuje silnik (`POST /tactical/produce`).
 */
export function ProductionOverlay() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const queryClient = useQueryClient();
  const hidden = useAppStore((s) => s.productionHidden);
  const setHidden = useAppStore((s) => s.setProductionHidden);
  const grantOpen = gameState?.productionGrant != null;
  // Okno produkcji otwiera się w kroku PRODUCTION ALBO przy jednorazowej produkcji z karty
  // (Freelancers z eksploracji, RULES.md 46).
  const active = gameState?.tacticalStep === "PRODUCTION" || grantOpen;
  const { data: view } = useProductionView(active);

  // Zmiana stanu gry (płatność, ruch innego gracza...) odświeża widok produkcji.
  useEffect(() => {
    if (active) {
      void queryClient.invalidateQueries({ queryKey: ["production"] });
      void queryClient.invalidateQueries({ queryKey: ["fleetPool"] });
    }
  }, [gameState, active, queryClient]);

  // Produkcja z karty otwiera okno od razu (gracz właśnie ją wybrał).
  useEffect(() => {
    if (grantOpen) setHidden(false);
  }, [grantOpen, setHidden]);

  // Poza krokiem PRODUCTION okno wraca do stanu zamkniętego - kolejna produkcja zaczyna się
  // od przycisku „Open production", a nie od okna wyskakującego samo.
  useEffect(() => {
    if (!active && !hidden) setHidden(true);
  }, [active, hidden, setHidden]);

  if (!active || !view?.active) return null;
  if (hidden) {
    return createPortal(
      <button
        type="button"
        className={styles.returnPill}
        onClick={() => setHidden(false)}
      >
        <IconBuildingFactory2 size={16} aria-hidden="true" />
        Open production
      </button>,
      document.body,
    );
  }
  return <ProductionWindow key={view.position} view={view} />;
}

export default ProductionOverlay;

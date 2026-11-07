import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import { useGameData } from "@/state/useGameContext";
import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard";
import { lookupUnit } from "@/entities/lookup/units";
import { playBattleSound, preloadBattleSounds } from "./battleSound";
import { IconShieldHalfFilled, IconSkull } from "@tabler/icons-react";
import { Unit } from "@/shared/ui/Unit";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { BattleSide } from "@/api/useBoardEditor";
import type { Mark, ShipEntity } from "./battleAssign";
import type { ShipView } from "./useBattleFx";
import styles from "./BattleOverlay.module.css";

/* Rozmiar okrętu na polu bitwy wg typu (asyncId): okręty liniowe wyraźnie większe od
   eskorty, myśliwce i piechota małe — skala oddaje „wagę" jednostki. */
const SHIP_SIZE: Record<string, number> = {
  ws: 180, // war sun — największa jednostka pola bitwy
  fs: 128,
  dn: 108,
  cv: 96,
  ca: 80,
  dd: 66,
  ff: 38,
  mf: 66,
  gf: 42,
};

/* Szereg w szyku bitewnym (0 = pierwsza linia, najbliżej przeciwnika): myśliwce i
   niszczyciele z przodu, okręty liniowe z tyłu; w walce naziemnej piechota przed mechami. */
const RANK: Record<string, number> = {
  ff: 0,
  gf: 0,
  dd: 1,
  mf: 1,
  ca: 2,
  cv: 3,
  dn: 4,
  fs: 5,
  ws: 5,
};

/** Czas wejścia formacji (zgodny z `fleetFly` w CSS, 5 s + zapas). */
const ENTRY_MS = 5400;
/** Wejście z war sunem trwa dłużej — wysuwanie z wormhole (`emerge*` w CSS, 10 s). */
const ENTRY_WS_MS = 10400;

/** Deterministyczne odchylenie (−max..max) z id okrętu — szyk nie stoi w idealnej linii. */
function jitter(id: string, salt: number, max: number): number {
  let h = salt * 2654435761;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return Math.round(((h % 1000) / 1000 - 0.5) * 2 * max);
}

/* DYSZE silników wg typu: przesunięcia w poprzek osi kadłuba (ułamek slotu), długość smugi
   (--el, ułamek slotu) i grubość (px). War sun bez silników (wyłania się z wormhole). */
const ENGINES: Record<
  string,
  { offsets: number[]; length: number; height: number }
> = {
  dd: { offsets: [0], length: 0.22, height: 5 },
  ca: { offsets: [-0.05, 0.05], length: 0.22, height: 4 },
  cv: { offsets: [-0.12, -0.04, 0.04, 0.12], length: 0.16, height: 3 },
  dn: { offsets: [-0.07, 0.07], length: 0.3, height: 6 },
  fs: { offsets: [-0.1, 0, 0.1], length: 0.34, height: 7 },
};

/** Jednostki „ciężkie": inne dźwięki, grubsze działa, specjalna aura (war sun, flagowiec). */
const HEAVY = new Set(["ws", "fs", "dn"]);

type UnitTag = { kind: "flagship" | "faction"; name: string };

function shipSize(asyncId: string): number {
  return SHIP_SIZE[asyncId] ?? 64;
}

/** „Życie" egzemplarza: 2 punkty (Sustain gotowy), 1 (uszkodzony/zwykły). */
function hpPips(ship: ShipEntity): { full: number; total: number } {
  if (ship.unit.sustain) return { full: ship.damaged ? 1 : 2, total: 2 };
  return { full: 1, total: 1 };
}

/** Grupuje egzemplarze w szeregi wg ``RANK`` (od pierwszej linii). */
function ranks(views: ShipView[]): ShipView[][] {
  const byRank = new Map<number, ShipView[]>();
  for (const view of views) {
    const rank = RANK[view.ship.asyncId] ?? 3;
    byRank.set(rank, [...(byRank.get(rank) ?? []), view]);
  }
  return [...byRank.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([, list]) => list);
}

function ShipToken({
  view,
  rank,
  index,
  count,
  side,
  colorAlias,
  faction,
  tag,
  mark,
  selectable,
  onToggle,
  onHover,
}: {
  view: ShipView;
  /** Podpis jednostki wyjątkowej (flagowiec) lub frakcyjnej; brak = zwykła jednostka. */
  tag: UnitTag | null;
  /** Najechanie / zjechanie kursorem — karta opisu jednostki jak na planszy. */
  onHover: (ship: ShipEntity | null, el?: HTMLElement) => void;
  rank: number;
  index: number;
  /** Liczba okrętów w szeregu — do ułożenia szyku w łuk (klin). */
  count: number;
  side: "left" | "right";
  colorAlias: string;
  faction: string;
  mark: Mark | undefined;
  selectable: boolean;
  onToggle: (ship: ShipEntity) => void;
}) {
  const { ship, dying, justSustained } = view;
  const size = shipSize(ship.asyncId);
  const pips = hpPips(ship);
  const label = `${ship.name}${ship.damaged ? " (damaged)" : ""}`;
  // Szyk-klin: okręty skrajne szeregu cofnięte względem środkowych (łuk ku wrogowi).
  const spread = Math.abs(index - (count - 1) / 2);
  const arcX = (side === "left" ? -1 : 1) * Math.round(spread * 22);
  const heavy = HEAVY.has(ship.asyncId);
  const engines = ENGINES[ship.asyncId];
  // Oś kadłuba MIERZONA z wyrenderowanego sprite'a (grafiki mają różne marginesy): środek
  // obrazka względem kadłuba (--ex/--ey) i odległość rufy od środka (--rear).
  const hullRef = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const hull = hullRef.current;
    const img = hull?.querySelector<HTMLElement>(".unit-sprite, img");
    if (!hull || !img) return;
    const h = hull.getBoundingClientRect();
    const r = img.getBoundingClientRect();
    hull.style.setProperty(
      "--ex",
      `${(r.left + r.width / 2 - (h.left + h.width / 2)).toFixed(1)}px`,
    );
    hull.style.setProperty(
      "--ey",
      `${(r.top + r.height / 2 - (h.top + h.height / 2)).toFixed(1)}px`,
    );
    // Obrazek obrócony ~45°: kadłub leży wzdłuż przekątnej; rufa ≈ 0,5 × przekątnej boku.
    const side = (img.offsetWidth + img.offsetHeight) / 2;
    hull.style.setProperty("--rear", `${(side * 0.5).toFixed(1)}px`);
  }, [size]);
  // Dźwięki zdarzeń okrętu: Sustain Damage i zniszczenie (wybuch opóźniony jak animacja).
  useEffect(() => {
    if (!justSustained) return;
    playBattleSound("sustain", { pan: side === "left" ? -0.5 : 0.5, heavy });
  }, [justSustained, side, heavy]);
  useEffect(() => {
    if (!dying) return;
    const t = window.setTimeout(
      () =>
        playBattleSound(heavy ? "explosionHeavy" : "explosion", {
          pan: side === "left" ? -0.5 : 0.5,
          heavy,
        }),
      1100,
    );
    return () => window.clearTimeout(t);
  }, [dying, side, heavy]);
  const style = {
    "--rank": rank,
    "--i": index,
    "--dir": side === "left" ? -1 : 1,
    "--jx": `${jitter(ship.id, 1, 8) + arcX}px`,
    "--jy": `${jitter(ship.id, 2, 12)}px`,
    "--slot": `${size}px`,
    "--ship-size": `${Math.round(size * 0.78)}px`,
  } as CSSProperties;
  const common = {
    className: styles.ship,
    style,
    "data-side": side,
    "data-base": ship.asyncId,
    "data-damaged": ship.damaged || undefined,
    "data-sustained": justSustained || undefined,
    "data-mark": mark,
    // Cel pocisków salwy — warstwa animacji mierzy położenia po tych atrybutach. Także
    // egzemplarze eksplodujące (np. myśliwce zestrzelone przez AFB w tej samej salwie):
    // pociski do nich dolatują, zanim wybuchną (wybuch jest opóźniony w CSS).
    "data-ship-side": side,
    "data-ship-base": ship.baseType,
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) =>
      onHover(ship, e.currentTarget),
    onMouseLeave: () => onHover(null),
  };
  const content = (
    <>
      <span className={styles.hull} ref={hullRef}>
        {ship.asyncId === "ws" && (
          <span className={styles.portal} aria-hidden="true" />
        )}
        {engines?.offsets.map((off, k) => (
          <span
            key={k}
            className={styles.engine}
            aria-hidden="true"
            style={
              {
                "--off": off,
                "--k": k,
                "--el": engines.length,
                "--eh": `${engines.height}px`,
              } as CSSProperties
            }
          />
        ))}
        {/* .emerge: nieobracana warstwa wyłaniania (war sun z wormhole, bokiem do przodu). */}
        <span className={styles.emerge}>
          <span className={styles.shipSprite}>
            <Unit
              unitType={ship.asyncId}
              colorAlias={colorAlias}
              faction={faction}
              scaleSprite
            />
          </span>
        </span>
      </span>
      {tag && (
        <span className={styles.unitTag} title={tag.name}>
          {tag.kind === "flagship" && <b>Flagship</b>}
          {tag.name}
        </span>
      )}
      <span
        className={styles.pips}
        aria-label={`${pips.full} of ${pips.total} hit points`}
      >
        {Array.from({ length: pips.total }, (_, i) => (
          <span
            key={i}
            className={styles.pip}
            data-full={i < pips.full || undefined}
          />
        ))}
      </span>
      {mark && (
        <span className={styles.markBadge} data-mark={mark}>
          {(mark === "sustain" || mark === "both") && (
            <IconShieldHalfFilled size={12} />
          )}
          {(mark === "destroy" || mark === "both") && <IconSkull size={12} />}
        </span>
      )}
      {justSustained && (
        <span className={styles.sustainFx} aria-hidden="true" />
      )}
      {justSustained &&
        Array.from({ length: 10 }, (_, i) => (
          <span
            key={`s${i}`}
            className={styles.sustainSpark}
            aria-hidden="true"
            style={
              {
                "--dx": `${jitter(ship.id, 200 + i, size * 0.7)}px`,
                "--dy": `${jitter(ship.id, 230 + i, size * 0.7)}px`,
              } as CSSProperties
            }
          />
        ))}
      {ship.damaged && !dying && (
        <span className={styles.damageFx} aria-hidden="true">
          {Array.from({ length: heavy ? 7 : 4 }, (_, i) => (
            <span
              key={i}
              className={styles.spark}
              style={
                {
                  "--x": `${50 + jitter(ship.id, 100 + i, 26)}%`,
                  "--y": `${50 + jitter(ship.id, 130 + i, 18)}%`,
                  "--sx": `${jitter(ship.id, 160 + i, 18)}px`,
                  "--d": `${(jitter(ship.id, 190 + i, 1500) + 1500) / 1000}s`,
                } as CSSProperties
              }
            />
          ))}
          {Array.from({ length: heavy ? 3 : 2 }, (_, i) => (
            <span
              key={`m${i}`}
              className={styles.smoke}
              style={
                {
                  "--x": `${50 + jitter(ship.id, 300 + i, 20)}%`,
                  "--y": `${50 + jitter(ship.id, 330 + i, 14)}%`,
                  "--d": `${(jitter(ship.id, 360 + i, 1800) + 1800) / 1000}s`,
                } as CSSProperties
              }
            />
          ))}
        </span>
      )}
      {dying && <span className={styles.explosion} aria-hidden="true" />}
      {dying &&
        Array.from({ length: heavy ? 14 : 7 }, (_, i) => (
          <span
            key={i}
            className={styles.debris}
            aria-hidden="true"
            style={
              {
                "--dx": `${jitter(ship.id, 10 + i, size)}px`,
                "--dy": `${jitter(ship.id, 40 + i, size)}px`,
                "--rot": `${jitter(ship.id, 70 + i, 540)}deg`,
              } as CSSProperties
            }
          />
        ))}
    </>
  );

  if (selectable && !dying) {
    return (
      <button
        type="button"
        {...common}
        data-selectable
        onClick={() => onToggle(ship)}
        title={`${label} — click to ${ship.canSustain ? "use Sustain Damage / destroy" : "destroy"}`}
        aria-pressed={mark !== undefined}
      >
        {content}
      </button>
    );
  }
  return (
    <div {...common} data-dying={dying || undefined} title={label}>
      {content}
    </div>
  );
}

/**
 * Kolumna jednej strony: nagłówek (frakcja, rola, kości, oczekiwane trafienia, pasek
 * życia), szyk bitewny (szeregi od pierwszej linii — myśliwce z przodu, okręty liniowe z
 * tyłu; wejście armady z boku) i spis jednostek z wartościami bojowymi. W kroku
 * przypisania strat okręty strony stają się klikalne.
 */
export function BattleFleet({
  side,
  views,
  align,
  name,
  colorAlias,
  maxHp,
  isWinner,
  assigning,
  marks,
  onToggle,
}: {
  side: BattleSide;
  views: ShipView[];
  align: "left" | "right";
  name: string;
  colorAlias: string;
  maxHp: number;
  isWinner: boolean;
  assigning: boolean;
  marks: Record<string, Mark>;
  onToggle: (ship: ShipEntity) => void;
}) {
  // Wejście armady gra tylko raz — późniejsze przemontowania okrętów (zmiana kroku) nie powtarzają go.
  const [entered, setEntered] = useState(false);
  useEffect(() => {
    const withWarSun = views.some((v) => v.ship.asyncId === "ws");
    const t = window.setTimeout(
      () => setEntered(true),
      withWarSun ? ENTRY_WS_MS : ENTRY_MS,
    );
    // Dźwięk: narastający pomruk lotu floty, a w chwili osiadania ciężki łoskot
    // (głębszy, gdy w szyku jest war sun / flagowiec / dreadnought).
    preloadBattleSounds();
    const pan = align === "left" ? -0.6 : 0.6;
    const hasHeavy = views.some((v) => HEAVY.has(v.ship.asyncId));
    playBattleSound("fleetEnter", { pan });
    // War sun: własny dźwięk (assets/extra/sfx/warSunEnter.mp3), gdy szczelina się otwiera.
    const warp = withWarSun
      ? window.setTimeout(() => playBattleSound("warSunEnter", { pan }), 1600)
      : undefined;
    const thud = window.setTimeout(
      () => playBattleSound(hasHeavy ? "arriveHeavy" : "arrive", { pan }),
      4500,
    );
    return () => {
      window.clearTimeout(t);
      window.clearTimeout(thud);
      window.clearTimeout(warp);
    };
    // Tylko przy montowaniu: wejście floty gra raz.
  }, []);
  // Podpisy: flagowiec zawsze; inne jednostki, gdy dane mają je jako frakcyjne (asset JSON).
  const gameData = useGameData();
  const player = gameData?.playerData?.find((p) => p.faction === side.faction);
  const tagOf = (asyncId: string, name: string): UnitTag | null => {
    if (asyncId === "fs") return { kind: "flagship", name };
    const data = lookupUnit(asyncId, side.faction, player);
    return data?.faction ? { kind: "faction", name } : null;
  };
  // Karta opisu jednostki przy najechaniu (ten sam UnitDetailsCard co na planszy). Portal do
  // body: pole bitwy drży przy salwach (`translate`), co psułoby pozycję `fixed` w środku.
  const [hover, setHover] = useState<{
    ship: ShipEntity;
    rect: DOMRect;
  } | null>(null);
  const onHover = (ship: ShipEntity | null, el?: HTMLElement) =>
    setHover(ship && el ? { ship, rect: el.getBoundingClientRect() } : null);
  const hoverUnitId = hover
    ? lookupUnit(hover.ship.asyncId, side.faction, player)?.id
    : undefined;
  const hpRatio = maxHp > 0 ? Math.max(0, side.hp / maxHp) : 0;
  return (
    <section
      className={styles.fleet}
      data-align={align}
      data-assigning={assigning || undefined}
      aria-label={`${side.role === "attacker" ? "Attacker" : "Defender"}: ${name}`}
    >
      <header className={styles.fleetHead}>
        <CircularFactionIcon faction={side.faction} size={38} />
        <div className={styles.fleetWho}>
          <span className={styles.role}>
            {side.role === "attacker" ? "Attacker" : "Defender"}
            {isWinner && <b className={styles.victor}>Victor</b>}
          </span>
          <b className={styles.fleetName}>{name}</b>
          <span className={styles.fleetStats}>
            {side.unitCount} unit{side.unitCount === 1 ? "" : "s"} ·{" "}
            {side.totalDice} dice · ~{side.expectedHits} hits
          </span>
        </div>
      </header>

      <div
        className={styles.hpBar}
        role="meter"
        aria-valuenow={side.hp}
        aria-valuemax={maxHp}
      >
        <span
          className={styles.hpFill}
          style={{ width: `${hpRatio * 100}%` }}
        />
        <span className={styles.hpText}>
          {side.hp} / {maxHp} HP
        </span>
      </div>

      <div
        className={styles.formation}
        data-formation={align}
        data-entered={entered || undefined}
      >
        {views.length === 0 && (
          <span className={styles.wiped}>Fleet destroyed</span>
        )}
        {ranks(views).map((rankViews, rank) => (
          <div
            key={rankViews[0].ship.asyncId}
            className={styles.rank}
            style={{ "--rank": rank } as CSSProperties}
          >
            {rankViews.map((view, i) => (
              <ShipToken
                key={view.ship.id}
                view={view}
                rank={rank}
                index={i}
                count={rankViews.length}
                side={align}
                colorAlias={colorAlias}
                faction={side.faction}
                tag={tagOf(view.ship.asyncId, view.ship.name)}
                onHover={onHover}
                mark={marks[view.ship.id]}
                selectable={assigning}
                onToggle={onToggle}
              />
            ))}
          </div>
        ))}
      </div>

      {hover &&
        hoverUnitId &&
        createPortal(
          <div
            className={styles.unitHover}
            style={{
              left:
                align === "left" ? hover.rect.right + 14 : hover.rect.left - 14,
              top: Math.max(
                12,
                Math.min(
                  hover.rect.top + hover.rect.height / 2 - 190,
                  window.innerHeight - 400,
                ),
              ),
              transform: align === "left" ? undefined : "translateX(-100%)",
            }}
            role="tooltip"
          >
            <UnitDetailsCard unitId={hoverUnitId} color={player?.color} />
          </div>,
          document.body,
        )}

      <table className={styles.roster}>
        <thead>
          <tr>
            <th>Unit</th>
            <th title="Hits on X+ × dice per unit">Combat</th>
            <th title="Anti-Fighter Barrage">AFB</th>
            <th title="Sustain Damage">Sustain</th>
          </tr>
        </thead>
        <tbody>
          {side.units.map((u) => (
            <tr key={u.baseType}>
              <td>
                <b>{u.count}×</b> {u.name}
                {u.damaged > 0 && (
                  <span className={styles.dmgTag}>{u.damaged} dmg</span>
                )}
              </td>
              <td>
                {u.hitsOn}+ ×{u.dicePerUnit}
                {u.modifier > 0 && (
                  <span className={styles.modTag}>+{u.modifier}</span>
                )}
              </td>
              <td>
                {u.afbHitsOn !== null ? `${u.afbHitsOn}+ ×${u.afbDice}` : "—"}
              </td>
              <td>{u.sustain ? `${u.sustainable}/${u.count}` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

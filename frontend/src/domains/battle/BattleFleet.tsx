import { useEffect, useState, type CSSProperties } from "react";
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
  ws: 150,
  fs: 138,
  dn: 100,
  cv: 84,
  ca: 72,
  dd: 62,
  ff: 36,
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

/** Czas wejścia formacji (zgodny z `armadaIn` w CSS, 5 s + zapas). */
const ENTRY_MS = 5400;

/** Deterministyczne odchylenie (−max..max) z id okrętu — szyk nie stoi w idealnej linii. */
function jitter(id: string, salt: number, max: number): number {
  let h = salt * 2654435761;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return Math.round(((h % 1000) / 1000 - 0.5) * 2 * max);
}

/** Jednostki „ciężkie": inne dźwięki, grubsze działa, specjalna aura (war sun, flagowiec). */
const HEAVY = new Set(["ws", "fs", "dn"]);

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
  mark,
  selectable,
  onToggle,
}: {
  view: ShipView;
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
  };
  const content = (
    <>
      <span className={styles.shipSprite}>
        <Unit
          unitType={ship.asyncId}
          colorAlias={colorAlias}
          faction={faction}
          scaleSprite
        />
      </span>
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
    const t = window.setTimeout(() => setEntered(true), ENTRY_MS);
    // Dźwięk: narastający pomruk lotu floty, a w chwili osiadania ciężki łoskot
    // (głębszy, gdy w szyku jest war sun / flagowiec / dreadnought).
    preloadBattleSounds();
    const pan = align === "left" ? -0.6 : 0.6;
    const hasHeavy = views.some((v) => HEAVY.has(v.ship.asyncId));
    playBattleSound("fleetEnter", { pan });
    const thud = window.setTimeout(
      () => playBattleSound(hasHeavy ? "arriveHeavy" : "arrive", { pan }),
      4500,
    );
    return () => {
      window.clearTimeout(t);
      window.clearTimeout(thud);
    };
    // Tylko przy montowaniu: wejście floty gra raz.
  }, []);
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
                mark={marks[view.ship.id]}
                selectable={assigning}
                onToggle={onToggle}
              />
            ))}
          </div>
        ))}
      </div>

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

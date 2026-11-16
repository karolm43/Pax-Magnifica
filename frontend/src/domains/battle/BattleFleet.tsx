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
  // War sun — największa jednostka pola bitwy. Grafika ma tylko 56×65 px: przy 180 była
  // rozciągana ~2,2× i wyglądała na rozpikselowaną; 136 (sprite ~106 px, ~1,6×) to kompromis
  // ostrość/rozmiar — wciąż większy od flagowca (128).
  ws: 136,
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

/*
 * UKŁAD SZEREGU:
 * - "wing": myśliwce w ESKADRACH po ≤5 — każda leci kluczem (prowadzący z przodu, skrzydłowi
 *   cofnięci po obu stronach), eskadry w 1–2 kolumnach; eskadra dryfuje razem jak jeden klucz.
 * - "double": liczny szereg (>5) w dwóch kolumnach z przesunięciem o pół okrętu (szachownica),
 *   zamiast jednej długiej, zmniejszonej linii.
 * - "column": jedna kolumna wygięta w klin (jak dotąd).
 */
type RankLayout = "column" | "double" | "wing";

/** Maksymalna liczebność eskadry myśliwców i próg szeregu dwukolumnowego. */
const SQUADRON = 5;
const DOUBLE_OVER = 5;
/** Klucz eskadry: cofnięcie skrzydłowego (ułamek slotu) i rozstaw w pionie. */
const WING_BACK = 0.95;
const WING_SIDE = 0.8;

function layoutOf(list: ShipView[]): RankLayout {
  if (list[0]?.ship.asyncId === "ff" && list.length > 2) return "wing";
  return list.length > DOUBLE_OVER ? "double" : "column";
}

/** Dzieli myśliwce na eskadry o RÓWNEJ liczebności (np. 7 → 4 + 3, nie 5 + 2). */
function squadrons(list: ShipView[]): ShipView[][] {
  const count = Math.ceil(list.length / SQUADRON);
  const out: ShipView[][] = [];
  let from = 0;
  for (let k = 0; k < count; k += 1) {
    const size = Math.ceil((list.length - from) / (count - k));
    out.push(list.slice(from, from + size));
    from += size;
  }
  return out;
}

/**
 * Pozycje w kluczu (px, w pudełku eskadry): prowadzący z przodu (od strony wroga), skrzydłowi
 * na przemian nad/pod nim, każdy kolejny o krok dalej w tył.
 */
function wingPlaces(n: number, slot: number, side: "left" | "right") {
  const steps = Array.from({ length: n }, (_, i) => {
    const k = Math.ceil(i / 2);
    return { back: k, lat: i === 0 ? 0 : i % 2 === 1 ? -k : k };
  });
  const maxBack = Math.max(...steps.map((s) => s.back));
  const minLat = Math.min(...steps.map((s) => s.lat));
  const maxLat = Math.max(...steps.map((s) => s.lat));
  const places = steps.map((s) => ({
    x: Math.round(
      (side === "left" ? maxBack - s.back : s.back) * WING_BACK * slot,
    ),
    y: Math.round((s.lat - minLat) * WING_SIDE * slot),
  }));
  return {
    places,
    width: Math.round(slot + maxBack * WING_BACK * slot),
    height: Math.round(slot + (maxLat - minLat) * WING_SIDE * slot),
  };
}

/*
 * Wlot floty gra RAZ na bitwę — także gdy okno schowano („Hide") i otwarto ponownie, co
 * montuje pole od nowa. Klucz = system + rodzaj + planeta + strona; czyszczone po walce.
 */
const ENTERED = new Set<string>();

/** Po zakończeniu walki kolejna bitwa w tym samym miejscu znów ma wlot floty. */
export function resetFleetEntries(): void {
  ENTERED.clear();
}

/**
 * SKALA SZYKU: okręty mają stałe rozmiary „wagi" (SHIP_SIZE), więc duża flota (war sun +
 * dreadnoughty + eskorta) wychodziła poza panel i była ucinana na krawędziach. Mierzymy
 * szeregi (offsetWidth/Height — bez transformacji animacji wejścia) i liczymy skalę, przy
 * której szyk mieści się w panelu z zapasem. Proporcje między typami zostają.
 */
function useFormationFit(views: ShipView[]) {
  const formationRef = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState(1);
  const signature = views.map((v) => v.ship.id).join(",");
  useLayoutEffect(() => {
    const el = formationRef.current;
    if (!el) return;
    const measure = () => {
      const rankEls = Array.from(el.children).filter((c) =>
        c.classList.contains(styles.rank),
      ) as HTMLElement[];
      if (rankEls.length === 0) return;
      const cs = getComputedStyle(el);
      const gaps = (parseFloat(cs.columnGap) || 0) * (rankEls.length - 1);
      const availW =
        el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const availH =
        el.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      if (availW <= 0 || availH <= 0) return;
      const usedW = rankEls.reduce((sum, r) => sum + r.offsetWidth, 0);
      const usedH = Math.max(...rankEls.map((r) => r.offsetHeight));
      setFit((prev) => {
        // Rozmiar „naturalny" (przy skali 1); odstępy między szeregami się nie skalują.
        const naturalW = usedW / prev;
        const naturalH = usedH / prev;
        const next = Math.max(
          0.4,
          Math.min(1, ((availW - gaps) * 0.92) / naturalW, (availH * 0.94) / naturalH),
        );
        return Math.abs(next - prev) < 0.02 ? prev : Math.round(next * 100) / 100;
      });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [signature, fit]);
  return { formationRef, fit };
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
  fit,
  layout,
  place,
  pickable,
  picked = false,
  pickLabel,
  onPick,
}: {
  /** Okręt zaznaczony w bieżącej decyzji „wskaż jednostkę”. */
  picked?: boolean;
  view: ShipView;
  /** Układ szeregu (klin kolumny, szachownica, klucz eskadry). */
  layout: RankLayout;
  /** Pozycja w kluczu eskadry (tylko ``layout === "wing"``). */
  place?: { x: number; y: number };
  /** Okręt można WSKAZAĆ dla decyzji (np. ofiara Assault Cannon) — klik zamiast formularza. */
  pickable: boolean;
  pickLabel?: string;
  onPick?: (ship: ShipEntity) => void;
  /** Skala szyku (0,4–1) — flota mieści się w panelu niezależnie od liczby okrętów. */
  fit: number;
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
  const { ship, dying, leaving, justSustained } = view;
  const size = Math.round(shipSize(ship.asyncId) * fit);
  const pips = hpPips(ship);
  const label = `${ship.name}${ship.damaged ? " (damaged)" : ""}`;
  // Szyk-klin: okręty skrajne szeregu cofnięte względem środkowych (łuk ku wrogowi).
  // Szachownica i klucz eskadry mają własny układ (bez łuku).
  const spread = Math.abs(index - (count - 1) / 2);
  const arcX =
    layout === "column"
      ? (side === "left" ? -1 : 1) * Math.round(spread * 22 * fit)
      : 0;
  const stagger = layout === "double" && index % 2 === 1 ? Math.round(size * 0.5) : 0;
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
    "--jx": place
      ? `${place.x}px`
      : `${Math.round(jitter(ship.id, 1, 8) * fit) + arcX}px`,
    "--jy": place
      ? `${place.y}px`
      : `${Math.round(jitter(ship.id, 2, 12) * fit) + stagger}px`,
    "--slot": `${size}px`,
    "--ship-size": `${Math.round(size * 0.78)}px`,
  } as CSSProperties;
  const common = {
    className: styles.ship,
    style,
    "data-side": side,
    "data-base": ship.asyncId,
    // Jednostki naziemne giną inaczej niż okręty (osuwają się i zapadają w pył, bez kuli ognia).
    "data-ground": ship.asyncId === "gf" || ship.asyncId === "mf" || undefined,
    "data-damaged": ship.damaged || undefined,
    "data-heavy": heavy || undefined,
    "data-sustained": justSustained || undefined,
    "data-mark": mark,
    "data-wing": place ? "" : undefined,
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
      {/* Ciężkie okręty: łańcuch wtórnych detonacji wzdłuż kadłuba (w trakcie konania,
          przed wybuchem reaktora) i rozbłysk, który oświetla cały panel floty. */}
      {dying &&
        heavy &&
        [0, 1, 2].map((i) => (
          <span
            key={`c${i}`}
            className={styles.chain}
            aria-hidden="true"
            style={
              {
                "--x": `${50 + jitter(ship.id, 400 + i, 28)}%`,
                "--y": `${50 + jitter(ship.id, 430 + i, 20)}%`,
                "--d": `${1.25 + i * 0.32}s`,
              } as CSSProperties
            }
          />
        ))}
      {dying && heavy && <span className={styles.lightFlash} aria-hidden="true" />}
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

  // ZAWSZE ten sam element (div): zamiana div ↔ button przy zmianie kroku przemontowywała
  // okręt i odtwarzała jego animacje. Klikalność = rola przycisku + klawiatura.
  const alive = !dying && !leaving;
  const picking = pickable && alive && onPick !== undefined;
  const interactive = (selectable && alive) || picking;
  const activate = () => {
    if (picking) onPick?.(ship);
    else if (selectable && alive) onToggle(ship);
  };
  return (
    <div
      {...common}
      data-dying={dying || undefined}
      data-leaving={leaving || undefined}
      data-selectable={interactive || undefined}
      data-pick={(picking && !picked) || undefined}
      data-picked={(picking && picked) || undefined}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-pressed={
        picking ? picked : selectable && alive ? mark !== undefined : undefined
      }
      aria-label={interactive ? label : undefined}
      onClick={interactive ? activate : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                activate();
              }
            }
          : undefined
      }
      title={
        picking
          ? picked
            ? `${label} — selected (click to unselect)`
            : `${label} — click: ${pickLabel ?? "choose this unit"}`
          : selectable && alive
            ? `${label} — click to ${ship.canSustain ? "use Sustain Damage / destroy" : "destroy"}`
            : label
      }
    >
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
  skipEntry,
  retreat,
  assigning,
  assignable,
  marks,
  onToggle,
  entryKey,
  pick,
}: {
  /** Tożsamość bitwy dla tej strony — wlot floty gra raz (także po Hide → powrót). */
  entryKey: string;
  /** Decyzja „wskaż okręt" (Assault Cannon, Devotion): które egzemplarze kliknąć i akcja. */
  pick?: {
    can: (ship: ShipEntity) => boolean;
    /** Okręt jest zaznaczony w tej decyzji (ponowny klik odznacza). */
    picked?: (ship: ShipEntity) => boolean;
    label: string;
    onPick: (ship: ShipEntity) => void;
  } | null;
  side: BattleSide;
  views: ShipView[];
  align: "left" | "right";
  name: string;
  colorAlias: string;
  maxHp: number;
  isWinner: boolean;
  /** Walka już ruszyła (rzut / straty) — wlot floty jest zakończony, okręty zostają na polu. */
  skipEntry: boolean;
  /** Odwrót strony (RULES.md 39.5): ogłoszony w tej rundzie, wykonywany teraz albo wykonany. */
  retreat: {
    state: "announced" | "withdrawing" | "withdrew";
    to: string | null;
  } | null;
  assigning: boolean;
  /** Które egzemplarze wolno oznaczyć przy przypisaniu (wymuszony cel: Devotion, Impulse Core). */
  assignable?: (ship: ShipEntity) => boolean;
  marks: Record<string, Mark>;
  onToggle: (ship: ShipEntity) => void;
}) {
  // Wejście armady gra tylko raz na bitwę — ponowne otwarcie okna (Hide) go nie powtarza.
  const [entered, setEntered] = useState(() => ENTERED.has(entryKey));
  const { formationRef, fit } = useFormationFit(views);
  useEffect(() => {
    if (ENTERED.has(entryKey)) return;
    ENTERED.add(entryKey);
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
    // Walka naziemna: obrońcy już stoją w szyku, atakujący SPADAJĄ z orbity — bez lotu floty.
    const ground =
      views.length > 0 &&
      views.every((v) => v.ship.asyncId === "gf" || v.ship.asyncId === "mf");
    if (ground) {
      const drops =
        align === "left"
          ? [900, 1250, 1600].map((ms) =>
              window.setTimeout(
                () => playBattleSound("impact", { pan, gain: 0.5 }),
                ms,
              ),
            )
          : [];
      return () => {
        window.clearTimeout(t);
        drops.forEach((d) => window.clearTimeout(d));
      };
    }
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
      data-retreat={retreat?.state}
      aria-label={`${side.role === "attacker" ? "Attacker" : "Defender"}: ${name}`}
    >
      <header className={styles.fleetHead}>
        <CircularFactionIcon faction={side.faction} size={38} />
        <div className={styles.fleetWho}>
          <span className={styles.role}>
            {side.role === "attacker" ? "Attacker" : "Defender"}
            {isWinner && <b className={styles.victor}>Victor</b>}
            {retreat && (
              <b className={styles.retreatTag} data-state={retreat.state}>
                {retreat.state === "announced"
                  ? "Retreat announced"
                  : retreat.state === "withdrawing"
                    ? "Withdrawing"
                    : "Withdrew"}
              </b>
            )}
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
        ref={formationRef}
        className={styles.formation}
        style={{ "--fit": fit } as CSSProperties}
        data-formation={align}
        data-entered={entered || skipEntry || undefined}
      >
        {views.length === 0 && (
          <span className={styles.wiped}>
            {retreat?.state === "withdrew"
              ? `Fleet withdrew${retreat.to ? ` to ${retreat.to}` : ""}`
              : "Fleet destroyed"}
          </span>
        )}
        {ranks(views).map((rankViews, rank) => {
          const layout = layoutOf(rankViews);
          const token = (
            view: ShipView,
            i: number,
            count: number,
            place?: { x: number; y: number },
          ) => (
            <ShipToken
              key={view.ship.id}
              view={view}
              rank={rank}
              index={i}
              count={count}
              side={align}
              colorAlias={colorAlias}
              faction={side.faction}
              tag={tagOf(view.ship.asyncId, view.ship.name)}
              onHover={onHover}
              mark={marks[view.ship.id]}
              selectable={assigning && (assignable?.(view.ship) ?? true)}
              onToggle={onToggle}
              fit={fit}
              layout={layout}
              place={place}
              pickable={pick?.can(view.ship) ?? false}
              picked={pick?.picked?.(view.ship) ?? false}
              pickLabel={pick?.label}
              onPick={pick?.onPick}
            />
          );
          if (layout === "wing") {
            const groups = squadrons(rankViews);
            const slot = Math.round(shipSize("ff") * fit);
            return (
              <div
                key={rankViews[0].ship.asyncId}
                className={styles.rank}
                data-layout="wing"
                data-cols={groups.length > 2 ? 2 : 1}
                style={
                  {
                    "--rank": rank,
                    "--cols": groups.length > 2 ? 2 : 1,
                  } as CSSProperties
                }
              >
                {groups.map((group, g) => {
                  const wing = wingPlaces(group.length, slot, align);
                  return (
                    <div
                      key={g}
                      className={styles.squadron}
                      style={
                        {
                          width: wing.width,
                          height: wing.height,
                          "--sq": g,
                        } as CSSProperties
                      }
                    >
                      {group.map((view, i) =>
                        token(view, i, group.length, wing.places[i]),
                      )}
                    </div>
                  );
                })}
              </div>
            );
          }
          return (
            <div
              key={rankViews[0].ship.asyncId}
              className={styles.rank}
              data-layout={layout}
              style={{ "--rank": rank } as CSSProperties}
            >
              {rankViews.map((view, i) => token(view, i, rankViews.length))}
            </div>
          );
        })}
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

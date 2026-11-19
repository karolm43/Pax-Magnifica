import {
  useLayoutEffect,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import { type Volley } from "./useBattleFx";

import {
  playBattleSound,
  } from "./battleSound";
import styles from "./BattleOverlay.module.css";

/* Okręty z ciężkim uzbrojeniem (war sun, flagowiec, dreadnought): grubsze wiązki i dźwięk. */
const HEAVY_BASES = new Set(["ws", "fs", "dn"]);

type ShotKind =
  | "laser"
  | "plasma"
  | "flak"
  | "sun"
  | "tracer"
  | "shell"
  | "missile";

/** Lot rakiety (ms) — wolniejsza od wiązek, łukiem, ze smugą dymu (`missileFly` w CSS). */
const MISSILE_MS = 1300;
/** Ile kłębów dymu zostawia rakieta na torze. */
const MISSILE_PUFFS = 14;
/* Okręty odpalające RAKIETY: krążowniki i lotniskowce zawsze, dreadnought co drugą kością. */
const MISSILE_BASES = new Set(["ca", "cv"]);

/** Czas lotu pocisku (ms): kule smugowe i flak są szybkie, reszta wolniejsza. */
const travelOf = (s: {
  afb: boolean;
  heavy?: boolean;
  ground?: "tracer" | "shell";
  missile?: boolean;
}) =>
  s.ground === "shell"
    ? s.heavy
      ? 1900
      : 1500
    : s.ground === "tracer"
      ? TRACER_MS
      : s.afb
      ? 550
      : s.missile
        ? MISSILE_MS
        : TRAVEL_MS;

/** Lot kuli smugowej piechoty (ms) — zgodny z `.beam[data-kind="tracer"]` w CSS. */
const TRACER_MS = 400;
/** Seria piechoty: tyle kul na jedną kość, co tyle ms. */
const BURST = 3;
const BURST_GAP_MS = 85;

/**
 * Broń jednostki w walce naziemnej: piechota strzela seriami z karabinu (kule smugowe),
 * mech i pozostałe (np. struktury) — z działa, pociskiem łukiem.
 */
export function groundWeapon(base: string): "tracer" | "shell" {
  return base === "gf" ? "tracer" : "shell";
}

/**
 * Odrzut strzelającej jednostki naziemnej (Web Animations, bez stanu Reacta): mech cofa się
 * ciężko po wystrzale z działa, piechota drga przy serii. `away` = kierunek od wroga (±1).
 */
function recoil(el: Element, kind: "tracer" | "shell", away: number, delayMs: number) {
  const sprite = el.querySelector(`.${styles.shipSprite}`);
  if (!sprite || typeof sprite.animate !== "function") return;
  const frames =
    kind === "shell"
      ? [
          { transform: "none" },
          { transform: `translate(${away * 8}px, -2px) rotate(${away * -3}deg)`, offset: 0.12 },
          { transform: `translate(${away * 3}px, 0)`, offset: 0.5 },
          { transform: "none" },
        ]
      : [
          { transform: "none" },
          { transform: `translateX(${away * 2}px)`, offset: 0.15 },
          { transform: "none", offset: 0.35 },
          { transform: `translateX(${away * 2}px)`, offset: 0.5 },
          { transform: "none", offset: 0.7 },
          { transform: `translateX(${away * 2}px)`, offset: 0.85 },
          { transform: "none" },
        ];
  sprite.animate(frames, {
    duration: kind === "shell" ? 520 : BURST * BURST_GAP_MS + 60,
    delay: Math.max(0, delayMs),
    easing: "ease-out",
  });
}

/**
 * Reakcja trafionej jednostki: biały błysk kadłuba i szarpnięcie od strony strzału (Web
 * Animations na właściwościach `translate`/`filter` — nie psują obrotu sprite'a z CSS).
 * `away` = kierunek od strzelca (±1); ciężkie trafienie szarpie mocniej.
 */
function flinch(el: Element, away: number, delayMs: number, heavy: boolean) {
  const sprite = el.querySelector(`.${styles.shipSprite}`);
  if (!sprite || typeof sprite.animate !== "function") return;
  const k = heavy ? 2 : 1;
  sprite.animate(
    [
      { translate: "0 0", filter: "brightness(1)" },
      { translate: `${away * 5 * k}px ${-1 * k}px`, filter: "brightness(2.6)", offset: 0.12 },
      { translate: `${away * -2 * k}px 0`, filter: "brightness(1.4)", offset: 0.35 },
      { translate: `${away * k}px 0`, offset: 0.6 },
      { translate: "0 0", filter: "brightness(1)" },
    ],
    { duration: heavy ? 520 : 380, delay: Math.max(0, delayMs), easing: "ease-out" },
  );
}

/** Rodzaj broni pocisku: AFB = flak; rakiety z krążowników; reszta laser (co 3.) i plazma. */
function shotKind(
  s: {
    afb: boolean;
    sun: boolean;
    ground?: "tracer" | "shell";
    missile?: boolean;
    orbital?: boolean;
  },
  n: number,
): ShotKind {
  if (s.orbital) return "plasma"; // bombardowanie z orbity: zawsze lanca plazmy
  if (s.ground) return s.ground;
  if (s.afb) return "flak";
  if (s.sun) return "sun"; // war sun: słoneczny ogień
  if (s.missile) return "missile";
  return n % 3 === 0 ? "laser" : "plasma";
}

/* Czas lotu pocisku (ms) — spójny z animacją `beamTravel` w CSS. */
const TRAVEL_MS = 900;

/* Grafika tła pola bitwy (podmienna przez użytkownika): plik w `assets/extra/`, serwowany
   przez backend pod `/static`. Brak pliku = brak obrazka (bez placeholdera). */
export const BATTLE_BACKGROUND: Record<"space" | "ground", string> = {
  space: "/static/extra/battle_background.jpg",
  ground: "/static/extra/battle_ground.jpg",
};

type Shot = {
  id: string;
  x1: number;
  y1: number;
  tx: number;
  ty: number;
  len: number;
  angle: number;
  hit: boolean;
  afb: boolean;
  delayMs: number;
  /** Strona, do której leci pocisk (cel). */
  target: "left" | "right";
  /** asyncId trafianej jednostki (dźwięk trafienia: pancerz mecha vs piechota). */
  targetBase: string;
  /** Element trafianej jednostki (reakcja na trafienie). */
  victim?: Element;
  /** Strzela okręt ciężki (war sun / flagowiec / dreadnought). */
  heavy: boolean;
  /** Strzela war sun (własny efekt: kula żaru z ładowaniem). */
  sun: boolean;
  /** Prototype War Sun Muaat (poziom "1"/"2") — gorętsza kula, większa pożoga. */
  proto?: string;
  /** Walka naziemna: kula smugowa albo pocisk artylerii (łukiem). */
  ground?: "tracer" | "shell";
  /** Znak łuku pocisku artylerii (−1, gdy tor biegnie w lewo). */
  arc: number;
  /** Rakieta: leci łukiem (punkt kontrolny krzywej) i zostawia smugę dymu. */
  missile: boolean;
  /** Bombardowanie z orbity w walce naziemnej (Harrow): lanca z góry pola, krater na ziemi. */
  orbital?: boolean;
  cx: number;
  cy: number;
};

/** Duży rozbłysk w środku pola strony, która dostaje trafienia. */
type Blast = {
  id: string;
  x: number;
  y: number;
  delayMs: number;
  power: number;
};

/**
 * Warstwa salwy: każdy pocisk startuje z KONKRETNEGO okrętu (typ, który rzucał kością) i
 * leci do okrętu przeciwnika — trafienie kończy się rozbłyskiem na celu, pudło mija cel.
 * Położenia mierzymy z DOM (atrybuty ``data-ship-side``/``data-ship-base`` okrętów) w chwili
 * salwy, względem pola bitwy. AFB celuje w myśliwce, gdy są.
 */
export function VolleyLayer({
  volley,
  fieldRef,
  ground,
}: {
  volley: Volley | null;
  fieldRef: RefObject<HTMLDivElement | null>;
  /** Walka naziemna: kule smugowe i artyleria zamiast laserów i plazmy. */
  ground: boolean;
}) {
  const [shots, setShots] = useState<{
    id: number;
    list: Shot[];
    blasts: Blast[];
  } | null>(null);

  useLayoutEffect(() => {
    const field = fieldRef.current;
    if (!volley || !field) return;
    const box = field.getBoundingClientRect();
    const center = (el: Element) => {
      const r = el.getBoundingClientRect();
      return {
        x: r.left - box.left + r.width / 2,
        y: r.top - box.top + r.height / 2,
      };
    };
    const query = (selector: string) => [...field.querySelectorAll(selector)];
    const list = volley.bolts.flatMap((bolt): Shot[] => {
      const enemy = bolt.from === "left" ? "right" : "left";
      const own = query(
        `[data-ship-side="${bolt.from}"][data-ship-base="${bolt.baseType}"]`,
      );
      const pool = own.length ? own : query(`[data-ship-side="${bolt.from}"]`);
      const fighters =
        volley.phase === "AFB"
          ? query(`[data-ship-side="${enemy}"][data-ship-base="fighter"]`)
          : [];
      // AFB celuje WYŁĄCZNIE w myśliwce (brak myśliwców = brak strzałów).
      const targets =
        volley.phase === "AFB"
          ? fighters
          : query(`[data-ship-side="${enemy}"]`);
      if (volley.phase === "BOMBARDMENT") {
        // Statki bombardujące są na orbicie (poza polem walki naziemnej): lanca plazmy spada
        // z góry pola na siły naziemne obrońcy; pudło rozrywa ziemię obok.
        if (targets.length === 0) return [];
        const victim = targets[Math.floor(Math.random() * targets.length)];
        const to = center(victim);
        const tx = bolt.hit ? to.x : to.x + (Math.random() - 0.5) * 110;
        const ty = bolt.hit ? to.y : to.y + 30 + Math.random() * 30;
        const x1 = tx + (Math.random() - 0.5) * 140;
        const y1 = -40;
        const dx = tx - x1;
        const dy = ty - y1;
        return [
          {
            id: bolt.id,
            x1,
            y1,
            tx,
            ty,
            len: Math.hypot(dx, dy),
            angle: (Math.atan2(dy, dx) * 180) / Math.PI,
            arc: 1,
            hit: bolt.hit,
            afb: false,
            delayMs: bolt.delayMs,
            target: enemy,
            targetBase: victim.getAttribute("data-base") ?? "",
            victim,
            heavy: true,
            sun: false,
            missile: false,
            orbital: true,
            cx: (x1 + tx) / 2,
            cy: (y1 + ty) / 2,
          },
        ];
      }
      if (pool.length === 0 || targets.length === 0) return [];
      const shooter = pool[bolt.shot % pool.length];
      const center0 = center(shooter);
      const victim = targets[Math.floor(Math.random() * targets.length)];
      const to = center(victim);
      // Pudło: pocisk mija cel (odchylenie w pionie i poziomie).
      const tx = bolt.hit ? to.x : to.x + (Math.random() - 0.5) * 90;
      const ty = bolt.hit
        ? to.y
        : to.y + (Math.random() < 0.5 ? -1 : 1) * (36 + Math.random() * 46);
      // Strzał wychodzi z KRAWĘDZI okrętu (od strony wroga), nie ze środka sprite'a.
      const sr = shooter.getBoundingClientRect();
      const reach = Math.min(sr.width, sr.height) * 0.42;
      const d0 = Math.hypot(tx - center0.x, ty - center0.y) || 1;
      // Walka naziemna: piechota strzela seriami z karabinu, mech to „ciężka artyleria"
      // (większy pocisk, wolniejszy, większy wybuch, odrzut przy wystrzale).
      const base = shooter.getAttribute("data-base") ?? "";
      const heavy = HEAVY_BASES.has(base) || (ground && base === "mf");
      const weapon = ground ? groundWeapon(base) : undefined;
      if (weapon) recoil(shooter, weapon, bolt.from === "left" ? -1 : 1, bolt.delayMs);
      const from = {
        x: center0.x + ((tx - center0.x) / d0) * reach,
        y: center0.y + ((ty - center0.y) / d0) * reach,
      };
      const dx = tx - from.x;
      const dy = ty - from.y;
      const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
      const missile =
        !ground &&
        volley.phase !== "AFB" &&
        (MISSILE_BASES.has(base) || (base === "dn" && bolt.shot % 2 === 1));
      // Łuk rakiety: punkt kontrolny odsunięty w bok od połowy toru (na przemian góra/dół).
      const len0 = Math.hypot(dx, dy) || 1;
      const bow =
        (bolt.shot % 2 === 0 ? 1 : -1) * len0 * (0.16 + Math.random() * 0.12);
      return [
        {
          id: bolt.id,
          x1: from.x,
          y1: from.y,
          tx,
          ty,
          len: Math.hypot(dx, dy),
          angle,
          arc: Math.abs(angle) > 90 ? -1 : 1,
          ground: weapon,
          hit: bolt.hit,
          afb: volley.phase === "AFB",
          delayMs: bolt.delayMs,
          target: enemy,
          targetBase: victim.getAttribute("data-base") ?? "",
          victim,
          heavy,
          sun: shooter.getAttribute("data-base") === "ws",
          // Prototype War Sun (Muaat): gorętsza salwa (data-proto okrętu = poziom 1/2).
          proto: shooter.getAttribute("data-proto") ?? undefined,
          missile,
          cx: (from.x + tx) / 2 + (-dy / len0) * bow,
          cy: (from.y + ty) / 2 + (dx / len0) * bow,
        },
      ];
    });
    // Rozbłysk w środku formacji każdej strony, która została trafiona (siła ~ liczba trafień).
    const blasts = (["left", "right"] as const).flatMap((side): Blast[] => {
      if (volley.phase === "AFB") return [];
      const hits = list.filter((s) => s.hit && s.target === side);
      const zone = field.querySelector(`[data-formation="${side}"]`);
      if (hits.length === 0 || !zone) return [];
      const c = center(zone);
      const last = Math.max(...hits.map((h) => h.delayMs));
      return [
        {
          id: `${volley.id}-blast-${side}`,
          x: c.x,
          y: c.y,
          delayMs: last + TRAVEL_MS,
          power: Math.min(hits.length, 6),
        },
      ];
    });
    // Seria piechoty = kilka kul tuż po sobie (dźwięk serii gra raz, na pierwszą kulę).
    const rendered = list.flatMap((s) =>
      s.ground === "tracer"
        ? Array.from({ length: BURST }, (_, k) => ({
            ...s,
            id: `${s.id}-b${k}`,
            delayMs: s.delayMs + k * BURST_GAP_MS,
            ty: s.ty + (k - 1) * 3,
          }))
        : [s],
    );
    setShots({ id: volley.id, list: rendered, blasts });

    // DŹWIĘKI salwy zsynchronizowane z animacją (wylot, trafienie). Limit, żeby duża
    // salwa nie zamieniła się w ścianę hałasu.
    const timers: number[] = [];
    let heard = 0;
    let impacts = 0;
    list.forEach((s, n) => {
      const pan = s.target === "right" ? -0.6 : 0.6; // strzela strona przeciwna do celu
      if (heard < 12 || s.heavy) {
        heard += 1;
        const kind = shotKind(s, n);
        timers.push(
          window.setTimeout(
            () =>
              playBattleSound(
                // Rodzaj broni = nazwa dźwięku; war sun ma własny „sunfire", piechota serię
                // z karabinu, mech wystrzał z działa.
                kind === "sun"
                  ? "sunfire"
                  : kind === "tracer"
                    ? "rifle"
                    : kind === "shell"
                      ? "mechCannon"
                      : kind,
                {
                  pan,
                  heavy: s.heavy && !s.ground,
                  gain: kind === "tracer" ? 0.45 : s.heavy ? 1 : 0.55,
                },
              ),
            s.delayMs,
          ),
        );
      }
      if (s.sun && s.hit) {
        timers.push(
          window.setTimeout(
            () => playBattleSound("explosion", { pan: -pan, gain: 0.7 }),
            s.delayMs + TRAVEL_MS,
          ),
        );
      }
      // Trafiona jednostka błyska i szarpie się w chwili trafienia (siła wg broni).
      if (s.hit && s.victim) {
        flinch(s.victim, s.target === "left" ? -1 : 1, s.delayMs + travelOf(s), s.heavy || s.sun);
      }
      // Trafienie: kula w ciało/pancerz, pocisk działa wybucha na ziemi (także przy pudle).
      const lands = s.hit || s.ground === "shell" || s.orbital;
      if (lands && impacts < 8) {
        impacts += 1;
        const sound =
          s.ground === "shell" || s.orbital
            ? "groundBlast"
            : s.ground === "tracer"
              ? s.targetBase === "mf"
                ? "armorHit"
                : "bulletHit"
              : "impact";
        timers.push(
          window.setTimeout(
            () =>
              playBattleSound(sound, {
                pan: -pan,
                heavy: s.heavy && !s.ground,
                gain: s.afb ? 0.4 : s.ground === "tracer" ? 0.5 : s.hit ? 0.8 : 0.55,
              }),
            s.delayMs + travelOf(s),
          ),
        );
      }
    });
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [volley, fieldRef, ground]);

  if (!volley || !shots || shots.id !== volley.id) return null;
  return (
    <div className={styles.volleyLayer} aria-hidden="true">
      {shots.list
        .filter((s) => s.missile)
        .flatMap((s) => {
          const path = `path('M ${s.x1.toFixed(1)} ${s.y1.toFixed(1)} Q ${s.cx.toFixed(1)} ${s.cy.toFixed(1)} ${s.tx.toFixed(1)} ${s.ty.toFixed(1)}')`;
          const vars = {
            "--path": path,
            "--rgb":
              s.target === "left" ? "var(--right-rgb)" : "var(--left-rgb)",
            "--delay": `${s.delayMs}ms`,
            "--travel": `${MISSILE_MS}ms`,
          };
          return [
            <span
              key={`${s.id}-missile`}
              className={styles.missile}
              data-hit={s.hit || undefined}
              style={vars as CSSProperties}
            />,
            ...Array.from({ length: MISSILE_PUFFS }, (_, k) => {
              const at = (k + 1) / (MISSILE_PUFFS + 1);
              return (
                <span
                  key={`${s.id}-puff-${k}`}
                  className={styles.puff}
                  style={
                    {
                      ...vars,
                      "--at": `${(at * 100).toFixed(1)}%`,
                      "--pdelay": `${Math.round(s.delayMs + MISSILE_MS * at)}ms`,
                    } as CSSProperties
                  }
                />
              );
            }),
          ];
        })}
      {shots.list.map((s, n) => (
        <span
          key={s.id}
          className={styles.beam}
          hidden={s.missile || undefined}
          data-kind={shotKind(s, n)}
          data-proto={s.proto}
          data-orbital={s.orbital || undefined}
          data-heavy={s.heavy || undefined}
          data-hit={s.hit || undefined}
          data-afb={s.afb || undefined}
          style={
            {
              left: s.x1,
              top: s.y1,
              width: s.len,
              transform: `rotate(${s.angle}deg)`,
              "--len": `${s.len}px`,
              "--rgb":
                s.target === "left" ? "var(--right-rgb)" : "var(--left-rgb)",
              "--delay": `${s.delayMs}ms`,
              "--arc": s.arc,
            } as CSSProperties
          }
        >
          <span className={styles.beamCore} />
          <span className={styles.beamLaser} />
        </span>
      ))}
      {shots.list.map((s) => (
        <span
          key={`${s.id}-muzzle`}
          className={styles.muzzle}
          data-sun={s.sun || undefined}
          data-proto={s.proto}
          data-ground={s.ground}
          style={
            {
              left: s.x1,
              top: s.y1,
              // War sun „ładuje" żar ~0,6 s przed wystrzałem.
              "--delay": `${s.sun ? s.delayMs - 600 : s.delayMs}ms`,
            } as CSSProperties
          }
        />
      ))}
      {shots.blasts.map((b) => (
        <span
          key={b.id}
          className={styles.blast}
          style={
            {
              left: b.x,
              top: b.y,
              "--delay": `${b.delayMs}ms`,
              "--power": b.power,
            } as CSSProperties
          }
        />
      ))}
      {shots.list
        .filter((s) => s.ground === "shell" || s.orbital)
        .map((s) => (
          <span
            key={`${s.id}-crater`}
            className={styles.crater}
            data-heavy={s.heavy || undefined}
            style={
              {
                left: s.tx,
                top: s.ty,
                "--delay": `${s.delayMs + travelOf(s)}ms`,
              } as CSSProperties
            }
          />
        ))}
      {shots.list
        .filter((s) => s.hit || s.ground === "shell" || s.orbital)
        .map((s) => (
          <span
            key={`${s.id}-impact`}
            className={styles.impact}
            data-miss={!s.hit || undefined}
            data-afb={s.afb || undefined}
            data-sun={s.sun || undefined}
            data-proto={s.proto}
            data-missile={s.missile || undefined}
            data-ground={s.ground || undefined}
            data-heavy={s.heavy || undefined}
            style={
              {
                left: s.tx,
                top: s.ty,
                "--delay": `${s.delayMs + travelOf(s)}ms`,
              } as CSSProperties
            }
          />
        ))}
    </div>
  );
}

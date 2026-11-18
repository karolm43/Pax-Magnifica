import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import {
  IconMinimize,
  IconSwords,
  IconVolume,
  IconVolumeOff,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import {
  useBattle,
  useBoardEditor,
  type BattleSide,
  type BattleView,
} from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { getColorAlias, resolvePrimaryRgb } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import {
  assignableShips,
  autoMarks,
  coveredCount,
  isCovered,
  planFromMarks,
  toggleMark,
  type Mark,
  type ShipEntity,
} from "./battleAssign";
import { useDyingShips, useMaxHp, useVolley, type Volley } from "./useBattleFx";
import { BattleFleet, resetFleetEntries } from "./BattleFleet";
import {
  INTENT_TTL_MS,
  NO_INTENT,
  useStableShips,
  type ShipIntent,
} from "./shipIdentity";
import { useOfferActions, useOffers, type OfferView } from "@/api/useOffers";
import { buildActionCardParams } from "@/api/useActionCard";
import { lookupUnit } from "@/entities/lookup/units";
import { asyncOfBase } from "@/domains/movement/routeTypes";
import type { BattleEffect } from "@/api/useBoardEditor";
import { BattleCenter, type PickNote } from "./BattleCenter";
import {
  canPick,
  complete,
  pickedAs,
  pickValues,
  shipPickSteps,
  togglePick,
  type PickState,
  type ShipPickStep,
} from "./shipPick";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import type { HoldState } from "@/domains/dice/HoldRollButton";
import { DiceTray } from "./DiceTray";
import { DicePool } from "./DicePool";
import { READ_MS, countDice, volleyStartMs } from "./diceRoll";
import { useDiceHold } from "@/domains/dice/useDiceHold";

/** Po starcie strzałów: odpowiedź obrońcy (1,5 s) + lot pocisków, zanim pokażemy straty. */
const HOLD_TAIL_MS = 3200;
import {
  isBattleMuted,
  playBattleSound,
  preloadBattleSounds,
  setBattleMuted,
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
  },
  n: number,
): ShotKind {
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
const BATTLE_BACKGROUND: Record<"space" | "ground", string> = {
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
  /** Walka naziemna: kula smugowa albo pocisk artylerii (łukiem). */
  ground?: "tracer" | "shell";
  /** Znak łuku pocisku artylerii (−1, gdy tor biegnie w lewo). */
  arc: number;
  /** Rakieta: leci łukiem (punkt kontrolny krzywej) i zostawia smugę dymu. */
  missile: boolean;
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
function VolleyLayer({
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
      const lands = s.hit || s.ground === "shell";
      if (lands && impacts < 8) {
        impacts += 1;
        const sound =
          s.ground === "shell"
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
        .filter((s) => s.ground === "shell")
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
        .filter((s) => s.hit || s.ground === "shell")
        .map((s) => (
          <span
            key={`${s.id}-impact`}
            className={styles.impact}
            data-miss={!s.hit || undefined}
            data-afb={s.afb || undefined}
            data-sun={s.sun || undefined}
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

function usePlayers() {
  const gameData = useGameData();
  return (key: string) => {
    const player = gameData?.playerData?.find((p) => p.faction === key);
    const rgb = player?.color ? resolvePrimaryRgb(player.color) : undefined;
    return {
      name: player ? getPlayerFactionDisplayName(player) : key,
      colorAlias: getColorAlias(player?.color),
      // Składowe ODDZIELONE SPACJAMI — CSS używa `rgb(var(--x) / alfa)`, a ta składnia
      // nie akceptuje przecinków (cała deklaracja tła byłaby odrzucona → przezroczyste okno).
      rgb: rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184",
    };
  };
}

function Battlefield({
  view,
  offersPending,
  reactionLabel,
}: {
  view: BattleView;
  /** W grze czekają decyzje graczy (``pendingOffers``) — sprawdź, czy któraś to „wskaż okręt". */
  offersPending: boolean;
  /** Trwa pauza ochronna (RULES.md 54.10) — etykieta okna; kroki walki czekają. */
  reactionLabel: string | null;
}) {
  const gameData = useGameData();
  const players = usePlayers();
  const setHidden = useAppStore((s) => s.setBattleHidden);
  const {
    battleAfb,
    battleAfbExtraDice,
    battleRoll,
    battleAssign,
    battleClose,
    battleAnnounceRetreat,
    battleRetreat,
  } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  const { data: offers } = useOffers(offersPending);
  // Kto może kliknąć za daną stronę: w sieci tylko ja; tryb lokalny i tryb testowy hosta
  // (bez miejsca) sterują każdym graczem.
  const { data: me } = useNetworkMe();
  const canAct = (playerId: string) =>
    !me?.network || !me.player_id || me.player_id === playerId;
  const offerActions = useOfferActions();
  const [muted, setMuted] = useState(isBattleMuted);
  useEffect(() => preloadBattleSounds(), []);
  const fieldRef = useRef<HTMLDivElement>(null);

  const attacker = view.attacker!;
  const defender = view.defender!;
  // Zamiar gracza (kliknięte egzemplarze) per strona: przy następnej zmianie składu giną /
  // przyjmują Sustain DOKŁADNIE te sztuki, a nie „ostatnie z typu” (silnik zna tylko liczby).
  const intents = useRef<Record<string, ShipIntent>>({});
  const intentOf = (key: string) => {
    const intent = intents.current[key];
    return intent && Date.now() - (intent.at ?? 0) < INTENT_TTL_MS ? intent : NO_INTENT;
  };
  const attackerShips = useStableShips(attacker, intentOf(attacker.faction), () => {
    delete intents.current[attacker.faction];
  });
  const defenderShips = useStableShips(defender, intentOf(defender.faction), () => {
    delete intents.current[defender.faction];
  });
  // Ostatni wykonany odwrót (wpis RETREAT na końcu dziennika) — jego statki ODLATUJĄ.
  const lastEntry = view.log.length > 0 ? view.log[view.log.length - 1] : null;
  const lastRetreat = lastEntry?.phase === "RETREAT" ? lastEntry.retreat : null;
  const leavingOf = (key: string) =>
    lastRetreat && lastRetreat.player === key ? lastRetreat.units : null;
  const attackerViews = useDyingShips(
    attackerShips,
    leavingOf(attacker.faction),
  );
  const defenderViews = useDyingShips(
    defenderShips,
    leavingOf(defender.faction),
  );

  // Dźwięki odwrotów: sygnał przy ogłoszeniu, świst silników przy odlocie.
  const retreatingCount = view.retreating.length;
  useEffect(() => {
    if (retreatingCount > 0) playBattleSound("retreatHorn");
  }, [retreatingCount]);
  const retreatLogKey = lastRetreat
    ? `${view.log.length}:${lastRetreat.player}`
    : null;
  const retreatSide = lastRetreat?.player === attacker.faction ? -0.6 : 0.6;
  useEffect(() => {
    if (retreatLogKey) playBattleSound("retreat", { pan: retreatSide });
  }, [retreatLogKey, retreatSide]);

  const systemLabel = (position: string) => {
    const t = gameData?.tiles?.[position];
    const name = t ? getTileById(t.systemId)?.name : undefined;
    return name ? `${name} (${position})` : position;
  };
  const retreatOf = (key: string) => {
    if (view.retreated[key]) {
      return {
        state: "withdrew" as const,
        to: systemLabel(view.retreated[key]),
      };
    }
    if (view.retreating.includes(key)) {
      return {
        state:
          view.step === "RETREAT"
            ? ("withdrawing" as const)
            : ("announced" as const),
        to: null,
      };
    }
    return null;
  };
  const attackerMax = useMaxHp(
    `${view.position}-${attacker.faction}`,
    attacker.hp,
  );
  const defenderMax = useMaxHp(
    `${view.position}-${defender.faction}`,
    defender.hp,
  );
  const volley = useVolley(view);
  // Kości toczą się po stole od początku salwy do chwili, gdy wszystkie leżą.
  const [rollingId, setRollingId] = useState<number | null>(null);
  const volleyId = volley?.id ?? null;
  const diceMs = volley?.diceMs ?? 0;
  useEffect(() => {
    if (volleyId === null || diceMs <= 0) return;
    setRollingId(volleyId);
    const t = window.setTimeout(() => setRollingId(null), diceMs);
    return () => window.clearTimeout(t);
  }, [volleyId, diceMs]);
  const rolling = volleyId !== null && rollingId === volleyId;
  // Pula kości: przytrzymanie „Roll" (hold) → puszczenie (await: czekamy na wynik z silnika,
  // kości lecą potem z puli) → zniknięcie, gdy kości są już na stole.
  const [pool, setPool] = useState<{
    phase: "off" | "hold" | "await";
    at: number;
    left: number;
    right: number;
  }>({ phase: "off", at: 0, left: 0, right: 0 });
  const diceOf = (s: BattleSide) =>
    view.step === "AFB"
      ? s.units.reduce(
          (n, u) => n + (u.afbHitsOn !== null ? u.count * u.afbDice : 0),
          0,
        )
      : s.totalDice;
  const onHold = (state: HoldState) => {
    if (state === "start") {
      setPool({
        phase: "hold",
        at: 0,
        left: diceOf(attacker),
        right: diceOf(defender),
      });
    } else if (state === "fire") {
      setPool((p) => ({ ...p, phase: "await", at: Date.now() }));
    } else {
      setPool((p) => ({ ...p, phase: "off" }));
    }
  };
  useEffect(() => {
    if (pool.phase !== "await") return;
    const t = window.setTimeout(
      () => setPool((p) => (p.phase === "await" ? { ...p, phase: "off" } : p)),
      3000,
    );
    return () => window.clearTimeout(t);
  }, [pool.phase]);
  const volleyFromPool =
    volley !== null &&
    pool.at > 0 &&
    volley.id >= pool.at &&
    volley.id - pool.at < 4000;
  const showPool =
    pool.phase === "hold" || (pool.phase === "await" && !volleyFromPool);
  // Walka dopiero się zaczyna (flota jeszcze wlatuje), a gracz już rzucił: pomiń wlot, żeby
  // statki zostały na polu, zamiast przemontować się i wlecieć drugi raz.
  const skipEntry = view.log.length > 0 || view.step === "ASSIGN";

  // Znaczniki strat są ważne tylko dla bieżącego przypisania (runda + gracz + salwa).
  const assignKey = `${view.round}:${view.assigning ?? ""}:${view.log.length}:${view.step}`;
  const [marksState, setMarksState] = useState<{
    key: string;
    marks: Record<string, Mark>;
  }>({ key: "", marks: {} });
  const assigningSide =
    view.assigning === attacker.faction
      ? attacker
      : view.assigning === defender.faction
        ? defender
        : null;
  const assigningShips =
    assigningSide === attacker
      ? attackerShips
      : assigningSide === defender
        ? defenderShips
        : [];
  const required = view.assigning ? (view.required[view.assigning] ?? 0) : 0;
  // Non-Euclidean Shielding: tarcza anuluje 2 trafienia (wartość z silnika).
  const cancels = assigningSide?.sustainCancels ?? 1;
  // Wymuszony cel (Devotion: statek wskazany przez Yin; Impulse Core: nie-myśliwce) - klikalne
  // tylko te okręty; gdy cel wskazał przeciwnik, znacznik stoi już na wskazanym statku.
  const hitTarget = view.assigning ? view.hitTargets?.[view.assigning] : undefined;
  const allowedShips = assignableShips(assigningShips, hitTarget, required);
  const allowedIds = new Set(allowedShips.map((s) => s.id));
  const presetMarks = hitTarget?.chooser
    ? autoMarks(allowedShips, required, cancels)
    : {};
  const marks = marksState.key === assignKey ? marksState.marks : presetMarks;
  const covered = coveredCount(marks, required, cancels);
  const ready = view.assigning !== null && isCovered(marks, required, cancels);

  const setMarks = (next: Record<string, Mark>) =>
    setMarksState({ key: assignKey, marks: next });

  // Nie pozwól pokryć więcej trafień, niż trzeba — wtedy znacznik znika.
  const toggle = (ship: ShipEntity) => {
    if (!allowedIds.has(ship.id)) return;
    setMarks(toggleMark(marks, ship, required, cancels));
  };
  const targetNote = (() => {
    if (!hitTarget || !assigningSide) return null;
    const names = hitTarget.types
      .map((t) => assigningSide.units.find((u) => u.baseType === t)?.name ?? t)
      .join(", ");
    const hits = hitTarget.count === 1 ? "the hit" : `${hitTarget.count} hits`;
    const state =
      hitTarget.damaged === true
        ? "damaged "
        : hitTarget.damaged === false
          ? "undamaged "
          : "";
    if (hitTarget.chooser) {
      return `${hitTarget.label}: ${players(hitTarget.chooser).name} assigned ${hits} to the ${state}${names}. Only that ship's Sustain Damage can cancel it.`;
    }
    return `${hitTarget.label}: assign ${hits} to ${names} if able.`;
  })();

  // Decyzje „wskaż jednostkę" (Assault Cannon, Duranium Armor, Devotion, Viscount Unlenn,
  // Evelyn DeLouis, Ambush…): jednostki z bieżącego pola decyzji są klikalne dla DECYDUJĄCEGO
  // gracza. Klik zaznacza (ponowny klik odznacza), decyzję zatwierdza „Confirm” w panelu
  // środkowym - przypadkowy klik niczego nie zużywa.
  const [pickStates, setPickStates] = useState<Record<string, PickState>>({});
  const forgetPick = (offerId: string) =>
    setPickStates((prev) => {
      const next = { ...prev };
      delete next[offerId];
      return next;
    });
  const picks = offersPending
    ? shipPickSteps(offers, [attacker.playerId, defender.playerId], pickStates)
    : new Map<string, ShipPickStep>();
  const pickFor = (side: BattleSide) => {
    const step = picks.get(side.playerId);
    if (!step || view.resolving || !canAct(step.offer.player_id)) return null;
    const { offer, state } = step;
    return {
      can: (ship: ShipEntity) => canPick(offer, state, ship, side.playerId),
      picked: (ship: ShipEntity) => pickedAs(offer, state, ship) !== null,
      label: `${offer.name} — ${step.input?.label ?? "selected"}`,
      onPick: (ship: ShipEntity) =>
        setPickStates((prev) => ({
          ...prev,
          [offer.id]: togglePick(offer, prev[offer.id] ?? {}, ship, side.playerId),
        })),
    };
  };
  const confirmPick = (offer: OfferView, state: PickState) => {
    // Wskazane egzemplarze (np. ofiara Assault Cannon) zmieniają się pierwsze — po obu stronach.
    const picked = new Set(Object.values(state).flatMap((byShip) => Object.keys(byShip)));
    for (const side of [attacker, defender]) {
      intents.current[side.faction] = { ...NO_INTENT, prefer: picked, at: Date.now() };
    }
    const { params } = buildActionCardParams(offer.inputs, pickValues(offer, state));
    void run(async () => {
      await offerActions.accept(offer.player_id, offer.id, params);
      forgetPick(offer.id);
    });
  };
  const skipPick = (offer: OfferView) =>
    void run(async () => {
      await offerActions.decline(offer.player_id, offer.id);
      forgetPick(offer.id);
    });
  // Jedna notka na decyzję (decyzja z jednostkami obu stron jest pod oboma właścicielami).
  const pickSteps = [...new Set(picks.values())];
  const pickNotes: PickNote[] = pickSteps.map((step) => {
    const { offer, input, state } = step;
    const decider = [attacker, defender].find(
      (s) => s.playerId === offer.player_id,
    );
    const chosen = offer.inputs.flatMap((field) =>
      Object.values(state[field.key] ?? {}).map((id) =>
        field.kind === "choice" || field.kind === "multi"
          ? (field.options.find((o) => o.id === id)?.label ?? id)
          : id,
      ),
    );
    const owners = input
      ? new Set(input.options.map((o) => o.meta?.player))
      : new Set<unknown>();
    const mode: PickNote["mode"] = !canAct(offer.player_id)
      ? "waiting"
      : me?.player_id === offer.player_id
        ? "you"
        : "control";
    return {
      key: offer.id,
      title: offer.name,
      who: decider ? players(decider.faction).name : offer.player_id,
      label: input?.label ?? null,
      whose:
        owners.size > 1 ? "any" : owners.has(offer.player_id) ? "own" : "enemy",
      many: input?.kind === "multi" ? input.max : 1,
      chosen,
      mode,
      onConfirm: complete(offer, state) ? () => confirmPick(offer, state) : undefined,
      onClear: chosen.length > 0 ? () => forgetPick(offer.id) : undefined,
      onSkip: offer.mandatory ? undefined : () => skipPick(offer),
    };
  });

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

  const a = players(attacker.faction);
  const d = players(defender.faction);
  const nameOf = (key: string) => players(key).name;
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName = tile
    ? (getTileById(tile.systemId)?.name ?? view.position)
    : view.position;
  const where =
    view.kind === "ground"
      ? `${view.planet ?? ""} · ${systemName ?? ""}`
      : (systemName ?? "");

  return (
    <div
      className={styles.overlay}
      // Okno pełnoekranowe: dok ręki zwija się do paska, a okno rezerwuje pod nim miejsce.
      data-fullscreen-overlay=""
      data-kind={view.kind ?? undefined}
      data-nebula={view.nebula || undefined}
      role="dialog"
      aria-modal="true"
      aria-label={`${view.kind === "ground" ? "Ground" : "Space"} combat: ${a.name} vs ${d.name}`}
      style={{ "--left-rgb": a.rgb, "--right-rgb": d.rgb } as CSSProperties}
    >
      {/* Miejsce na grafikę tła (assets/extra/battle_background.jpg / battle_ground.jpg)
          + przyciemnienie dla czytelności. Bez pliku zostaje ciemne tło z gwiazdami. */}
      <div
        className={styles.backdrop}
        style={{
          backgroundImage: `url("${BATTLE_BACKGROUND[view.kind === "ground" ? "ground" : "space"]}")`,
        }}
        aria-hidden="true"
      />
      <div className={styles.stars} aria-hidden="true" />
      <header className={styles.topBar}>
        <span className={styles.topTitle}>
          <IconSwords size={18} aria-hidden="true" />
          {view.kind === "ground" ? "Ground Combat" : "Space Combat"}
          <small>
            {view.position} · {where}
          </small>
        </span>
        <span className={styles.versus}>
          <b
            className={styles.vsName}
            style={{ "--c": a.rgb } as CSSProperties}
          >
            <span className={styles.vsDot} />
            {a.name}
          </b>
          <i>vs</i>
          <b
            className={styles.vsName}
            style={{ "--c": d.rgb } as CSSProperties}
          >
            <span className={styles.vsDot} />
            {d.name}
          </b>
        </span>
        <span className={styles.topActions}>
          <button
            type="button"
            className={styles.hideBtn}
            data-sound
            onClick={() => {
              setBattleMuted(!muted);
              setMuted(!muted);
            }}
            title={
              muted ? "Sound off — click to enable" : "Sound on — click to mute"
            }
            aria-pressed={!muted}
          >
            {muted ? (
              <IconVolumeOff size={15} aria-hidden="true" />
            ) : (
              <IconVolume size={15} aria-hidden="true" />
            )}
            {muted ? "Muted" : "Sound"}
          </button>
          <button
            type="button"
            className={styles.hideBtn}
            onClick={() => setHidden(true)}
            title="Hide the battle and look at the map (the combat keeps going)"
          >
            <IconMinimize size={15} aria-hidden="true" /> Hide
          </button>
        </span>
      </header>

      {/* Technologie obu stron działające w walce (Assault Cannon, Duranium Armor, Magen...). */}
      <div className={styles.techBar}>
        <ActiveTechs context="combat" faction={attacker.faction} label={a.name} />
        <ActiveTechs context="combat" faction={defender.faction} label={d.name} />
      </div>

      <div
        className={styles.field}
        ref={fieldRef}
        data-volley={volley ? volley.id : undefined}
        data-hits={volley?.bolts.some((b) => b.hit) || undefined}
        style={
          {
            "--dice-ms": `${volley ? volley.diceMs + READ_MS : 0}ms`,
          } as CSSProperties
        }
      >
        <RoundStamp round={view.round} kind={view.kind} />
        <BattleFleet
          side={attacker}
          views={attackerViews}
          align="left"
          name={a.name}
          colorAlias={a.colorAlias}
          maxHp={attackerMax}
          isWinner={view.winner === attacker.faction}
          skipEntry={skipEntry}
          retreat={retreatOf(attacker.faction)}
          assigning={
            view.step === "ASSIGN" && view.assigning === attacker.faction
          }
          marks={view.assigning === attacker.faction ? marks : {}}
          assignable={(ship) => allowedIds.has(ship.id)}
          onToggle={toggle}
          entryKey={`${view.position}|${view.kind}|${view.planet ?? ""}|${attacker.faction}`}
          pick={pickFor(attacker)}
          kind={view.kind === "ground" ? "ground" : "space"}
        />
        <BattleCenter
          view={view}
          nameOf={nameOf}
          colorOf={(key) => players(key).colorAlias}
          busy={busy}
          rolling={rolling}
          onHold={onHold}
          absorbed={covered}
          ready={ready}
          cancels={cancels}
          pickNotes={pickNotes}
          onAfb={() => void run(battleAfb)}
          onAfbExtra={(side, picks) => {
            const playerId = [view.attacker, view.defender].find((s) => s?.faction === side)?.playerId;
            if (playerId) void run(() => battleAfbExtraDice(playerId, picks));
          }}
          afbEditable={(side) => {
            const playerId = [view.attacker, view.defender].find((s) => s?.faction === side)?.playerId;
            return !!playerId && canAct(playerId);
          }}
          onRoll={() => void run(battleRoll)}
          onAuto={() => setMarks(autoMarks(allowedShips, required, cancels))}
          targetNote={targetNote}
          onClearMarks={() => setMarks({})}
          onConfirmAssign={() => {
            if (!view.assigning) return;
            const ids = (...kinds: Mark[]) =>
              new Set(
                Object.entries(marks)
                  .filter(([, m]) => kinds.includes(m))
                  .map(([id]) => id),
              );
            intents.current[view.assigning] = {
              destroy: ids("destroy", "both"),
              sustain: ids("sustain", "both"),
              prefer: new Set(),
              at: Date.now(),
            };
            void run(() =>
              battleAssign(
                view.assigning!,
                planFromMarks(assigningShips, marks),
              ),
            );
          }}
          onClose={() => void run(battleClose)}
          decisionsPending={offersPending}
          reactionLabel={reactionLabel}
          systemLabel={systemLabel}
          onAnnounce={(announce) =>
            view.announcing &&
            void run(() => battleAnnounceRetreat(view.announcing!, announce))
          }
          onRetreat={(destination, ionStormToken) =>
            view.retreating[0] &&
            void run(() => battleRetreat(view.retreating[0], destination, ionStormToken))
          }
        />
        <BattleFleet
          side={defender}
          views={defenderViews}
          align="right"
          name={d.name}
          colorAlias={d.colorAlias}
          maxHp={defenderMax}
          isWinner={view.winner === defender.faction}
          skipEntry={skipEntry}
          retreat={retreatOf(defender.faction)}
          assigning={
            view.step === "ASSIGN" && view.assigning === defender.faction
          }
          marks={view.assigning === defender.faction ? marks : {}}
          assignable={(ship) => allowedIds.has(ship.id)}
          onToggle={toggle}
          entryKey={`${view.position}|${view.kind}|${view.planet ?? ""}|${defender.faction}`}
          pick={pickFor(defender)}
          kind={view.kind === "ground" ? "ground" : "space"}
        />
        <VolleyLayer
          volley={volley}
          fieldRef={fieldRef}
          ground={view.kind === "ground"}
        />
        <AssaultCannonLayer
          effects={view.effects ?? []}
          fieldRef={fieldRef}
          attacker={attacker.faction}
          nameOf={nameOf}
          unitName={(faction, baseType) => {
            const player = gameData?.playerData?.find((p) => p.faction === faction);
            return lookupUnit(asyncOfBase(baseType), faction, player)?.name ?? baseType;
          }}
        />
        {showPool && <DicePool left={pool.left} right={pool.right} />}
        {volley && volley.diceMs > 0 && (
          <DiceTray
            key={volley.id}
            volley={volley}
            fromPool={volleyFromPool}
            pool={{ left: pool.left, right: pool.right }}
          />
        )}
      </div>
    </div>
  );
}

/**
 * Okno POLA BITWY (RULES.md 39) — pełnoekranowe, pojawia się samo, gdy trwa walka
 * (``gameState.activeCombat``). Floty wlatują z lewej (atakujący) i prawej (obrońca),
 * widać życie stron, wartości bojowe, salwy z animacją pocisków i wynik. Rzuty i straty
 * rozstrzyga silnik; okno tylko prowadzi i animuje. „Hide" chowa je na chwilę.
 */
/** Jak długo trzymać stan sprzed rzutu: kości na stole + salwa strzałów obu stron. */
function battleHoldMs(view: BattleView): number {
  const entry = view.log[view.log.length - 1];
  if (!entry || entry.phase === "RETREAT" || !view.attacker || !view.defender)
    return 0;
  const left = countDice(entry.rolls[view.attacker.faction] ?? []);
  const right = countDice(entry.rolls[view.defender.faction] ?? []);
  if (left + right === 0) return 0;
  return volleyStartMs(left, right) + HOLD_TAIL_MS;
}

/**
 * Widok z jednostkami i wynikiem sprzed rzutu; dziennik zostaje żywy (rusza animacja kości).
 * Do końca animacji nie zdradzamy też, KTO trafił: bez panelu przypisania strat (ile trafień
 * pokryć) i bez akcji kolejnego kroku — panel pokazuje „salwa w toku" (``resolving``).
 */
function freezeBattleSides(live: BattleView, before: BattleView): BattleView {
  return {
    ...live,
    attacker: before.attacker,
    defender: before.defender,
    winner: before.winner,
    outcome: before.outcome,
    assigning: null,
    required: {},
    pendingHits: {},
    resolving: true,
  };
}

export function BattleOverlay() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const hidden = useAppStore((s) => s.battleHidden);
  const setHidden = useAppStore((s) => s.setBattleHidden);
  const inCombat = gameState?.activeCombat != null;
  const { data: live } = useBattle(inCombat);
  // Straty z rzutu (np. auto-przypisane neutralnym albo AFB) pokazujemy dopiero po kościach i strzałach.
  const { view, holding } = useDiceHold(live, battleHoldMs, freezeBattleSides);
  // Po walce kolejna bitwa (także w tym samym systemie) znów ma wlot floty.
  const over = !inCombat && !holding;
  // Chwilowy brak walki w odczycie stanu (np. przejście kroku) nie może kasować pamięci wlotu —
  // inaczej flota wlatywała drugi raz. Kasujemy dopiero, gdy walki nie ma przez dłuższą chwilę.
  useEffect(() => {
    if (!over) return;
    const t = window.setTimeout(resetFleetEntries, 4000);
    return () => window.clearTimeout(t);
  }, [over]);
  const offersPending = (gameState?.pendingOffers ?? []).length > 0;

  if (
    (!inCombat && !holding) ||
    !view?.active ||
    !view.attacker ||
    !view.defender
  )
    return null;

  if (hidden) {
    return createPortal(
      <button
        type="button"
        className={styles.returnPill}
        onClick={() => setHidden(false)}
      >
        <IconSwords size={16} aria-hidden="true" />
        Battle in progress — return
      </button>,
      document.body,
    );
  }
  return createPortal(
    <Battlefield
      view={view}
      offersPending={offersPending}
      reactionLabel={gameState?.reactionPause?.label ?? null}
    />,
    document.body,
  );
}

export default BattleOverlay;

/**
 * Plansza nowej rundy: „ROUND 2" przecina pole bitwy na ~2 s, gdy silnik przechodzi do
 * kolejnej rundy (RULES.md 39 — walka toczy się rundami do wyniku). Runda 1 nie ma planszy:
 * jej wstępem jest wejście flot. Czysta prezentacja, bez wpływu na klik (pointer-events: none).
 */
function RoundStamp({ round, kind }: { round: number; kind: string | null | undefined }) {
  const first = useRef(round);
  if (round <= 1 || round === first.current) return null;
  return (
    <div key={round} className={styles.roundStamp} aria-hidden="true">
      <small>{kind === "ground" ? "Ground combat" : "Space combat"}</small>
      <b>Round {round}</b>
    </div>
  );
}

/** Okręt strzelający z Assault Cannon: największy z floty właściciela. */
const CANNON_PRIORITY = ["ws", "fs", "dn", "cv", "ca", "dd"];
/** Ładowanie działa przed strzałem (ms) — zgodne z `acCharge` w CSS. */
const CANNON_CHARGE_MS = 800;
/** Odstęp między kolejnymi strzałami (Assault Cannon obu stron). */
const CANNON_GAP_MS = 1500;

type CannonShot = {
  id: string;
  x1: number;
  y1: number;
  len: number;
  angle: number;
  tx: number;
  ty: number;
  delayMs: number;
};

/**
 * ASSAULT CANNON (C_technology): na starcie walki przeciwnik niszczy statek niemyśliwski.
 * Silnik dopisuje efekt do ``view.effects``; tu: plansza „ASSAULT CANNON" z opisem, ładowanie
 * działa na największym okręcie właściciela i ciężka wiązka do niszczonego okrętu (ten jest
 * jeszcze rysowany jako ginący — ``useDyingShips``), z rozbłyskiem w chwili trafienia.
 * Efekty sprzed otwarcia okna nie są odtwarzane (jak salwy z dziennika).
 */
function AssaultCannonLayer({
  effects,
  fieldRef,
  attacker,
  nameOf,
  unitName,
}: {
  effects: BattleEffect[];
  fieldRef: RefObject<HTMLDivElement | null>;
  attacker: string;
  nameOf: (key: string) => string;
  unitName: (faction: string, baseType: string) => string;
}) {
  const seen = useRef<number | null>(null);
  const latest = useRef(effects);
  latest.current = effects;
  const [run, setRun] = useState<{
    id: number;
    shots: CannonShot[];
    captions: { id: string; title: string; text: string; delayMs: number }[];
  } | null>(null);
  const length = effects.length;
  const describe = useRef({ nameOf, unitName });
  describe.current = { nameOf, unitName };

  useEffect(() => {
    if (seen.current === null || length < seen.current) {
      seen.current = length;
      return;
    }
    if (length === seen.current) return;
    const fresh = latest.current
      .slice(seen.current)
      .filter((e) => e.kind === "assault_cannon");
    seen.current = length;
    if (fresh.length === 0) return;
    const id = Date.now();
    // Chwila na przerysowanie: niszczony okręt pojawia się jako „ginący" (useDyingShips).
    const measure = window.setTimeout(() => {
      const field = fieldRef.current;
      if (!field) return;
      const box = field.getBoundingClientRect();
      const center = (el: Element) => {
        const r = el.getBoundingClientRect();
        return { x: r.left - box.left + r.width / 2, y: r.top - box.top + r.height / 2 };
      };
      const shots: CannonShot[] = [];
      const captions = fresh.map((e, k) => {
        const from = e.player === attacker ? "left" : "right";
        const to = from === "left" ? "right" : "left";
        const own = [...field.querySelectorAll(`[data-ship-side="${from}"]`)];
        const gun =
          CANNON_PRIORITY.map((b) =>
            own.find((el) => el.getAttribute("data-base") === b),
          ).find(Boolean) ?? own[0];
        const target =
          field.querySelector(
            `[data-ship-side="${to}"][data-ship-base="${e.unit}"][data-dying]`,
          ) ??
          field.querySelector(`[data-ship-side="${to}"][data-ship-base="${e.unit}"]`) ??
          field.querySelector(`[data-formation="${to}"]`);
        const delayMs = k * CANNON_GAP_MS;
        if (gun && target) {
          const a = center(gun);
          const b = center(target);
          shots.push({
            id: `${id}-${k}`,
            x1: a.x,
            y1: a.y,
            tx: b.x,
            ty: b.y,
            len: Math.hypot(b.x - a.x, b.y - a.y),
            angle: (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI,
            delayMs,
          });
        }
        window.setTimeout(
          () =>
            playBattleSound("assaultCannon", {
              pan: from === "left" ? -0.4 : 0.4,
              heavy: true,
            }),
          delayMs,
        );
        const { nameOf: n, unitName: u } = describe.current;
        return {
          id: `${id}-c${k}`,
          title: "Assault Cannon",
          text: `${n(e.player)} destroys ${n(e.victim)}'s ${u(e.victim, e.unit)}`,
          delayMs,
        };
      });
      setRun({ id, shots, captions });
    }, 60);
    const clear = window.setTimeout(
      () => setRun((r) => (r?.id === id ? null : r)),
      3600 + fresh.length * CANNON_GAP_MS,
    );
    return () => {
      window.clearTimeout(measure);
      window.clearTimeout(clear);
    };
  }, [length, attacker, fieldRef]);

  if (!run) return null;
  return (
    <div className={styles.volleyLayer} aria-hidden="true">
      {run.shots.map((s) => (
        <span key={s.id}>
          <span
            className={styles.acCharge}
            style={
              { left: s.x1, top: s.y1, "--delay": `${s.delayMs}ms` } as CSSProperties
            }
          />
          <span
            className={styles.acBeam}
            style={
              {
                left: s.x1,
                top: s.y1,
                width: s.len,
                // Osobna właściwość `rotate` — animacja wiązki skaluje ją (`scale`).
                rotate: `${s.angle}deg`,
                "--delay": `${s.delayMs + CANNON_CHARGE_MS}ms`,
              } as CSSProperties
            }
          />
          <span
            className={styles.acImpact}
            style={
              {
                left: s.tx,
                top: s.ty,
                "--delay": `${s.delayMs + CANNON_CHARGE_MS + 120}ms`,
              } as CSSProperties
            }
          />
        </span>
      ))}
      {run.captions.map((c) => (
        <div
          key={c.id}
          className={styles.acStamp}
          style={{ "--delay": `${c.delayMs}ms` } as CSSProperties}
        >
          <small>{c.title}</small>
          <b>{c.text}</b>
        </div>
      ))}
    </div>
  );
}

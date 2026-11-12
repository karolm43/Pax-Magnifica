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
  absorbed,
  autoMarks,
  expandShips,
  MARK_WEIGHT,
  nextMark,
  planFromMarks,
  type Mark,
  type ShipEntity,
} from "./battleAssign";
import { useDyingShips, useMaxHp, useVolley, type Volley } from "./useBattleFx";
import { BattleFleet } from "./BattleFleet";
import { BattleCenter } from "./BattleCenter";
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

type ShotKind = "laser" | "plasma" | "flak" | "sun" | "tracer" | "shell";

/** Czas lotu pocisku (ms): kule smugowe i flak są szybkie, reszta wolniejsza. */
const travelOf = (s: {
  afb: boolean;
  heavy?: boolean;
  ground?: "tracer" | "shell";
}) =>
  s.ground === "shell"
    ? s.heavy
      ? 1900
      : 1500
    : s.afb
      ? 550
      : TRAVEL_MS;

/** Rodzaj broni pocisku: AFB = flak; reszta na przemian laser (co 3.) i plazma. */
function shotKind(
  s: { afb: boolean; sun: boolean; ground?: "tracer" | "shell" },
  n: number,
): ShotKind {
  if (s.ground) return s.ground;
  if (s.afb) return "flak";
  if (s.sun) return "sun"; // war sun: słoneczny ogień
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
  /** Strzela okręt ciężki (war sun / flagowiec / dreadnought). */
  heavy: boolean;
  /** Strzela war sun (własny efekt: kula żaru z ładowaniem). */
  sun: boolean;
  /** Walka naziemna: kula smugowa albo pocisk artylerii (łukiem). */
  ground?: "tracer" | "shell";
  /** Znak łuku pocisku artylerii (−1, gdy tor biegnie w lewo). */
  arc: number;
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
      const to = center(targets[Math.floor(Math.random() * targets.length)]);
      // Pudło: pocisk mija cel (odchylenie w pionie i poziomie).
      const tx = bolt.hit ? to.x : to.x + (Math.random() - 0.5) * 90;
      const ty = bolt.hit
        ? to.y
        : to.y + (Math.random() < 0.5 ? -1 : 1) * (36 + Math.random() * 46);
      // Strzał wychodzi z KRAWĘDZI okrętu (od strony wroga), nie ze środka sprite'a.
      const sr = shooter.getBoundingClientRect();
      const reach = Math.min(sr.width, sr.height) * 0.42;
      const d0 = Math.hypot(tx - center0.x, ty - center0.y) || 1;
      // Walka naziemna: mech to „ciężka artyleria" (większy pocisk, wolniejszy, większy wybuch).
      const base = shooter.getAttribute("data-base") ?? "";
      const heavy = HEAVY_BASES.has(base) || (ground && base === "mf");
      const from = {
        x: center0.x + ((tx - center0.x) / d0) * reach,
        y: center0.y + ((ty - center0.y) / d0) * reach,
      };
      const dx = tx - from.x;
      const dy = ty - from.y;
      const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
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
          ground: ground ? "shell" : undefined,
          hit: bolt.hit,
          afb: volley.phase === "AFB",
          delayMs: bolt.delayMs,
          target: enemy,
          heavy,
          sun: shooter.getAttribute("data-base") === "ws",
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
    setShots({ id: volley.id, list, blasts });

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
                // Rodzaj broni = nazwa dźwięku; war sun ma własny „sunfire".
                kind === "sun"
                  ? "sunfire"
                  : kind === "tracer"
                    ? "flak"
                    : kind === "shell"
                      ? "plasma"
                      : kind,
                {
                  pan,
                  heavy: s.heavy,
                  gain: s.heavy ? 1 : 0.55,
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
      if (s.hit && impacts < 8) {
        impacts += 1;
        timers.push(
          window.setTimeout(
            () =>
              playBattleSound("impact", {
                pan: -pan,
                heavy: s.heavy,
                gain: s.afb ? 0.4 : 0.8,
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
      {shots.list.map((s, n) => (
        <span
          key={s.id}
          className={styles.beam}
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
        .filter((s) => s.hit)
        .map((s) => (
          <span
            key={`${s.id}-impact`}
            className={styles.impact}
            data-afb={s.afb || undefined}
            data-sun={s.sun || undefined}
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

function Battlefield({ view }: { view: BattleView }) {
  const gameData = useGameData();
  const players = usePlayers();
  const setHidden = useAppStore((s) => s.setBattleHidden);
  // Okno przykrywa panel komunikatów mapy — odrzucenia (422) pokazujemy tutaj.
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);
  const {
    battleAfb,
    battleRoll,
    battleAssign,
    battleClose,
    battleAnnounceRetreat,
    battleRetreat,
  } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  const [muted, setMuted] = useState(isBattleMuted);
  useEffect(() => preloadBattleSounds(), []);
  const fieldRef = useRef<HTMLDivElement>(null);

  const attacker = view.attacker!;
  const defender = view.defender!;
  const attackerShips = expandShips(attacker);
  const defenderShips = expandShips(defender);
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
  const assignKey = `${view.round}:${view.assigning ?? ""}:${view.log.length}`;
  const [marksState, setMarksState] = useState<{
    key: string;
    marks: Record<string, Mark>;
  }>({ key: "", marks: {} });
  const marks = marksState.key === assignKey ? marksState.marks : {};
  const assigningShips =
    view.assigning === attacker.faction
      ? attackerShips
      : view.assigning === defender.faction
        ? defenderShips
        : [];
  const required = view.assigning ? (view.required[view.assigning] ?? 0) : 0;
  const covered = absorbed(marks);

  const setMarks = (next: Record<string, Mark>) =>
    setMarksState({ key: assignKey, marks: next });

  const toggle = (ship: ShipEntity) => {
    const current = marks[ship.id];
    let candidate = nextMark(ship, current);
    const others = covered - (current ? MARK_WEIGHT[current] : 0);
    // Nie pozwól pokryć więcej trafień, niż trzeba — wtedy znacznik znika.
    while (candidate && others + MARK_WEIGHT[candidate] > required) {
      candidate = nextMark(ship, candidate);
    }
    const next = { ...marks };
    if (candidate) next[ship.id] = candidate;
    else delete next[ship.id];
    setMarks(next);
  };

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

      {notice && (
        <div className={styles.notice} data-kind={notice.kind} role="alert">
          <span>{notice.text}</span>
          <button type="button" onClick={clearNotice} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

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
          onToggle={toggle}
        />
        <BattleCenter
          view={view}
          nameOf={nameOf}
          busy={busy}
          rolling={rolling}
          onHold={onHold}
          absorbed={covered}
          onAfb={() => void run(battleAfb)}
          onRoll={() => void run(battleRoll)}
          onAuto={() => setMarks(autoMarks(assigningShips, required))}
          onClearMarks={() => setMarks({})}
          onConfirmAssign={() =>
            view.assigning &&
            void run(() =>
              battleAssign(
                view.assigning!,
                planFromMarks(assigningShips, marks),
              ),
            )
          }
          onClose={() => void run(battleClose)}
          systemLabel={systemLabel}
          onAnnounce={(announce) =>
            view.announcing &&
            void run(() => battleAnnounceRetreat(view.announcing!, announce))
          }
          onRetreat={(destination) =>
            view.retreating[0] &&
            void run(() => battleRetreat(view.retreating[0], destination))
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
          onToggle={toggle}
        />
        <VolleyLayer
          volley={volley}
          fieldRef={fieldRef}
          ground={view.kind === "ground"}
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

/** Widok z jednostkami i wynikiem sprzed rzutu; dziennik zostaje żywy (rusza animacja kości). */
function freezeBattleSides(live: BattleView, before: BattleView): BattleView {
  return {
    ...live,
    attacker: before.attacker,
    defender: before.defender,
    winner: before.winner,
    outcome: before.outcome,
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
  return createPortal(<Battlefield view={view} />, document.body);
}

export default BattleOverlay;

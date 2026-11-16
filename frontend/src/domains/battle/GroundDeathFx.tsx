import type { CSSProperties } from "react";
import { playBattleSound } from "./battleSound";
import fx from "./GroundCombat.module.css";

/**
 * ŚMIERĆ JEDNOSTEK NAZIEMNYCH (czysta prezentacja) — piechota i mech giną zupełnie inaczej:
 *
 * - PIECHOTA: kule trafiają (rozpryski pyłu na ciele), żołnierz zostaje odrzucony od wroga
 *   i pada na plecy, w miejscu upadku wzbija się kurz; leży chwilę, potem znika. Dźwięk:
 *   okrzyk i odgłos upadającego ciała.
 * - MECH: pancerz sypie iskrami, z kadłuba bije dym, reaktor żarzy się na czerwono i gaśnie
 *   (zawodzenie serw), maszyna osuwa się na kolana i wybucha — metalowe odłamki, pierścień
 *   pyłu na ziemi; zostaje płonący wrak, który dopala się do końca animacji.
 *
 * Ruch samego sprite'a (upadek / osunięcie) to `[data-ground-kind]` w `BattleOverlay.module.css`
 * (reguły na `.hull`); tu są warstwy efektów nad nim. Oś czasu jak w walce kosmicznej: pociski
 * dolatują przez ~1,1 s, dopiero potem jednostka ginie (`DYING_MS` = 3,8 s w `useBattleFx`).
 */

export type GroundKind = "infantry" | "mech";

/** Rodzaj jednostki naziemnej z asyncId (`gf` piechota, `mf` mech); reszta = nie naziemna. */
export function groundKindOf(asyncId: string): GroundKind | null {
  if (asyncId === "gf") return "infantry";
  if (asyncId === "mf") return "mech";
  return null;
}

/** Chwile (ms od oznaczenia jednostki jako zniszczonej) — zgodne z animacjami w CSS. */
export const GROUND_DEATH_TIMING = {
  infantry: { cry: 1150, fall: 1750 },
  mech: { powerDown: 1250, blast: 2150, collapse: 2300 },
} as const;

/*
 * Ograniczenie hałasu: gdy ginie cały oddział naraz, nie chcemy chóru krzyków. Ten sam
 * dźwięk nie częściej niż `limit` razy w oknie `windowMs`.
 */
const recent = new Map<string, number[]>();

/** Czy wolno teraz zagrać ten dźwięk (i zapisuje odtworzenie). Eksport dla testów. */
export function allowSound(
  key: string,
  limit: number,
  windowMs: number,
  now: number = performance.now(),
): boolean {
  const list = (recent.get(key) ?? []).filter((t) => now - t < windowMs);
  if (list.length >= limit) {
    recent.set(key, list);
    return false;
  }
  list.push(now);
  recent.set(key, list);
  return true;
}

/** Planuje dźwięki śmierci jednostki naziemnej; zwraca funkcję odwołującą zaplanowane. */
export function scheduleGroundDeathSounds(kind: GroundKind, pan: number): () => void {
  const at = (ms: number, play: () => void) => window.setTimeout(play, ms);
  const timers =
    kind === "infantry"
      ? [
          at(GROUND_DEATH_TIMING.infantry.cry, () => {
            if (allowSound("infantryDeath", 2, 700)) {
              playBattleSound("infantryDeath", { pan, gain: 0.55 });
            }
          }),
          at(GROUND_DEATH_TIMING.infantry.fall, () => {
            if (allowSound("bodyFall", 3, 300)) {
              playBattleSound("bodyFall", { pan, gain: 0.7 });
            }
          }),
        ]
      : [
          at(GROUND_DEATH_TIMING.mech.powerDown, () =>
            playBattleSound("mechPowerDown", { pan, gain: 0.6 }),
          ),
          at(GROUND_DEATH_TIMING.mech.blast, () =>
            playBattleSound("groundBlast", { pan, heavy: true }),
          ),
          at(GROUND_DEATH_TIMING.mech.collapse, () =>
            playBattleSound("mechCollapse", { pan, gain: 0.8 }),
          ),
        ];
  return () => timers.forEach((t) => window.clearTimeout(t));
}

/** Deterministyczny rozrzut (−1..1) z ziarna — efekty nie skaczą przy ponownym renderze. */
function wobble(seed: string, salt: number): number {
  let h = salt * 2654435761;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return ((h % 1000) / 1000 - 0.5) * 2;
}

function vars(v: Record<string, string | number>): CSSProperties {
  return v as CSSProperties;
}

/** Warstwy efektów śmierci (pył, iskry, dym, wybuch, wrak) nad konającą jednostką. */
export function GroundDeathFx({
  kind,
  seed,
  size,
}: {
  kind: GroundKind;
  /** Id egzemplarza — stały rozrzut efektów. */
  seed: string;
  /** Rozmiar slotu jednostki (px) — skala odłamków. */
  size: number;
}) {
  if (kind === "infantry") {
    return (
      <span className={fx.layer} data-kind="infantry" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <i
            key={`h${i}`}
            className={fx.bulletPuff}
            style={vars({
              "--x": `${50 + wobble(seed, 10 + i) * 18}%`,
              "--y": `${42 + wobble(seed, 20 + i) * 16}%`,
              "--d": `${1.1 + i * 0.09}s`,
            })}
          />
        ))}
        <i className={fx.fallDust} />
        {[0, 1, 2, 3].map((i) => (
          <i
            key={`p${i}`}
            className={fx.pebble}
            style={vars({
              "--dx": `${wobble(seed, 30 + i) * size * 0.45}px`,
              "--h": `${10 + Math.abs(wobble(seed, 40 + i)) * 14}px`,
            })}
          />
        ))}
      </span>
    );
  }
  return (
    <span className={fx.layer} data-kind="mech" aria-hidden="true">
      <i className={fx.reactor} />
      {Array.from({ length: 9 }, (_, i) => (
        <i
          key={`s${i}`}
          className={fx.armorSpark}
          style={vars({
            "--x": `${50 + wobble(seed, 50 + i) * 22}%`,
            "--y": `${40 + wobble(seed, 60 + i) * 18}%`,
            "--a": `${-90 + wobble(seed, 70 + i) * 70}deg`,
            "--len": `${14 + Math.abs(wobble(seed, 80 + i)) * 22}px`,
            "--d": `${1.1 + (i % 5) * 0.17}s`,
          })}
        />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <i
          key={`m${i}`}
          className={fx.plume}
          style={vars({
            "--x": `${50 + wobble(seed, 90 + i) * 14}%`,
            "--d": `${1.3 + i * 0.45}s`,
            "--drift": `${wobble(seed, 100 + i) * 16}px`,
          })}
        />
      ))}
      <i className={fx.mechBlast} />
      <i className={fx.groundRing} />
      {Array.from({ length: 10 }, (_, i) => (
        <i
          key={`d${i}`}
          className={fx.shard}
          style={vars({
            "--dx": `${wobble(seed, 110 + i) * size * 0.9}px`,
            "--up": `${18 + Math.abs(wobble(seed, 120 + i)) * size * 0.5}px`,
            "--rot": `${wobble(seed, 130 + i) * 720}deg`,
            "--w": `${4 + Math.abs(wobble(seed, 140 + i)) * 6}px`,
          })}
        />
      ))}
      {[0, 1, 2].map((i) => (
        <i
          key={`f${i}`}
          className={fx.wreckFire}
          style={vars({
            "--x": `${50 + (i - 1) * 16 + wobble(seed, 150 + i) * 6}%`,
            "--k": i,
          })}
        />
      ))}
    </span>
  );
}

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import type { BattleEffect } from "@/api/useBoardEditor";

import {
  playBattleSound,
  } from "./battleSound";
import styles from "./BattleOverlay.module.css";

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
export function AssaultCannonLayer({
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

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { IconDice5 } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import { isHit, type DiceGroup } from "@/domains/battle/diceRoll";
import { useDiceStage } from "./diceStage";
import styles from "./TableRoll.module.css";

type Toast = {
  seq: number;
  who: string;
  label: string;
  summary: string;
  hits: number;
  total: number;
};

/**
 * Rzuty kośćmi spoza walki (The Fracture, karty akcji…): silnik zapisuje je w
 * ``gameState.tableRoll`` (``core.dice.record_table_roll``), a ten komponent odtwarza je
 * fizycznymi kośćmi (``useDiceStage``) i PO wylądowaniu pokazuje wynik. Rzut, który już był w
 * stanie przy otwarciu strony, nie jest odtwarzany. Montowany raz na stronie gry.
 */
export function TableRollWatcher() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const look = usePlayerLook();
  const throwDice = useDiceStage((s) => s.throwDice);
  const roll = gameState?.tableRoll ?? null;
  const seq = roll?.seq ?? 0;
  const seen = useRef<number | undefined>(undefined);
  const [toast, setToast] = useState<Toast | null>(null);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    if (gameState === undefined) return;
    if (seen.current === undefined) {
      seen.current = seq; // pierwszy odczyt: stary rzut nie jest nowością
      return;
    }
    if (!roll || seq <= seen.current) {
      seen.current = Math.max(seen.current, seq);
      return;
    }
    seen.current = seq;
    const faction =
      gameData?.playerData?.find((p) => p.discordId === roll.playerId)
        ?.faction ?? roll.playerId;
    const who = look(faction);
    const group: DiceGroup = {
      dice: roll.dice,
      modifier: 0,
      hitsOn: roll.hitsOn ?? 99,
      hitValues: roll.hitValues,
    };
    const { pauseMs } = throwDice({ left: [group], leftRgb: who.rgb });
    const hits = roll.dice.filter((v) => isHit(group, v)).length;
    // Liczniki żyją poza cyklem efektu (efekt odpala się przy każdym renderze - ``look`` jest
    // nową funkcją); sprząta je dopiero odmontowanie.
    timers.current.push(
      window.setTimeout(
        () =>
          setToast({
            seq,
            who: who.name,
            label: roll.label,
            summary: roll.summary,
            hits,
            total: roll.dice.length,
          }),
        pauseMs,
      ),
      window.setTimeout(
        () => setToast((t) => (t?.seq === seq ? null : t)),
        pauseMs + 7000,
      ),
    );
  }, [gameState, roll, seq, gameData, look, throwDice]);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((t) => window.clearTimeout(t));
  }, []);

  if (!toast) return null;
  return createPortal(
    <div
      className={styles.toast}
      data-success={toast.hits > 0 || undefined}
      role="status"
    >
      <span className={styles.icon}>
        <IconDice5 size={22} aria-hidden="true" />
      </span>
      <span className={styles.text}>
        <b>
          {toast.who}: {toast.label}
        </b>
        <small>{toast.summary}</small>
      </span>
      <button
        type="button"
        className={styles.dismiss}
        onClick={() => setToast(null)}
      >
        OK
      </button>
    </div>,
    document.body,
  );
}

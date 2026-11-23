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
import { latestTableRollSeq, pendingTableRolls } from "./tableRolls";
import styles from "./TableRoll.module.css";

/** Przerwa po wylądowaniu kości, zanim poleci rzut następnego gracza (czas na odczyt wyniku). */
const NEXT_ROLL_GAP_MS = 1500;

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
 * ``gameState.tableRolls`` (``core.dice.record_table_roll``), a ten komponent odtwarza je
 * fizycznymi kośćmi (``useDiceStage``) i PO wylądowaniu pokazuje wynik. Kilka nowych rzutów
 * naraz (np. każdy przeciwnik przy Dimensional Anchor) leci PO KOLEI, każdy w kolorze gracza.
 * Rzut, który już był w stanie przy otwarciu strony, nie jest odtwarzany. Montowany raz na
 * stronie gry.
 */
export function TableRollWatcher() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const look = usePlayerLook();
  const throwDice = useDiceStage((s) => s.throwDice);
  const seq = latestTableRollSeq(gameState);
  const seen = useRef<number | undefined>(undefined);
  const [toast, setToast] = useState<Toast | null>(null);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    if (gameState === undefined) return;
    if (seen.current === undefined) {
      seen.current = seq; // pierwszy odczyt: stare rzuty nie są nowością
      return;
    }
    if (seq <= seen.current) {
      // Licznik spadł (nowa gra, Undo): zapamiętaj nowy punkt odniesienia, inaczej pierwsze
      // rzuty nowej gry (seq 1, 2…) byłyby uznane za stare i pominięte.
      seen.current = seq;
      return;
    }
    const rolls = pendingTableRolls(gameState, seen.current);
    seen.current = seq;
    // Liczniki żyją poza cyklem efektu (efekt odpala się przy każdym renderze - ``look`` jest
    // nową funkcją); sprząta je dopiero odmontowanie.
    const play = (index: number) => {
      const roll = rolls[index];
      if (!roll) return;
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
      timers.current.push(
        window.setTimeout(
          () =>
            setToast({
              seq: roll.seq,
              who: who.name,
              label: roll.label,
              summary: roll.summary,
              hits,
              total: roll.dice.length,
            }),
          pauseMs,
        ),
        window.setTimeout(
          () => setToast((t) => (t?.seq === roll.seq ? null : t)),
          pauseMs + 7000,
        ),
      );
      if (index + 1 < rolls.length) {
        timers.current.push(
          window.setTimeout(() => play(index + 1), pauseMs + NEXT_ROLL_GAP_MS),
        );
      }
    };
    play(0);
  }, [gameState, seq, gameData, look, throwDice]);

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

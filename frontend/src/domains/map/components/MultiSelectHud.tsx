import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { useAppStore } from "@/state/appStore";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { DEFAULT_GAME_ID } from "@/config";
import { summarizeSelection } from "./UnitStack/selectionCapacity";
import styles from "./MultiSelectHud.module.css";

/**
 * Plakietka przy kursorze pokazująca zaznaczenie Ctrl+klik: liczbę zaznaczonych
 * jednostek i zajęcie/pojemność (ładunek / capacity zaznaczonych nosicieli).
 * Esc (lub koniec akcji taktycznej) czyści zaznaczenie.
 */
export function MultiSelectHud() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const selection = useAppStore((s) => s.multiSelect);
  const clear = useAppStore((s) => s.clearMultiSelect);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const active = selection !== null;

  useEffect(() => {
    if (!active) return;
    const onMove = (e: PointerEvent) => setPos({ x: e.clientX, y: e.clientY });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") clear();
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("keydown", onKey);
    };
  }, [active, clear]);

  // Koniec akcji taktycznej (brak aktywnego systemu) unieważnia zaznaczenie.
  const hasActiveSystem = (gameState?.activeSystem ?? null) !== null;
  useEffect(() => {
    if (active && gameState && !hasActiveSystem) clear();
  }, [active, gameState, hasActiveSystem, clear]);

  if (!selection) return null;
  const sum = summarizeSelection(selection, gameData?.playerData);
  const over = sum.used > sum.capacity;
  return createPortal(
    <div
      className={styles.hud}
      style={{ left: `${pos.x + 16}px`, top: `${pos.y + 16}px` }}
      data-over={over || undefined}
      aria-hidden="true"
    >
      <span>Selected {sum.total}</span>
      <span className={styles.cap}>
        Cap {sum.used}/{sum.capacity}
      </span>
    </div>,
    document.body,
  );
}

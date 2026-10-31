import type { ReactElement } from "react";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor, useStrategyCards } from "@/api/useBoardEditor";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import { DEFAULT_GAME_ID } from "@/config";
import styles from "./StrategyCardTable.module.css";

/* Initiative → sygnał koloru dysku (spójnie z pickerem w GameStatePanel). */
const SC_TONE: Record<number, string> = {
  1: "var(--gd-red)",
  2: "var(--gd-orange)",
  3: "var(--gd-yellow)",
  4: "var(--gd-green)",
  5: "var(--gd-teal)",
  6: "var(--gd-cyan)",
  7: "var(--gd-blue)",
  8: "var(--gd-purple)",
};

/**
 * Card_Table_View (Requirement 1, 8) — widok kart strategii „na stole" w stylu
 * AsyncTI4, montowany jako nakładka nad mapą OBOK istniejącego ``GameStatePanel``
 * (który ZOSTAJE jako alternatywny picker, Requirement 8.2). Oba czytają ten sam
 * ``gameData``/``useStrategyCards``, więc odzwierciedlają ten sam stan gry.
 *
 * To ZADANIE 9.1 to SZKIELET: poprawny gating fazy, podłączone hooki i wstępny,
 * minimalny render listy kart (initiative + nazwa + TG). Pełna grafika kart
 * (AsyncTI4), oznaczenie właściciela i wskazanie pickera dochodzą w zadaniu 9.2;
 * interakcja wyboru karty — w zadaniu 9.3.
 *
 * Źródła danych: WYŁĄCZNIE istniejące hooki (zero nowych):
 * - ``useGameState`` → ``gameState`` (faza, mówca, aktywny gracz) — ten sam
 *   selektor web-data, którego używa ``GameStatePanel`` (spójny stan, R8.2);
 * - ``useStrategyCards`` → pula kart zestawu + ich stan (``StrategyCardState[]``);
 * - ``useBoardEditor`` → akcja ``pickStrategyCard`` (użyta dopiero w 9.3).
 */
export function StrategyCardTable(): ReactElement | null {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: cards } = useStrategyCards();
  // ``pickStrategyCard`` podłączone pod przyszłą interakcję wyboru (zadanie 9.3).
  const { pickStrategyCard: _pickStrategyCard } = useBoardEditor();

  // Gating fazy: render tylko w fazie strategii (Requirement 8.1). Poza nią —
  // komponent nie istnieje w drzewie (zwraca ``null``), więc nie dubluje się z
  // innymi nakładkami i nie wpływa na pozostałe fazy.
  if (gameState?.phase !== "strategy") return null;
  if (!cards || cards.length === 0) return null;

  return (
    <div className={styles.table} aria-label="Karty strategii na stole">
      <span className={styles.heading}>Faza strategii</span>
      <div className={styles.cards} role="list">
        {cards.map((card) => (
          <div key={card.initiative} role="listitem" className={styles.card}>
            <span
              className={styles.disc}
              style={{ ["--scc" as string]: SC_TONE[card.initiative] }}
            >
              {card.initiative}
            </span>
            <span className={styles.name}>
              {card.name || SC_NAMES[card.initiative] || "—"}
            </span>
            {card.trade_goods > 0 && (
              <span className={styles.tg} title="Trade goods na karcie">
                +{card.trade_goods} TG
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

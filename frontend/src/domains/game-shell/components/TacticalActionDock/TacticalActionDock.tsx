import { useParams } from "react-router-dom";
import { IconCrosshair } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { getTileById } from "@/entities/lookup/systems";
import { TacticalActionPanel } from "@/domains/game-shell/components/GameStatePanel";
import styles from "./TacticalActionDock.module.css";

/**
 * Pływający dok akcji taktycznej na MAP VIEW.
 *
 * Problem, który rozwiązuje: pływający „Game state" na mapie jest TYLKO
 * informacyjny (``variant="info"``) — nie pokazuje kroków akcji taktycznej, więc
 * na samej mapie gracz nie widział panelu-przewodnika po fazach akcji (ruch →
 * cannon → walka → inwazja → produkcja). Ten dok dokłada ten brakujący panel:
 * jest WIDOCZNY i POMOCNY przez całą akcję taktyczną, bez wchodzenia w zakładkę.
 *
 * Reużywa ten sam ``TacticalActionPanel`` co panel fazy (jedno źródło logiki
 * kroków), opakowany w przypiętą, elegancką obudowę. Renderuje się TYLKO, gdy
 * trwa akcja taktyczna (``activeSystem`` ustawiony) — start akcji jest w
 * ``TurnControls`` (przycisk „Activate system").
 */
export function TacticalActionDock() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();

  const activeSystem = gameState?.activeSystem ?? null;
  // Dok ma sens wyłącznie podczas trwającej akcji taktycznej.
  if (!activeSystem) return null;

  // Kolor gracza, którego jest tura (do produkcji / doboru wariantu jednostek).
  const activePlayerColor =
    gameState?.activeTurnPlayer ?? gameState?.activePlayer ?? null;

  // Czytelna etykieta systemu: „<pozycja> <nazwa>" (gdy znana), inaczej pozycja.
  const sysId = gameData?.tiles?.[activeSystem]?.systemId;
  const name = sysId ? getTileById(sysId)?.name : undefined;
  const label = name ? `${activeSystem} · ${name}` : activeSystem;

  return (
    <aside className={styles.dock} aria-label="Tactical action">
      <header className={styles.dockHead}>
        <IconCrosshair size={15} aria-hidden="true" />
        <span className={styles.dockTitle}>Tactical action</span>
      </header>
      <TacticalActionPanel
        activeSystem={activeSystem}
        tacticalStep={gameState?.tacticalStep ?? null}
        systemLabel={label}
        activePlayerColor={activePlayerColor}
      />
    </aside>
  );
}

export default TacticalActionDock;

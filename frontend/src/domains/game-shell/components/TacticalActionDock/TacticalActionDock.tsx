import { useParams } from "react-router-dom";
import { IconCrosshair, IconGripVertical } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { getTileById } from "@/entities/lookup/systems";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { TacticalActionPanel } from "@/domains/game-shell/components/GameStatePanel";
import styles from "./TacticalActionDock.module.css";

/** Klucz zapisu pozycji doku (localStorage) — pamięta przesunięcie między sesjami. */
const DOCK_POS_KEY = "ti4_tactical_dock_pos";

/**
 * Pływający dok akcji taktycznej na MAP VIEW.
 *
 * Problem, który rozwiązuje: pływający „Game state" na mapie jest TYLKO
 * informacyjny (``variant="info"``) — nie pokazuje kroków akcji taktycznej, więc
 * na samej mapie gracz nie widział panelu-przewodnika po fazach akcji (ruch →
 * cannon → walka → inwazja → produkcja). Ten dok dokłada ten brakujący panel:
 * jest WIDOCZNY i POMOCNY przez całą akcję taktyczną, bez wchodzenia w zakładkę.
 *
 * PRZESUWANY (``useDraggablePanel``): nagłówek to uchwyt (grip), pozycja zapisuje
 * się w localStorage; dwuklik na uchwycie resetuje do domyślnej. Reużywa ten sam
 * ``TacticalActionPanel`` co panel fazy (jedno źródło logiki kroków). Renderuje
 * się TYLKO, gdy trwa akcja taktyczna (``activeSystem`` ustawiony) — start akcji
 * jest w ``TurnControls`` (przycisk „Activate system").
 */
export function TacticalActionDock() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const drag = useDraggablePanel(DOCK_POS_KEY);

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
    <aside
      className={styles.dock}
      style={drag.style}
      aria-label="Tactical action"
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
    >
      {/* Nagłówek = uchwyt przeciągania (pointer-down zaczyna drag). Dwuklik =
          reset pozycji. Elementy [data-no-drag] nie startują przeciągania. */}
      <header
        className={styles.dockHead}
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move · double-click resets position"
      >
        <span className={styles.grip} aria-hidden="true">
          <IconGripVertical size={13} />
        </span>
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

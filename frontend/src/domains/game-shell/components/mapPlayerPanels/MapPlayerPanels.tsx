// Panele graczy w widoku mapy (Map_View, R13) — zadanie 14.1.
//
// Renderuje POWIĘKSZONY panel aktywnego gracza (≥1,5× wymiarów nieaktywnego,
// R13.1), a pod nim JEDEN PIONOWY STOS paneli graczy nieaktywnych w kolejności
// zasiadania od gracza po lewej aktywnego (R13.2). Każdy nieaktywny panel ma
// kontrolkę collapse/expand ze stanem lokalnym per gracz (R13.3, R13.4). Gdy
// zmienia się aktywny gracz, nowy panel się powiększa, poprzedni wraca do stosu,
// a wszystkie nieaktywne wracają do stanu „rozwinięte" (R13.5).
//
// To KONTENER/layout widoku mapy — reużywa istniejący `PlayerCardSidebar` jako
// treść panelu, nie modyfikując go (podział pracy z zakładkami Player/Players).

import { memo, useEffect, useRef, useState } from "react";
import cx from "clsx";
import { ActionIcon, Box, Collapse } from "@/ds";
import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";
import PlayerCardSidebar from "@/domains/player/components/composition/PlayerCardSidebar";
import type { PlayerData } from "@/entities/data/types";
import {
  filterPlayersWithAssignedFaction,
  getPlayerFactionDisplayName,
} from "@/entities/game/playerUtils";
import { useGameData } from "@/state/useGameContext";
import { useGameState } from "@/api/useGameState";
import {
  findActivePlayer,
  orderInactivePlayers,
} from "./mapSeating";
import styles from "./MapPlayerPanels.module.css";

type Props = {
  /** Dane wszystkich graczy (z web-data, już zredagowane projekcją widoczności). */
  playerData: PlayerData[];
  /** Kolor aktywnego gracza z `gameState.activePlayer` (albo null). */
  activePlayer: string | null | undefined;
  /** Kolejność zasiadania jako kolory z `gameState.seatingOrder`. */
  seatingOrder: readonly string[] | undefined;
};

/**
 * Panel pojedynczego nieaktywnego gracza z kontrolką collapse/expand. Nagłówek
 * (nazwa + kontrolka) zostaje widoczny także po zwinięciu; chowana jest tylko
 * szczegółowa zawartość (R13.3, R13.4). Stan zwinięcia steruje rodzic, by przy
 * zmianie aktywnego móc zresetować wszystkie panele naraz (R13.5).
 */
function InactivePlayerPanel({
  player,
  collapsed,
  onToggle,
}: {
  player: PlayerData;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const label = getPlayerFactionDisplayName(player);
  return (
    <Box className={cx(styles.panel, styles.inactive)} data-player-color={player.color}>
      <Box className={styles.inactiveHeader}>
        <span className={styles.inactiveHeaderLabel}>{label}</span>
        <ActionIcon
          variant="subtle"
          size="sm"
          aria-label={collapsed ? `Rozwiń panel: ${label}` : `Zwiń panel: ${label}`}
          aria-expanded={!collapsed}
          onClick={onToggle}
        >
          {collapsed ? (
            <IconChevronRight size={16} />
          ) : (
            <IconChevronDown size={16} />
          )}
        </ActionIcon>
      </Box>
      <Collapse in={!collapsed}>
        <Box className={styles.details}>
          <PlayerCardSidebar playerData={player} />
        </Box>
      </Collapse>
    </Box>
  );
}

/**
 * Kontener paneli graczy w widoku mapy: powiększony aktywny + stos nieaktywnych.
 */
export const MapPlayerPanels = memo(function MapPlayerPanels({
  playerData,
  activePlayer,
  seatingOrder,
}: Props) {
  const active = findActivePlayer(playerData, activePlayer);
  const inactivePlayers = orderInactivePlayers(
    playerData,
    seatingOrder ?? [],
    active?.color ?? activePlayer,
  );

  // Stan zwinięcia per gracz (kolor → zwinięty?). Lokalny, zgodnie z R13.3/R13.4.
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Reset wszystkich paneli do „rozwinięte" przy zmianie aktywnego gracza (R13.5).
  // Śledzimy poprzedni kolor aktywnego, by reset nastąpił tylko na realnej zmianie,
  // a nie przy każdym renderze (np. odświeżeniu web-data).
  const prevActiveRef = useRef<string | null | undefined>(active?.color ?? null);
  useEffect(() => {
    const current = active?.color ?? null;
    if (prevActiveRef.current !== current) {
      prevActiveRef.current = current;
      setCollapsed({});
    }
  }, [active?.color]);

  const toggle = (color: string) => {
    setCollapsed((prev) => ({ ...prev, [color]: !prev[color] }));
  };

  if (playerData.length === 0) return null;

  return (
    <Box className={styles.stack} data-testid="map-player-panels">
      {active && (
        <Box
          className={cx(styles.panel, styles.active)}
          data-active-panel
          data-player-color={active.color}
        >
          <PlayerCardSidebar playerData={active} />
        </Box>
      )}

      {inactivePlayers.map((player) => (
        <InactivePlayerPanel
          key={player.color}
          player={player}
          collapsed={!!collapsed[player.color]}
          onToggle={() => toggle(player.color)}
        />
      ))}
    </Box>
  );
});

/**
 * Nakładka paneli graczy nad mapą — cienki wrapper łączący dane z hooków
 * (`useGameData` → `playerData`, `useGameState` → `activePlayer`/`seatingOrder`)
 * z czystym komponentem {@link MapPlayerPanels}. Pozycjonuje stos przy prawej
 * krawędzi obszaru mapy i nie renderuje się, gdy brak graczy z frakcją.
 */
export function MapPlayerPanelsOverlay({
  gameId,
  rightOffset = "12px",
}: {
  gameId: string;
  /** Odsunięcie od prawej krawędzi (robi miejsce na prawy pasek dossier). */
  rightOffset?: string;
}) {
  const gameData = useGameData();
  const { data: gameState } = useGameState(gameId);
  const players = filterPlayersWithAssignedFaction(gameData?.playerData ?? []);
  if (players.length === 0) return null;

  return (
    <Box className={styles.overlay} style={{ right: rightOffset }}>
      <MapPlayerPanels
        playerData={players}
        activePlayer={gameState?.activePlayer}
        seatingOrder={gameState?.seatingOrder}
      />
    </Box>
  );
}

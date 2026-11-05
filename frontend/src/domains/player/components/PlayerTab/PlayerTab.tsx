import { useParams } from "react-router-dom";
import { Box, Stack, Text, Title } from "@/ds";
import { useGameData } from "@/state/useGameContext";
import { DEFAULT_GAME_ID } from "@/config";
import PlayerCard from "@/domains/player/components/composition/PlayerCard";
import { SecretHand } from "@/domains/game-shell/components/SecretHand";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { useSecretHandAccess } from "@/domains/game-shell/components/SecretHand/useSecretHandAccess";
import { GameStateActionControls } from "@/domains/game-shell/components/GameStatePanel";
import styles from "./PlayerTab.module.css";

/**
 * ``Player_Tab`` (zadanie 13.2) — zakładka SKUPIONA na AKTYWNYM graczu (R12.1/R12.2/
 * R12.3). W przeciwieństwie do ``Players_Tab`` (przegląd wszystkich, ręce jako liczby)
 * pokazuje JEDEN widok z pełnymi informacjami aktywnego gracza plus kontrolki akcji:
 *
 * - Public_Info aktywnego gracza — pełna ``PlayerCard`` (ta sama kompozycja, co w
 *   przeglądzie wszystkich graczy; reużycie, nie duplikat).
 * - Private_Info aktywnego gracza — ręce kart Z IDENTYFIKATORAMI (karty akcji, tajne
 *   obiektywy, promissory notes). Jest to możliwe TYLKO dla viewera = active: web-data
 *   redaguje cudze ręce do samych liczników (projekcja), a pełne listy z identyfikatorami
 *   viewer pobiera osobnym kanałem (``/game/{id}/hand`` przez ``usePlayerHand``). Reużywamy
 *   gotowy komponent ``SecretHand`` (karty akcji/sekrety/noty z podglądem treści).
 * - Kontrolki akcji legalnych w bieżącym OKNIE CZASOWYM / kroku taktycznym — reużywamy
 *   ``GameStateActionControls`` (ten sam ``PlateBody`` co pływający ``GameStatePanel``),
 *   sterowany ``pendingWindow``/``tacticalStep`` z ``gameState`` (R12.2). Akcja nielegalna
 *   → endpoint 422 → baner komunikatu wewnątrz kontrolek, stan gry bez zmian (R12.3 —
 *   egzekucja po stronie core/API).
 *
 * Etykieta zakładki „Player" (l. poj.) jest w pasku zakładek (``mainTabs.ts``), obok
 * „Players" (l. mn.) — R12.6.
 */
export function PlayerTab() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const gameData = useGameData();
  const playerData = gameData?.playerData ?? [];

  // Aktywny gracz = ten oznaczony ``active`` w web-data (spójne z ``activePlayer``
  // w gameState, Bug 7). Gdy nikt nie jest aktywny (np. między turami albo stan
  // God-Mode bez aktywnego), pokazujemy komunikat zamiast pustej zakładki.
  const activePlayer = playerData.find((player) => player.active);

  // Dostęp do ręki viewera: pełne listy z identyfikatorami ciągniemy TYLKO, gdy
  // bieżący użytkownik jest w grze (viewer). Hook sam gatuje request (``enabled``).
  const { canViewSecretHand } = useSecretHandAccess(playerData);
  const { data: handData, isLoading, error } = usePlayerHand(gameId);

  if (!activePlayer) {
    return (
      <Box className={styles.empty}>
        <Text c="dimmed">No active player in the current game state.</Text>
      </Box>
    );
  }

  return (
    <Box className={styles.layout}>
      {/* Główna kolumna: pełna karta aktywnego gracza (Public_Info). */}
      <Box className={styles.main}>
        <PlayerCard key={activePlayer.color} playerData={activePlayer} />
      </Box>

      {/* Boczna kolumna = „pulpit sterowania" aktywnego gracza. Kolejność wg
          wagi w turze: najpierw AKCJE (co mogę teraz zrobić: zagrać kartę
          strategii, akcja taktyczna/komponentowa, zakończ turę / pas), pod spodem
          RĘKA (karty akcji / sekrety / weksle jako zakładki z licznikami). */}
      <Stack className={styles.side} gap="md">
        <Box className={styles.panel}>
          <Title order={4} className={styles.panelTitle}>
            Actions
          </Title>
          <Text c="dimmed" size="xs" className={styles.panelHint}>
            Your turn in the action phase: play your strategy card, take a
            tactical or component action, then end your turn or pass.
          </Text>
          {/* Kontrolki okna czasowego / kroku taktycznego — zawierają własny baner
              komunikatu odrzuconej akcji (422 → R12.3). Zwracają null, gdy brak
              sensownej fazy (np. przed startem gry). */}
          <GameStateActionControls />
        </Box>

        <Box className={styles.panel}>
          <Title order={4} className={styles.panelTitle}>
            Your hand
          </Title>
          <Text c="dimmed" size="xs" className={styles.panelHint}>
            Action cards, secret objectives and promissory notes — tap a tab,
            then a card to read it.
          </Text>
          {canViewSecretHand ? (
            <SecretHand
              handData={handData}
              isLoading={isLoading}
              error={error}
              inlineDetails
            />
          ) : (
            <Text c="dimmed" size="sm">
              Full hand visible only to the logged-in player in this game.
            </Text>
          )}
        </Box>
      </Stack>
    </Box>
  );
}

export default PlayerTab;

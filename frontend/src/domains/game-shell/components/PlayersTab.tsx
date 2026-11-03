import { SimpleGrid } from "@/ds";
import type { PlayerData } from "@/entities/data/types";
import PlayerCard from "@/domains/player/components/composition/PlayerCard";
import { filterPlayersWithAssignedFaction } from "@/entities/game/playerUtils";

type Props = {
  /** Pełna lista graczy z web-data (już zredagowana projekcją backendu). */
  playerData: PlayerData[];
};

/**
 * Zakładka „Players" (liczba mnoga, R12.6) — przegląd WSZYSTKICH graczy.
 *
 * Reużywa istniejący widok gracza (`PlayerCard` → `PlayerCardDeck`), prezentując
 * Public_Info każdego gracza (R12.4). Ręce graczy innych niż Viewing_Player są już
 * zredagowane przez projekcję widoczności backendu i trafiają tu wyłącznie jako
 * liczniki (`acCount`/`soCount`/`pnCount`), nigdy jako identyfikatory kart (R12.5).
 * Dzięki temu ta zakładka nie musi sama filtrować widoczności — dostaje gotowy,
 * bezpieczny dokument i tylko go renderuje.
 *
 * Skupiony na aktywnym graczu widok z kontrolkami to osobna zakładka „Player"
 * (liczba pojedyncza) — poza zakresem tego komponentu.
 */
export default function PlayersTab({ playerData }: Props) {
  // Pomijamy sloty bez przypisanej frakcji (nieobsadzone), zgodnie z dotychczasowym widokiem.
  const players = filterPlayersWithAssignedFaction(playerData);

  return (
    <SimpleGrid cols={{ base: 1, md: 2, xl2: 3 }} spacing="sm">
      {players.map((player) => (
        <PlayerCard key={player.color} playerData={player} />
      ))}
    </SimpleGrid>
  );
}

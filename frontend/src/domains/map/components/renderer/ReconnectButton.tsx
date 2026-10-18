import type { GameDataState } from "@/state/gameContextTypes";
import { FloatingRefreshButton } from "@/shared/ui/FloatingRefreshButton";

type Props = {
  gameDataState: GameDataState | null | undefined;
};

/**
 * Przycisk odświeżenia planszy. Custodian Engine nie ma live-sync (backend nie
 * wystawia STOMP), więc po zmianie stanu w backendzie trzeba ręcznie pobrać
 * świeży dokument `web-data`. Przycisk wisi na stałe i woła `refetch`.
 */
export function ReconnectButton({ gameDataState }: Props) {
  if (!gameDataState) return null;

  return (
    <FloatingRefreshButton
      label="Odśwież"
      onClick={() => gameDataState.refetch?.()}
      loading={gameDataState.isReconnecting}
    />
  );
}

import { Button } from "@/ds";
import { IconRefresh } from "@tabler/icons-react";
import { useGameDataState } from "@/state/useGameContext";
import hud from "./hudChrome.module.css";

/**
 * Przycisk odświeżenia planszy w nagłówku. Custodian Engine nie ma live-sync,
 * więc po zmianie stanu w backendzie trzeba ręcznie pobrać świeży `web-data`.
 * Woła `refetch` z kontekstu gry; kręci się ikona podczas ładowania.
 */
export function HeaderRefreshButton() {
  const dataState = useGameDataState();
  if (!dataState) return null;

  const loading = dataState.isLoading;
  return (
    <Button
      variant="default"
      size="xs"
      className={hud.hudButton}
      leftSection={
        <IconRefresh size={14} className={loading ? hud.hudButtonSpin : undefined} />
      }
      disabled={loading}
      onClick={() => dataState.refetch?.()}
      visibleFrom="sm"
    >
      Odśwież
    </Button>
  );
}

import { HeaderMenu } from "@/domains/tabs/components/HeaderMenu";
import { useTabManagement } from "@/domains/tabs/hooks/useTabManagement";

type GamesBarProps = {
  currentMapId?: string;
};

/**
 * Pasek gier w nagłówku. Custodian Engine obsługuje jedną lokalną grę, więc nie
 * ma dashboardu ani logowania — zostaje sama lista zakładek (na razie: bieżąca gra).
 */
export function GamesBar({ currentMapId }: GamesBarProps) {
  const { activeTabs, changeTab, removeTab } = useTabManagement();

  return (
    <HeaderMenu
      mapId={currentMapId ?? ""}
      activeTabs={activeTabs}
      changeTab={changeTab}
      removeTab={removeTab}
    />
  );
}

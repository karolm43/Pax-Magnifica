import type { ReactNode } from "react";
import { AppHeader } from "@/shared/ui/AppHeader";
import { GamesBar } from "@/layout/GamesBar";
import { WhoAmIBadge } from "@/domains/network/WhoAmIBadge";
import mapClasses from "@/shared/ui/map/MapUI.module.css";

type SiteHeaderProps = {
  currentMapId?: string;
  children?: ReactNode;
};

export function SiteHeader({ currentMapId, children }: SiteHeaderProps) {
  return (
    <AppHeader groupProps={{ className: mapClasses.newHeaderGroup }}>
      <GamesBar currentMapId={currentMapId} />
      {/* „Kim gram" — zawsze widoczne w rogu (gra sieciowa: moje miejsce z tokenu). */}
      <WhoAmIBadge />
      {children}
    </AppHeader>
  );
}

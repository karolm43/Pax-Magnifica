import { useEffect } from "react";
import { SystemDetailsCard } from "@/domains/cards/components/SystemDetailsCard";
import { type MapLayout } from "@/domains/map/components/mapLayout";
import { MapTooltipPositioner } from "@/domains/map/components/MapTooltipPositioner";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";

type Props = {
  mapPadding?: number;
  mapZoom?: number;
  mapLayout?: MapLayout;
};

/** Dymek najechanego systemu (kafla); chowa go MapRenderLayer, gdy widać planetę/jednostkę. */
export function MapSystemDetailsCard({ mapPadding, mapZoom, mapLayout = "panels" }: Props) {
  const hovered = useAppStore((state) => state.hoveredSystem);
  const setHovered = useAppStore((state) => state.setHoveredSystem);
  const gameData = useGameData();
  const position = hovered?.tile.position;

  /* Dymek ma zniknąć od razu, jak dymek planety: przy każdym kliknięciu, menu, przewijaniu,
     klawiszu oraz gdy kursor nie jest już nad swoim kaflem (mouseleave bywa gubiony, np. gdy
     po kliknięciu otwiera się okno systemu nad mapą). */
  useEffect(() => {
    if (!position) return;
    const hide = () => setHovered(null);
    const onMove = (event: PointerEvent) => {
      const target = event.target as Element | null;
      if (!target?.closest(`#tile-${CSS.escape(position)}`)) hide();
    };
    window.addEventListener("pointermove", onMove, true);
    for (const type of ["pointerdown", "contextmenu", "wheel", "keydown", "blur"]) {
      window.addEventListener(type, hide, true);
    }
    return () => {
      window.removeEventListener("pointermove", onMove, true);
      for (const type of ["pointerdown", "contextmenu", "wheel", "keydown", "blur"]) {
        window.removeEventListener(type, hide, true);
      }
    };
  }, [position, setHovered]);

  if (!hovered) return null;

  return (
    <MapTooltipPositioner
      coords={hovered.coords}
      mapPadding={mapPadding}
      mapZoom={mapZoom}
      mapLayout={mapLayout}
      zIndexVar="var(--z-map-planet-details)"
      applyBrowserScale
    >
      <SystemDetailsCard tile={hovered.tile} allTiles={gameData?.tiles ?? {}} />
    </MapTooltipPositioner>
  );
}

import { Box } from "@/ds";
import type { ComponentProps, CSSProperties } from "react";
import { ExpeditionLayer } from "@/domains/map/components/ExpeditionLayer";
import { MapTilesRenderer } from "./MapTilesRenderer";
import { MapUnitDetailsCard } from "@/domains/map/components/tooltips/MapUnitDetailsCard";
import { MapPlanetDetailsCard } from "@/domains/map/components/tooltips/MapPlanetDetailsCard";
import type { GameData, Tile } from "@/entities/game/types";
import classes from "@/shared/ui/map/MapUI.module.css";
import type { MapLayout } from "../mapLayout";
import { MapUnitTransitionLayer } from "../layers/MapUnitTransitionLayer";
import { MoveRouteLayer } from "../layers/MoveRouteLayer";
import { WormholeLinkLayer } from "../layers/WormholeLinkLayer";
import { HeroBoardFxLayer } from "../layers/HeroBoardFxLayer";
import { BoardEffectsZone } from "@/domains/effects/BoardEffectsZone";
import { isMobileDevice } from "@/utils/isTouchDevice";

type Props = {
  gameData: GameData | undefined;
  tilesList: Tile[];
  contentSize: { width: number; height: number };
  tileContainerStyle: CSSProperties;
  onUnitMouseOver: (faction: string, unitId: string, x: number, y: number) => void;
  onUnitMouseLeave: () => void;
  onUnitSelect: (faction: string) => void;
  onPlanetMouseEnter: (planetId: string, x: number, y: number) => void;
  onPlanetMouseLeave: () => void;
  tooltipUnit: ComponentProps<typeof MapUnitDetailsCard>["tooltipUnit"];
  tooltipPlanet: ComponentProps<typeof MapPlanetDetailsCard>["tooltipPlanet"];
  mapLayout: MapLayout;
  mapPadding: number;
  mapZoom: number;
};

export function MapRenderLayer({
  gameData,
  tilesList,
  contentSize,
  tileContainerStyle,
  onUnitMouseOver,
  onUnitMouseLeave,
  onUnitSelect,
  onPlanetMouseEnter,
  onPlanetMouseLeave,
  tooltipUnit,
  tooltipPlanet,
  mapLayout,
  mapPadding,
  mapZoom,
}: Props) {
  if (!gameData) return null;
  const replayAnimationsEnabled = !isMobileDevice();

  return (
    <>
      <Box className={classes.tileRenderingContainer} style={tileContainerStyle}>
        <MapTilesRenderer
          tiles={tilesList}
          playerData={gameData.playerData}
          statTilePositions={gameData.statTilePositions}
          onUnitMouseOver={onUnitMouseOver}
          onUnitMouseLeave={onUnitMouseLeave}
          onUnitSelect={onUnitSelect}
          onPlanetMouseEnter={onPlanetMouseEnter}
          onPlanetMouseLeave={onPlanetMouseLeave}
        />
        <WormholeLinkLayer tiles={tilesList} contentSize={contentSize} />
        <MoveRouteLayer tiles={tilesList} contentSize={contentSize} />
        {replayAnimationsEnabled && <MapUnitTransitionLayer />}
        <ExpeditionLayer contentSize={contentSize} />
        {/* Efekt bohatera na planszy po jego scenie (RULES.md 64.4). */}
        <HeroBoardFxLayer tiles={tilesList} contentSize={contentSize} />
        {/* Taca efektów trwałych po prawej, między polami graczy 2 i 3 (RULES.md 54). */}
        <BoardEffectsZone gameData={gameData} />
      </Box>

      <MapUnitDetailsCard
        tooltipUnit={tooltipUnit}
        mapPadding={mapPadding}
        mapZoom={mapZoom}
        mapLayout={mapLayout}
      />
      <MapPlanetDetailsCard
        tooltipPlanet={tooltipPlanet}
        mapPadding={mapPadding}
        mapZoom={mapZoom}
        mapLayout={mapLayout}
      />
    </>
  );
}

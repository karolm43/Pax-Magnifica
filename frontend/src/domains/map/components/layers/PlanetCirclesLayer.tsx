import { useEffect, useRef, type CSSProperties } from "react";
import cx from "clsx";
import classes from "../MapTile.module.css";
import {
  getPlanetPositionsBySystemId,
  getPlanetData,
} from "@/entities/lookup/planets";
import type { Tile } from "@/entities/game/types";
import { useSettingsStore, useAppStore } from "@/state/appStore";
import { getTokenData } from "@/entities/lookup/tokens";
import { DEFAULT_PLANET_RADIUS } from "@/entities/positioning/constants";
import { isLargeLegendaryPlanet } from "./legendaryPlanetSize";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";

const TOKEN_PLANET_RADIUS = 45;
const REGULAR_PLANET_Z_INDEX = 52;
const TOKEN_PLANET_Z_INDEX = 54;
const HOVER_DELAY_MS = 1000;

type CircleGeometry = { radius: number; offsetX: number; offsetY: number };

function getCircleGeometry(
  planetId: string,
  planet: NonNullable<ReturnType<typeof getPlanetData>>,
  isTokenPlanet: boolean,
): CircleGeometry {
  if (isTokenPlanet) {
    return {
      radius: TOKEN_PLANET_RADIUS,
      offsetX: planetId === "avernus" ? 10 : 0,
      offsetY: -10,
    };
  }
  const geometry = { radius: DEFAULT_PLANET_RADIUS, offsetX: 0, offsetY: 0 };
  if (planetId === "mr" || planetId === "mrte")
    return { ...geometry, radius: 120 };
  if (planetId === "industrex") return { ...geometry, radius: 55 };
  if (planetId === "emelpar") return { ...geometry, radius: 100, offsetY: -5 };
  if (isLargeLegendaryPlanet(planetId, planet))
    return { ...geometry, radius: 100 };
  return geometry;
}

type Props = {
  systemId: string;
  mapTile: Tile;
  position: { x: number; y: number };
  onPlanetMouseEnter?: (planetId: string, x: number, y: number) => void;
  onPlanetMouseLeave?: () => void;
  /** Planet circles sit above the hex target, so they forward the click. */
  onPlanetClick?: (event: React.MouseEvent) => void;
};

/** Aktywny wybór celu z planetami (``appStore.mapPick``), albo ``null``. */
function usePlanetPick() {
  return useAppStore((state) =>
    state.mapPick && state.mapPick.planets.length > 0 ? state.mapPick : null,
  );
}

/** Planeta-cel leży nad jednostkami i żetonami: klik w planetę zawsze trafia w wybór. */
const PICK_PLANET_Z_INDEX = 1241;

export function PlanetCirclesLayer({
  systemId,
  mapTile,
  position,
  onPlanetMouseEnter,
  onPlanetMouseLeave,
  onPlanetClick,
}: Props) {
  const showExhaustedPlanets = useSettingsStore(
    (state) => state.settings.showExhaustedPlanets,
  );
  const hoveredPlanetId = useAppStore((state) => {
    const planetId = state.hoveredPlanetId;
    return planetId && mapTile.planets[planetId] ? planetId : null;
  });
  const hoverTimeoutRef = useRef<Record<string, number>>({});
  const planetPick = usePlanetPick();

  const handlePlanetMouseEnter = (planetId: string, x: number, y: number) => {
    if (!onPlanetMouseEnter) return;
    hoverTimeoutRef.current[planetId] = window.setTimeout(() => {
      onPlanetMouseEnter(planetId, position.x + x, position.y + y);
    }, HOVER_DELAY_MS);
  };

  const handlePlanetMouseLeave = (planetId: string) => {
    if (hoverTimeoutRef.current[planetId]) {
      clearTimeout(hoverTimeoutRef.current[planetId]);
      delete hoverTimeoutRef.current[planetId];
    }
    onPlanetMouseLeave?.();
  };

  useEffect(() => {
    return () => {
      Object.values(hoverTimeoutRef.current).forEach(clearTimeout);
    };
  }, []);

  if (!mapTile?.planets) return null;
  const planetPositions = getPlanetPositionsBySystemId(systemId);

  const createPlanetCircle = (
    planetId: string,
    x: number,
    y: number,
    isExhausted: boolean,
    isTokenPlanet = false,
  ) => {
    const planet = getPlanetData(planetId);
    if (!planet) return null;

    const { radius, offsetX, offsetY } = getCircleGeometry(
      planetId,
      planet,
      isTokenPlanet,
    );
    const diameter = radius * 2;
    const isSpaceStation =
      planet.planetTypes?.some((type) => (type as string) === "SPACESTATION") ??
      false;
    // Żeton-planeta (Avernus) szarzeje sam w Token.tsx - okrąg zakrywałby tylko jego część.
    const showExhausted =
      isExhausted && showExhaustedPlanets && !isSpaceStation && !isTokenPlanet;
    const isHighlighted = hoveredPlanetId === planetId;
    const isPickTarget = planetPick?.planets.includes(planetId) ?? false;

    return (
      <div
        key={`${systemId}-${planetId}${isTokenPlanet ? "-token" : ""}-circle`}
        className={cx(
          classes.planetCircle,
          isHighlighted && !isPickTarget && classes.highlighted,
          isPickTarget && classes.mapPickPlanet,
        )}
        data-planet-circle=""
        data-selected={(isPickTarget && planetPick?.selected === planetId) || undefined}
        {...searchTarget(searchKey("planet", planetId), "map")}
        style={{
          position: "absolute",
          left: `${x + offsetX}px`,
          top: `${y + offsetY}px`,
          width: `${diameter}px`,
          height: `${diameter}px`,
          zIndex: isPickTarget
            ? PICK_PLANET_Z_INDEX
            : isTokenPlanet
              ? TOKEN_PLANET_Z_INDEX
              : REGULAR_PLANET_Z_INDEX,
          backdropFilter: showExhausted
            ? "brightness(0.7) grayscale(1) blur(0px)"
            : undefined,
          ...(isPickTarget && planetPick?.hue
            ? ({ "--pick-hue": planetPick.hue } as CSSProperties)
            : {}),
        }}
        onMouseEnter={() => handlePlanetMouseEnter(planetId, x, y)}
        onMouseLeave={() => handlePlanetMouseLeave(planetId)}
        onClick={(event) => {
          if (isPickTarget && planetPick) {
            // Wybór na mapie ma pierwszeństwo przed dossier systemu.
            event.stopPropagation();
            planetPick.onPick(planetId, "planet");
            return;
          }
          onPlanetClick?.(event);
        }}
      />
    );
  };

  const tokenPlanets: Record<string, { x: number; y: number }> = {};
  for (const placement of Object.values(mapTile.entityPlacements ?? {})) {
    if (placement.entityType !== "token") continue;
    const tokenData = getTokenData(placement.entityId);
    if (!tokenData?.isPlanet || !tokenData.tokenPlanetName) continue;
    tokenPlanets[tokenData.tokenPlanetName] = {
      x: placement.x,
      y: placement.y,
    };
  }

  const regularPlanetCircles = Object.entries(mapTile.planets).flatMap(
    ([planetId, planetTile]) => {
      const position = planetPositions[planetId];
      if (!position) return [];
      const { x, y } = position;
      const circle = createPlanetCircle(planetId, x, y, planetTile.exhausted);
      return circle ? [circle] : [];
    },
  );

  const tokenPlanetCircles = Object.entries(tokenPlanets).flatMap(
    ([planetName, tokenPlanet]) => {
      if (planetPositions[planetName]) return [];
      const planetTileData = mapTile.planets[planetName];
      const circle = createPlanetCircle(
        planetName,
        tokenPlanet.x,
        tokenPlanet.y,
        planetTileData?.exhausted || false,
        true,
      );
      return circle ? [circle] : [];
    },
  );

  return <>{[...regularPlanetCircles, ...tokenPlanetCircles]}</>;
}

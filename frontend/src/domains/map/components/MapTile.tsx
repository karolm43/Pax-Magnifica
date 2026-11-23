import React, { useEffect, useRef, type CSSProperties } from "react";
import { Tile } from "./Tile";
import classes from "./MapTile.module.css";
import { useSettingsStore, useAppStore } from "@/state/appStore";
import { useGameData, useMapReplay } from "@/state/useGameContext";
import { UnitImagesLayer } from "./layers/UnitImagesLayer";
import { ControlTokensLayer } from "./layers/ControlTokensLayer";
import { PlanetCirclesLayer } from "./layers/PlanetCirclesLayer";
import { CommodityIndicatorsLayer } from "./layers/CommodityIndicatorsLayer";
import { SystemIndicatorsLayer } from "./layers/SystemIndicatorsLayer";
import { CommandCounterLayer } from "./layers/CommandCounterLayer";
import { PdsOverlayLayer } from "./layers/PdsOverlayLayer";
import { PlanetaryShieldOverlayLayer } from "./layers/PlanetaryShieldOverlayLayer";
import { AnomalyOverlay } from "./layers/AnomalyOverlay";
import { BorderAnomalyLayer } from "./layers/BorderAnomalyLayer";
import {
  TILE_HEIGHT,
  TILE_WIDTH,
} from "@/entities/geometry/tilePositioning";
import { tileOutline } from "@/entities/geometry/tileOutline";
import type { Tile as TileType } from "@/entities/game/types";
import { TechSkipIconsLayer } from "./layers/TechSkipIconsLayer";
import { AttachmentsLayer } from "./layers/AttachmentsLayer";
import { PlanetTraitIconsLayer } from "./layers/PlanetTraitIconsLayer";
import { WormholeBlockedLayer } from "./layers/WormholeBlockedLayer";
import { WormholeHotspotsLayer } from "./layers/WormholeHotspotsLayer";
import { FactionColorOverlay } from "./FactionColorOverlay";
import { FactionControlBorderOverlay } from "./FactionControlBorderOverlay";
import { SystemHexTarget } from "./SystemHexTarget";
import { getTileById, systemDisplayName } from "@/entities/lookup/systems";
import { useHeroFx } from "@/domains/game-shell/components/KeyMoments/heroBoardFx";
import { isMobileDevice } from "@/utils/isTouchDevice";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";
import { IconInfoCircle, IconTarget } from "@tabler/icons-react";
import {
  ContextMenu,
  useContextMenu,
} from "@/shared/ui/ContextMenu/ContextMenu";
import { useBoardEditor } from "@/api/useBoardEditor";

/** Zawis kursora nad kaflem, po którym pokazujemy dymek systemu (jak przy planecie). */
const SYSTEM_HOVER_DELAY_MS = 1000;

type Props = {
  mapTile: TileType;
  onUnitMouseOver?: (
    faction: string,
    unitId: string,
    x: number,
    y: number,
  ) => void;
  onUnitMouseLeave?: () => void;
  onUnitSelect?: (faction: string) => void;
  onUnitClick?: (faction: string, unitId: string, x: number, y: number) => void;
  onPlanetMouseEnter?: (planetId: string, x: number, y: number) => void;
  onPlanetMouseLeave?: () => void;
  controlOpenSides?: number[];
  /** Render as a self-contained preview without map offsets. */
  embedded?: boolean;
};

export const MapTile = React.memo<Props>(
  ({
    mapTile,
    onUnitMouseOver,
    onUnitMouseLeave,
    onUnitSelect,
    onUnitClick,
    onPlanetMouseEnter,
    onPlanetMouseLeave,
    controlOpenSides,
    embedded = false,
  }) => {
    const gameData = useGameData();
    const mapReplay = useMapReplay();

    const ringPosition = mapTile.position;
    const systemId = mapTile.systemId;
    // Nova Seed: stary kafel na mapie, dopóki efekt bohatera nie odsłoni nowego (`heroBoardFx`).
    const coverSystemId = useHeroFx((s) => s.covers[ringPosition]);
    /* Obrys widocznego kafla: heks albo kształt nieregularnej grafiki (Creuss, Mallice…) —
       wszystkie podświetlenia kafla rysujemy po nim, nie po stałym heksie. */
    const outline = tileOutline(coverSystemId ?? systemId);
    const outlineBox = `0 0 ${outline.width} ${outline.height}`;
    const outlineSize = { width: outline.width, height: outline.height };
    const position = {
      x: mapTile.properties.x,
      y: mapTile.properties.y,
    };
    const techSkipsMode = useSettingsStore(
      (state) => state.settings.techSkipsMode,
    );
    const overlaysEnabled = useSettingsStore(
      (state) => state.settings.overlaysEnabled,
    );
    const planetTypesMode = useSettingsStore(
      (state) => state.settings.planetTypesMode,
    );
    const attachmentsMode = useSettingsStore(
      (state) => state.settings.attachmentsMode,
    );
    const pdsMode = useSettingsStore((state) => state.settings.showPDSLayer);
    const openSystemDossier = useAppStore((state) => state.openSystemDossier);
    const moveMode = useAppStore((state) => state.moveMode);
    const moveFrom = useAppStore((state) => state.moveFrom);
    const pickMoveTile = useAppStore((state) => state.pickMoveTile);
    const activateMode = useAppStore((state) => state.activateMode);
    const pickActivateTile = useAppStore((state) => state.pickActivateTile);
    const dragOver = useAppStore((state) => state.dragOver);
    const moveRangeSources = useAppStore((state) => state.moveRangeSources);
    const { activateSystem } = useBoardEditor();
    const tileMenu = useContextMenu();
    // Aktywny wybór celu okna gry (rejestr ``appStore.mapPicks``): heksy i/lub planety.
    const mapPick = useAppStore((state) => (embedded ? null : state.mapPick));
    // Wybór źródła/waypointu trasy ruchu (krok MOVEMENT); nie blokuje dossier pozostałych kafelków.
    const routePick = useAppStore((state) => state.routePick);
    const isRoutePickTarget =
      !embedded && (routePick?.targets.includes(mapTile.position) ?? false);
    const isRoutePickSelected =
      isRoutePickTarget && (routePick?.selected.includes(mapTile.position) ?? false);
    const isSystemPickTarget = mapPick?.systems.includes(mapTile.position) ?? false;
    // Planeta tego systemu jest celem - heks nie gaśnie, świeci sama planeta.
    const hasPlanetPickTarget =
      mapPick !== null && Object.keys(mapTile.planets ?? {}).some((p) => mapPick.planets.includes(p));
    const isPickRelevant = isSystemPickTarget || hasPlanetPickTarget || isRoutePickTarget;
    // Podczas wyboru systemy BEZ celu przygasają - cele widać od razu, także przy małym zoomie.
    const isPickDimmed = mapPick !== null && !isPickRelevant;

    /* Hyperlanes have nothing to report. Hover feedback is pure CSS so the
       tile never re-renders under a moving cursor. */
    const tileData = getTileById(mapTile.systemId);
    const isHyperlane = !!tileData?.isHyperlane;
    // Nadruk wormhole/egress: najechanie pokazuje, dokąd prowadzi (WormholeLinkLayer).
    const hasPrintedLink = !!tileData?.wormholes?.some(Boolean) || !!tileData?.hasEgress;
    const dossierEligible = !embedded && !isHyperlane;
    /* LEWY klik zależy od trybu: wybór celu/trasy, przenoszenie, aktywacja; inaczej menu
       „Activate system" pod kursorem. PRAWY klik otwiera okno systemu (dossier).
       Telefon (brak prawego klawisza): tap otwiera dossier. */
    const handleDossierOpen = (event: React.MouseEvent) => {
      // Wybór celu na mapie (okno gry) ma pierwszeństwo przed resztą trybów; trasa ruchu
      // działa obok niego (inne cele), żeby otwarta decyzja nie blokowała panelu ruchu.
      if (isSystemPickTarget && mapPick) return mapPick.onPick(mapTile.position, "system");
      if (isRoutePickTarget && routePick) return routePick.onPick(mapTile.position);
      if (mapPick) return; // tryb wyboru: klik obok celu nic nie robi
      if (moveMode) return pickMoveTile(mapTile.position);
      if (activateMode) return pickActivateTile(mapTile.position);
      if (isMobileDevice()) return openSystemDossier(mapTile.position, mapTile.systemId);
      return tileMenu.onContextMenu(event);
    };
    const openDossierByRightClick = (event: React.MouseEvent) => {
      event.preventDefault();
      openSystemDossier(mapTile.position, mapTile.systemId);
    };

    // Czy jest aktywny gracz — aktywacja kładzie jego żeton dowodzenia. Bez
    // aktywnego gracza backend zwróciłby 422, więc pozycję wtedy blokujemy.
    const activePlayer = gameData?.playerData?.find((p) => p.active);
    // Menu lewego kliku: aktywacja systemu + okno systemu (to samo, co prawy klik).
    const tileMenuItems =
      dossierEligible && !isHyperlane
        ? [
            {
              label: activePlayer
                ? "Activate system"
                : "Activate system (no active player)",
              icon: <IconTarget size={14} />,
              disabled: !activePlayer,
              onSelect: () => void activateSystem(mapTile.position),
            },
            {
              label: "System details (right-click)",
              icon: <IconInfoCircle size={14} />,
              onSelect: () => openSystemDossier(mapTile.position, mapTile.systemId),
            },
          ]
        : [];
    /* A phone has no hover, and at board zoom a hex is mostly planets and
       units, so a tap anywhere on the system opens the dossier. The hover
       cards are dropped there: the dossier carries the same detail, and a
       tap would otherwise raise one over it. */
    const tapOpensDossier = dossierEligible && isMobileDevice();

    // Dymek systemu: po krótkim zawisie kursora nad kaflem (jak dymek planety); nie na telefonie.
    const setHoveredSystem = useAppStore((state) => state.setHoveredSystem);
    const systemHoverTimer = useRef<number | undefined>(undefined);
    const clearSystemHover = () => {
      window.clearTimeout(systemHoverTimer.current);
      systemHoverTimer.current = undefined;
      if (useAppStore.getState().hoveredSystem?.tile.position === mapTile.position) {
        setHoveredSystem(null);
      }
    };
    const startSystemHover = () => {
      if (!dossierEligible || tapOpensDossier || mapPick || moveMode || activateMode) return;
      if (systemHoverTimer.current !== undefined) return; // zawis już odliczany
      systemHoverTimer.current = window.setTimeout(() => {
        systemHoverTimer.current = undefined;
        setHoveredSystem({
          tile: mapTile,
          coords: { x: position.x + TILE_WIDTH / 2, y: position.y + TILE_HEIGHT / 2 },
        });
      }, SYSTEM_HOVER_DELAY_MS);
    };
    useEffect(() => () => window.clearTimeout(systemHoverTimer.current), []);
    // Nad planetą, jednostką, żetonem i attachmentem pokazujemy tylko ich własny dymek: dymek systemu znika i nie wraca, póki kursor
    // nie zjedzie z planety na resztę kafla.
    const handleTileMouseOver = (event: React.MouseEvent) => {
      if ((event.target as HTMLElement).closest("[data-planet-circle], [data-map-object]")) clearSystemHover();
      else if (useAppStore.getState().hoveredSystem?.tile.position !== mapTile.position) {
        startSystemHover();
      }
    };

    const controllingFaction = mapTile.controlledBy;

    const getTileOpacity = () => {
      // Cel wyboru zawsze w pełni: przezroczystość tworzy osobny kontekst warstw i poświata
      // celu zostawała uwięziona w kafelku (sąsiednie heksy ją przycinały).
      if (isPickRelevant) return 1;
      if (techSkipsMode && attachmentsMode) {
        return mapTile.hasTechSkips && mapTile.hasAttachments ? 1 : 0.2;
      }
      if (techSkipsMode) return mapTile.hasTechSkips ? 1 : 0.2;
      if (attachmentsMode) return mapTile.hasAttachments ? 1 : 0.2;
      if (planetTypesMode) {
        return Object.values(mapTile.planets).length > 0 ? 1 : 0.2;
      }
      if (pdsMode && gameData?.tilesWithPds) {
        return gameData.tilesWithPds.has(ringPosition) ? 1 : 0.2;
      }
      if (overlaysEnabled && !controllingFaction) return 0.7;
      return 1;
    };
    const showSystemHighlight =
      mapReplay.active &&
      ((mapReplay.showTacticalActivation &&
        mapReplay.tacticalTargetPosition === ringPosition) ||
        mapReplay.changedPositions.has(ringPosition));

    /* Podświetlenie trybu przenoszenia: źródło (wybrane) vs kandydat (klikalny
       cel). Rysowane jako kontur heksa SVG na wierzchu tekstury (patrz CSS). */
    const isMoveSource = moveMode && moveFrom === mapTile.position;
    const isMoveCandidate =
      moveMode && !embedded && !isHyperlane && moveFrom !== mapTile.position;

    /* Podświetlenie celu drag-and-drop: kafelek pod kursorem w trakcie przeciągania
       jednostki. Zielony = upuszczenie dozwolone, czerwony = niedozwolone (np. siła
       naziemna nad orbitą). Daje planszówkowy feedback „tu wyląduje". */
    const isDragTarget = !embedded && dragOver?.position === mapTile.position;
    const dragTargetValid = isDragTarget && dragOver?.valid === true;

    /* Podgląd zasięgu ruchu (krok MOVEMENT): heks jest LEGALNYM ŹRÓDŁEM ruchu do
       aktywnego systemu (gracz ma tam statki z trasą). Reużywa wzorzec konturu SVG. */
    const isMoveRangeSource =
      !embedded && !isHyperlane && moveRangeSources.has(mapTile.position);

    return (
      <div
        id={`tile-${ringPosition}`}
        className={classes.mapTile}
        style={{
          left: embedded ? 0 : `${position.x}px`,
          top: embedded ? 0 : `${position.y}px`,
          position: embedded ? "relative" : undefined,
          opacity: getTileOpacity(),
          cursor: isSystemPickTarget || isRoutePickTarget
            ? "pointer"
            : moveMode || activateMode
              ? "crosshair"
              : undefined,
        }}
        onContextMenu={dossierEligible ? openDossierByRightClick : undefined}
        onMouseOver={handleTileMouseOver}
        onMouseLeave={clearSystemHover}
      >
        {tileMenuItems.length > 0 && (
          <ContextMenu
            position={tileMenu.position}
            items={tileMenuItems}
            onClose={tileMenu.close}
            title={systemDisplayName(systemId, ringPosition)}
          />
        )}
        <div
          className={`${classes.tileContainer} ${
            dossierEligible ? classes.dossierEligible : ""
          }`}
        >
          <Tile
            systemId={coverSystemId ?? systemId}
            className={classes.tile}
            data-map-tile-visual="true"
            {...(!embedded &&
              searchTarget(searchKey("system", ringPosition), "map-tile"))}
          />

          {dossierEligible && <SystemHexTarget onOpen={handleDossierOpen} systemId={systemId} />}

          <AnomalyOverlay
            show={mapTile.hasAnomaly}
            width={TILE_WIDTH}
            height={TILE_HEIGHT}
          />
          <BorderAnomalyLayer mapTile={mapTile} />
          {showSystemHighlight && (
            <svg
              key={`${mapReplay.key}-system-highlight`}
              className={classes.tacticalActivationGlow}
              viewBox={outlineBox}
              style={outlineSize}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          {isPickDimmed && (
            <svg
              className={classes.mapPickDim}
              viewBox={outlineBox}
              style={outlineSize}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          {isSystemPickTarget && (
            <svg
              className={classes.mapPickHex}
              data-selected={mapPick?.selected === mapTile.position || undefined}
              style={
                mapPick?.hue
                  ? ({ ...outlineSize, "--pick-hue": mapPick.hue } as CSSProperties)
                  : outlineSize
              }
              viewBox={outlineBox}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          {isRoutePickTarget && (!isMoveRangeSource || isRoutePickSelected) && (
            <svg
              className={classes.mapPickHex}
              data-selected={isRoutePickSelected || undefined}
              style={
                routePick?.hue
                  ? ({ ...outlineSize, "--pick-hue": routePick.hue } as CSSProperties)
                  : outlineSize
              }
              viewBox={outlineBox}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          {(isMoveSource || isMoveCandidate) && (
            <svg
              className={`${classes.moveHighlight} ${
                isMoveSource ? classes.moveSource : classes.moveCandidate
              }`}
              viewBox={outlineBox}
              style={outlineSize}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          {isMoveRangeSource && (
            <svg
              className={`${classes.moveHighlight} ${classes.moveRangeSource}`}
              viewBox={outlineBox}
              style={outlineSize}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          {isDragTarget && (
            <svg
              className={`${classes.dropHighlight} ${
                dragTargetValid ? classes.dropValid : classes.dropInvalid
              }`}
              viewBox={outlineBox}
              style={outlineSize}
              aria-hidden="true"
            >
              <path d={outline.path} />
            </svg>
          )}
          <PlanetCirclesLayer
            systemId={systemId}
            mapTile={mapTile}
            position={position}
            onPlanetMouseEnter={
              tapOpensDossier ? undefined : onPlanetMouseEnter
            }
            onPlanetMouseLeave={onPlanetMouseLeave}
            onPlanetClick={dossierEligible ? handleDossierOpen : undefined}
          />
          <PlanetaryShieldOverlayLayer systemId={systemId} mapTile={mapTile} />
          <WormholeBlockedLayer systemId={systemId} />
          {dossierEligible && hasPrintedLink && !isMobileDevice() && (
            <WormholeHotspotsLayer systemId={systemId} position={ringPosition} />
          )}
          {!techSkipsMode && !planetTypesMode && !attachmentsMode && (
            <>
              <ControlTokensLayer systemId={systemId} mapTile={mapTile} />
              <UnitImagesLayer
                systemId={systemId}
                mapTile={mapTile}
                position={position}
                onUnitMouseOver={tapOpensDossier ? undefined : onUnitMouseOver}
                onUnitMouseLeave={onUnitMouseLeave}
                onUnitSelect={onUnitSelect}
                onUnitClick={
                  // Tryb wyboru: statki leżą na heksie-celu, więc klik w nie = klik w system
                  // (a nie karta jednostki); poza celem klik nic nie robi.
                  mapPick
                    ? () => {
                        if (isSystemPickTarget) mapPick.onPick(mapTile.position, "system");
                      }
                    : tapOpensDossier
                      ? () => openSystemDossier(mapTile.position, mapTile.systemId)
                      : onUnitClick
                }
              />
            </>
          )}
          {techSkipsMode && (
            <TechSkipIconsLayer systemId={systemId} mapTile={mapTile} />
          )}
          {attachmentsMode && (
            <AttachmentsLayer systemId={systemId} mapTile={mapTile} />
          )}
          {planetTypesMode && (
            <PlanetTraitIconsLayer systemId={systemId} mapTile={mapTile} />
          )}
          <CommodityIndicatorsLayer systemId={systemId} mapTile={mapTile} />
          <SystemIndicatorsLayer
            systemId={systemId}
            highestProduction={mapTile.highestProduction}
            largestCapacity={mapTile.largestCapacity}
            hasBorderAnomaly={Boolean(mapTile.borderAnomalies?.length)}
          />
          <CommandCounterLayer
            position={mapTile.position}
            factions={mapTile.commandCounters}
          />
          <div className={classes.ringPosition}>{ringPosition}</div>

          {controllingFaction && overlaysEnabled && (
            <>
              <FactionColorOverlay
                faction={controllingFaction}
                opacity={0.15}
              />
              <FactionControlBorderOverlay
                faction={controllingFaction}
                openSides={controlOpenSides}
              />
            </>
          )}

          {pdsMode && (
            <PdsOverlayLayer
              ringPosition={ringPosition}
              pdsByTile={gameData?.pdsByTile}
            />
          )}
        </div>
      </div>
    );
  },
);

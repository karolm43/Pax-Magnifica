import React from "react";
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
  HEX_PATH,
  TILE_HEIGHT,
  TILE_WIDTH,
} from "@/entities/geometry/tilePositioning";
import type { Tile as TileType } from "@/entities/game/types";
import { TechSkipIconsLayer } from "./layers/TechSkipIconsLayer";
import { AttachmentsLayer } from "./layers/AttachmentsLayer";
import { PlanetTraitIconsLayer } from "./layers/PlanetTraitIconsLayer";
import { WormholeBlockedLayer } from "./layers/WormholeBlockedLayer";
import { FactionColorOverlay } from "./FactionColorOverlay";
import { FactionControlBorderOverlay } from "./FactionControlBorderOverlay";
import { SystemHexTarget } from "./SystemHexTarget";
import { getTileById } from "@/entities/lookup/systems";
import { isMobileDevice } from "@/utils/isTouchDevice";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";
import { IconTarget } from "@tabler/icons-react";
import {
  ContextMenu,
  useContextMenu,
} from "@/shared/ui/ContextMenu/ContextMenu";
import { useBoardEditor } from "@/api/useBoardEditor";

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

    /* Hyperlanes have nothing to report. Hover feedback is pure CSS so the
       tile never re-renders under a moving cursor. */
    const isHyperlane = !!getTileById(mapTile.systemId)?.isHyperlane;
    const dossierEligible = !embedded && !isHyperlane;
    /* Klik w kafelek zależy od trybu: przenoszenie → wybór źródła/celu;
       aktywacja (akcja taktyczna) → aktywacja systemu; inaczej → dossier. */
    const handleDossierOpen = () => {
      if (moveMode) return pickMoveTile(mapTile.position);
      if (activateMode) return pickActivateTile(mapTile.position);
      return openSystemDossier(mapTile.position, mapTile.systemId);
    };

    // Czy jest aktywny gracz — aktywacja kładzie jego żeton dowodzenia. Bez
    // aktywnego gracza backend zwróciłby 422, więc pozycję wtedy blokujemy.
    const activePlayer = gameData?.playerData?.find((p) => p.active);
    // Menu kontekstowe kafelka (RMB): aktywacja systemu. Rozszerzalne — dokładamy
    // kolejne pozycje (np. „Otwórz dossier", „Zakończ akcję") później.
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
          ]
        : [];
    /* A phone has no hover, and at board zoom a hex is mostly planets and
       units, so a tap anywhere on the system opens the dossier. The hover
       cards are dropped there: the dossier carries the same detail, and a
       tap would otherwise raise one over it. */
    const tapOpensDossier = dossierEligible && isMobileDevice();

    const controllingFaction = mapTile.controlledBy;

    const getTileOpacity = () => {
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
          cursor: moveMode || activateMode ? "crosshair" : undefined,
        }}
        onContextMenu={
          tileMenuItems.length > 0 ? tileMenu.onContextMenu : undefined
        }
      >
        {tileMenuItems.length > 0 && (
          <ContextMenu
            position={tileMenu.position}
            items={tileMenuItems}
            onClose={tileMenu.close}
            title={`System ${ringPosition}`}
          />
        )}
        <div
          className={`${classes.tileContainer} ${
            dossierEligible ? classes.dossierEligible : ""
          }`}
        >
          <Tile
            systemId={systemId}
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
              viewBox={`0 0 ${TILE_WIDTH} ${TILE_HEIGHT}`}
              aria-hidden="true"
            >
              <path d={HEX_PATH} />
            </svg>
          )}
          {(isMoveSource || isMoveCandidate) && (
            <svg
              className={`${classes.moveHighlight} ${
                isMoveSource ? classes.moveSource : classes.moveCandidate
              }`}
              viewBox={`0 0 ${TILE_WIDTH} ${TILE_HEIGHT}`}
              aria-hidden="true"
            >
              <path d={HEX_PATH} />
            </svg>
          )}
          {isMoveRangeSource && (
            <svg
              className={`${classes.moveHighlight} ${classes.moveRangeSource}`}
              viewBox={`0 0 ${TILE_WIDTH} ${TILE_HEIGHT}`}
              aria-hidden="true"
            >
              <path d={HEX_PATH} />
            </svg>
          )}
          {isDragTarget && (
            <svg
              className={`${classes.dropHighlight} ${
                dragTargetValid ? classes.dropValid : classes.dropInvalid
              }`}
              viewBox={`0 0 ${TILE_WIDTH} ${TILE_HEIGHT}`}
              aria-hidden="true"
            >
              <path d={HEX_PATH} />
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
                onUnitClick={tapOpensDossier ? handleDossierOpen : onUnitClick}
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

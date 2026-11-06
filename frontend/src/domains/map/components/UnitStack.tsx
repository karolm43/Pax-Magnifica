import { Unit } from "@/shared/ui/Unit";
import { Token } from "./Token";
import { Attachment } from "./Attachment";
import { EntityStack } from "@/entities/positioning";
import { getUnitZIndex } from "@/utils/zIndexLayers";
import { UnitBadge } from "./UnitBadge";
import { getTextColor } from "@/entities/lookup/colors";
import type { LawInPlay } from "@/entities/data/types";
import { isBadgeUnit } from "./UnitStack/unitType";
import {
  calculateUnitArrangement,
  getRenderedStackFootprint,
} from "@/entities/geometry/renderedStackGeometry";
import { useDelayedHover } from "./UnitStack/useDelayedHover";
import { useDecalPaths } from "./UnitStack/useDecalPaths";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import { useMapFlightAnimation } from "./UnitStack/useMapFlightAnimation";
import { GalvanizeBadge } from "./UnitStack/GalvanizeBadge";
import {
  flightOptions,
  transitionClassName,
  transitionDelayStyle,
  unitSlots,
} from "./UnitStack/transition";
import type { MapUnitTransition, StateCounts } from "@/entities/replay/types";
import { stateCount, stackHolder, unitStates } from "@/entities/replay/unitState";
import { useUnitDrag } from "./hooks/useUnitDrag";
import { UnitDragGhost } from "./UnitDragGhost";
import { useAppStore } from "@/state/appStore";
import classes from "./UnitStack.module.css";

const EMPTY_STATES: StateCounts = [0, 0, 0, 0];

type UnitStackProps = {
  stack: EntityStack;
  stackKey: string;
  colorAlias: string;
  onUnitMouseOver?: (stackKey: string, event: React.MouseEvent) => void;
  onUnitMouseLeave?: (stackKey: string, event: React.MouseEvent) => void;
  onUnitSelect?: (stackKey: string, event: React.MouseEvent) => void;
  onUnitClick?: (stackKey: string, event: React.MouseEvent) => void;
  lawsInPlay?: LawInPlay[];
  mapTransition?: MapUnitTransition;
  replayHidden?: boolean;
  layoutUnitStates?: StateCounts;
  layoutStateOffsets?: StateCounts;
  damageAtMs?: number;
  delayedDamageStates?: StateCounts;
  /** Pozycja kafelka (RPP) — włącza drag-and-drop przenoszenia jednostek. */
  tilePosition?: string;
};

export function UnitStack({
  stackKey,
  stack,
  colorAlias,
  onUnitMouseOver,
  onUnitMouseLeave,
  onUnitSelect,
  onUnitClick,
  lawsInPlay,
  mapTransition,
  replayHidden = false,
  layoutUnitStates,
  layoutStateOffsets,
  damageAtMs,
  delayedDamageStates,
  tilePosition,
}: UnitStackProps) {
  const { entityId: unitType, faction, count, x, y, entityType } = stack;
  const isBadge = isBadgeUnit(unitType);

  /* Drag-and-drop przenoszenia (God-Mode). Aktywny tylko dla realnych jednostek
     z pozycją kafelka i poza replayem (``mapTransition``) — żetony/attachmenty i
     odtwarzanie historii nie są przenoszone gestem. Hook podpina natywne listenery
     startu gestu (``dragRef``) blokujące pan mapy; patrz useUnitDrag. */
  const dndEnabled = entityType === "unit" && !!tilePosition && !mapTransition;
  const unitDrag = useUnitDrag(
    dndEnabled
      ? {
          fromPosition: tilePosition,
          fromZone: stackHolder(stack),
          faction,
          asyncId: unitType,
          count,
        }
      : null,
  );
  // Łączy ref animacji lotu (flightRef) z refem DnD (dragRef) na jednym wrapperze.
  const setWrapperRef = (node: HTMLDivElement | null) => {
    (flightRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
    if (dndEnabled) unitDrag.dragRef(node);
  };
  const dragProps = dndEnabled
    ? { onClickCapture: unitDrag.onClickCapture }
    : {};
  /* Oznaczenie stosu STATKU w DOM — pozwala drop-detekcji (``elementFromPoint``)
     rozpoznać „upuszczono ładunek NA ten statek" i otworzyć okno załadunku. Niesie
     asyncId/frakcję/pozycję; capacity rozstrzyga logika dragu (useUnitDrag). */
  const shipTag =
    entityType === "unit" && tilePosition
      ? {
          "data-ship-async": unitType,
          "data-ship-faction": faction,
          "data-ship-pos": tilePosition,
        }
      : {};
  // Czy ten statek jest aktualnym celem załadunku (kursor z ładunkiem nad nim) —
  // wtedy go podświetlamy, by było jasne „tu włożysz jednostkę".
  const dragLoadTarget = useAppStore((s) => s.dragLoadTarget);
  const isLoadTarget =
    !!tilePosition &&
    dragLoadTarget?.position === tilePosition &&
    dragLoadTarget?.asyncId === unitType;
  /* Combat badges are compact summaries and must stay legible above the much
     larger rotated ship silhouettes in the transition layer. */
  const baseZIndex =
    getUnitZIndex(unitType, 0) + (mapTransition && isBadge ? 200 : 0);
  const rotateInFlight =
    !isBadge && getGenericUnitDataByAsyncId(unitType)?.isShip === true;
  const flightRef = useMapFlightAnimation(
    flightOptions(mapTransition, x, y, rotateInFlight),
  );
  const isUnit = entityType === "unit";
  const clickableClass = isUnit && onUnitClick ? classes.clickable : "";
  const wrapperClass = `${transitionClassName(mapTransition)} ${replayHidden ? classes.mapReplayHidden : ""} ${clickableClass}`;
  const delayStyle = transitionDelayStyle(mapTransition);
  const { handleMouseEnter, handleMouseLeave } = useDelayedHover(
    stackKey,
    onUnitMouseOver,
    onUnitMouseLeave,
  );
  const { bgDecalPath, decalPath } = useDecalPaths(
    unitType,
    faction,
    colorAlias,
  );

  const states = unitStates(stack);
  const galvanizedCount = states[2] + states[3];
  const handlers = {
    onMouseEnter: isUnit && onUnitMouseOver ? handleMouseEnter : undefined,
    onMouseLeave: isUnit && onUnitMouseLeave ? handleMouseLeave : undefined,
    onMouseDown:
      isUnit && onUnitSelect
        ? (e: React.MouseEvent) => onUnitSelect(stackKey, e)
        : undefined,
    onClick:
      isUnit && onUnitClick
        ? (e: React.MouseEvent) => onUnitClick(stackKey, e)
        : undefined,
  };

  if (isBadge) {
    const badgeFootprint = getRenderedStackFootprint({
      entityId: unitType,
      entityType,
      count,
    });

    return (
      <div
        ref={setWrapperRef}
        className={`${classes.badgeContainer} ${wrapperClass} ${dndEnabled ? classes.draggable : ""} ${isLoadTarget ? classes.loadTarget : ""}`}
        style={{
          left: `${x}px`,
          top: `${y}px`,
          zIndex: baseZIndex,
          ...delayStyle,
        }}
        {...handlers}
        {...dragProps}
        {...shipTag}
      >
        <UnitDragGhost ghost={unitDrag.ghost} />
        <div
          className={classes.badgeInnerWrapper}
          style={{
            width: `${badgeFootprint.width}px`,
            height: `${badgeFootprint.height}px`,
          }}
        >
          <UnitBadge
            unitType={unitType}
            colorAlias={colorAlias}
            faction={faction}
            count={count}
            textColor={getTextColor(colorAlias)}
          />
          {galvanizedCount > 0 && (
            <GalvanizeBadge
              count={galvanizedCount}
              style={{ top: "5%", left: "100%", zIndex: baseZIndex + 100 }}
            />
          )}
        </div>
      </div>
    );
  }

  const transitionLayout = mapTransition?.layoutUnitStates ?? layoutUnitStates;
  const layoutStates = transitionLayout ?? states;
  const layoutCount = stateCount(layoutStates);
  const showIndividualGalvanized = galvanizedCount === 1 || unitType === "mf";
  const slots = unitSlots({
    states,
    layoutStates,
    layoutOffsets:
      mapTransition?.layoutStateOffsets ?? layoutStateOffsets ?? EMPTY_STATES,
    delayedDamage:
      mapTransition?.delayedDamageStates ?? delayedDamageStates ?? EMPTY_STATES,
    showIndividualGalvanized,
  });
  const damageDelayMs = mapTransition?.damageAtMs ?? damageAtMs;
  const footprint = getRenderedStackFootprint({
    entityId: unitType,
    entityType,
    count: layoutCount,
  });

  return (
    <div
      ref={setWrapperRef}
      {...handlers}
      {...dragProps}
      {...shipTag}
      className={`${classes.stackWrapper} ${wrapperClass} ${dndEnabled ? classes.draggable : ""} ${isLoadTarget ? classes.loadTarget : ""}`}
      style={{
        left: `${x + (footprint.left + footprint.right) / 2}px`,
        top: `${y + (footprint.top + footprint.bottom) / 2}px`,
        width: `${footprint.width}px`,
        height: `${footprint.height}px`,
        zIndex: baseZIndex,
        ...delayStyle,
      }}
    >
      <UnitDragGhost ghost={unitDrag.ghost} />
      {galvanizedCount > 1 && !showIndividualGalvanized && (
        <GalvanizeBadge
          count={galvanizedCount}
          className={classes.galvanizeBadgeContainer}
          style={{ left: "50%", top: "45%", zIndex: baseZIndex + 100 }}
        />
      )}

      {slots.map((slot) => {
        const { stackOffsetX, stackOffsetY, zIndexOffset } =
          calculateUnitArrangement(
            unitType,
            entityType,
            slot.index,
            layoutCount,
          );
        const unitKey = `${stackKey}-${slot.index}`;
        const xPos = stackOffsetX - footprint.left;
        const yPos = stackOffsetY - footprint.top;

        if (entityType === "token") {
          return (
            <Token
              key={unitKey}
              tokenId={unitType}
              faction={faction}
              x={xPos}
              y={yPos}
              zIndex={baseZIndex + zIndexOffset}
            />
          );
        }
        if (entityType === "attachment") {
          return (
            <Attachment
              key={unitKey}
              unitType={unitType}
              faction={faction}
              x={xPos}
              y={yPos}
              zIndex={baseZIndex}
            />
          );
        }
        return (
          <Unit
            key={unitKey}
            unitType={unitType}
            colorAlias={colorAlias}
            faction={faction}
            bgDecalPath={bgDecalPath}
            decalPath={decalPath || undefined}
            lawsInPlay={lawsInPlay}
            galvanized={slot.galvanized}
            sustained={slot.sustained}
            damageMarkerDelayMs={slot.delayDamage ? damageDelayMs : undefined}
            x={xPos}
            y={yPos}
            zIndex={baseZIndex + zIndexOffset}
          />
        );
      })}
    </div>
  );
}

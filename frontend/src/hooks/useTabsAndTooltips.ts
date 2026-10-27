import { useEffect, useState, useRef } from "react";
import type { Point } from "@/entities/data/types";
import { useAppStore } from "@/state/appStore";

const TOOLTIP_DELAY_MS = 300;

export type TooltipUnit = {
  faction: string;
  unitId?: string;
  coords: Point;
};

export type AreaType = ({ type: "faction" } & TooltipUnit) | null;

export function useTabsAndTooltips() {
  const [selectedArea, setSelectedArea] = useState<AreaType>(null);
  const [activeArea, setActiveArea] = useState<AreaType>(null);
  const [tooltipUnit, setTooltipUnit] = useState<TooltipUnit | null>(null);
  const hoverTimeoutRef = useRef<number | null>(null);
  const isDraggingUnit = useAppStore((s) => s.isDraggingUnit);

  // Start przeciągania jednostki chowa tooltip (zasłaniał widok w trakcie dragu).
  useEffect(() => {
    if (isDraggingUnit) {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
        hoverTimeoutRef.current = null;
      }
      setTooltipUnit(null);
    }
  }, [isDraggingUnit]);

  const selectedFaction =
    selectedArea?.type === "faction" ? selectedArea.faction : null;
  const activeUnit =
    activeArea?.type === "faction"
      ? {
          faction: activeArea.faction,
          unitId: activeArea.unitId,
          coords: activeArea.coords,
        }
      : null;

  const clearHoverTimeout = () => {
    if (!hoverTimeoutRef.current) return;
    clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = null;
  };

  const handleMouseEnter = (
    faction: string,
    unitId: string,
    x: number,
    y: number,
  ) => {
    setActiveArea({ type: "faction", faction, unitId, coords: { x, y } });
    clearHoverTimeout();
    // Nie pokazuj tooltipa w trakcie przeciągania jednostki (zasłaniałby mapę).
    if (useAppStore.getState().isDraggingUnit) return;
    hoverTimeoutRef.current = window.setTimeout(() => {
      setTooltipUnit({ faction, unitId, coords: { x, y } });
      hoverTimeoutRef.current = null;
    }, TOOLTIP_DELAY_MS);
  };

  const handleMouseLeave = () => {
    clearHoverTimeout();
    setActiveArea(null);
    setTooltipUnit(null);
  };

  const handleMouseDown = (faction: string, x: number = 0, y: number = 0) => {
    setSelectedArea({ type: "faction", faction, coords: { x, y } });
  };

  const handleAreaSelect = (area: AreaType) => {
    setSelectedArea(area);
    setActiveArea(null);
  };

  const handleAreaMouseEnter = (area: AreaType) => setActiveArea(area);
  const handleAreaMouseLeave = () => setActiveArea(null);

  return {
    selectedArea,
    activeArea,
    selectedFaction,
    activeUnit,
    tooltipUnit,
    handleAreaSelect,
    handleAreaMouseEnter,
    handleAreaMouseLeave,
    handleMouseEnter,
    handleMouseLeave,
    handleMouseDown,
  };
}

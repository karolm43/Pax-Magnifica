import { useCallback } from "react";
import { useKeyboardShortcuts, type KeyboardShortcutsProps } from "@/hooks/useKeyboardShortcuts";
import type { SettingsStore } from "@/state/appStore";

// Wspólne podpięcie skrótów klawiszowych dla układów mapy.
type ShortcutHandlers = Pick<
  SettingsStore["handlers"],
  | "toggleOverlays"
  | "toggleTechSkipsMode"
  | "toggleAttachmentsMode"
  | "togglePlanetTypesMode"
  | "togglePdsMode"
  | "setKeyboardShortcutsModalOpened"
>;

type UseMapKeyboardShortcutsParams = {
  handlers: ShortcutHandlers;
  handleZoomIn: KeyboardShortcutsProps["handleZoomIn"];
  handleZoomOut: KeyboardShortcutsProps["handleZoomOut"];
  handleZoomFit?: KeyboardShortcutsProps["handleZoomFit"];
  scrollToBoard: KeyboardShortcutsProps["scrollToBoard"];
};

export function useMapKeyboardShortcuts({
  handlers,
  handleZoomIn,
  handleZoomOut,
  handleZoomFit,
  scrollToBoard,
}: UseMapKeyboardShortcutsParams) {
  const { setKeyboardShortcutsModalOpened } = handlers;
  const openShortcutsHelp = useCallback(
    () => setKeyboardShortcutsModalOpened(true),
    [setKeyboardShortcutsModalOpened],
  );
  useKeyboardShortcuts({
    toggleOverlays: handlers.toggleOverlays,
    toggleTechSkipsMode: handlers.toggleTechSkipsMode,
    toggleAttachmentsMode: handlers.toggleAttachmentsMode,
    togglePlanetTypesMode: handlers.togglePlanetTypesMode,
    togglePdsMode: handlers.togglePdsMode,
    openShortcutsHelp,
    handleZoomIn,
    handleZoomOut,
    handleZoomFit,
    scrollToBoard,
  });
}

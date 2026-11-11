import { useEffect, useRef } from "react";
import { useGameData } from "@/state/useGameContext";
import { useIsTabActive } from "@/hooks/useIsTabActive";
import { filterPlayersWithAssignedFaction } from "@/entities/game/playerUtils";
import { findSearchHits, focusSearchHit } from "@/domains/search/searchHits";
import { searchKey } from "@/domains/search/searchKeys";

export type KeyboardShortcutsProps = {
  toggleOverlays: () => void;
  toggleTechSkipsMode: () => void;
  toggleAttachmentsMode: () => void;
  togglePlanetTypesMode: () => void;
  togglePdsMode: () => void;
  openShortcutsHelp: () => void;
  handleZoomIn: () => void;
  handleZoomOut: () => void;
  /** Dopasowanie planszy do okna (klawisz „0"). */
  handleZoomFit?: () => void;
  /** Powrót na górę planszy (klawisze „B" / „Home", drugie naciśnięcie cyfry). */
  scrollToBoard: () => void;
};

/** Atrybut sekcji celów/punktów pod planszą — cel skrótu „G". */
export const JUMP_OBJECTIVES_ATTR = "data-jump-objectives";

/** Jak długo zostaje podświetlenie celu skoku. */
const JUMP_FLASH_MS = 1600;

function isTypingTarget(target: EventTarget | null) {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  );
}

/** Otwarte okno modalne (walka, produkcja, ustawienia...) — skróty mapy wtedy milczą. */
function isModalOpen() {
  // Nakładki gry mają aria-modal; okna design systemu (Base UI) — data-open.
  return (
    document.querySelector(
      '[role="dialog"][aria-modal="true"], [role="dialog"][data-open], [role="alertdialog"][data-open]',
    ) !== null
  );
}

/** Cyfra 1–8 z kodu fizycznego klawisza — działa też z Shiftem i na numpadzie. */
function seatDigit(event: KeyboardEvent): number | null {
  const match = /^(?:Digit|Numpad)([1-8])$/.exec(event.code);
  return match ? Number(match[1]) - 1 : null;
}

let flashTimer = 0;

/** Przewija do elementu i na chwilę podświetla go stylem bieżącego trafienia wyszukiwarki. */
function jumpTo(hit: HTMLElement) {
  focusSearchHit(hit);
  window.clearTimeout(flashTimer);
  flashTimer = window.setTimeout(
    () => hit.removeAttribute("data-search-current"),
    JUMP_FLASH_MS,
  );
}

/**
 * Skróty klawiszowe widoku mapy. Pełna lista (i jedyne miejsce jej opisu dla gracza):
 * `KeyboardShortcutsModal`. Skróty milkną, gdy gracz pisze w polu albo gdy otwarte jest
 * okno modalne; Ctrl/Alt/Cmd zostawiamy przeglądarce (Ctrl+F obsługuje `BoardSearch`).
 */
export function useKeyboardShortcuts({
  toggleOverlays,
  toggleTechSkipsMode,
  toggleAttachmentsMode,
  togglePlanetTypesMode,
  togglePdsMode,
  openShortcutsHelp,
  handleZoomIn,
  handleZoomOut,
  handleZoomFit,
  scrollToBoard,
}: KeyboardShortcutsProps) {
  const enhancedData = useGameData();
  const isTabActive = useIsTabActive();
  /** Miejsce ostatniego skoku do pola gracza: ponowne naciśnięcie tej cyfry wraca na planszę. */
  const lastSeatRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isTabActive) return;
    const seats = filterPlayersWithAssignedFaction(enhancedData?.playerData ?? []);

    function factionHit(index: number, onBoard: boolean): HTMLElement | undefined {
      const faction = seats[index]?.faction;
      if (!faction) return undefined;
      const hits = findSearchHits([searchKey("faction", faction)]);
      return onBoard
        ? hits.find((hit) => hit.dataset.searchScope?.startsWith("map"))
        : hits.find((hit) => !hit.dataset.searchScope);
    }

    function jumpToSeat(index: number, onBoard: boolean) {
      if (!onBoard && lastSeatRef.current === index) {
        lastSeatRef.current = null;
        scrollToBoard();
        return;
      }
      const hit = factionHit(index, onBoard);
      if (!hit) return;
      lastSeatRef.current = onBoard ? null : index;
      jumpTo(hit);
    }

    function stepSeat(delta: number) {
      if (seats.length === 0) return;
      const current = lastSeatRef.current ?? (delta > 0 ? -1 : 0);
      const next = (current + delta + seats.length) % seats.length;
      const hit = factionHit(next, false);
      if (!hit) return;
      lastSeatRef.current = next;
      jumpTo(hit);
    }

    function jumpToObjectives() {
      lastSeatRef.current = null;
      const section = document.querySelector<HTMLElement>(`[${JUMP_OBJECTIVES_ATTR}]`);
      section?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function backToBoard() {
      lastSeatRef.current = null;
      scrollToBoard();
    }

    const keyActions: Record<string, () => void> = {
      "+": handleZoomIn,
      "=": handleZoomIn,
      "-": handleZoomOut,
      // Polska klawiatura: „_" to Shift + „-", numpad daje „+"/„-" jak wyżej.
      _: handleZoomOut,
      ...(handleZoomFit ? { "0": handleZoomFit } : {}),
      y: togglePlanetTypesMode,
      t: toggleTechSkipsMode,
      a: toggleAttachmentsMode,
      p: togglePdsMode,
      o: toggleOverlays,
      g: jumpToObjectives,
      b: backToBoard,
      Home: backToBoard,
      "[": () => stepSeat(-1),
      "]": () => stepSeat(1),
      "?": openShortcutsHelp,
    };

    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || isTypingTarget(event.target)) return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (isModalOpen()) return;

      const seat = seatDigit(event);
      if (seat !== null) {
        event.preventDefault();
        if (!event.repeat) jumpToSeat(seat, event.shiftKey);
        return;
      }

      const action = keyActions[event.key] ?? keyActions[event.key.toLowerCase()];
      if (!action) return;
      event.preventDefault();
      action();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [
    isTabActive,
    enhancedData?.playerData,
    toggleOverlays,
    toggleTechSkipsMode,
    toggleAttachmentsMode,
    togglePlanetTypesMode,
    togglePdsMode,
    openShortcutsHelp,
    handleZoomIn,
    handleZoomOut,
    handleZoomFit,
    scrollToBoard,
  ]);
}

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  IconArrowBackUp,
  IconPackage,
  IconShip,
} from "@tabler/icons-react";
import { Switch } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useMoveRange } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { lookupUnit } from "@/entities/lookup/units";
import { FleetPoolWarning } from "@/domains/map/components/FleetPoolWarning";
import { MoveRouteBox } from "@/domains/movement/MoveRouteBox";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import type { PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";
import {
  CARGO_ASYNC,
  isStructureUnit,
} from "@/domains/map/components/UnitStack/cargo";
import styles from "./GameStatePanel.module.css";

type Stack = { asyncId: string; count: number };

/** Statki + ładunek gracza w przestrzeni danego kafelka (z web-data). */
function playerSpaceStacks(tile: Tile | undefined, faction: string): Stack[] {
  if (!tile) return [];
  const entities = tile.unitsByFaction?.[faction] ?? [];
  return entities
    .filter((e) => e.entityType === "unit" && e.count > 0)
    .map((e) => ({ asyncId: e.entityId, count: e.count }));
}

type Capacity = { total: number; used: number };

/**
 * Pojemność floty gracza w przestrzeni systemu (RULES.md 32.3/R_capacity): suma
 * ``capacityValue`` statków (bez doków) vs liczba przewożonych myśliwców/sił
 * naziemnych (ładunek). Liczone dla KONKRETNEGO gracza (nie max frakcji), z
 * wariantu jednostki (``lookupUnit``). Dane z UnitDef, nie z pamięci.
 */
function fleetCapacity(stacks: Stack[], faction: string, player?: PlayerData): Capacity {
  let total = 0;
  let used = 0;
  for (const s of stacks) {
    const unit = lookupUnit(s.asyncId, faction, player);
    // Struktury (dok/PDS) nie dają pojemności transportu, mimo capacity w danych.
    if (unit?.capacityValue && !isStructureUnit(s.asyncId)) {
      total += unit.capacityValue * s.count;
    }
    // Myśliwce i siły naziemne zajmują pojemność jako ładunek.
    if (CARGO_ASYNC.has(s.asyncId)) {
      used += (unit?.capacityUsed ?? 1) * s.count;
    }
  }
  return { total, used };
}

/**
 * Krok MOVEMENT akcji taktycznej — MONITOR floty + premie ruchu + okno trasy.
 *
 * Ruch ma JEDNO okno: ``MoveRouteBox`` (trasa rysowana na mapie). Otwiera je przeciągnięcie
 * jednostek na aktywny system, Ctrl+klik/Ctrl+drag grupy albo klik w świecący system źródłowy.
 * Monitor pokazuje flotę i pojemność w aktywnym systemie; „Undo last move" cofa ostatni ruch.
 * Zasięg/capacity egzekwuje backend (422 z powodem).
 */
export function MovementStepPanel({
  activeSystem,
  activePlayerColor,
}: {
  activeSystem: string;
  activePlayerColor: string | null;
}) {
  const gameData = useGameData();
  const look = usePlayerLook();
  const { undoMove } = useBoardEditor();
  const setMoveRangeSources = useAppStore((s) => s.setMoveRangeSources);
  const gravityDrive = useAppStore((s) => s.gravityDrive);
  const setGravityDrive = useAppStore((s) => s.setGravityDrive);
  const routeParams = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(routeParams.mapid ?? DEFAULT_GAME_ID);
  const [busy, setBusy] = useState(false);

  const player = gameData?.playerData?.find((p) => p.color === activePlayerColor);
  const faction = player?.faction ?? null;

  // Podgląd zasięgu ruchu (legalne systemy źródłowe) — podświetla heksy na mapie.
  // Gravity Drive (RULES.md 55.6): przełącznik tylko dla właściciela technologii, dopóki w tej
  // akcji nie zużyto premii - to GRACZ decyduje, silnik nie włącza jej sam.
  const gravityDriveReady =
    (player?.techs ?? []).includes("gd") && gameState?.gravityDriveUsed !== true;
  const useGd = gravityDrive && gravityDriveReady;
  useEffect(() => {
    if (!gravityDriveReady && gravityDrive) setGravityDrive(false);
  }, [gravityDriveReady, gravityDrive, setGravityDrive]);
  // Ionian Fuel Refinery (Tempesta, RULES.md 60): osobny przełącznik, dostępny po wyczerpaniu
  // karty po aktywacji systemu (`extraMoveBoostActive`), dopóki premia nie została zużyta.
  const tempesta = useAppStore((s) => s.tempesta);
  const setTempesta = useAppStore((s) => s.setTempesta);
  const tempestaReady =
    gameState?.extraMoveBoostActive === true && gameState?.tempestaUsed !== true;
  const useTempesta = tempesta && tempestaReady;
  useEffect(() => {
    if (!tempestaReady && tempesta) setTempesta(false);
  }, [tempestaReady, tempesta, setTempesta]);
  // Imperator (Winnu, RULES.md 62.7): osobna premia „+1 dla jednego statku” po aktywacji systemu
  // z planetą legendarną — może trafić na inny statek niż Gravity Drive.
  const imperator = useAppStore((s) => s.imperator);
  const setImperator = useAppStore((s) => s.setImperator);
  const imperatorReady =
    gameState?.imperatorBoostActive === true && gameState?.imperatorUsed !== true;
  const useImperator = imperator && imperatorReady;
  useEffect(() => {
    if (!imperatorReady && imperator) setImperator(false);
  }, [imperatorReady, imperator, setImperator]);
  const { data: moveRange } = useMoveRange(
    faction,
    Boolean(activeSystem),
    useGd,
    useTempesta,
    useImperator,
  );
  useEffect(() => {
    setMoveRangeSources(new Set(Object.keys(moveRange?.sources ?? {})));
    return () => setMoveRangeSources(new Set());
  }, [moveRange, setMoveRangeSources]);

  // Flota AKTYWNEGO systemu (monitor) + jej pojemność.
  const activeTile = gameData?.tiles?.[activeSystem];
  const fleet = faction ? playerSpaceStacks(activeTile, faction) : [];
  const capacity = faction ? fleetCapacity(fleet, faction, player) : { total: 0, used: 0 };
  const free = Math.max(capacity.total - capacity.used, 0);
  const over = capacity.used > capacity.total;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  if (!faction) {
    return (
      <span className={styles.prodNote}>
        No active player with a faction — cannot move.
      </span>
    );
  }

  return (
    <div className={styles.movement}>
      {/* MONITOR floty aktywnego systemu. */}
      <div className={styles.moveMonitorHead}>
        <span className={styles.prodZoneLabel}>
          <IconShip size={11} aria-hidden="true" /> Fleet here
        </span>
        <span
          className={styles.capBadge}
          data-over={over || undefined}
          title="Cargo used / total capacity (fighters + ground forces)"
        >
          <IconPackage size={11} aria-hidden="true" />
          {capacity.used}/{capacity.total}
          {!over && free > 0 ? ` · ${free} free` : ""}
          {over ? " · over!" : ""}
        </span>
      </div>

      {/* Technologie wpływające na ruch (Antimass, Light/Wave, Gravity Drive...) - także stałe. */}
      <ActiveTechs context="movement" color={activePlayerColor} />

      {gravityDriveReady && (
        <Switch
          label="Use Gravity Drive"
          description="+1 move for ONE ship this action (the ship that needs it)."
          checked={gravityDrive}
          onChange={(event) => setGravityDrive(event.currentTarget.checked)}
        />
      )}
      {tempestaReady && (
        <Switch
          label="Use Ionian Fuel Refinery"
          description="+1 move for ONE ship this action (the ship that needs it)."
          checked={tempesta}
          onChange={(event) => setTempesta(event.currentTarget.checked)}
        />
      )}
      {imperatorReady && (
        <Switch
          label="Use Imperator"
          description="+1 move for ONE ship this action (can be a different ship than Gravity Drive)."
          checked={imperator}
          onChange={(event) => setImperator(event.currentTarget.checked)}
        />
      )}
      {gameState?.imperatorBoostActive === true && gameState?.imperatorUsed === true && (
        <span className={styles.prodZoneLabel}>Imperator used this action</span>
      )}
      {gameState?.extraMoveBoostActive === true && gameState?.tempestaUsed === true && (
        <span className={styles.prodZoneLabel}>Ionian Fuel Refinery used this action</span>
      )}
      {(player?.techs ?? []).includes("gd") && gameState?.gravityDriveUsed === true && (
        <span className={styles.prodZoneLabel}>Gravity Drive used this action</span>
      )}

      {/* Fleet pool (RULES.md 42): ruch ponad pulę jest dozwolony, ale nadwyżka zostanie usunięta. */}
      <FleetPoolWarning />
      {/* Ruch z trasą: klik w świecący system na mapie otwiera box, trasa rysuje się na mapie. */}
      <MoveRouteBox
        faction={faction}
        player={player}
        sources={Object.keys(moveRange?.sources ?? {})}
        hue={`rgb(${look(faction).rgb})`}
        gravityDrive={useGd}
        tempesta={useTempesta}
        imperator={useImperator}
      />
      <span className={styles.prodNote}>
        Drag units onto the active system, or click a glowing system (Ctrl+click picks units
        first) - the route window opens with the path drawn on the map.
      </span>

      <button
        type="button"
        className={styles.subAction}
        disabled={busy}
        onClick={() => void run(undoMove)}
        title="Undo your last ship move"
      >
        <IconArrowBackUp size={13} aria-hidden="true" /> Undo last move
      </button>
    </div>
  );
}

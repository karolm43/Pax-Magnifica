import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  IconArrowBackUp,
  IconArrowRight,
  IconMinus,
  IconPackage,
  IconPlus,
  IconShip,
} from "@tabler/icons-react";
import { Switch } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useMoveRange } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { lookupUnit } from "@/entities/lookup/units";
import { Unit } from "@/shared/ui/Unit";
import { FleetPoolWarning } from "@/domains/map/components/FleetPoolWarning";
import type { PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";
import {
  BASE_TYPE_BY_ASYNC,
  CARGO_ASYNC,
  isStructureUnit,
  SHIP_ONLY_ASYNC,
} from "@/domains/map/components/UnitStack/cargo";
import styles from "./GameStatePanel.module.css";

/* Wszystkie statki (ruszające + myśliwiec-ładunek) — do wykrycia systemów źródłowych. */
const SHIP_ASYNC = new Set([...SHIP_ONLY_ASYNC, "ff"]);

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
 * Krok MOVEMENT akcji taktycznej — MONITOR floty + kreator ruchu.
 *
 * Górna część = MONITOR: co gracz ma w przestrzeni AKTYWNEGO systemu (statki +
 * ładunek), pojemność zajęta/wolna, i „Undo last move" (cofa ostatni ruch przez
 * globalny event store). Preferowany sposób ruszania to DRAG & DROP statków na
 * mapie (walidowany), a ten panel pokazuje efekt i pozwala cofnąć.
 *
 * Dolna część = KREATOR (opcjonalny): wybór systemu źródłowego + statków/ładunku
 * i ruch przez walidowany ``/tactical/move`` — dla graczy wolących klikać niż
 * przeciągać. Zasięg/capacity egzekwuje backend (422 z powodem).
 */
export function MovementStepPanel({
  activeSystem,
  activePlayerColor,
}: {
  activeSystem: string;
  activePlayerColor: string | null;
}) {
  const gameData = useGameData();
  const { moveShips, undo } = useBoardEditor();
  const setMoveRangeSources = useAppStore((s) => s.setMoveRangeSources);
  const gravityDrive = useAppStore((s) => s.gravityDrive);
  const setGravityDrive = useAppStore((s) => s.setGravityDrive);
  const routeParams = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(routeParams.mapid ?? DEFAULT_GAME_ID);
  const openLoadTransport = useAppStore((s) => s.openLoadTransport);
  const [source, setSource] = useState<string | null>(null);
  const [picked, setPicked] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [showPicker, setShowPicker] = useState(false);

  const player = gameData?.playerData?.find((p) => p.color === activePlayerColor);
  const faction = player?.faction ?? null;
  const colorAlias = getColorAlias(player?.color);

  // Podgląd zasięgu ruchu (legalne systemy źródłowe) — podświetla heksy na mapie.
  // Gravity Drive (RULES.md 55.6): przełącznik tylko dla właściciela technologii, dopóki w tej
  // akcji nie zużyto premii - to GRACZ decyduje, silnik nie włącza jej sam.
  const gravityDriveReady =
    (player?.techs ?? []).includes("gd") && gameState?.gravityDriveUsed !== true;
  const useGd = gravityDrive && gravityDriveReady;
  useEffect(() => {
    if (!gravityDriveReady && gravityDrive) setGravityDrive(false);
  }, [gravityDriveReady, gravityDrive, setGravityDrive]);
  const { data: moveRange } = useMoveRange(faction, Boolean(activeSystem), useGd);
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

  // Systemy źródłowe (kreator): kafelki poza aktywnym, gdzie gracz ma statki.
  const sources = useMemo(() => {
    const tiles = gameData?.tiles ?? {};
    if (!faction) return [] as { position: string; label: string }[];
    return Object.entries(tiles)
      .filter(([pos]) => pos !== activeSystem)
      .filter(([, tile]) =>
        (tile.unitsByFaction?.[faction] ?? []).some(
          (e) => e.entityType === "unit" && e.count > 0 && SHIP_ASYNC.has(e.entityId),
        ),
      )
      .map(([pos, tile]) => {
        const name = getTileById(tile.systemId)?.name;
        return { position: pos, label: name ? `${pos} · ${name}` : pos };
      })
      .sort((a, b) => a.position.localeCompare(b.position));
  }, [gameData?.tiles, faction, activeSystem]);

  // Wiersze zasięgu: systemy z legalnym ruchem + statki, które tam dolecą, i ich pojemność.
  const rangeRows = useMemo(() => {
    if (!faction) return [];
    const asyncByBase = Object.fromEntries(
      Object.entries(BASE_TYPE_BY_ASYNC).map(([a, b]) => [b, a]),
    );
    return Object.entries(moveRange?.sources ?? {})
      .map(([position, baseTypes]) => {
        const tile = gameData?.tiles?.[position];
        const reach = new Set(baseTypes.map((b) => asyncByBase[b] ?? b));
        const all = playerSpaceStacks(tile, faction);
        const ships = all.filter((s) => reach.has(s.asyncId) && SHIP_ONLY_ASYNC.has(s.asyncId));
        const cap = fleetCapacity(ships, faction, player);
        // Ładunek do zabrania: myśliwce/siły naziemne w przestrzeni ORAZ siły naziemne
        // na planetach systemu (statki mogą je zabrać przy ruchu).
        const cargoMap = new Map<string, { count: number; planet: number }>();
        const addCargo = (asyncId: string, count: number, onPlanet: boolean) => {
          const cur = cargoMap.get(asyncId) ?? { count: 0, planet: 0 };
          cur.count += count;
          if (onPlanet) cur.planet += count;
          cargoMap.set(asyncId, cur);
        };
        for (const s of all) {
          if (CARGO_ASYNC.has(s.asyncId)) addCargo(s.asyncId, s.count, false);
        }
        for (const planet of Object.values(tile?.planets ?? {})) {
          for (const s of playerSpaceStacks(
            { unitsByFaction: planet.unitsByFaction } as Tile,
            faction,
          )) {
            if (CARGO_ASYNC.has(s.asyncId)) addCargo(s.asyncId, s.count, true);
          }
        }
        let cargoUsed = 0;
        const cargo = [...cargoMap.entries()].map(([asyncId, v]) => {
          cargoUsed += (lookupUnit(asyncId, faction, player)?.capacityUsed ?? 1) * v.count;
          return {
            asyncId,
            count: v.count,
            planet: v.planet,
            name: lookupUnit(asyncId, faction, player)?.name ?? asyncId.toUpperCase(),
          };
        });
        const name = tile ? getTileById(tile.systemId)?.name : undefined;
        return {
          position,
          label: name ? `${position} · ${name}` : position,
          ships: ships.map((s) => ({
            ...s,
            name: lookupUnit(s.asyncId, faction, player)?.name ?? s.asyncId.toUpperCase(),
            loadable:
              !isStructureUnit(s.asyncId) &&
              (lookupUnit(s.asyncId, faction, player)?.capacityValue ?? 0) > 0,
          })),
          cargo,
          capacity: cap.total,
          cargoUsed,
        };
      })
      .filter((r) => r.ships.length > 0)
      .sort((a, b) => a.position.localeCompare(b.position));
  }, [moveRange, gameData?.tiles, faction, player]);

  const sourceTile = source ? gameData?.tiles?.[source] : undefined;
  const stacks = faction ? playerSpaceStacks(sourceTile, faction) : [];
  const ships = stacks.filter((s) => SHIP_ONLY_ASYNC.has(s.asyncId));
  // Ładunek źródła: myśliwce/siły naziemne z przestrzeni ORAZ siły naziemne z planet.
  const cargo: { asyncId: string; count: number; zone: string; zoneLabel: string; key: string }[] =
    [];
  for (const s of stacks) {
    if (CARGO_ASYNC.has(s.asyncId)) {
      cargo.push({ ...s, zone: "space", zoneLabel: "space", key: `${s.asyncId}@space` });
    }
  }
  for (const [planetId, planet] of Object.entries(sourceTile?.planets ?? {})) {
    for (const s of playerSpaceStacks(
      { unitsByFaction: planet.unitsByFaction } as Tile,
      faction ?? "",
    )) {
      if (CARGO_ASYNC.has(s.asyncId) && s.asyncId !== "ff") {
        cargo.push({
          ...s,
          zone: planetId,
          zoneLabel: planetId,
          key: `${s.asyncId}@${planetId}`,
        });
      }
    }
  }
  const unitName = (asyncId: string) =>
    (faction ? lookupUnit(asyncId, faction, player)?.name : undefined) ??
    asyncId.toUpperCase();

  const pick = (asyncId: string, max: number, delta: number) => {
    setPicked((prev) => {
      const next = Math.min(Math.max((prev[asyncId] ?? 0) + delta, 0), max);
      return { ...prev, [asyncId]: next };
    });
  };
  const totalPicked = Object.values(picked).reduce((a, b) => a + b, 0);

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!source || !faction || totalPicked === 0) return;
    await moveShips({
      fromPosition: source,
      faction,
      ships: ships
        .filter((s) => (picked[s.asyncId] ?? 0) > 0)
        .map((s) => ({
          baseType: BASE_TYPE_BY_ASYNC[s.asyncId] ?? s.asyncId,
          count: picked[s.asyncId],
        })),
      cargo: cargo
        .filter((s) => (picked[s.key] ?? 0) > 0)
        .map((s) => ({
          baseType: BASE_TYPE_BY_ASYNC[s.asyncId] ?? s.asyncId,
          count: picked[s.key],
          fromZone: s.zone,
        })),
    });
    setPicked({});
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
      {(player?.techs ?? []).includes("gd") && gameState?.gravityDriveUsed === true && (
        <span className={styles.prodZoneLabel}>Gravity Drive used this action</span>
      )}

      {/* Fleet pool (RULES.md 42): ruch ponad pulę jest dozwolony, ale nadwyżka zostanie usunięta. */}
      <FleetPoolWarning />
      {/* ZASIĘG: z których systemów statki dolecą do aktywnego + ich pojemność. */}
      <span className={styles.prodZoneLabel}>
        <IconShip size={11} aria-hidden="true" /> In range
      </span>
      {rangeRows.length === 0 ? (
        <span className={styles.prodNote}>No ships can reach this system.</span>
      ) : (
        <div className={styles.rangeList}>
          {rangeRows.map((row) => (
            <div key={row.position} className={styles.rangeItem}>
            <button
              type="button"
              className={styles.rangeRow}
              data-active={row.position === source || undefined}
              onClick={() => {
                setSource(row.position);
                setPicked({});
                setShowPicker(true);
              }}
              title={`Pick units from ${row.label}`}
            >
              <span className={styles.rangePos}>{row.position}</span>
              <span className={styles.rangeShips}>
                {row.ships.map((s) => (
                  <span key={s.asyncId} className={styles.rangeShip}>
                    {s.count}× {s.name}
                  </span>
                ))}
                {row.cargo.map((c) => (
                  <span
                    key={`c-${c.asyncId}`}
                    className={styles.rangeShip}
                    data-cargo
                  >
                    {c.count}× {c.name}
                    {c.planet > 0 ? ` (${c.planet} on planets)` : ""}
                  </span>
                ))}
              </span>
              <span
                className={styles.capBadge}
                title="Cargo available here (space + planets) / capacity of the ships that can reach"
              >
                <IconPackage size={11} aria-hidden="true" />
                {row.cargoUsed}/{row.capacity}
              </span>
            </button>
            {/* Załadunek: ładunek w przestrzeni LUB piechota/mech z planet systemu. */}
            {row.cargo.length > 0 &&
              row.ships
                .filter((s) => s.loadable)
                .map((s) => (
                  <button
                    key={`load-${s.asyncId}`}
                    type="button"
                    className={styles.moveToggle}
                    onClick={() =>
                      openLoadTransport({
                        fromPosition: row.position,
                        faction,
                        shipAsyncId: s.asyncId,
                      })
                    }
                    title="Load this ship with fighters / ground forces (from space or planets) and move it"
                  >
                    <IconPackage size={12} aria-hidden="true" /> Load {s.name} with
                    cargo…
                  </button>
                ))}
            </div>
          ))}
        </div>
      )}
      <span className={styles.prodNote}>
        Drag ships onto the active system on the map, or pick a system above.
      </span>

      <button
        type="button"
        className={styles.subAction}
        disabled={busy}
        onClick={() => void run(undo)}
        title="Undo the last move (reverts the most recent change)"
      >
        <IconArrowBackUp size={13} aria-hidden="true" /> Undo last move
      </button>

      {/* KREATOR ruchu (opcjonalny) — dla wolących klikać zamiast przeciągać. */}
      <button
        type="button"
        className={styles.moveToggle}
        onClick={() => setShowPicker((v) => !v)}
        aria-expanded={showPicker}
      >
        {showPicker ? "− Hide mover" : "+ Move by picking a system"}
      </button>

      {showPicker && (
        <>
          <span className={styles.prodZoneLabel}>Move from</span>
          {sources.length === 0 ? (
            <span className={styles.prodNote}>
              No system with your ships to move from.
            </span>
          ) : (
            <div className={styles.planetTabs}>
              {sources.map((s) => (
                <button
                  key={s.position}
                  type="button"
                  className={styles.planetTab}
                  data-active={s.position === source || undefined}
                  onClick={() => {
                    setSource(s.position);
                    setPicked({});
                  }}
                  title={`Move units from ${s.label}`}
                >
                  {s.position}
                </button>
              ))}
            </div>
          )}

          {source && (
            <>
              {ships.length > 0 && (
                <>
                  <span className={styles.prodZoneLabel}>
                    <IconShip size={11} aria-hidden="true" /> Ships
                  </span>
                  <div className={styles.unitGrid}>
                    {ships.map((s) => (
                      <MoveUnitTile
                        key={s.asyncId}
                        asyncId={s.asyncId}
                        name={unitName(s.asyncId)}
                        count={s.count}
                        picked={picked[s.asyncId] ?? 0}
                        colorAlias={colorAlias}
                        faction={faction}
                        busy={busy}
                        onAdd={() => pick(s.asyncId, s.count, +1)}
                        onRemove={() => pick(s.asyncId, s.count, -1)}
                      />
                    ))}
                  </div>
                  {/* Statki z pojemnością → skrót do okna załadunku (zapakuj i rusz). */}
                  {(cargo.length > 0 ||
                    (rangeRows.find((r) => r.position === source)?.cargo.length ?? 0) > 0) &&
                    source &&
                    ships
                      .filter(
                        (s) =>
                          !isStructureUnit(s.asyncId) &&
                          (lookupUnit(s.asyncId, faction, player)?.capacityValue ??
                            0) > 0,
                      )
                      .map((s) => (
                        <button
                          key={`load-${s.asyncId}`}
                          type="button"
                          className={styles.moveToggle}
                          onClick={() =>
                            openLoadTransport({
                              fromPosition: source,
                              faction,
                              shipAsyncId: s.asyncId,
                            })
                          }
                          title="Open the load window to pack this ship with cargo"
                        >
                          <IconPackage size={12} aria-hidden="true" /> Load{" "}
                          {unitName(s.asyncId)} with cargo…
                        </button>
                      ))}
                </>
              )}
              {cargo.length > 0 && (
                <>
                  <span className={styles.prodZoneLabel}>
                    Cargo · carried (fighters / ground)
                  </span>
                  <div className={styles.unitGrid}>
                    {cargo.map((s) => (
                      <MoveUnitTile
                        key={s.key}
                        asyncId={s.asyncId}
                        name={unitName(s.asyncId)}
                        zoneLabel={s.zoneLabel}
                        count={s.count}
                        picked={picked[s.key] ?? 0}
                        colorAlias={colorAlias}
                        faction={faction}
                        busy={busy}
                        onAdd={() => pick(s.key, s.count, +1)}
                        onRemove={() => pick(s.key, s.count, -1)}
                      />
                    ))}
                  </div>
                </>
              )}
              <button
                type="button"
                className={styles.subAction}
                disabled={busy || totalPicked === 0}
                onClick={() => void run(submit)}
                title="Move the selected fleet to the active system (rules validated)"
              >
                <IconArrowRight size={13} aria-hidden="true" /> Move {totalPicked} to
                active system
              </button>
            </>
          )}
          <span className={styles.prodNote}>
            Range, anomalies and capacity are checked by the engine — an illegal
            move is rejected with a reason.
          </span>
        </>
      )}
    </div>
  );
}

/** Kafelek jednej jednostki do ruszenia: ikona, „wybrane / dostępne", +/−. */
function MoveUnitTile({
  asyncId,
  name,
  zoneLabel,
  count,
  picked,
  colorAlias,
  faction,
  busy,
  onAdd,
  onRemove,
}: {
  asyncId: string;
  name: string;
  zoneLabel?: string;
  count: number;
  picked: number;
  colorAlias: string;
  faction: string;
  busy: boolean;
  onAdd: () => void;
  onRemove: () => void;
}) {
  return (
    <div
      className={styles.unitTile}
      title={zoneLabel ? `${name} · from ${zoneLabel}` : name}
    >
      <div className={styles.unitTileIcon}>
        <Unit
          unitType={asyncId}
          colorAlias={colorAlias}
          faction={faction}
          scaleSprite
        />
      </div>
      <span className={styles.unitTileName}>
        {name}
        {zoneLabel ? ` · ${zoneLabel}` : ""}
      </span>
      <span className={styles.unitTileCost} title="Selected / available">
        {picked}/{count}
      </span>
      <div className={styles.unitTileBtns}>
        <button
          type="button"
          className={styles.unitStep}
          disabled={busy || picked <= 0}
          onClick={onRemove}
          aria-label={`Fewer ${asyncId}`}
        >
          <IconMinus size={13} />
        </button>
        <button
          type="button"
          className={styles.unitStep}
          disabled={busy || picked >= count}
          onClick={onAdd}
          aria-label={`More ${asyncId}`}
        >
          <IconPlus size={13} />
        </button>
      </div>
    </div>
  );
}

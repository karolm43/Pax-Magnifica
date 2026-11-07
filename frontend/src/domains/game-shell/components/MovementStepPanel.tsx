import { useEffect, useMemo, useState } from "react";
import {
  IconArrowBackUp,
  IconArrowRight,
  IconMinus,
  IconPackage,
  IconPlus,
  IconShip,
} from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useMoveRange } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
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
  const openLoadTransport = useAppStore((s) => s.openLoadTransport);
  const [source, setSource] = useState<string | null>(null);
  const [picked, setPicked] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [showPicker, setShowPicker] = useState(false);

  const player = gameData?.playerData?.find((p) => p.color === activePlayerColor);
  const faction = player?.faction ?? null;
  const colorAlias = getColorAlias(player?.color);

  // Podgląd zasięgu ruchu (legalne systemy źródłowe) — podświetla heksy na mapie.
  const { data: moveRange } = useMoveRange(faction, Boolean(activeSystem));
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

  // Transporty (statki z capacity) w systemach źródłowych — skrót do okna załadunku.
  // Wyeksponowane WPROST (bez ukrywania), bo transport to główna część ruchu.
  const transports = useMemo(() => {
    const tiles = gameData?.tiles ?? {};
    if (!faction || !player) return [] as { position: string; asyncId: string }[];
    const out: { position: string; asyncId: string }[] = [];
    for (const [pos, tile] of Object.entries(tiles)) {
      if (pos === activeSystem) continue;
      for (const e of tile.unitsByFaction?.[faction] ?? []) {
        if (
          e.entityType === "unit" &&
          e.count > 0 &&
          !isStructureUnit(e.entityId) &&
          (lookupUnit(e.entityId, faction, player)?.capacityValue ?? 0) > 0
        ) {
          out.push({ position: pos, asyncId: e.entityId });
        }
      }
    }
    return out.sort((a, b) => a.position.localeCompare(b.position));
  }, [gameData?.tiles, faction, player, activeSystem]);

  const sourceTile = source ? gameData?.tiles?.[source] : undefined;
  const stacks = faction ? playerSpaceStacks(sourceTile, faction) : [];
  const ships = stacks.filter((s) => SHIP_ONLY_ASYNC.has(s.asyncId));
  const cargo = stacks.filter((s) => CARGO_ASYNC.has(s.asyncId));

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
    const toOrders = (list: Stack[]) =>
      list
        .filter((s) => (picked[s.asyncId] ?? 0) > 0)
        .map((s) => ({
          baseType: BASE_TYPE_BY_ASYNC[s.asyncId] ?? s.asyncId,
          count: picked[s.asyncId],
        }));
    await moveShips({
      fromPosition: source,
      faction,
      ships: toOrders(ships),
      cargo: toOrders(cargo),
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

      {/* Fleet pool (RULES.md 42): ruch ponad pulę jest dozwolony, ale nadwyżka zostanie usunięta. */}
      <FleetPoolWarning />
      {fleet.length === 0 ? (
        <span className={styles.prodNote}>
          Nothing moved here yet. Drag ships onto this system, or use the mover below.
        </span>
      ) : (
        <div className={styles.unitGrid}>
          {fleet.map((s) => (
            <div key={s.asyncId} className={styles.unitTile} title={s.asyncId.toUpperCase()}>
              <div className={styles.unitTileIcon}>
                <Unit unitType={s.asyncId} colorAlias={colorAlias} faction={faction} scaleSprite />
              </div>
              <span className={styles.unitTileName}>{s.asyncId.toUpperCase()}</span>
              <span className={styles.unitTileCost}>×{s.count}</span>
            </div>
          ))}
        </div>
      )}

      {/* TRANSPORT — główny sposób zabrania myśliwców/piechoty (z przestrzeni i planet
          systemu źródłowego). Wprost widoczny, jedno kliknięcie otwiera okno załadunku. */}
      {transports.length > 0 && (
        <>
          <span className={styles.prodZoneLabel}>
            <IconPackage size={11} aria-hidden="true" /> Load a transport
          </span>
          <div className={styles.unitGrid}>
            {transports.map((t) => (
              <button
                key={`${t.position}-${t.asyncId}`}
                type="button"
                className={styles.transportTile}
                onClick={() =>
                  faction &&
                  openLoadTransport({
                    fromPosition: t.position,
                    faction,
                    shipAsyncId: t.asyncId,
                  })
                }
                title={`Load ${t.asyncId.toUpperCase()} in ${t.position} with fighters / ground forces`}
              >
                <div className={styles.unitTileIcon}>
                  <Unit
                    unitType={t.asyncId}
                    colorAlias={colorAlias}
                    faction={faction}
                    scaleSprite
                  />
                </div>
                <span className={styles.unitTileName}>
                  {t.asyncId.toUpperCase()}
                </span>
                <span className={styles.unitTileCost}>{t.position}</span>
              </button>
            ))}
          </div>
        </>
      )}

      <button
        type="button"
        className={styles.nextStep}
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
                  {cargo.length > 0 &&
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
                          {s.asyncId.toUpperCase()} with cargo…
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
                        key={s.asyncId}
                        asyncId={s.asyncId}
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
                </>
              )}
              <button
                type="button"
                className={styles.nextStep}
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
  count,
  picked,
  colorAlias,
  faction,
  busy,
  onAdd,
  onRemove,
}: {
  asyncId: string;
  count: number;
  picked: number;
  colorAlias: string;
  faction: string;
  busy: boolean;
  onAdd: () => void;
  onRemove: () => void;
}) {
  return (
    <div className={styles.unitTile} title={asyncId.toUpperCase()}>
      <div className={styles.unitTileIcon}>
        <Unit
          unitType={asyncId}
          colorAlias={colorAlias}
          faction={faction}
          scaleSprite
        />
      </div>
      <span className={styles.unitTileName}>{asyncId.toUpperCase()}</span>
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

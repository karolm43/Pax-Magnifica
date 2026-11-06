import { useEffect, useMemo, useState } from "react";
import { IconArrowRight, IconMinus, IconPlus, IconShip } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useMoveRange } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { Unit } from "@/shared/ui/Unit";
import type { Tile } from "@/entities/game/types";
import {
  BASE_TYPE_BY_ASYNC,
  CARGO_ASYNC,
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

/**
 * Okno RUCHU (krok MOVEMENT akcji taktycznej) — dedykowany kreator zamiast trybu
 * „move" na mapie. Gracz wybiera system ŹRÓDŁOWY (spośród tych, gdzie ma statki,
 * poza aktywnym), a potem ile statków i ile ładunku (myśliwce / siły naziemne)
 * ruszyć do aktywnego systemu. Transport i zasięg (R1–R6 + capacity) waliduje
 * backend (RULES.md 32/32.3) — nielegalny ruch wraca 422 i trafia do panelu
 * komunikatów. Cel jest zawsze aktywnym systemem (ruch taktyczny nie wybiera celu).
 */
export function MovementStepPanel({
  activeSystem,
  activePlayerColor,
}: {
  activeSystem: string;
  activePlayerColor: string | null;
}) {
  const gameData = useGameData();
  const { moveShips } = useBoardEditor();
  const setMoveRangeSources = useAppStore((s) => s.setMoveRangeSources);
  const [source, setSource] = useState<string | null>(null);
  // Wybrane liczby do ruszenia: {asyncId: liczba}. Reset przy zmianie źródła.
  const [picked, setPicked] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  const player = gameData?.playerData?.find((p) => p.color === activePlayerColor);
  const faction = player?.faction ?? null;
  const colorAlias = getColorAlias(player?.color);

  // Podgląd zasięgu ruchu z backendu (legalne systemy źródłowe) — podświetla heksy
  // na mapie. Odświeża się z każdym stanem gry (statki się ruszają). Czyszczone przy
  // odmontowaniu panelu (wyjście z kroku MOVEMENT / zakończenie akcji).
  const { data: moveRange } = useMoveRange(faction, Boolean(activeSystem));
  useEffect(() => {
    setMoveRangeSources(new Set(Object.keys(moveRange?.sources ?? {})));
    return () => setMoveRangeSources(new Set());
  }, [moveRange, setMoveRangeSources]);

  // Systemy źródłowe: kafelki (poza aktywnym), w których gracz ma statki w przestrzeni.
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

  const submit = async () => {
    if (!source || !faction || busy || totalPicked === 0) return;
    setBusy(true);
    try {
      const shipList = ships
        .filter((s) => (picked[s.asyncId] ?? 0) > 0)
        .map((s) => ({
          baseType: BASE_TYPE_BY_ASYNC[s.asyncId] ?? s.asyncId,
          count: picked[s.asyncId],
        }));
      const cargoList = cargo
        .filter((s) => (picked[s.asyncId] ?? 0) > 0)
        .map((s) => ({
          baseType: BASE_TYPE_BY_ASYNC[s.asyncId] ?? s.asyncId,
          count: picked[s.asyncId],
        }));
      await moveShips({
        fromPosition: source,
        faction,
        ships: shipList,
        cargo: cargoList,
      });
      // Po udanym ruchu wyzeruj wybór (jednostki już są w aktywnym systemie).
      setPicked({});
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
      {/* Wybór systemu źródłowego (gdzie gracz ma statki). */}
      <span className={styles.prodZoneLabel}>Move from</span>
      {sources.length === 0 ? (
        <span className={styles.prodNote}>
          No system with your ships to move from (other than the active system).
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
          {/* Statki ruszające. */}
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
            </>
          )}

          {/* Ładunek (myśliwce / siły naziemne) — wymaga statku z capacity. */}
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
            onClick={() => void submit()}
            title="Move the selected fleet to the active system (rules validated)"
          >
            <IconArrowRight size={13} aria-hidden="true" /> Move {totalPicked} to
            active system
          </button>
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

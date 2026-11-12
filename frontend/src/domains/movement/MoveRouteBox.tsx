import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  IconArrowRight,
  IconPackage,
  IconRoute,
  IconSend,
  IconX,
} from "@tabler/icons-react";
import { getPortalRoot } from "@/ds";
import { useBoardEditor, useMoveRoute } from "@/api/useBoardEditor";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { getPlanetData } from "@/entities/lookup/planets";
import { getTileById } from "@/entities/lookup/systems";
import { lookupUnit } from "@/entities/lookup/units";
import type { PlayerData } from "@/entities/data/types";
import { RouteUnitChip } from "./RouteUnitChip";
import {
  asyncOfBase,
  draftCapacity,
  pickKey,
  type PickTarget,
} from "./routeTypes";
import styles from "./MoveRouteBox.module.css";

type Props = {
  faction: string;
  player: PlayerData | undefined;
  /** Systemy, z których ruch do aktywnego jest legalny (klikalne źródła na mapie). */
  sources: string[];
  /** Kolor gracza (CSS) do podświetleń na mapie. */
  hue: string;
  gravityDrive: boolean;
  tempesta: boolean;
};

/**
 * Ruch z trasą w kroku MOVEMENT. Klik w system źródłowy na mapie otwiera ten mały, przeciągalny
 * box: lista statków stamtąd i ładunku leżącego NA TRASIE (lewy przycisk +1, prawy −1, Shift =
 * wszystkie), pasek capacity, alternatywne trasy. Sama trasa i ładunek po drodze są też
 * rysowane na mapie (``MoveRouteLayer``); klik w świecący system na mapie przerzuca trasę
 * przez niego (jak waypoint w nawigacji). Zasięg, blokady i capacity egzekwuje backend.
 */
export function MoveRouteBox({ faction, player, sources, hue, gravityDrive, tempesta }: Props) {
  const gameData = useGameData();
  const draft = useAppStore((s) => s.moveDraft);
  const openMoveDraft = useAppStore((s) => s.openMoveDraft);
  const closeMoveDraft = useAppStore((s) => s.closeMoveDraft);
  const setMoveDraftVia = useAppStore((s) => s.setMoveDraftVia);
  const setMoveDraftRoute = useAppStore((s) => s.setMoveDraftRoute);
  const bumpDraftPick = useAppStore((s) => s.bumpDraftPick);
  const clearDraftPicks = useAppStore((s) => s.clearDraftPicks);
  const setRoutePick = useAppStore((s) => s.setRoutePick);
  const { moveShips } = useBoardEditor();
  const drag = useDraggablePanel("moveRouteBox.pos.v1");
  const [busy, setBusy] = useState(false);
  const colorAlias = getColorAlias(player?.color);

  // Podgląd trasy z backendu; stary wynik (placeholder) nie trafia do store przy zmianie źródła.
  const { data: routeData, isPlaceholderData } = useMoveRoute(
    draft ? faction : null,
    draft?.from ?? null,
    draft?.via ?? [],
    gravityDrive,
    tempesta,
  );
  useEffect(() => {
    if (draft && routeData && !isPlaceholderData) setMoveDraftRoute(routeData);
  }, [draft?.from, routeData, isPlaceholderData, setMoveDraftRoute]);

  // Klikalne cele na mapie: źródła (otwierają/zamykają box), a przy otwartym boxie także
  // systemy, przez które da się poprowadzić trasę (waypointy).
  const route = draft?.route ?? null;
  const waypointTargets = draft ? (route?.waypoints ?? []).filter((w) => !sources.includes(w)) : [];
  const targets = [...new Set([...waypointTargets, ...sources])];
  const selected = draft ? [draft.from, ...draft.via] : [];
  const onPickRef = useRef((_position: string) => {});
  onPickRef.current = (position: string) => {
    const current = useAppStore.getState().moveDraft;
    if (sources.includes(position)) {
      if (current?.from === position) closeMoveDraft();
      else openMoveDraft(position, faction);
      return;
    }
    if (!current) return;
    if (current.via.includes(position)) {
      setMoveDraftVia(current.via.filter((v) => v !== position));
      return;
    }
    // Trasa alternatywna przez ten system (i dotychczasowe waypointy) = od razu cała trasa.
    const alt = current.route?.alternatives.find(
      (a) => a.includes(position) && current.via.every((v) => a.includes(v)),
    );
    setMoveDraftVia(alt ? alt.slice(1, -1) : [...current.via, position]);
  };
  const targetsKey = targets.join("|");
  const selectedKey = selected.join("|");
  useEffect(() => {
    if (targetsKey === "") {
      setRoutePick(null);
      return;
    }
    setRoutePick({
      targets: targetsKey.split("|"),
      selected: selectedKey === "" ? [] : selectedKey.split("|"),
      hue,
      onPick: (position) => onPickRef.current(position),
    });
    return () => setRoutePick(null);
  }, [targetsKey, selectedKey, hue, setRoutePick]);

  // Wyjście z kroku MOVEMENT (odmontowanie panelu) zamyka box i czyści podgląd.
  useEffect(
    () => () => {
      useAppStore.getState().closeMoveDraft();
      useAppStore.getState().setRoutePick(null);
    },
    [],
  );

  useEffect(() => {
    if (!draft) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMoveDraft();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [draft, closeMoveDraft]);

  const portalRoot = getPortalRoot();
  if (!draft || !portalRoot) return null;

  const tiles = gameData?.tiles ?? {};
  const systemName = (position: string): string => {
    const tile = tiles[position];
    const name = tile ? getTileById(tile.systemId)?.name : undefined;
    return name ? `${position} · ${name}` : position;
  };
  const unitName = (asyncId: string) =>
    lookupUnit(asyncId, faction, player)?.name ?? asyncId.toUpperCase();
  const zoneLabel = (zone: string) =>
    zone === "space" ? "Space" : (getPlanetData(zone)?.name ?? zone);

  const cap = draftCapacity(draft);
  const over = cap.used > cap.total;
  const picks = Object.values(draft.picks);
  const shipCount = picks.filter((p) => p.kind === "ship").reduce((n, p) => n + p.count, 0);
  const cargoCount = picks.filter((p) => p.kind === "cargo").reduce((n, p) => n + p.count, 0);
  const jumps = route?.route ? route.route.length - 1 : null;

  const bump = (target: PickTarget, delta: number) => bumpDraftPick(target, delta);

  const submit = async () => {
    if (busy || shipCount + cargoCount === 0) return;
    setBusy(true);
    try {
      await moveShips({
        fromPosition: draft.from,
        faction,
        ships: picks
          .filter((p) => p.kind === "ship")
          .map((p) => ({ baseType: p.baseType, count: p.count })),
        cargo: picks
          .filter((p) => p.kind === "cargo")
          .map((p) => ({
            baseType: p.baseType,
            count: p.count,
            fromZone: p.zone,
            fromPosition: p.position,
          })),
        route: route?.route ?? undefined,
      });
      closeMoveDraft();
    } catch {
      // Powód (422) trafia do panelu komunikatów; box zostaje, żeby poprawić wybór.
    } finally {
      setBusy(false);
    }
  };

  const reachableShips = route?.ships.filter((s) => s.reachable) ?? [];
  const cargoNodes = (route?.route ?? [])
    .slice(0, -1)
    .map((position) => ({
      position,
      entries: (route?.cargo ?? []).filter((c) => c.position === position),
    }))
    .filter((n) => n.entries.length > 0);

  return createPortal(
    <section
      ref={drag.ref}
      className={styles.box}
      role="group"
      aria-label={`Move from ${systemName(draft.from)}`}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
      style={drag.style}
    >
      <header
        className={styles.head}
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move (double-click resets)"
      >
        <IconRoute size={16} aria-hidden="true" />
        <span className={styles.title}>
          <b>{systemName(draft.from)}</b>
          <IconArrowRight size={12} aria-hidden="true" />
          <b>{route?.active ?? "active system"}</b>
        </span>
        <button
          type="button"
          className={styles.iconBtn}
          data-no-drag
          aria-label="Close move box"
          onClick={closeMoveDraft}
        >
          <IconX size={14} />
        </button>
      </header>

      <div className={styles.cap} data-over={over || undefined}>
        <IconPackage size={13} aria-hidden="true" />
        <span>
          Capacity {cap.used}/{cap.total}
          {over ? " · over!" : ""}
        </span>
        <span className={styles.capBar} aria-hidden="true">
          <i style={{ width: `${cap.total > 0 ? Math.min(100, (cap.used / cap.total) * 100) : 0}%` }} />
        </span>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHead}>
          <span>Route{jumps !== null ? ` · ${jumps} jump${jumps === 1 ? "" : "s"}` : ""}</span>
          {draft.via.length > 0 && (
            <button type="button" className={styles.link} onClick={() => setMoveDraftVia([])}>
              Reset route
            </button>
          )}
        </div>
        {route?.route && (
          <ol className={styles.path} aria-label="Route">
            {route.route.map((position) => (
              <li key={position} data-via={draft.via.includes(position) || undefined}>
                {position}
              </li>
            ))}
          </ol>
        )}
        {route && route.reason !== "" && <p className={styles.warn}>{route.reason}</p>}
        {route && route.alternatives.length > 1 && (
          <div className={styles.alts} role="group" aria-label="Alternative routes">
            {route.alternatives.map((alt, index) => {
              const current = route.route !== null && alt.join("|") === route.route.join("|");
              const middle = alt.slice(1, -1);
              return (
                <button
                  type="button"
                  key={alt.join("|")}
                  className={styles.alt}
                  aria-pressed={current}
                  onClick={() => setMoveDraftVia(middle)}
                  title={`Fly via ${middle.join(" → ") || "directly"}`}
                >
                  {String.fromCharCode(65 + index)} · {alt.length - 1}
                  <small>{middle.length > 0 ? `via ${middle.join(", ")}` : "direct"}</small>
                </button>
              );
            })}
          </div>
        )}
        <p className={styles.hint}>
          Click a glowing system on the map to route through it. Units along the route can be
          picked up here or right on the route.
        </p>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHead}>
          <span>Ships</span>
          {reachableShips.length > 0 && (
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                for (const s of reachableShips) {
                  bump(
                    {
                      kind: "ship",
                      position: draft.from,
                      zone: "space",
                      baseType: s.baseType,
                      max: s.boosted ? 1 : s.count,
                    },
                    Number.POSITIVE_INFINITY,
                  );
                }
              }}
            >
              Select all
            </button>
          )}
        </div>
        {route === null && <p className={styles.hint}>Loading route…</p>}
        {route?.ships.length === 0 && (
          <p className={styles.hint}>No ships that can move on their own here.</p>
        )}
        <div className={styles.list}>
          {route?.ships.map((s) => {
            const target: PickTarget = {
              kind: "ship",
              position: draft.from,
              zone: "space",
              baseType: s.baseType,
              max: s.boosted ? 1 : s.count,
            };
            const asyncId = asyncOfBase(s.baseType);
            return (
              <RouteUnitChip
                key={s.baseType}
                variant="row"
                asyncId={asyncId}
                colorAlias={colorAlias}
                faction={faction}
                name={unitName(asyncId)}
                caption={
                  !s.reachable
                    ? s.reason || "out of range"
                    : s.boosted
                      ? "+1 move bonus, 1 ship"
                      : s.capacity > 0
                        ? `capacity ${s.capacity}`
                        : undefined
                }
                picked={draft.picks[pickKey(target)]?.count ?? 0}
                max={target.max}
                disabled={!s.reachable}
                title={s.reachable ? undefined : s.reason}
                onChange={(delta) => bump(target, delta)}
              />
            );
          })}
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHead}>
          <span>Cargo along the route</span>
        </div>
        {cargoNodes.length === 0 && (
          <p className={styles.hint}>No fighters or ground forces to pick up.</p>
        )}
        {cargoNodes.map((node) => (
          <div key={node.position} className={styles.node}>
            <div className={styles.nodeHead}>
              {node.position === draft.from ? "Start" : "En route"} · {systemName(node.position)}
            </div>
            <div className={styles.list}>
              {node.entries.map((c) => {
                const target: PickTarget = {
                  kind: "cargo",
                  position: c.position,
                  zone: c.zone,
                  baseType: c.baseType,
                  max: c.count,
                };
                const asyncId = asyncOfBase(c.baseType);
                return (
                  <RouteUnitChip
                    key={pickKey(target)}
                    variant="row"
                    asyncId={asyncId}
                    colorAlias={colorAlias}
                    faction={faction}
                    name={unitName(asyncId)}
                    caption={zoneLabel(c.zone)}
                    picked={draft.picks[pickKey(target)]?.count ?? 0}
                    max={c.count}
                    onChange={(delta) => bump(target, delta)}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <footer className={styles.foot}>
        <button
          type="button"
          className={styles.ghost}
          disabled={busy || picks.length === 0}
          onClick={clearDraftPicks}
        >
          Clear
        </button>
        <button
          type="button"
          className={styles.primary}
          disabled={busy || shipCount + cargoCount === 0 || route?.route == null}
          onClick={() => void submit()}
        >
          <IconSend size={14} aria-hidden="true" />
          Move {shipCount} ship{shipCount === 1 ? "" : "s"}
          {cargoCount > 0 ? ` + ${cargoCount} cargo` : ""}
        </button>
      </footer>
    </section>,
    portalRoot,
  );
}

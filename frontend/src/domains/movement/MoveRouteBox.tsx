import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import {
  IconArrowRight,
  IconPackage,
  IconPlaylistAdd,
  IconRoute,
  IconX,
} from "@tabler/icons-react";
import { getPortalRoot } from "@/ds";
import { useMoveRoute } from "@/api/useBoardEditor";
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
  BOOST_NAMES,
  draftAsLeg,
  neededBoosts,
  newLegId,
  stagedElsewhere,
} from "./flightPlan";
import {
  asyncOfBase,
  draftCapacity,
  draftProblems,
  otherRoleCount,
  pickKey,
  shipMax,
  type MoveRouteShip,
  type PickTarget,
} from "./routeTypes";
import styles from "./MoveRouteBox.module.css";

const SIZE_KEY = "moveRouteBox.size.v1";
const EDGE = 8;

type Size = { width: number; height: number };

function readSize(): Size | null {
  try {
    const raw = localStorage.getItem(SIZE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Size;
    return typeof parsed.width === "number" && typeof parsed.height === "number" ? parsed : null;
  } catch {
    return null; // uszkodzony wpis - domyślny rozmiar z CSS
  }
}

function writeSize(size: Size): void {
  try {
    localStorage.setItem(SIZE_KEY, JSON.stringify(size));
  } catch {
    /* brak localStorage - rozmiar po prostu nie przetrwa przeładowania */
  }
}

/** Maksymalny rozmiar = miejsce od rogu przesuniętego panelu do krawędzi okna. */
function maxSizeFor(style: CSSProperties): CSSProperties {
  if (typeof style.left !== "number" || typeof style.top !== "number") return {};
  return {
    maxWidth: `calc(100vw - ${style.left + EDGE}px)`,
    maxHeight: `calc(100vh - ${style.top + EDGE}px)`,
  };
}

type Props = {
  faction: string;
  player: PlayerData | undefined;
  /** Systemy, z których ruch do aktywnego jest legalny (klikalne źródła na mapie). */
  sources: string[];
  /** Kolor gracza (CSS) do podświetleń na mapie. */
  hue: string;
  gravityDrive: boolean;
  tempesta: boolean;
  imperator?: boolean;
  /** Rendered inside the tactical window (no floating, draggable portal). */
  embedded?: boolean;
};

/**
 * One LEG of the flight plan (Move Ships step, RULES.md 32.4). Clicking a source system on the
 * map opens this picker: ships from there and cargo lying ON THE ROUTE (left click +1, right
 * -1, Shift = all), capacity bar, alternative routes. The route and cargo along it are also
 * drawn on the map (``MoveRouteLayer``); clicking a glowing system reroutes through it (like a
 * waypoint in navigation). "Add to flight plan" stages the leg - nothing moves until the
 * tactical window's "Fly" sends the whole plan. Units staged in other legs are not offered
 * again. ``embedded`` renders it inside the tactical window instead of a floating box.
 */
export function MoveRouteBox({
  faction,
  player,
  sources,
  hue,
  gravityDrive,
  tempesta,
  imperator = false,
  embedded = false,
}: Props) {
  const gameData = useGameData();
  const draft = useAppStore((s) => s.moveDraft);
  const openMoveDraft = useAppStore((s) => s.openMoveDraft);
  const closeMoveDraft = useAppStore((s) => s.closeMoveDraft);
  const setMoveDraftVia = useAppStore((s) => s.setMoveDraftVia);
  const setMoveDraftRoute = useAppStore((s) => s.setMoveDraftRoute);
  const bumpDraftPick = useAppStore((s) => s.bumpDraftPick);
  const clearDraftPicks = useAppStore((s) => s.clearDraftPicks);
  const setRoutePick = useAppStore((s) => s.setRoutePick);
  const movePlan = useAppStore((s) => s.movePlan);
  const stageMoveDraft = useAppStore((s) => s.stageMoveDraft);
  const editStagedLeg = useAppStore((s) => s.editStagedLeg);
  const drag = useDraggablePanel("moveRouteBox.pos.v1");
  // Ion Storm w systemie z własnym wormholem tego typu: którego wormholu używają statki
  // (C_exploration_cards; żeton obraca się tylko przy jego użyciu). Wybór per źródło ruchu.
  const [stormPick, setStormPick] = useState<{ from: string; token: boolean } | null>(null);
  // Rozmiar ustawiony uchwytem w rogu: zapamiętany w localStorage, wraca przy kolejnym otwarciu.
  const [savedSize] = useState(readSize);
  const observerRef = useRef<ResizeObserver | null>(null);
  const boxRef = useCallback(
    (el: HTMLElement | null) => {
      drag.ref(el);
      observerRef.current?.disconnect();
      observerRef.current = null;
      if (!el || typeof ResizeObserver === "undefined") return;
      const observer = new ResizeObserver(() => {
        const rect = el.getBoundingClientRect();
        writeSize({ width: Math.round(rect.width), height: Math.round(rect.height) });
      });
      observer.observe(el);
      observerRef.current = observer;
    },
    [drag.ref],
  );
  const colorAlias = getColorAlias(player?.color);

  // Podgląd trasy z backendu; stary wynik (placeholder) nie trafia do store przy zmianie źródła.
  const { data: routeData, isPlaceholderData } = useMoveRoute(
    draft ? faction : null,
    draft?.from ?? null,
    draft?.via ?? [],
    gravityDrive,
    tempesta,
    imperator,
  );
  // ``routeMissing``: nowy wybór (np. Ctrl+drag z TEGO SAMEGO źródła) zeruje trasę w store, a
  // zapytanie zwraca te same dane z cache — bez tej zależności box zostawał bez trasy i wyboru.
  const routeMissing = draft !== null && draft.route === null;
  useEffect(() => {
    if (draft && routeData && !isPlaceholderData) setMoveDraftRoute(routeData);
  },[draft?.from, routeMissing, routeData, isPlaceholderData, setMoveDraftRoute]);

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
      if (current?.from === position) {
        closeMoveDraft();
        return;
      }
      // A system with a staged leg reopens that leg for editing (one leg per source system).
      const staged = useAppStore.getState().movePlan.find((l) => l.from === position);
      if (staged) editStagedLeg(staged.id);
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
  // Sources with a staged leg stay highlighted as "selected" (their route is on the map too).
  const stagedFroms = movePlan.map((l) => l.from).filter((f) => f !== draft?.from);
  const targetsKey = targets.join("|");
  const selectedKey = [...selected, ...stagedFroms].join("|");
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
  if (!draft || (!embedded && !portalRoot)) return null;

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

  const bonusName = (bonus: string) =>
    bonus === "gravity_drive"
      ? "Gravity Drive"
      : bonus === "tempesta"
        ? "Ionian Fuel Refinery"
        : bonus === "imperator"
          ? "Imperator"
          : bonus;
  const shipCaption = (s: MoveRouteShip): string | undefined => {
    if (!s.reachable) return s.reason || "out of range";
    // Fighter II leci sam (nie zajmuje miejsca w transporcie), ale w celu potrzebuje capacity;
    // nadwyżka liczy się wtedy do fleet pool.
    if (s.alone && s.baseType === "fighter") return "flies on its own · needs capacity there";
    if (s.alone) return s.capacity > 0 ? `capacity ${s.capacity}` : undefined;
    if (s.withShips.length > 0) {
      const mates = s.withShips.map((bt) => unitName(asyncOfBase(bt))).join(" / ");
      return `with ${mates} (Gravleash)`;
    }
    const combo = s.bonusOptions[0] ?? [];
    const via = combo.map(bonusName).join(" + ") || "+1 move";
    return s.bonusMax > 1 ? `needs ${via}` : `needs ${via}, 1 ship`;
  };
  const enabledBoosts = { gravity_drive: gravityDrive, tempesta, imperator };
  const legBoosts = route ? neededBoosts(route, draft.picks) : [];
  const problems = [
    ...draftProblems(
      draft,
      (bt) => unitName(asyncOfBase(bt)),
      gravityDrive || tempesta || imperator,
    ),
    ...legBoosts
      .filter((b) => !enabledBoosts[b])
      .map((b) => `This leg needs ${BOOST_NAMES[b]} - turn it on in the movement step.`),
  ];
  const cap = draftCapacity(draft);
  const over = cap.used > cap.total;
  const picks = Object.values(draft.picks);
  const shipCount = picks.filter((p) => p.kind === "ship").reduce((n, p) => n + p.count, 0);
  const cargoCount = picks.filter((p) => p.kind === "cargo").reduce((n, p) => n + p.count, 0);
  const jumps = route?.route ? route.route.length - 1 : null;

  // Units staged in OTHER legs of the plan cannot be picked again here.
  const withoutStaged = (target: PickTarget): PickTarget => ({
    ...target,
    max: target.max - stagedElsewhere(movePlan, draft.legId, target),
  });
  const bump = (target: PickTarget, delta: number) =>
    bumpDraftPick(withoutStaged(target), delta);
  const roomFor = (target: PickTarget) =>
    withoutStaged(target).max - otherRoleCount(draft.picks, draft.from, target);
  const stormToken = stormPick?.from === draft.from ? stormPick.token : undefined;
  const stormMissing = Boolean(route?.ionStormChoice) && stormToken === undefined;

  const stage = () => {
    const leg = draftAsLeg(draft, draft.legId ?? newLegId(), stormToken);
    if (leg) stageMoveDraft(leg);
  };

  const reachableShips = route?.ships.filter((s) => s.reachable) ?? [];
  const lastNode = route?.route?.[route.route.length - 1];
  const cargoNodes = (route?.route ?? [])
    .map((position) => ({
      position,
      entries: (route?.cargo ?? []).filter((c) => c.position === position),
    }))
    .filter((n) => n.entries.length > 0);

  const box = (
    <section
      ref={embedded ? undefined : boxRef}
      className={embedded ? styles.embedded : styles.box}
      role="group"
      aria-label={`Move from ${systemName(draft.from)}`}
      data-draggable-panel={embedded ? undefined : true}
      data-dragging={(!embedded && drag.isDragging) || undefined}
      style={
        embedded ? undefined : { ...(savedSize ?? {}), ...drag.style, ...maxSizeFor(drag.style) }
      }
    >
      <header
        className={styles.head}
        onPointerDown={embedded ? undefined : drag.onHandlePointerDown}
        onDoubleClick={embedded ? undefined : drag.reset}
        title={embedded ? undefined : "Drag to move (double-click resets)"}
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
          aria-label="Close leg editor"
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
        {route && route.riftNodes.length > 0 && (
          <p className={styles.rift}>
            Gravity rift ({route.riftNodes.join(", ")}): +{route.riftNodes.length} move
            {route.riftRolls
              ? ", but every ship rolls a d10 and is removed on 1–3. Cargo on removed ships is lost."
              : " without rolling (Circlet of the Void)."}
          </p>
        )}
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
        {route?.ionStormChoice && (
          <div className={styles.alts} role="group" aria-label="Ion Storm wormhole">
            <p className={styles.hint}>
              {systemName(route.ionStormChoice)} has its own wormhole of the same type as the Ion
              Storm token. Which one do your ships use?
            </p>
            <button
              type="button"
              className={styles.alt}
              aria-pressed={stormToken === true}
              onClick={() => setStormPick({ from: draft.from, token: true })}
            >
              Ion Storm token
              <small>flips at the end of the step</small>
            </button>
            <button
              type="button"
              className={styles.alt}
              aria-pressed={stormToken === false}
              onClick={() => setStormPick({ from: draft.from, token: false })}
            >
              System&apos;s own wormhole
              <small>the token stays</small>
            </button>
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
                      max: shipMax(s),
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
              max: shipMax(s),
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
                caption={shipCaption(s)}
                picked={draft.picks[pickKey(target)]?.count ?? 0}
                max={roomFor(target)}
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
              {node.position === draft.from
                ? "Start"
                : node.position === lastNode
                  ? "Destination (ground forces on planets)"
                  : "En route"}{" "}
              · {systemName(node.position)}
              {route?.riftNodes.includes(node.position) ? " · gravity rift" : ""}
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
                    max={roomFor(target)}
                    onChange={(delta) => bump(target, delta)}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {problems.map((problem) => (
        <p key={problem} className={styles.warn} role="alert">
          {problem}
        </p>
      ))}

      <footer className={styles.foot}>
        <button
          type="button"
          className={styles.ghost}
          disabled={picks.length === 0}
          onClick={clearDraftPicks}
        >
          Clear
        </button>
        <button
          type="button"
          className={styles.primary}
          disabled={
            shipCount + cargoCount === 0 ||
            route?.route == null ||
            problems.length > 0 ||
            stormMissing
          }
          onClick={stage}
          title="Stage this leg - nothing moves until you fly the whole plan"
        >
          <IconPlaylistAdd size={14} aria-hidden="true" />
          {draft.legId ? "Update leg" : "Add to flight plan"} ({shipCount} ship
          {shipCount === 1 ? "" : "s"}
          {cargoCount > 0 ? ` + ${cargoCount} cargo` : ""})
        </button>
      </footer>
    </section>
  );
  if (embedded) return box;
  return portalRoot ? createPortal(box, portalRoot) : null;
}

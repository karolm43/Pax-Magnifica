import { useRef } from "react";
import { IconFocus2, IconPointer } from "@tabler/icons-react";
import type { MapTargetKind } from "@/state/appStore";
import type { MapPickHandle } from "@/domains/strategy/mapPick";
import { findSearchHits, jumpToSearchHit } from "@/domains/search/searchHits";
import { searchKey } from "@/domains/search/searchKeys";
import styles from "./DecisionFields.module.css";

export type MapTarget = { kind: MapTargetKind; id: string };

/** Co klikać: „planet”, „system” albo „planet or system” (wybór mieszany). */
export function placeWord(targets: MapTarget[]): string {
  const kinds = new Set(targets.map((t) => t.kind));
  if (kinds.size > 1) return "planet or system";
  return kinds.has("planet") ? "planet" : "system";
}

/** Środek celu jest poza oknem albo przykryty czymś spoza planszy (dok ręki, panel HUD)? */
function isCovered(hit: HTMLElement): boolean {
  const r = hit.getBoundingClientRect();
  const x = r.left + r.width / 2;
  const y = r.top + r.height / 2;
  if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) return true;
  const top = document.elementFromPoint(x, y);
  const board = hit.closest("[id^='tile-']")?.parentElement ?? null;
  return !top || !(board?.contains(top) ?? false);
}

/**
 * Jedna linia stanu wyboru na mapie w oknie decyzji (zamiast dużego pola „kliknij na mapie”):
 * - wybór aktywny: „Click a glowing … on the map” + „Show” (przewija mapę do kolejnego celu -
 *   cel bywa pod dokiem ręki albo poza ekranem),
 * - inne okno trzyma mapę: „Pick here” przejmuje ją dla tego pola,
 * - brak celów: komunikat.
 */
export function MapPickStatus({
  targets,
  handle,
  disabled,
}: {
  targets: MapTarget[];
  handle: MapPickHandle;
  disabled: boolean;
}) {
  const next = useRef(0);
  const word = placeWord(targets);
  if (targets.length === 0) {
    return <p className={styles.mapStatus} data-state="empty">No legal target right now.</p>;
  }
  const show = () => {
    handle.claim();
    const hits = findSearchHits(
      targets.map((t) => searchKey(t.kind, t.id)),
      true,
    );
    // Najpierw cele zasłonięte (dok ręki, panele) albo poza ekranem - to ich gracz nie widzi.
    const hidden = hits.filter(isCovered);
    const pool = hidden.length > 0 ? hidden : hits;
    if (pool.length === 0) return;
    const hit = pool[next.current % pool.length];
    next.current += 1;
    if (hit) jumpToSearchHit(hit);
  };
  if (handle.registered && !handle.active) {
    return (
      <div className={styles.mapStatus} data-state="waiting">
        <IconPointer size={14} aria-hidden="true" />
        <span>Another window is using the map.</span>
        <button type="button" className={styles.mapStatusBtn} disabled={disabled} onClick={handle.claim}>
          Pick here
        </button>
      </div>
    );
  }
  return (
    <div className={styles.mapStatus} data-state="active">
      <IconPointer size={14} aria-hidden="true" />
      <span>Click a glowing {word}</span>
      <small className={styles.mapStatusCount} title={`${targets.length} targets on the map`}>
        {targets.length}
      </small>
      <button
        type="button"
        className={styles.mapStatusBtn}
        disabled={disabled}
        onClick={show}
        title="Scroll the map to the next target"
      >
        <IconFocus2 size={13} aria-hidden="true" />
        Show
      </button>
    </div>
  );
}

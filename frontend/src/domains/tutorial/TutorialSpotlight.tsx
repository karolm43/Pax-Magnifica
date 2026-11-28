import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { getPortalRoot } from "@/ds";
import { findTutorialTarget, type TutorialTargetId } from "./targets";
import styles from "./TutorialSpotlight.module.css";

/** Ring padding around the target and the gap between the ring and the callout (px). */
const RING_PAD = 6;
const GAP = 12;
/** Minimum distance from the viewport edge (px). */
const MARGIN = 12;
/** Re-measure period: the map pans and panels animate without firing resize/scroll. */
const REMEASURE_MS = 200;

export type Box = { top: number; left: number; width: number; height: number };
type Size = { width: number; height: number };
export type CalloutSide = "below" | "above" | "right" | "left" | "inside";

function sameBox(a: Box | null, b: Box | null): boolean {
  if (!a || !b) return a === b;
  return a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height;
}

/** The target's rect padded by the ring and clipped to the viewport; null when fully off-screen. */
export function ringBox(rect: Box, viewport: Size): Box | null {
  const left = Math.max(0, rect.left - RING_PAD);
  const top = Math.max(0, rect.top - RING_PAD);
  const right = Math.min(viewport.width, rect.left + rect.width + RING_PAD);
  const bottom = Math.min(viewport.height, rect.top + rect.height + RING_PAD);
  if (right <= left || bottom <= top) return null;
  return { top, left, width: right - left, height: bottom - top };
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(v, Math.max(lo, hi)));

/**
 * Where the callout goes next to the ring: below, above, right or left — the first side with
 * room for it — else inside the ring at its bottom (a target that fills the screen, e.g. the
 * map). Always clamped to the viewport.
 */
export function placeCallout(
  ring: Box,
  callout: Size,
  viewport: Size,
): { top: number; left: number; side: CalloutSide } {
  const maxLeft = viewport.width - callout.width - MARGIN;
  const maxTop = viewport.height - callout.height - MARGIN;
  const centerX = clamp(ring.left + ring.width / 2 - callout.width / 2, MARGIN, maxLeft);
  const centerY = clamp(ring.top + ring.height / 2 - callout.height / 2, MARGIN, maxTop);
  const bottom = ring.top + ring.height;
  const right = ring.left + ring.width;

  if (viewport.height - bottom - GAP >= callout.height + MARGIN) {
    return { top: bottom + GAP, left: centerX, side: "below" };
  }
  if (ring.top - GAP >= callout.height + MARGIN) {
    return { top: ring.top - GAP - callout.height, left: centerX, side: "above" };
  }
  if (viewport.width - right - GAP >= callout.width + MARGIN) {
    return { top: centerY, left: right + GAP, side: "right" };
  }
  if (ring.left - GAP >= callout.width + MARGIN) {
    return { top: centerY, left: ring.left - GAP - callout.width, side: "left" };
  }
  return {
    top: clamp(bottom - callout.height - GAP * 2, MARGIN, maxTop),
    left: centerX,
    side: "inside",
  };
}

function viewportSize(): Size {
  return { width: window.innerWidth, height: window.innerHeight };
}

function reducedMotion(): boolean {
  return typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Live rect of the element: ResizeObserver, window resize/scroll (capture: every scroller,
 * incl. the map's drag-scroll) and a light periodic re-measure for panning/animations.
 */
function useTrackedRect(el: HTMLElement | null): Box | null {
  const [rect, setRect] = useState<Box | null>(null);

  useLayoutEffect(() => {
    if (!el) {
      setRect(null);
      return;
    }
    const measure = () => {
      const r = el.getBoundingClientRect();
      const next = { top: r.top, left: r.left, width: r.width, height: r.height };
      setRect((prev) => (sameBox(prev, next) ? prev : next));
    };
    measure();
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(measure) : null;
    observer?.observe(el);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    const timer = window.setInterval(measure, REMEASURE_MS);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
      window.clearInterval(timer);
    };
  }, [el]);

  return rect;
}

/**
 * Spotlight on a tutorial target (Layer 1): a ring in the player's accent colour around the
 * region (with a dimmed backdrop in the `spotlight` variant) and a callout card placed beside
 * it. The `pulse` variant is the ring alone, pulsing — the "Show me" / milestone tip pointer.
 * The ring never takes pointer events; only the callout is interactive.
 */
export function TutorialSpotlight({
  target,
  variant = "spotlight",
  label,
  children,
}: {
  /** Target id (resolved with `findTutorialTarget`) or an element already resolved. */
  target: TutorialTargetId | HTMLElement | null;
  variant?: "spotlight" | "pulse";
  /** Accessible name of the callout dialog. */
  label?: string;
  /** Callout content (spotlight variant only). */
  children?: ReactNode;
}) {
  const el = typeof target === "string" ? findTutorialTarget(target) : target;
  const rect = useTrackedRect(el);
  const calloutRef = useRef<HTMLDivElement>(null);
  const [calloutSize, setCalloutSize] = useState<Size | null>(null);
  const viewport = viewportSize();
  const ring = rect ? ringBox(rect, viewport) : null;

  // A target below the fold (the HUD under the board) is scrolled into view once.
  useLayoutEffect(() => {
    if (!el || variant !== "spotlight") return;
    const r = el.getBoundingClientRect();
    const visible = r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < window.innerWidth;
    if (!visible && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: reducedMotion() ? "auto" : "smooth" });
    }
  }, [el, variant]);

  useLayoutEffect(() => {
    const node = calloutRef.current;
    if (!node) return;
    const measure = () => {
      const { width, height } = node.getBoundingClientRect();
      setCalloutSize((prev) =>
        prev && prev.width === width && prev.height === height ? prev : { width, height },
      );
    };
    measure();
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(measure) : null;
    observer?.observe(node);
    return () => observer?.disconnect();
  });

  const portal = getPortalRoot() ?? document.body;
  const showCallout = variant === "spotlight" && children != null;
  const place = ring && calloutSize ? placeCallout(ring, calloutSize, viewport) : null;

  return createPortal(
    <>
      {ring && (
        <div
          className={styles.ring}
          data-variant={variant}
          aria-hidden="true"
          style={{ top: ring.top, left: ring.left, width: ring.width, height: ring.height }}
        />
      )}
      {showCallout && (
        <div
          ref={calloutRef}
          role="dialog"
          aria-label={label}
          className={styles.callout}
          data-side={place?.side}
          style={
            place
              ? { top: place.top, left: place.left }
              : // Until measured (or with no target on screen): bottom-centre, out of the way.
                { bottom: MARGIN * 6, left: "50%", transform: "translateX(-50%)" }
          }
        >
          {children}
        </div>
      )}
    </>,
    portal,
  );
}

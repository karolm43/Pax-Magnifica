import { useCallback, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { IconArrowLeft, IconArrowRight, IconRoute } from "@tabler/icons-react";
import { Button, CloseButton } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { findTutorialTarget } from "./targets";
import { TutorialSpotlight } from "./TutorialSpotlight";
import { TOUR_STEPS, nextAvailableStep, resolveStep, type TargetFinder, type TourStep } from "./tourSteps";
import { useTutorialStore } from "./tutorialStore";
import styles from "./TutorialTour.module.css";

/** The offer waits for the HUD to mount (and the intro to settle) before it shows. */
const OFFER_DELAY_MS = 1500;
/** How long a "Show me" pulse ring stays on its target. */
const PULSE_MS = 2500;

const defaultFind: TargetFinder = (id) => findTutorialTarget(id);

/** "Show me" / milestone pointer: pulse on `pulseTarget`, cleared after a moment or on any click. */
function PulseRing() {
  const pulseTarget = useTutorialStore((s) => s.pulseTarget);
  const clearPulse = useTutorialStore((s) => s.clearPulse);

  useEffect(() => {
    if (!pulseTarget) return;
    const timer = window.setTimeout(clearPulse, PULSE_MS);
    // Deferred, so the click that started the pulse ("Show me") does not clear it at once.
    const listen = window.setTimeout(() => window.addEventListener("pointerdown", clearPulse, true), 0);
    return () => {
      window.clearTimeout(timer);
      window.clearTimeout(listen);
      window.removeEventListener("pointerdown", clearPulse, true);
    };
  }, [pulseTarget, clearPulse]);

  if (!pulseTarget) return null;
  return <TutorialSpotlight target={pulseTarget} variant="pulse" />;
}

function TourOffer({ gameId }: { gameId: string }) {
  const startTour = useTutorialStore((s) => s.startTour);
  const endTour = useTutorialStore((s) => s.endTour);
  const skipAll = useTutorialStore((s) => s.skipAll);

  return (
    <div className={styles.offer} role="dialog" aria-label="Screen tour">
      <IconRoute size={18} className={styles.offerIcon} aria-hidden="true" />
      <p className={styles.offerText}>Take a quick tour of the screen?</p>
      <div className={styles.offerActions}>
        <Button variant="subtle" size="xs" onClick={() => skipAll(gameId)}>
          Skip all
        </Button>
        <Button variant="default" size="xs" onClick={() => endTour(gameId)}>
          Not now
        </Button>
        <Button size="xs" onClick={startTour}>
          Start tour
        </Button>
      </div>
    </div>
  );
}

function TourCallout({
  step,
  position,
  total,
  hasBack,
  hasNext,
  onBack,
  onNext,
  onClose,
  onSkipAll,
}: {
  step: TourStep;
  position: number;
  total: number;
  hasBack: boolean;
  hasNext: boolean;
  onBack: () => void;
  onNext: () => void;
  onClose: () => void;
  onSkipAll: () => void;
}) {
  return (
    <>
      <header className={styles.head}>
        <span className={styles.counter} aria-label={`Step ${position} of ${total}`}>
          {position} / {total}
        </span>
        <CloseButton size="sm" aria-label="Close tour" onClick={onClose} />
      </header>
      <h3 className={styles.title}>{step.title}</h3>
      <p className={styles.body}>{step.body}</p>
      <footer className={styles.actions}>
        <Button variant="subtle" size="xs" onClick={onSkipAll}>
          Skip all
        </Button>
        <span className={styles.spacer} />
        <Button
          variant="default"
          size="xs"
          disabled={!hasBack}
          leftSection={<IconArrowLeft size={14} aria-hidden="true" />}
          onClick={onBack}
        >
          Back
        </Button>
        {hasNext ? (
          <Button size="xs" rightSection={<IconArrowRight size={14} aria-hidden="true" />} onClick={onNext}>
            Next
          </Button>
        ) : (
          <Button size="xs" onClick={onNext}>
            Finish
          </Button>
        )}
      </footer>
    </>
  );
}

/**
 * Guided UI Tour (Layer 2): the first-visit offer, the spotlighted steps (Back / Next, arrow
 * keys, Escape) and the "Show me" pulse ring. Steps whose regions are not on screen (another
 * phase, a mobile layout) are skipped in the direction of travel. All state in `useTutorialStore`.
 */
export function TutorialTour({
  steps = TOUR_STEPS,
  find = defaultFind,
  offerDelayMs = OFFER_DELAY_MS,
}: {
  steps?: TourStep[];
  find?: TargetFinder;
  offerDelayMs?: number;
} = {}) {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const tourStep = useTutorialStore((s) => s.tourStep);
  const tourOffered = useTutorialStore((s) => s.tourOffered);
  const offerTourIfFirstVisit = useTutorialStore((s) => s.offerTourIfFirstVisit);
  const setTourStep = useTutorialStore((s) => s.setTourStep);
  const endTour = useTutorialStore((s) => s.endTour);
  const skipAll = useTutorialStore((s) => s.skipAll);
  /** Direction of the last move, so an unmounted target is skipped the same way. */
  const dir = useRef<1 | -1>(1);

  useEffect(() => {
    if (offerDelayMs <= 0) {
      offerTourIfFirstVisit(gameId);
      return;
    }
    const timer = window.setTimeout(() => offerTourIfFirstVisit(gameId), offerDelayMs);
    return () => window.clearTimeout(timer);
  }, [gameId, offerDelayMs, offerTourIfFirstVisit]);

  const running = tourStep != null;
  const step = running ? steps[tourStep] : undefined;
  const target = step ? resolveStep(step, find) : null;

  const go = useCallback(
    (d: 1 | -1) => {
      if (tourStep == null) return;
      dir.current = d;
      const next = nextAvailableStep(steps, tourStep, d, find);
      if (next != null) setTourStep(next);
      else if (d === 1) endTour(gameId); // past the last step = Finish
    },
    [tourStep, steps, find, setTourStep, endTour, gameId],
  );

  // Auto-skip: the current step's region is gone (or the index is out of range).
  useEffect(() => {
    if (tourStep == null || target) return;
    const next =
      nextAvailableStep(steps, tourStep, dir.current, find) ??
      (dir.current === -1 ? nextAvailableStep(steps, tourStep, 1, find) : null);
    if (next != null) setTourStep(next);
    else endTour(gameId);
  }, [tourStep, target, steps, find, setTourStep, endTour, gameId]);

  useEffect(() => {
    if (!running) return;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el?.closest?.("input, textarea, select, [contenteditable='true']")) return;
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "Escape") endTour(gameId);
      else return;
      // The tour owns these keys while it runs (map shortcuts must not pan underneath).
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [running, go, endTour, gameId]);

  const available = running ? steps.filter((s) => resolveStep(s, find)) : [];
  const position = step ? available.indexOf(step) + 1 : 0;

  return (
    <>
      {running && step && target && (
        <TutorialSpotlight target={target} label={step.title}>
          <TourCallout
            step={step}
            position={position}
            total={available.length}
            hasBack={nextAvailableStep(steps, tourStep, -1, find) != null}
            hasNext={nextAvailableStep(steps, tourStep, 1, find) != null}
            onBack={() => go(-1)}
            onNext={() => go(1)}
            onClose={() => endTour(gameId)}
            onSkipAll={() => skipAll(gameId)}
          />
        </TutorialSpotlight>
      )}
      {!running && tourOffered && <TourOffer gameId={gameId} />}
      <PulseRing />
    </>
  );
}

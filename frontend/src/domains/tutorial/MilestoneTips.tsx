import { useEffect, useRef } from "react";
import { IconBulb, IconPointer } from "@tabler/icons-react";
import { MILESTONE_TIPS, milestoneActive, pendingMilestone } from "./milestones";
import { useCoachContext } from "./useCoachContext";
import { useTutorialStore, type MilestoneId } from "./tutorialStore";
import styles from "./MilestoneTips.module.css";

/**
 * First-time milestone tips (Layer 3): a small just-in-time card the first time a moment comes
 * up (first Strategy Card pick, tactical action, secondary, battle, production). Each tip is
 * shown once: "Got it" dismisses it, and so does acting on it - once its moment is over (card
 * picked, combat ended, window closed...) it is marked seen. Never shown with tips disabled
 * ("Skip all") or while the Guided UI Tour runs or is being offered.
 */
export function MilestoneTips() {
  const context = useCoachContext();
  const tipsDisabled = useTutorialStore((s) => s.tipsDisabled);
  const seenTips = useTutorialStore((s) => s.seenTips);
  const touring = useTutorialStore((s) => s.tourStep != null || s.tourOffered);
  const markTipSeen = useTutorialStore((s) => s.markTipSeen);
  const pulse = useTutorialStore((s) => s.pulse);

  const suppressed = tipsDisabled || touring || context == null;
  const current = suppressed ? null : pendingMilestone(context, seenTips);

  // The tip shown on the previous render: when its moment is over, the player acted on it.
  const shown = useRef<MilestoneId | null>(null);
  useEffect(() => {
    const previous = shown.current;
    if (previous && previous !== current && context && !milestoneActive(previous, context)) {
      markTipSeen(previous);
    }
    shown.current = current;
  });

  if (!current) return null;
  const tip = MILESTONE_TIPS[current];
  const titleId = `milestone-tip-${tip.id}`;

  return (
    <aside className={styles.tip} role="dialog" aria-modal="false" aria-labelledby={titleId}>
      <span className={styles.kicker}>
        <IconBulb size={14} aria-hidden="true" /> First time
      </span>
      <b id={titleId} className={styles.title}>
        {tip.title}
      </b>
      <ul className={styles.lines}>
        {tip.lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.button} ${styles.primary}`}
          onClick={() => markTipSeen(tip.id)}
        >
          Got it
        </button>
        <button
          type="button"
          className={styles.button}
          title="Highlight where to look on screen"
          onClick={() => pulse(tip.targetId)}
        >
          <IconPointer size={14} aria-hidden="true" /> Show me
        </button>
      </div>
    </aside>
  );
}

import { IconBook2, IconChevronDown, IconCompass, IconPointer } from "@tabler/icons-react";
import { coachHint } from "./coachHint";
import { useCoachContext } from "./useCoachContext";
import { useTutorialStore } from "./tutorialStore";
import styles from "./CoachSection.module.css";

/**
 * The tutorial's "What now?" section - part of the phase panel (GameStatePanel, top left): one
 * short hint on what to do in the current phase/step, "Show me" pulsing the screen region the
 * hint talks about, and "Learn more" opening the matching How to play chapter. It used to be a
 * separate floating window bottom-left - it overlapped the phase panel and the chat icon, so
 * (user decision: fewer windows) it lives in one panel with the phase. The header collapses the
 * section to one line (choice remembered in `tutorialStore`).
 */
export function CoachSection() {
  const context = useCoachContext();
  const coachOpen = useTutorialStore((s) => s.coachOpen);
  const setCoachOpen = useTutorialStore((s) => s.setCoachOpen);
  const openGuide = useTutorialStore((s) => s.openGuide);
  const pulse = useTutorialStore((s) => s.pulse);
  if (!context) return null;
  const hint = coachHint(context);
  const toggle = coachOpen ? "Hide hints" : "Show hints: what to do now";
  const target = hint.targetId;

  return (
    <section
      className={styles.section}
      aria-label="What now?"
      aria-live="polite"
      data-act={hint.act || undefined}
    >
      <button
        type="button"
        className={styles.head}
        aria-expanded={coachOpen}
        aria-label={toggle}
        title={toggle}
        onClick={() => setCoachOpen(!coachOpen)}
      >
        <IconCompass size={14} aria-hidden="true" className={styles.compass} />
        <span className={styles.kicker}>What now?</span>
        {!coachOpen && <span className={styles.peek}>{hint.title}</span>}
        <IconChevronDown
          size={13}
          aria-hidden="true"
          className={styles.chevron}
          data-open={coachOpen || undefined}
        />
      </button>
      {coachOpen && (
        <div className={styles.body}>
          <b className={styles.title}>{hint.title}</b>
          <ul className={styles.lines}>
            {hint.lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <div className={styles.actions}>
            <button type="button" className={styles.more} onClick={() => openGuide(hint.chapter)}>
              <IconBook2 size={14} aria-hidden="true" /> Learn more
            </button>
            {target && (
              <button
                type="button"
                className={styles.more}
                title="Highlight where to look on screen"
                onClick={() => pulse(target)}
              >
                <IconPointer size={14} aria-hidden="true" /> Show me
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

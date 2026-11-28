import { IconArrowLeft, IconArrowRight, IconBulb, IconRoute } from "@tabler/icons-react";
import { Button } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { CHAPTERS, chapterById } from "./tutorialContent";
import { useTutorialStore } from "./tutorialStore";
import classes from "./HowToPlayModal.module.css";

/**
 * Okno „How to play” — samouczek w rozdziałach (spis po lewej, treść po prawej, Previous/Next).
 * Otwierane z toolbara mapy, z menu głównego i z panelu „What now?” (od razu na właściwym
 * rozdziale). Stan w `useTutorialStore`, więc jedno okno obsługuje wszystkie wejścia.
 */
export function HowToPlayModal() {
  const chapterId = useTutorialStore((s) => s.chapter);
  const openGuide = useTutorialStore((s) => s.openGuide);
  const closeGuide = useTutorialStore((s) => s.closeGuide);
  const restartTour = useTutorialStore((s) => s.restartTour);
  const chapter = chapterById(chapterId ?? "goal");
  const index = CHAPTERS.findIndex((c) => c.id === chapter.id);
  const prev = CHAPTERS[index - 1];
  const next = CHAPTERS[index + 1];

  return (
    <AppModal
      opened={chapterId != null}
      onClose={closeGuide}
      title="How to play"
      size={860}
      padding={0}
    >
      <div className={classes.layout}>
        <nav className={classes.toc} aria-label="Chapters">
          {CHAPTERS.map((c, i) => (
            <button
              key={c.id}
              type="button"
              className={classes.tocItem}
              aria-current={c.id === chapter.id ? "page" : undefined}
              onClick={() => openGuide(c.id)}
            >
              <span className={classes.tocNum}>{i + 1}</span>
              {c.title}
            </button>
          ))}
        </nav>
        <article className={classes.body} aria-labelledby="how-to-play-chapter">
          <h2 id="how-to-play-chapter" className={classes.heading}>
            {chapter.title}
          </h2>
          <p className={classes.intro}>{chapter.intro}</p>
          <ul className={classes.points}>
            {chapter.points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
          {chapter.hint && (
            <p className={classes.hint}>
              <IconBulb size={16} aria-hidden="true" />
              <span>{chapter.hint}</span>
            </p>
          )}
        </article>
      </div>
      <footer className="overlay-modal-footer">
        <p className="overlay-modal-note">Full rules: the Rules button (in game and in the main menu).</p>
        {/* Closes this window (via the store) and replays the on-screen tour from step 1. */}
        <Button
          variant="subtle"
          size="sm"
          leftSection={<IconRoute size={14} aria-hidden="true" />}
          onClick={restartTour}
        >
          Restart tour
        </Button>
        <Button
          variant="default"
          size="sm"
          disabled={!prev}
          leftSection={<IconArrowLeft size={14} aria-hidden="true" />}
          onClick={() => prev && openGuide(prev.id)}
        >
          Previous
        </Button>
        {next ? (
          <Button
            size="sm"
            rightSection={<IconArrowRight size={14} aria-hidden="true" />}
            onClick={() => openGuide(next.id)}
          >
            Next: {next.title}
          </Button>
        ) : (
          <Button size="sm" onClick={closeGuide}>
            Start playing
          </Button>
        )}
      </footer>
    </AppModal>
  );
}

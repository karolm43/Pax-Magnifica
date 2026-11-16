import { useState, type ReactNode } from "react";
import { IconPlayerPause, IconX } from "@tabler/icons-react";
import { Tooltip } from "@/ds";
import { useHoldCandidates, type HoldStep } from "@/api/useActionCard";
import { useActivityFeed } from "@/api/useBoardEditor";
import { describeActivity } from "@/domains/game-shell/components/ActivityPanel/describeActivity";
import { useActivityContext } from "@/domains/game-shell/components/ActivityPanel/useActivityContext";
import { prettifyId } from "@/domains/game-shell/components/GameEventPanel/eventFormatting";
import { ActionCardPlayModal } from "@/domains/game-shell/components/TurnControls/ActionCardPlayModal";
import styles from "./HoldControls.module.css";
import { ToolHint } from "./ToolHint";

type Pick = { step: HoldStep; cardId: string; cardName: string };

/** Etykieta techniczna commita jako ostatnia deska ratunku („battle:assign:p2" → „Battle assign"). */
function plainLabel(label: string): string {
  return prettifyId(label.split(":").slice(0, 2).join(" "));
}

/**
 * Przycisk HOLD (RULES.md 53.7): "chciałem zagrać kartę, ale gra poszła dalej". Pokazuje kroki
 * historii, do których wolno się cofnąć (silnik wyklucza kości, dobrania, zmianę fazy i limit
 * kroków), a przy każdym - karty z ręki zagrywalne w tamtym oknie. Wybór karty otwiera zwykły
 * formularz, liczony na stanie z tamtej chwili; potwierdzenie cofa grę i zagrywa kartę.
 */
export function HoldControls({ playerId }: { playerId: string }) {
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState<Pick | null>(null);
  const { data, isLoading } = useHoldCandidates(playerId, open);
  const steps = data?.steps ?? [];
  // Cofany krok opisany tak samo jak w feedzie Activity (ten sam opis, nie surowa etykieta).
  const { data: feed } = useActivityFeed();
  const ctx = useActivityContext(feed?.players);
  const undone = (step: HoldStep): ReactNode => {
    const entry = feed?.entries.find((e) => e.seq === step.nextSeq);
    if (entry) return describeActivity(entry.activity, ctx).headline;
    return step.nextLabel ? plainLabel(step.nextLabel) : null;
  };

  return (
    <>
      <Tooltip
        position="top"
        multiline
        maw={300}
        disabled={open}
        label={
          <ToolHint title="Hold" status="Opens a list of earlier steps and the cards you can still play there.">
            Missed the moment to play a card? Hold rewinds the game to the step where the card
            was playable and plays it there. Everything after that step is undone.
          </ToolHint>
        }
      >
        <button
          type="button"
          className={styles.toolBtn}
          data-tone="hold"
          data-open={open || undefined}
          aria-expanded={open}
          aria-description="Rewind to an earlier step to play a card you missed"
          onClick={() => setOpen((v) => !v)}
        >
          <IconPlayerPause size={15} aria-hidden="true" />
          <span className={styles.toolLabel}>Hold</span>
        </button>
      </Tooltip>

      {open && (
        <aside className={styles.panel} aria-label="Hold - play a card in an earlier step">
          <header className={styles.head}>
            <b>Play a card in an earlier step</b>
            <button
              type="button"
              className={styles.close}
              aria-label="Close"
              onClick={() => setOpen(false)}
            >
              <IconX size={14} aria-hidden="true" />
            </button>
          </header>
          <p className={styles.note}>
            The game returns to the step you pick and everything after it is undone. It is not
            possible after dice were rolled, cards were drawn or revealed, or the phase changed.
          </p>
          {isLoading && <p className={styles.empty}>Looking through the history…</p>}
          {!isLoading && steps.length === 0 && (
            <p className={styles.empty}>
              {data?.limitReason
                ? `Nothing to go back to: ${data.limitReason}`
                : "None of your cards can be played in an earlier step."}
            </p>
          )}
          <ol className={styles.steps}>
            {steps.map((step) => (
              <li key={step.seq} className={styles.step}>
                <div className={styles.stepHead}>
                  <b>
                    {step.stepsBack === 0
                      ? "Right now"
                      : `${step.stepsBack} step${step.stepsBack === 1 ? "" : "s"} back`}
                  </b>
                  <small>
                    Round {step.round} · {prettifyId(step.phase)} phase
                  </small>
                  {step.stepsBack > 0 && (
                    <span>Undoes: {undone(step)}</span>
                  )}
                </div>
                <div className={styles.cards}>
                  {step.cards.map((card) => (
                    <button
                      key={card.card_id}
                      type="button"
                      className={styles.cardBtn}
                      title={card.window}
                      onClick={() =>
                        setPick({ step, cardId: card.card_id, cardName: card.name })
                      }
                    >
                      {card.name}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ol>
          {steps.length > 0 && data?.limitReason && (
            <p className={styles.note}>Further back is blocked: {data.limitReason}</p>
          )}
        </aside>
      )}

      {pick && (
        <ActionCardPlayModal
          key={`${pick.cardId}-${pick.step.seq}`}
          cardId={pick.cardId}
          cardName={pick.cardName}
          playerId={playerId}
          seq={pick.step.seq}
          rewindNote={pick.step.nextLabel ?? pick.step.label}
          onClose={() => setPick(null)}
          onPlayed={() => {
            setPick(null);
            setOpen(false);
          }}
        />
      )}
    </>
  );
}

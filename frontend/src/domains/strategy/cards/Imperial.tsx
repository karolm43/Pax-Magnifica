import { useState } from "react";
import { IconArrowLeft, IconCheck } from "@tabler/icons-react";
import { Button } from "@/ds";
import { getPublicObjective } from "@/entities/lookup/publicObjectives";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import styles from "../StrategyPrompt.module.css";
import { num, strList, type StrategyPrompt } from "../strategyPrompt";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/*
 * Imperial (RULES.md 30.10): primary - zdobądź cel publiczny (jeśli spełniasz), potem 1 VP
 * za Mecatol albo tajny cel; secondary - tajny cel. Limit 3 tajnych: nadmiar wymaga zwrotu
 * jednego NIEzdobytego celu (albo świeżo dobranego, "drawn").
 */

function ReturnPicker({
  unscored,
  value,
  onChange,
  busy,
}: {
  unscored: string[];
  value: string | null;
  onChange: (next: string) => void;
  busy: boolean;
}) {
  return (
    <Section title="You would hold more than 3 secret objectives - return one">
      <div className={styles.chips}>
        {unscored.map((id) => (
          <button
            key={id}
            type="button"
            className={styles.chip}
            data-on={value === id || undefined}
            disabled={busy}
            onClick={() => onChange(id)}
            title={getSecretObjectiveData(id)?.text}
          >
            {getSecretObjectiveData(id)?.name ?? id}
          </button>
        ))}
        <button
          type="button"
          className={styles.chip}
          data-on={value === "drawn" || undefined}
          disabled={busy}
          onClick={() => onChange("drawn")}
        >
          The card I draw now
        </button>
      </div>
    </Section>
  );
}

export function ImperialPrimary({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const o = prompt.options;
  const objectives = strList(o.objectives);
  const mecatol = o.mecatol === true;
  const overLimit = o.over_limit === true && !mecatol;
  const [objective, setObjective] = useState<string | null>(null);
  const [giveBack, setGiveBack] = useState<string | null>(null);
  const ready = !overLimit || giveBack != null;
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Score an objective"
      footer={
        <ConfirmButton
          disabled={busy || !ready}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ objective, return: giveBack })}
        >
          {objective ? "Score and continue" : "Continue without scoring"}
        </ConfirmButton>
      }
    >
      <Hint>
        You may immediately score <b>1 public objective</b> whose requirements you meet.{" "}
        {mecatol ? (
          <>
            You control Mecatol Rex, so you then <b>gain 1 victory point</b>.
          </>
        ) : (
          <>
            You do not control Mecatol Rex, so you then <b>draw 1 secret objective</b>.
          </>
        )}
      </Hint>
      <Section title="Public objectives you can score now">
        {objectives.length === 0 ? (
          <span className={styles.empty}>
            None - you meet no requirements (or do not control all of your home planets).
          </span>
        ) : (
          <div className={styles.chips}>
            <button
              type="button"
              className={styles.chip}
              data-on={objective == null || undefined}
              disabled={busy}
              onClick={() => setObjective(null)}
            >
              Score none
            </button>
            {objectives.map((id) => (
              <button
                key={id}
                type="button"
                className={styles.chip}
                data-on={objective === id || undefined}
                disabled={busy}
                onClick={() => setObjective(id)}
                title={getPublicObjective(id)?.text}
              >
                {getPublicObjective(id)?.name ?? id}
              </button>
            ))}
          </div>
        )}
      </Section>
      {overLimit ? (
        <ReturnPicker
          unscored={strList(o.unscored)}
          value={giveBack}
          onChange={setGiveBack}
          busy={busy}
        />
      ) : null}
    </PromptShell>
  );
}

/** Secondary pokazuje się tylko przy nadmiarze tajnych celów (``needs_input``). */
export function ImperialSecondary({ prompt, shell, busy, submit, back }: SecondaryViewProps) {
  const [giveBack, setGiveBack] = useState<string | null>(null);
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Secondary"
      subtitle="Draw a secret objective"
      footer={
        <>
          <Button variant="default" disabled={busy} leftSection={<IconArrowLeft size={16} />} onClick={back}>
            Back
          </Button>
          <ConfirmButton
            disabled={busy || giveBack == null}
            icon={<IconCheck size={16} />}
            onClick={() => submit({ return: giveBack })}
          >
            Follow
          </ConfirmButton>
        </>
      }
    >
      <Hint>
        Spend <b>1 token from your strategy pool</b> to draw 1 secret objective.
      </Hint>
      <ReturnPicker
        unscored={strList(prompt.options.unscored)}
        value={giveBack}
        onChange={setGiveBack}
        busy={busy}
      />
      <Hint>Deck: {num(prompt.options.secret_deck)} card(s) left.</Hint>
    </PromptShell>
  );
}

export type { StrategyPrompt };

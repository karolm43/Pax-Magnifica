import { useState } from "react";
import { IconAlertTriangle, IconArrowLeft, IconCheck } from "@tabler/icons-react";
import { Button } from "@/ds";
import { publicObjectives } from "@/entities/data/publicObjectives";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { ComponentInfoButton } from "@/domains/cards/components/ComponentInfo";
import type { ObjectivePaymentBody, StatusObjectiveOption } from "@/entities/data/types";
import { ObjectiveRow } from "@/domains/game-shell/components/StatusPhasePanel/StatusPhasePanel";
import statusStyles from "@/domains/game-shell/components/StatusPhasePanel/StatusPhasePanel.module.css";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import styles from "../StrategyPrompt.module.css";
import { num, strList, type StrategyPrompt } from "../strategyPrompt";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/*
 * Imperial (RULES.md 30.10): primary - zdobądź cel publiczny (jeśli spełniasz), potem 1 VP
 * za Mecatol albo tajny cel; secondary - tajny cel. Cele pokazuje TEN SAM wiersz z paskiem
 * postępu co panel punktowania fazy statusu. Limit 3 tajnych: nadmiar wymaga zwrotu
 * jednego NIEzdobytego celu (albo świeżo dobranego, "drawn").
 */

const objectiveInfo = new Map(publicObjectives.map((o) => [o.alias, o]));

function optionsOf(prompt: StrategyPrompt): StatusObjectiveOption[] {
  const raw = prompt.options.public_options;
  return Array.isArray(raw) ? (raw as StatusObjectiveOption[]) : [];
}

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
    <Section title="You would hold more than 3 secret objectives - return one first">
      <div className={styles.chips}>
        {unscored.map((id) => {
          const secret = getSecretObjectiveData(id);
          const name = secret?.name ?? id;
          return (
            <span key={id} className={styles.chipWithInfo}>
              <button
                type="button"
                className={styles.chip}
                data-on={value === id || undefined}
                disabled={busy}
                onClick={() => onChange(id)}
              >
                <span className={styles.chipText}>
                  <b>{name}</b>
                  {secret?.text && <small>{secret.text}</small>}
                </span>
              </button>
              <ComponentInfoButton componentRef={{ kind: "objective", id }} name={name} />
            </span>
          );
        })}
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
  const mecatol = o.mecatol === true;
  const homeOk = o.home_controlled !== false;
  const overLimit = o.over_limit === true && !mecatol;
  const [giveBack, setGiveBack] = useState<string | null>(null);
  const blocked = overLimit && giveBack == null;
  const rows = [...optionsOf(prompt)].sort((a, b) => Number(b.ready) - Number(a.ready));
  const send = (objective: string | null, payment?: ObjectivePaymentBody) =>
    submit({ objective, return: giveBack, ...(payment ? { payment } : {}) });
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Score an objective"
      footer={
        <ConfirmButton
          disabled={busy || blocked}
          icon={<IconCheck size={16} />}
          onClick={() => send(null)}
        >
          Score nothing
        </ConfirmButton>
      }
    >
      <Hint>
        You may immediately score <b>1 public objective</b> whose requirements you meet. Then{" "}
        {mecatol ? (
          <>
            you control Mecatol Rex, so you <b>gain 1 victory point</b>.
          </>
        ) : (
          <>
            you do not control Mecatol Rex, so you <b>draw 1 secret objective</b>.
          </>
        )}
      </Hint>
      {overLimit ? (
        <ReturnPicker
          unscored={strList(o.unscored)}
          value={giveBack}
          onChange={setGiveBack}
          busy={busy}
        />
      ) : null}
      <div className={statusStyles.group}>
        <h4>
          Public objectives
          <small>score up to one</small>
        </h4>
        {!homeOk && (
          <p className={statusStyles.warnLine}>
            <IconAlertTriangle size={14} aria-hidden="true" />
            You do not control every planet in your home system - public objectives are locked.
          </p>
        )}
        {rows.length === 0 && (
          <span className={statusStyles.empty}>No revealed objectives left to score.</span>
        )}
        {rows.map((option) => {
          const info = objectiveInfo.get(option.key);
          const points = info?.points ?? 1;
          return (
            <ObjectiveRow
              key={option.key}
              name={info?.name ?? option.key}
              text={info?.text}
              points={points}
              option={option}
              stage={points >= 2 ? "blue" : "orange"}
              scored={false}
              busy={busy || blocked}
              onScore={(pay) => send(option.key, pay)}
            />
          );
        })}
      </div>
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
          <Button
            variant="default"
            disabled={busy}
            leftSection={<IconArrowLeft size={16} />}
            onClick={back}
          >
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

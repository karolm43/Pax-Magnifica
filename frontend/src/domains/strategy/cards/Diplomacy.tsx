import { useState } from "react";
import { IconArrowLeft, IconCheck } from "@tabler/icons-react";
import { Button } from "@/ds";
import { getPlanetData } from "@/entities/lookup/planets";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import styles from "../StrategyPrompt.module.css";
import { num, strList } from "../strategyPrompt";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/*
 * Diplomacy (RULES.md 30.8): primary - wybierz system (nie Mecatol) z własną planetą,
 * inni kładą tam żeton, potem odnów do 2 planet; secondary - odnów do 2 planet.
 */

/** Wybór do `limit` wyczerpanych planet do odnowienia. */
function ReadyPicker({
  planets,
  limit,
  chosen,
  onToggle,
  busy,
}: {
  planets: string[];
  limit: number;
  chosen: string[];
  onToggle: (id: string) => void;
  busy: boolean;
}) {
  return (
    <Section title={`Exhausted planets to ready (up to ${limit})`}>
      {planets.length === 0 ? (
        <span className={styles.empty}>You have no exhausted planets.</span>
      ) : (
        <div className={styles.planets}>
          {planets.map((id) => {
            const on = chosen.includes(id);
            const blocked = !on && chosen.length >= limit;
            return (
              <div className={styles.planetSlot} key={id}>
                <PlanetCard
                  planetId={id}
                  isExhausted
                  picked={on}
                  onPick={busy || blocked ? undefined : () => onToggle(id)}
                />
              </div>
            );
          })}
        </div>
      )}
    </Section>
  );
}

function useToggle(): [string[], (id: string) => void] {
  const [chosen, setChosen] = useState<string[]>([]);
  return [
    chosen,
    (id) => setChosen((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id])),
  ];
}

export function DiplomacyPrimary({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const [system, setSystem] = useState<string | null>(null);
  const [planets, toggle] = useToggle();

  if (prompt.step === "ready_planets") {
    return (
      <PromptShell
        hue={shell.hue}
        initiative={shell.initiative}
        title={shell.title}
        badge="Primary"
        subtitle="Ready up to 2 planets"
        footer={
          <ConfirmButton
            disabled={busy}
            icon={<IconCheck size={16} />}
            onClick={() => submit({ planets })}
          >
            {planets.length === 0 ? "Ready nothing" : `Ready ${planets.length}`}
          </ConfirmButton>
        }
      >
        <Hint>
          Command tokens are placed. Now <b>ready up to 2</b> of your exhausted planets.
        </Hint>
        <ReadyPicker
          planets={strList(prompt.options.exhausted)}
          limit={num(prompt.options.limit) || 2}
          chosen={planets}
          onToggle={toggle}
          busy={busy}
        />
      </PromptShell>
    );
  }

  const systems = (prompt.options.systems ?? {}) as Record<string, string[]>;
  const positions = Object.keys(systems);
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Choose a system"
      footer={
        <ConfirmButton
          disabled={busy || (positions.length > 0 && system == null)}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ system })}
        >
          {positions.length === 0 ? "Continue (no valid system)" : "Place command tokens"}
        </ConfirmButton>
      }
    >
      <Hint>
        Choose a system <b>other than Mecatol Rex</b> that contains a planet you control. Each
        other player places a command token there from their reinforcements.
      </Hint>
      {positions.length === 0 ? (
        <span className={styles.empty}>
          You control no planet outside Mecatol Rex - nobody places a token.
        </span>
      ) : (
        <Section title="Systems with your planets">
          <div className={styles.chips}>
            {positions.map((pos) => (
              <button
                key={pos}
                type="button"
                className={styles.chip}
                data-on={system === pos || undefined}
                disabled={busy}
                onClick={() => setSystem(pos)}
              >
                {systems[pos].map((id) => getPlanetData(id)?.name ?? id).join(" · ")}
                <small>({pos})</small>
              </button>
            ))}
          </div>
        </Section>
      )}
    </PromptShell>
  );
}

export function DiplomacySecondary({ prompt, shell, busy, submit, back }: SecondaryViewProps) {
  const [planets, toggle] = useToggle();
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Secondary"
      subtitle="Ready up to 2 planets"
      footer={
        <>
          <Button variant="default" disabled={busy} leftSection={<IconArrowLeft size={16} />} onClick={back}>
            Back
          </Button>
          <ConfirmButton
            disabled={busy}
            icon={<IconCheck size={16} />}
            onClick={() => submit({ planets })}
          >
            {planets.length === 0 ? "Follow (ready nothing)" : `Ready ${planets.length} and follow`}
          </ConfirmButton>
        </>
      }
    >
      <Hint>
        Spend <b>1 token from your strategy pool</b> to ready up to 2 of your exhausted planets.
      </Hint>
      <ReadyPicker
        planets={strList(prompt.options.exhausted)}
        limit={num(prompt.options.limit) || 2}
        chosen={planets}
        onToggle={toggle}
        busy={busy}
      />
    </PromptShell>
  );
}

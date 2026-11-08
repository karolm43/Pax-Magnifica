import { useState } from "react";
import { IconCheck } from "@tabler/icons-react";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import styles from "../StrategyPrompt.module.css";
import { playerLabel, type PrimaryViewProps } from "./types";

/*
 * Trade (RULES.md 30.6): +3 trade goods i uzupełnienie commodities dzieją się same;
 * aktywny gracz wybiera tylko, kto robi secondary ZA DARMO (i musi).
 */
export function TradePrimary({ prompt, shell, players, owner, busy, submit }: PrimaryViewProps) {
  const [chosen, setChosen] = useState<string[]>([]);
  const others = players.filter((p) => p.discordId !== owner?.discordId);
  const toggle = (id: string) =>
    setChosen((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  void prompt;
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="+3 trade goods, replenish commodities"
      footer={
        <ConfirmButton
          disabled={busy}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ players: chosen })}
        >
          {chosen.length === 0 ? "Choose nobody" : `Confirm (${chosen.length})`}
        </ConfirmButton>
      }
    >
      <Hint>
        You gain <b>3 trade goods</b> and replenish your commodities. Now choose the players who
        will resolve the secondary <b>for free</b> - they <b>must</b> do it and spend no command
        token.
      </Hint>
      <Section title="Players resolving the secondary for free">
        <div className={styles.chips}>
          {others.map((p) => (
            <button
              key={p.discordId}
              type="button"
              className={styles.chip}
              data-on={chosen.includes(p.discordId) || undefined}
              disabled={busy}
              onClick={() => toggle(p.discordId)}
            >
              {playerLabel(p)}
            </button>
          ))}
        </div>
      </Section>
    </PromptShell>
  );
}

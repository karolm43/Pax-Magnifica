import { useState } from "react";
import { IconCheck } from "@tabler/icons-react";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import { PlayerChip } from "../PlayerChip";
import styles from "../StrategyPrompt.module.css";
import type { PrimaryViewProps } from "./types";

/*
 * Trade (RULES.md 30.6): +3 trade goods i uzupełnienie commodities dzieją się same;
 * aktywny gracz wybiera tylko, kto robi secondary ZA DARMO. Wskazani gracze rozstrzygają
 * je AUTOMATYCZNIE (bez okna i bez żetonu) - pozostali dostają zwykłe follow / don't follow.
 */
export function TradePrimary({ shell, players, owner, busy, submit }: PrimaryViewProps) {
  const [chosen, setChosen] = useState<string[]>([]);
  const others = players.filter((p) => p.discordId !== owner?.discordId);
  const toggle = (id: string) =>
    setChosen((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
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
        You gain <b>3 trade goods</b> and replenish your commodities. Choose the players who
        replenish their commodities <b>for free</b> - it happens automatically, they spend no
        command token. Everyone else may still follow by spending a strategy token.
      </Hint>
      <Section title="Replenish for free">
        <div className={styles.chips}>
          {others.map((p) => (
            <PlayerChip
              key={p.discordId}
              player={p}
              selected={chosen.includes(p.discordId)}
              disabled={busy}
              onClick={() => toggle(p.discordId)}
              badge={chosen.includes(p.discordId) ? "free" : undefined}
            />
          ))}
        </div>
      </Section>
    </PromptShell>
  );
}

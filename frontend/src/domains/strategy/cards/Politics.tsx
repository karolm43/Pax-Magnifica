import { useState } from "react";
import { IconArrowDown, IconArrowUp, IconCheck } from "@tabler/icons-react";
import { getAgenda } from "@/entities/lookup/agendas";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import styles from "../StrategyPrompt.module.css";
import { strList } from "../strategyPrompt";
import { playerLabel, type PrimaryViewProps } from "./types";

/*
 * Politics (RULES.md 30.9): primary - wskaż nowego mówcę, (dobór 2 kart akcji dzieje się
 * sam), obejrzyj 2 górne agendy i ułóż je na górze/spodzie talii. Podgląd jest PRYWATNY:
 * opcje kroku dostaje tylko właściciel karty.
 */

export function PoliticsPrimary(props: PrimaryViewProps) {
  return props.prompt.step === "agenda_order" ? (
    <AgendaOrder {...props} />
  ) : (
    <ChooseSpeaker {...props} />
  );
}

function ChooseSpeaker({ prompt, shell, players, busy, submit }: PrimaryViewProps) {
  const [chosen, setChosen] = useState<string | null>(null);
  const allowed = new Set(strList(prompt.options.players));
  const candidates = players.filter((p) => allowed.has(p.discordId));
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Choose the new speaker"
      footer={
        <ConfirmButton
          disabled={busy || chosen == null}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ player: chosen })}
        >
          Give the speaker token
        </ConfirmButton>
      }
    >
      <Hint>
        Choose any player <b>without the speaker token</b> (you may choose yourself). Then you
        draw 2 action cards and look at the top 2 agenda cards.
      </Hint>
      <Section title="New speaker">
        <div className={styles.chips}>
          {candidates.map((p) => (
            <button
              key={p.discordId}
              type="button"
              className={styles.chip}
              data-on={chosen === p.discordId || undefined}
              disabled={busy}
              onClick={() => setChosen(p.discordId)}
            >
              {playerLabel(p)}
            </button>
          ))}
        </div>
      </Section>
    </PromptShell>
  );
}

type Side = "top" | "bottom";

function AgendaOrder({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const cards = strList(prompt.options.cards);
  const [sides, setSides] = useState<Record<string, Side>>(
    Object.fromEntries(cards.map((c) => [c, "top" as Side])),
  );
  // Kolejność w obrębie strony = kolejność w tej tablicy.
  const [order, setOrder] = useState<string[]>(cards);

  const move = (id: string, dir: -1 | 1) =>
    setOrder((cur) => {
      const same = cur.filter((c) => sides[c] === sides[id]);
      const i = same.indexOf(id);
      const j = i + dir;
      if (j < 0 || j >= same.length) return cur;
      const swapWith = same[j];
      const next = [...cur];
      const a = next.indexOf(id);
      const b = next.indexOf(swapWith);
      [next[a], next[b]] = [next[b], next[a]];
      return next;
    });

  const top = order.filter((c) => sides[c] === "top");
  const bottom = order.filter((c) => sides[c] === "bottom");

  const renderCard = (id: string) => {
    const agenda = getAgenda(id);
    const sameSide = order.filter((c) => sides[c] === sides[id]);
    const idx = sameSide.indexOf(id);
    return (
      <div className={styles.row} key={id}>
        <span className={styles.rowLabel}>
          {agenda?.name ?? id}
          <small>
            {[agenda?.type, agenda?.text1].filter(Boolean).join(" - ")}
          </small>
        </span>
        <span className={styles.stepper}>
          <button
            type="button"
            className={styles.stepBtn}
            disabled={busy || idx <= 0}
            onClick={() => move(id, -1)}
            aria-label="Move earlier"
          >
            <IconArrowUp size={16} />
          </button>
          <button
            type="button"
            className={styles.stepBtn}
            disabled={busy || idx >= sameSide.length - 1}
            onClick={() => move(id, 1)}
            aria-label="Move later"
          >
            <IconArrowDown size={16} />
          </button>
          <button
            type="button"
            className={styles.chip}
            disabled={busy}
            onClick={() =>
              setSides((cur) => ({ ...cur, [id]: cur[id] === "top" ? "bottom" : "top" }))
            }
          >
            {sides[id] === "top" ? "On top" : "On bottom"}
          </button>
        </span>
      </div>
    );
  };

  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Secretly look at the agenda deck"
      footer={
        <ConfirmButton
          disabled={busy || cards.length === 0}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ top, bottom })}
        >
          Place the cards
        </ConfirmButton>
      }
    >
      <Hint>
        Only you can see these cards - <b>do not show them to the other players</b>. Put each on
        the top or the bottom of the deck; cards on the same side can be ordered.
      </Hint>
      <Section title="Top of the deck (first = drawn first)">
        {top.length ? top.map(renderCard) : <span className={styles.empty}>None</span>}
      </Section>
      <Section title="Bottom of the deck (last = very bottom)">
        {bottom.length ? bottom.map(renderCard) : <span className={styles.empty}>None</span>}
      </Section>
    </PromptShell>
  );
}

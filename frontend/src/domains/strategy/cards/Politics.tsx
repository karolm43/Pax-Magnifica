import { useState, type CSSProperties } from "react";
import { IconArrowDown, IconArrowUp, IconCheck } from "@tabler/icons-react";
import { getAgenda } from "@/entities/lookup/agendas";
import { getActionCard } from "@/entities/lookup/actionCards";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import { playerName, playerRgb } from "../PlayerChip";
import styles from "../StrategyPrompt.module.css";
import { strList, type PromptPlayer } from "../strategyPrompt";
import type { PrimaryViewProps } from "./types";

/*
 * Politics (RULES.md 30.9): primary - wskaż nowego mówcę (koło stołu: widać, gdzie siedzi
 * obecny mówca, ty i dokąd trafi żeton), od razu dobierasz 2 karty akcji, potem oglądasz
 * 2 górne agendy i układasz je na górze/spodzie talii. Podgląd i karty są PRYWATNE.
 */

export function PoliticsPrimary(props: PrimaryViewProps) {
  return props.prompt.step === "agenda_order" ? (
    <AgendaOrder {...props} />
  ) : (
    <ChooseSpeaker {...props} />
  );
}

/** Lista kart akcji (nazwa + okno zagrania + tekst) - dobrane w Politics. */
export function DrawnActionCards({ cards }: { cards: string[] }) {
  if (cards.length === 0) {
    return <span className={styles.empty}>No cards drawn (the deck is empty).</span>;
  }
  return (
    <div className={styles.cardList}>
      {cards.map((id, i) => {
        const card = getActionCard(id);
        return (
          <div className={styles.actionCard} key={`${id}-${i}`}>
            <b>{card?.name ?? id}</b>
            <small>{[card?.window, card?.text].filter(Boolean).join(" - ")}</small>
          </div>
        );
      })}
    </div>
  );
}

/** Koło stołu: gracze w kolejności zasiadania (zegarowo), mówca i wybór nowego. */
function SpeakerTable({
  players,
  seating,
  speaker,
  me,
  chosen,
  allowed,
  onChoose,
  busy,
}: {
  players: PromptPlayer[];
  seating: string[];
  speaker: string | null;
  me: string | undefined;
  chosen: string | null;
  allowed: Set<string>;
  onChoose: (id: string) => void;
  busy: boolean;
}) {
  const byColor = new Map(players.map((p) => [p.color, p]));
  const ordered = [
    ...seating.map((c) => byColor.get(c)).filter((p): p is PromptPlayer => p != null),
    ...players.filter((p) => !seating.includes(p.color)),
  ];
  // Ty na dole koła, reszta zgodnie z ruchem wskazówek zegara.
  const start = Math.max(0, ordered.findIndex((p) => p.discordId === me));
  const rotated = [...ordered.slice(start), ...ordered.slice(0, start)];
  const radius = 116;
  return (
    <div className={styles.table}>
      <div className={styles.tableFelt}>
        Speaker
        <br />
        token
      </div>
      {rotated.map((p, i) => {
        const angle = Math.PI / 2 + (2 * Math.PI * i) / rotated.length;
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        const isSpeaker = p.color === speaker;
        const isChosen = chosen === p.discordId;
        const can = allowed.has(p.discordId);
        return (
          <button
            key={p.discordId}
            type="button"
            className={styles.seat}
            style={
              {
                "--x": `${x.toFixed(1)}px`,
                "--y": `${y.toFixed(1)}px`,
                "--pc": playerRgb(p.color),
              } as CSSProperties
            }
            data-on={isChosen || undefined}
            disabled={busy || !can}
            onClick={() => onChoose(p.discordId)}
            title={can ? `Give the speaker token to ${playerName(p)}` : "Already the speaker"}
          >
            <span className={styles.seatIcon}>
              {p.faction ? <CircularFactionIcon faction={p.faction} size={38} /> : null}
              {isSpeaker && !chosen ? <span className={styles.speakerToken}>S</span> : null}
              {isChosen ? (
                <span className={styles.speakerToken} data-ghost>
                  S
                </span>
              ) : null}
            </span>
            <span className={styles.seatName}>{playerName(p)}</span>
            <span
              className={styles.seatTag}
              data-kind={isChosen ? "new" : isSpeaker ? "speaker" : undefined}
            >
              {isChosen
                ? "new speaker"
                : isSpeaker
                  ? "speaker"
                  : p.discordId === me
                    ? "you"
                    : p.color}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ChooseSpeaker({ prompt, shell, players, owner, table, busy, submit }: PrimaryViewProps) {
  const [chosen, setChosen] = useState<string | null>(null);
  const allowed = new Set(strList(prompt.options.players));
  const target = players.find((p) => p.discordId === chosen);
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
          {target ? `Give the token to ${playerName(target)}` : "Choose a player"}
        </ConfirmButton>
      }
    >
      <Hint>
        Pick a seat at the table: any player <b>without the speaker token</b> (you may choose
        yourself). Then you draw 2 action cards and look at the top 2 agenda cards.
      </Hint>
      <SpeakerTable
        players={players}
        seating={table.seating}
        speaker={table.speaker}
        me={owner?.discordId}
        chosen={chosen}
        allowed={allowed}
        onChoose={setChosen}
        busy={busy}
      />
    </PromptShell>
  );
}

type Side = "top" | "bottom";

function AgendaOrder({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const cards = strList(prompt.options.cards);
  const drawn = strList(prompt.options.drawn);
  const [sides, setSides] = useState<Record<string, Side>>(
    Object.fromEntries(cards.map((c) => [c, "top" as Side])),
  );
  // Kolejność w obrębie strony = kolejność w tej tablicy.
  const [order, setOrder] = useState<string[]>(cards);

  const move = (id: string, dir: -1 | 1) =>
    setOrder((cur) => {
      const same = cur.filter((c) => sides[c] === sides[id]);
      const j = same.indexOf(id) + dir;
      if (j < 0 || j >= same.length) return cur;
      const next = [...cur];
      const a = next.indexOf(id);
      const b = next.indexOf(same[j]);
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
          <small>{[agenda?.type, agenda?.text1].filter(Boolean).join(" - ")}</small>
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
      <Section title="You drew these action cards">
        <DrawnActionCards cards={drawn} />
      </Section>
      <Hint>
        Only you can see the agenda cards - <b>do not show them to the other players</b>. Put
        each on the top or the bottom of the deck; cards on the same side can be ordered.
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

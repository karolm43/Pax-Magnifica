import { useEffect, useMemo, useState, type ReactNode } from "react";
import { IconHourglassHigh, IconHourglassOff, IconX } from "@tabler/icons-react";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { useActionCardPlayability } from "@/api/useActionCard";
import { usePromissoryPlayability } from "@/api/useFactionComponents";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { useFactionColors } from "@/hooks/useFactionColors";
import { readyReactions, type ReadyReaction } from "@/domains/game-shell/components/BottomHandDock/reactionReady";
import { timingPhrase } from "./handReactions";
import { useRecentlyGone } from "./TimingWindowChips";
import styles from "./AbilityPrompts.module.css";

/*
 * „Window open now” (RULES.md 54.8): karta akcji albo notka z ręki gracza, którą wolno zagrać
 * TERAZ w oknie reakcji (np. „At the start of an invasion combat”). Okno mija z następnym
 * krokiem gry, więc karta wyskakuje sama - także nad oknem walki/inwazji, gdzie dok ręki jest
 * zwinięty. Przycisk otwiera ten sam formularz zagrania co upuszczenie karty z ręki.
 */

export type HandPlay = { playerId: string; tab: ReadyReaction["tab"]; id: string; name: string };

/** Jeden wpis na RODZAJ karty: kopie (Morale Boost 1-4) to jedno okno z licznikiem. */
type Row = ReadyReaction & { key: string; name: string; text: string; when: string | null; copies: number };

const rowKey = (r: Row) => r.key;

export function HandReactionRows({
  gameId,
  playerId,
  owner,
  onPlay,
}: {
  gameId: string;
  playerId: string;
  /** Znacznik gracza (``PlayerTag``), gdy przy ekranie jest kilku ludzi (tryb lokalny). */
  owner: ReactNode;
  onPlay: (play: HandPlay) => void;
}) {
  const { data: hand } = usePlayerHand(gameId, { ignoreAuthGate: true, player: playerId });
  const { data: actions } = useActionCardPlayability(playerId, (hand?.actionCards.length ?? 0) > 0);
  const { data: notes } = usePromissoryPlayability(playerId, (hand?.promissoryNotes.length ?? 0) > 0);
  const colors = useFactionColors();
  const rows = useMemo(() => {
    const byName = new Map<string, Row>();
    for (const r of readyReactions(actions, notes)) {
      const note = r.tab === "notes" ? getPromissoryNoteData(r.id, colors) : null;
      const card = r.tab === "actions" ? getActionCard(r.id) : undefined;
      const name = note?.displayName || card?.name || r.id;
      const key = `${r.tab}:${name}`;
      const seen = byName.get(key);
      if (seen) {
        seen.copies += 1;
        continue;
      }
      const text = note?.noteData.text ?? card?.text ?? "";
      const when = card?.window?.trim() || timingPhrase(text);
      byName.set(key, { ...r, key, name, text, when, copies: 1 });
    }
    return [...byName.values()];
  }, [actions, notes, colors]);

  // Okno minęło, a karta została w ręce (nie zagrana) - prywatny komunikat „Window closed”
  // (RULES.md 54.9). Zagrana karta znika z ręki i komunikatu nie dostaje.
  const gone = useRecentlyGone(rows, rowKey);

  // „Not now” wycisza kartę do końca TEGO okna: gdy przestanie być zagrywalna i wróci, znów wyskoczy.
  // Wyciszona karta nie dostaje też komunikatu o zamknięciu (gracz świadomie ją pominął).
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  useEffect(() => {
    const live = new Set([...rows, ...gone].map((r) => r.key));
    setDismissed((cur) => {
      const kept = [...cur].filter((k) => live.has(k));
      return kept.length === cur.size ? cur : new Set(kept);
    });
  }, [rows, gone]);
  const missed = gone.filter(
    (r) =>
      !dismissed.has(r.key) &&
      (r.tab === "notes" ? hand?.promissoryNotes : hand?.actionCards)?.includes(r.id),
  );

  return (
    <>
      {rows
        .filter((r) => !dismissed.has(r.key))
        .map((r) => {
          const { name, when } = r;
          // Fraza okna stoi osobno pogrubiona - nie powtarzamy jej na początku tekstu.
          const text =
            when && r.text.startsWith(`${when}:`) ? r.text.slice(when.length + 1).trim() : r.text;
          const kind = r.tab === "notes" ? "Promissory note" : "Action card";
          return (
            <section
              key={r.key}
              className={styles.card}
              data-tone="window"
              title="This window closes when the game moves on - play the card before the next step"
              aria-label={`Window open now: ${name}`}
            >
              <header className={styles.head}>
                <IconHourglassHigh size={16} aria-hidden="true" className={styles.icon} />
                <span className={styles.titleBox}>
                  <small className={styles.kind}>
                    Window open now · {kind}
                    {owner && <> · {owner}</>}
                  </small>
                  <b className={styles.title}>
                    {name}
                    {r.copies > 1 ? ` ×${r.copies}` : ""}
                  </b>
                </span>
                <button
                  type="button"
                  className={styles.iconBtn}
                  aria-label={`Not now: ${name}`}
                  onClick={() => setDismissed((cur) => new Set(cur).add(r.key))}
                >
                  <IconX size={14} aria-hidden="true" />
                </button>
              </header>
              {when && <p className={styles.when}>{when}</p>}
              <p className={styles.text}>{text}</p>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.ghost}
                  onClick={() => setDismissed((cur) => new Set(cur).add(r.key))}
                >
                  Not now
                </button>
                <button
                  type="button"
                  className={styles.primary}
                  onClick={() => onPlay({ playerId, tab: r.tab, id: r.id, name })}
                >
                  Play {name}
                </button>
              </div>
            </section>
          );
        })}
      {missed.map((r) => (
        <section
          key={`closed:${r.key}`}
          className={styles.card}
          data-tone="closed"
          aria-label={`Window closed: ${r.name}`}
        >
          <header className={styles.head}>
            <IconHourglassOff size={16} aria-hidden="true" className={styles.icon} />
            <span className={styles.titleBox}>
              <small className={styles.kind}>
                Window closed · {r.tab === "notes" ? "Promissory note" : "Action card"}
                {owner && <> · {owner}</>}
              </small>
              <b className={styles.title}>{r.name}</b>
            </span>
          </header>
          <p className={styles.text}>
            The game moved on{r.when ? ` past “${r.when}”` : ""} - this card can no longer be
            played in that window.
          </p>
        </section>
      ))}
    </>
  );
}

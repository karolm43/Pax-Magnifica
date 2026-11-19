import { useState } from "react";
import { IconPlayerSkipForward, IconX } from "@tabler/icons-react";
import { Popover, SegmentedControl, Switch } from "@/ds";
import type {
  PassDuration,
  PlayerData,
  ReactionCategory,
  ReactionPrefsData,
} from "@/entities/data/types";
import { postReactionPrefs, type ReactionPrefsChange } from "@/api/useActionCard";
import styles from "./ReactionSettings.module.css";

/*
 * Ustawienia okien reakcji gracza w JEDNYM miejscu - przycisk „Reactions” w nagłówku panelu
 * akcji (RULES.md 54.11-54.12): deklaracje pasu z góry (kategoria + czas), „only when it
 * concerns me” i wyciszone karty/oferty. Ustawienia są prywatne: okna trwają tyle samo.
 */

type Row = { category: ReactionCategory; label: string; text: string };

const ROWS: Row[] = [
  {
    category: "all",
    label: "All reactions",
    text: "The game passes for you in every reaction window, even when you hold a card you could play.",
  },
  {
    category: "strategy",
    label: "Strategic actions",
    text: "Coup d'Etat and other reactions to a Strategy Card being played.",
  },
  {
    category: "agenda",
    label: "Agendas",
    text: "No whens, no afters: riders, Veto and other reactions to a revealed agenda.",
  },
  {
    category: "combat",
    label: "Combat",
    text: "Salvage, Direct Hit and other reactions after a combat or Sustain Damage.",
  },
  {
    category: "sabotage",
    label: "Cards played by others",
    text: "Sabotage and other answers to another player's action card.",
  },
];

const OFF = "off";

function durations(category: ReactionCategory) {
  return [
    { value: OFF, label: "Off" },
    category === "agenda"
      ? { value: "agenda", label: "This agenda" }
      : { value: "turn", label: "This turn" },
    { value: "round", label: "This round" },
    { value: "always", label: "Always" },
  ];
}

const EMPTY: ReactionPrefsData = { passes: {}, onlyInvolved: false, mutedCards: [], mutedOffers: [] };

/** Krótki opis stanu na przycisku (żeby gracz nie zapomniał, że coś włączył). */
export function reactionSummary(prefs: ReactionPrefsData): string | null {
  const all = prefs.passes.all;
  if (all) return all === "always" ? "Auto-pass" : `Passing: this ${all}`;
  const count = Object.keys(prefs.passes).length;
  if (count > 0) return `Passing ${count}`;
  if (prefs.onlyInvolved) return "Only mine";
  return null;
}

export function ReactionSettings({
  player,
  quickWindows,
}: {
  player: PlayerData;
  /** „Quick windows” hosta (RULES.md 54.12) - informacja w panelu. */
  quickWindows?: boolean;
}) {
  const [opened, setOpened] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const prefs = player.reactionPrefs ?? {
    ...EMPTY,
    passes: player.autoPassReactions ? { all: "always" as PassDuration } : {},
  };
  const summary = reactionSummary(prefs);

  const change = (body: ReactionPrefsChange) => {
    setBusy(true);
    setError(null);
    postReactionPrefs(player.discordId, body)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <Popover opened={opened} onChange={setOpened} position="top-end" offset={8} zIndex={3100}>
      <Popover.Target>
        <button
          type="button"
          className={styles.trigger}
          data-no-drag
          data-on={summary ? true : undefined}
          aria-haspopup="dialog"
          aria-expanded={opened}
          aria-label={summary ? `Reaction settings: ${summary}` : "Reaction settings"}
          title="Reactions outside your turn"
          onClick={() => setOpened((o) => !o)}
        >
          <IconPlayerSkipForward size={14} stroke={2} aria-hidden />
          <span>{summary ?? "Reactions"}</span>
        </button>
      </Popover.Target>
      <Popover.Dropdown className={styles.panel}>
        <div role="dialog" aria-label="Reaction settings">
          <h4 className={styles.title}>Pass in advance</h4>
          <p className={styles.note}>
            The game already passes for you when you have nothing to play. Here you can also
            pass when you do.
          </p>
          <div className={styles.rows}>
            {ROWS.map((row) => (
              <div key={row.category} className={styles.row}>
                <div className={styles.rowText}>
                  <b>{row.label}</b>
                  <small>{row.text}</small>
                </div>
                <SegmentedControl
                  aria-label={`Pass on ${row.label}`}
                  size="xs"
                  fullWidth
                  disabled={busy}
                  data={durations(row.category)}
                  value={prefs.passes[row.category] ?? OFF}
                  onChange={(value) =>
                    change({ declare: { [row.category]: value === OFF ? null : value } })
                  }
                />
              </div>
            ))}
          </div>

          <div className={styles.switchRow}>
            <Switch
              checked={prefs.onlyInvolved}
              disabled={busy}
              onChange={(event) => change({ only_involved: event.currentTarget.checked })}
              label="Ask me only when it concerns me"
              description="Skip windows about other players: their combats, their Strategy Cards, cards played on someone else. Agendas always concern you."
            />
          </div>

          {(prefs.mutedCards.length > 0 || prefs.mutedOffers.length > 0) && (
            <>
              <h4 className={styles.title}>Never asked about</h4>
              <div className={styles.chips}>
                {prefs.mutedCards.map((name) => (
                  <button
                    key={`card:${name}`}
                    type="button"
                    className={styles.chip}
                    disabled={busy}
                    aria-label={`Ask again about ${name}`}
                    onClick={() => change({ mute_cards: { [name]: false } })}
                  >
                    <span>{name}</span>
                    <IconX size={12} aria-hidden />
                  </button>
                ))}
                {prefs.mutedOffers.map((offer) => (
                  <button
                    key={`offer:${offer.key}`}
                    type="button"
                    className={styles.chip}
                    disabled={busy}
                    aria-label={`Ask again about ${offer.name}`}
                    onClick={() => change({ mute_offers: { [offer.key]: false } })}
                  >
                    <span>{offer.name}</span>
                    <IconX size={12} aria-hidden />
                  </button>
                ))}
              </div>
            </>
          )}

          <p className={styles.note}>
            Use “Never ask” on a decision or a card prompt to add it here. Windows last the same
            time for everyone, so nobody can tell what you chose.
            {quickWindows &&
              " The host turned on Quick windows: a window ends as soon as everyone has passed."}
          </p>
          {prefs.passes.all && (
            <p className={styles.warn}>You may miss a chance to react. Turn it off any time.</p>
          )}
          {error && <p className={styles.error}>{error}</p>}
        </div>
      </Popover.Dropdown>
    </Popover>
  );
}

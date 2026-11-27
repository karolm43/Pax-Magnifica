import { useState } from "react";
import { IconPlayerSkipForward, IconX } from "@tabler/icons-react";
import { Popover, SegmentedControl, Switch } from "@/ds";
import type {
  AutoHitsPolicy,
  PassDuration,
  PlayerData,
  ReactionCategory,
  ReactionPrefsData,
} from "@/entities/data/types";
import { postReactionPrefs, type ReactionPrefsChange } from "@/api/useActionCard";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { CooperativeSettings } from "./CooperativeSettings";
import styles from "./ReactionSettings.module.css";

/*
 * Ustawienia okien reakcji gracza w JEDNYM miejscu - przycisk „Reactions” w nagłówku panelu
 * akcji (RULES.md 54.11-54.15): deklaracje pasu z góry (kategoria + czas, opcjonalnie „unless
 * something changes”), „only when it concerns me”, auto-przypisanie trafień, agenci
 * kooperacyjni i wyciszone karty/oferty. Ustawienia są prywatne: okna trwają tyle samo.
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

const HIT_POLICIES: { value: AutoHitsPolicy; label: string }[] = [
  { value: "off", label: "By hand" },
  { value: "sustain", label: "Sustain only" },
  { value: "cheap", label: "Sustain + fodder" },
];

const HIT_TEXT: Record<AutoHitsPolicy, string> = {
  off: "You always assign combat hits yourself.",
  sustain: "Hits go on Sustain Damage automatically; you are asked when a unit would be destroyed.",
  cheap: "Sustain Damage first, then fighters and infantry; you are asked before anything else dies.",
};

function categoryLabel(category: ReactionCategory): string {
  return ROWS.find((r) => r.category === category)?.label ?? category;
}

function durations(category: ReactionCategory) {
  return [
    { value: OFF, label: "Off" },
    category === "agenda"
      ? { value: "agenda", label: "This agenda" }
      : { value: "turn", label: "This turn" },
    ...(category === "combat" || category === "all"
      ? [{ value: "combat", label: "This combat" }]
      : []),
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
  inCombat = false,
  othersTurn = false,
}: {
  player: PlayerData;
  /** „Quick windows” hosta (RULES.md 54.12) - informacja w panelu. */
  quickWindows?: boolean;
  /** A combat is going on ("Watch this combat", RULES.md 54.15). */
  inCombat?: boolean;
  /** Another player's turn ("Watch this turn"). */
  othersTurn?: boolean;
}) {
  const [opened, setOpened] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // "Unless something changes" (RULES.md 54.13): applies to the declarations made next.
  const [unlessChanges, setUnlessChanges] = useState(false);
  const prefs = player.reactionPrefs ?? {
    ...EMPTY,
    passes: player.autoPassReactions ? { all: "always" as PassDuration } : {},
  };
  const summary = reactionSummary(prefs);
  const notices = prefs.notices ?? [];
  const conditional = new Set(prefs.unlessChanges ?? []);

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
          {notices.length > 0 && (
            <div className={styles.notice} role="status">
              {notices.map((n, i) => (
                <p key={`${n.category}-${i}`}>
                  Your pass on <b>{categoryLabel(n.category)}</b> was cancelled:{" "}
                  {n.actor ? <PlayerTag playerId={n.actor} size={14} /> : "someone"} {n.reason}.
                </p>
              ))}
              <button
                type="button"
                className={styles.chip}
                disabled={busy}
                onClick={() => change({ clear_notices: true })}
              >
                Got it
              </button>
            </div>
          )}
          <h4 className={styles.title}>Pass in advance</h4>
          <p className={styles.note}>
            The game already passes for you when you have nothing to play. Here you can also
            pass when you do.
          </p>
          <div className={styles.rows}>
            {ROWS.map((row) => (
              <div key={row.category} className={styles.row}>
                <div className={styles.rowText}>
                  <b>
                    {row.label}
                    {conditional.has(row.category) && (
                      <span className={styles.tag}> · unless something changes</span>
                    )}
                  </b>
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
                    change({
                      declare: { [row.category]: value === OFF ? null : value },
                      ...(unlessChanges && value !== OFF ? { unless_changes: true } : {}),
                    })
                  }
                />
              </div>
            ))}
          </div>
          <div className={styles.switchRow}>
            <Switch
              checked={unlessChanges}
              disabled={busy}
              onChange={(event) => setUnlessChanges(event.currentTarget.checked)}
              label="…unless something changes"
              description="A pass you set next is cancelled as soon as another player plays a card, uses an agent, retreats or adds hits - the game asks you again."
            />
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

          <div className={styles.row}>
            <div className={styles.rowText}>
              <b>Combat hits</b>
              <small>{HIT_TEXT[prefs.autoHits ?? "off"]}</small>
            </div>
            <SegmentedControl
              aria-label="Assign combat hits"
              size="xs"
              fullWidth
              disabled={busy}
              data={HIT_POLICIES}
              value={prefs.autoHits ?? "off"}
              onChange={(value) => change({ auto_hits: value })}
            />
          </div>

          {opened && (
            <CooperativeSettings player={player} inCombat={inCombat} othersTurn={othersTurn} />
          )}

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
              " The host turned on Quick windows: once everyone has passed, a window ends a few seconds later, at a random moment."}
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

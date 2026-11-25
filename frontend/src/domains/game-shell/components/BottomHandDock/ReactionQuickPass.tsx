import { useState } from "react";
import type { PlayerData, ReactionCategory } from "@/entities/data/types";
import { postReactionPrefs } from "@/api/useActionCard";
import styles from "./HeldPlayBanner.module.css";

/*
 * Jedno kliknięcie zamiast pytania w każdym oknie (RULES.md 54.12): „Pass this combat”,
 * „Pass <agent> this round” i „Auto-pass uninvolved”. Wszystko to prywatne preferencje gracza
 * (silnik używa ich tylko do auto-pasu), więc okno trwa tyle samo i nic nie zdradza o ręce.
 */
export function ReactionQuickPass({
  me,
  category,
  inCombat,
  onPassed,
}: {
  me: PlayerData;
  /** Kategoria bieżącego okna (np. „combat”); null = tylko „all”. */
  category: ReactionCategory | null | undefined;
  /** Trwa walka - wtedy „this combat” ma sens także dla okien spoza kategorii combat. */
  inCombat: boolean;
  /** Po zapisaniu preferencji gracz od razu pasuje w bieżącym oknie. */
  onPassed: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const prefs = me.reactionPrefs;
  const components = (prefs?.windowComponents ?? []).filter(
    (c) => !prefs?.mutedComponents?.[c.key],
  );

  const run = (change: Parameters<typeof postReactionPrefs>[1], pass: boolean) => {
    setBusy(true);
    postReactionPrefs(me.discordId, change)
      .then(() => {
        if (pass) onPassed();
      })
      .catch(() => undefined)
      .finally(() => setBusy(false));
  };

  const combatCategory: ReactionCategory | null =
    category === "combat" ? "combat" : inCombat ? "all" : null;

  return (
    <span style={{ display: "inline-flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      {combatCategory && (
        <button
          type="button"
          className={styles.wait}
          disabled={busy}
          title="Don't ask me about reactions again until this combat ends."
          onClick={() => run({ declare: { [combatCategory]: "combat" } }, true)}
        >
          Pass this combat
        </button>
      )}
      {components.map((c) => (
        <button
          key={c.key}
          type="button"
          className={styles.wait}
          disabled={busy}
          title={`Don't ask me about ${c.name} again this round.`}
          onClick={() => run({ mute_components: { [c.key]: "round" } }, true)}
        >
          Pass {c.name} this round
        </button>
      ))}
      <button
        type="button"
        className={styles.wait}
        disabled={busy}
        aria-pressed={prefs?.onlyInvolved === true}
        title="Skip windows that don't involve you (no units or planets there, not a target)."
        onClick={() => run({ only_involved: !(prefs?.onlyInvolved === true) }, false)}
      >
        Auto-pass uninvolved{prefs?.onlyInvolved ? ": on" : ""}
      </button>
    </span>
  );
}

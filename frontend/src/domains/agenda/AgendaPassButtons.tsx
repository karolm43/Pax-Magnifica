import { useState } from "react";
import { IconCheck } from "@tabler/icons-react";
import type { PlayerData, ReactionCategory } from "@/entities/data/types";
import { postReactionPrefs } from "@/api/useActionCard";
import styles from "./AgendaOverlay.module.css";

/*
 * „No whens” / „No afters” zaraz po ujawnieniu agendy (RULES.md 54.12, jak w AsyncTI4):
 * deklaracja pasu tylko na bieżącą agendę. Prywatna - okno trwa tyle samo, więc nikt nie
 * widzi, co gracz kliknął. Pełne ustawienia są w panelu „Reactions” (TurnControls).
 */

type Half = { category: Extract<ReactionCategory, "agenda_when" | "agenda_after">; label: string; title: string };

const HALVES: Half[] = [
  {
    category: "agenda_when",
    label: "No whens",
    title: "Pass on reactions played when an agenda is revealed (Veto and similar) for this agenda.",
  },
  {
    category: "agenda_after",
    label: "No afters",
    title: "Pass on reactions played after an agenda is revealed (riders and similar) for this agenda.",
  },
];

export function AgendaPassButtons({ me }: { me: PlayerData }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const passes = me.reactionPrefs?.passes ?? {};
  // Szersza deklaracja („Agendas” albo „All reactions”) obejmuje obie połowy.
  const covered = Boolean(passes.agenda || passes.all || me.autoPassReactions);

  const toggle = (category: Half["category"], on: boolean) => {
    setBusy(true);
    setError(null);
    postReactionPrefs(me.discordId, { declare: { [category]: on ? "agenda" : null } })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <div className={styles.passRow} role="group" aria-label="Reactions to this agenda">
      {HALVES.map((half) => {
        const on = covered || Boolean(passes[half.category]);
        return (
          <button
            key={half.category}
            type="button"
            className={styles.ghostBtn}
            aria-pressed={on}
            disabled={busy || covered}
            title={covered ? "You already pass on all reactions to agendas (Reactions panel)." : half.title}
            onClick={() => toggle(half.category, !on)}
          >
            {on ? <IconCheck size={15} aria-hidden="true" /> : null}
            {half.label}
          </button>
        );
      })}
      {error && <p className={styles.warn}>{error}</p>}
    </div>
  );
}

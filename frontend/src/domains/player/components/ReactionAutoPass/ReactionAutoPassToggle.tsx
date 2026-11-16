import { useState } from "react";
import { IconPlayerSkipForward } from "@tabler/icons-react";
import { Popover, Switch } from "@/ds";
import type { PlayerData } from "@/entities/data/types";
import { postAutoPass } from "@/api/useActionCard";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import styles from "./ReactionAutoPassToggle.module.css";

/**
 * „Skip all reactions” (RULES.md 54.11) — cichy przełącznik na pasku własnego gracza w player area.
 *
 * Widoczny tylko na wierszu gracza przy tym biurku (ustawienie jest prywatne). Wyłączony = blada
 * ikona; włączony = wyraźna pigułka „Auto-pass”, żeby gracz nie zapomniał, że go włączył. Opis i
 * przełącznik w dymku po kliknięciu.
 */
export function ReactionAutoPassToggle({ player }: { player: PlayerData }) {
  const desk = useDeskPlayer();
  const [opened, setOpened] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!desk || desk.discordId !== player.discordId) return null;
  const enabled = player.autoPassReactions === true;

  const change = (next: boolean) => {
    setBusy(true);
    setError(null);
    postAutoPass(player.discordId, next)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <Popover opened={opened} onChange={setOpened} position="bottom-end" offset={6} zIndex={3100}>
      <Popover.Target>
        <button
          type="button"
          className={styles.trigger}
          data-on={enabled || undefined}
          aria-haspopup="dialog"
          aria-expanded={opened}
          aria-label={enabled ? "Skip all reactions: on" : "Skip all reactions: off"}
          title={enabled ? "Skipping all reactions" : "Reaction settings"}
          onClick={() => setOpened((o) => !o)}
        >
          <IconPlayerSkipForward size={13} stroke={2} aria-hidden />
          {enabled && <span>Auto-pass</span>}
        </button>
      </Popover.Target>
      <Popover.Dropdown className={styles.panel}>
        <div role="dialog" aria-label="Skip all reactions">
          <Switch
            checked={enabled}
            disabled={busy}
            onChange={(event) => change(event.currentTarget.checked)}
            label="Skip all reactions"
            description="The game passes for you in every reaction window: Sabotage, Coup d'Etat, agenda riders and vetoes, Salvage, Direct Hit and the rest. It does so even when you hold a card you could play."
          />
          <p className={styles.warn}>
            You may miss a chance to react. Turn it off any time.
          </p>
          <p className={styles.note}>
            Without this, the game already passes for you whenever you have nothing to play.
            Windows take the same time for everyone, so nobody can tell this is on.
          </p>
          {error && <p className={styles.error}>{error}</p>}
        </div>
      </Popover.Dropdown>
    </Popover>
  );
}

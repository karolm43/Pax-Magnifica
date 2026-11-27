import { useState } from "react";
import { NumberInput, SegmentedControl } from "@/ds";
import type { PlayerData } from "@/entities/data/types";
import { useBoostActions, useBoosts, type BoostMode, type OwnedBoost } from "@/api/useBoosts";
import { LeaderChip } from "@/domains/player/components/Leader/LeaderChip";
import { PlayerChip } from "@/domains/strategy/PlayerChip";
import type { PromptPlayer } from "@/domains/strategy/strategyPrompt";
import { useGameData } from "@/state/useGameContext";
import styles from "./ReactionSettings.module.css";

/*
 * "Agents & abilities" in the Reactions panel (RULES.md 54.15): how the player's COOPERATIVE
 * effects (pull - Captain Mendosa, Trilossa Aun Mirik...) may be used by others. They never pop
 * up on other players' turns; the other player asks for them ("Boosts" in the hand dock).
 * "Watch" brings the old behaviour back for this turn / combat.
 */

const MODES: { value: BoostMode; label: string }[] = [
  { value: "ask", label: "Ask me" },
  { value: "standing", label: "Standing offer" },
  { value: "self", label: "Self-only" },
];

const MODE_TEXT: Record<BoostMode, string> = {
  ask: "Others can ask for it, optionally paying. You accept or decline each time.",
  standing: "A request that pays your price is accepted at once, free for the players you pick.",
  self: "Only for your own turn and combats - nobody can ask for it.",
};

function leaderId(source: string): string | null {
  const [category, id] = source.split(":");
  return category === "leaders" && id ? id : null;
}

function OwnedRow({
  row,
  me,
  others,
  busy,
  onChange,
}: {
  row: OwnedBoost;
  me: string;
  others: PromptPlayer[];
  busy: boolean;
  onChange: (mode: BoostMode, price: number, freeFor: string[]) => void;
}) {
  const leader = leaderId(row.source);
  const toggleAlly = (pid: string) =>
    onChange(
      row.mode,
      row.price,
      row.freeFor.includes(pid) ? row.freeFor.filter((p) => p !== pid) : [...row.freeFor, pid],
    );
  return (
    <div className={styles.coopRow}>
      <div className={styles.coopHead}>
        {leader ? (
          <LeaderChip id={leader} type="agent" exhausted={false} locked={false} active={false} playerId={me} />
        ) : null}
        <div className={styles.rowText}>
          <b>{row.name}</b>
          <small>{MODE_TEXT[row.mode]}</small>
        </div>
      </div>
      <SegmentedControl
        aria-label={`Others using ${row.name}`}
        size="xs"
        fullWidth
        disabled={busy}
        data={MODES}
        value={row.mode}
        onChange={(value) => onChange(value as BoostMode, row.price, row.freeFor)}
      />
      {row.mode === "standing" && (
        <>
          <NumberInput
            label="Price (trade goods or commodities)"
            size="xs"
            min={0}
            max={20}
            disabled={busy}
            value={row.price}
            onChange={(value) =>
              onChange("standing", typeof value === "number" ? value : 0, row.freeFor)
            }
          />
          {others.length > 0 && (
            <div className={styles.chips} role="group" aria-label={`Free ${row.name} for`}>
              {others.map((p) => (
                <PlayerChip
                  key={p.discordId}
                  player={p}
                  selected={row.freeFor.includes(p.discordId)}
                  disabled={busy}
                  badge={row.freeFor.includes(p.discordId) ? "Free" : undefined}
                  onClick={() => toggleAlly(p.discordId)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function CooperativeSettings({
  player,
  inCombat,
  othersTurn,
}: {
  player: PlayerData;
  /** A combat is going on - "Watch this combat" makes sense. */
  inCombat: boolean;
  /** It is another player's turn - "Watch this turn" makes sense. */
  othersTurn: boolean;
}) {
  const me = player.discordId ?? null;
  const { data } = useBoosts(me);
  const actions = useBoostActions();
  const gameData = useGameData();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const owned = data?.owned ?? [];
  if (!me || owned.length === 0) return null;
  const others = ((gameData?.playerData ?? []) as unknown as PromptPlayer[]).filter(
    (p) => p.discordId && p.discordId !== me,
  );

  const run = (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    fn()
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  const watchData = [
    { value: "off", label: "Off" },
    ...(othersTurn ? [{ value: "turn", label: "This turn" }] : []),
    ...(inCombat ? [{ value: "combat", label: "This combat" }] : []),
  ];

  return (
    <section className={styles.section} aria-label="Agents and abilities">
      <h4 className={styles.title}>Agents &amp; abilities</h4>
      <p className={styles.note}>
        Your agents that help another player never interrupt their turn. They see them under
        Boosts and can ask - here you choose how.
      </p>
      <div className={styles.rows}>
        {owned.map((row) => (
          <OwnedRow
            key={row.source}
            row={row}
            me={me}
            others={others}
            busy={busy}
            onChange={(mode, price, freeFor) =>
              run(() => actions.configure(me, row.source, mode, price, freeFor))
            }
          />
        ))}
      </div>
      {watchData.length > 1 && (
        <div className={styles.row}>
          <div className={styles.rowText}>
            <b>Watch</b>
            <small>Offer me my agents on my own, without being asked, until this ends.</small>
          </div>
          <SegmentedControl
            aria-label="Watch"
            size="xs"
            fullWidth
            disabled={busy}
            data={watchData}
            value={data?.watch ?? "off"}
            onChange={(value) =>
              run(() => actions.watch(me, value === "off" ? null : (value as "turn" | "combat")))
            }
          />
        </div>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </section>
  );
}

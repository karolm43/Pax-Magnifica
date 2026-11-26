import { HandCard, type CardTab } from "@/domains/game-shell/components/BottomHandDock/HandCard";
import { KnownCards } from "@/domains/game-shell/components/BottomHandDock/KnownCards";
import { usePlayerData } from "@/api/usePlayerData";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import type { PlayerData } from "@/entities/data/types";
import styles from "./PlayerTab.module.css";

/*
 * Ręka w zakładce Player: TE SAME kafelki co pasek ręki na mapie (`HandCard` - rewers, nazwa,
 * znacznik, klik = pełna karta), ale jako siatka pogrupowana po kategoriach, nie pasek.
 * Tylko podgląd - zagrywa się przeciągnięciem z paska ręki na mapie. Cudza ręka = same liczby.
 */

const GROUPS: { tab: CardTab; label: string }[] = [
  { tab: "actions", label: "Action cards" },
  { tab: "secrets", label: "Secret objectives" },
  { tab: "notes", label: "Promissory notes" },
];

export function HandPanel({ gameId, player, own }: { gameId: string; player: PlayerData; own: boolean }) {
  if (!own) {
    return (
      <section className={styles.panel} aria-label="Hand">
        <h3 className={styles.panelTitle}>Hand</h3>
        <p className={styles.hint}>
          {player.acCount} action cards · {player.soCount} secret objectives · {player.pnCount}{" "}
          promissory notes (hidden).
        </p>
      </section>
    );
  }
  return <OwnHand gameId={gameId} player={player} />;
}

/** Ręka gracza pulpitu - ten sam endpoint co pasek ręki na mapie. */
function OwnHand({ gameId, player }: { gameId: string; player: PlayerData }) {
  const { data: hand, isLoading } = usePlayerHand(gameId, {
    ignoreAuthGate: true,
    player: player.discordId ?? null,
  });
  // Knowledge from "look at..." cards: agenda deck order (RULES.md 53.5.a1), revealed secrets, M'aban.
  const { data: mabanPeek } = usePlayerData(gameId, { select: (d) => d.gameState?.peek ?? null });
  const { data: players } = usePlayerData(gameId, { select: (d) => d.playerData ?? [] });
  const frontier = player.frontierCards ?? [];
  const ids: Record<CardTab, string[]> = {
    actions: [...(hand?.actionCards ?? []), ...frontier],
    secrets: hand?.secretObjectives ?? [],
    notes: hand?.promissoryNotes ?? [],
    relics: [],
  };

  const hasKnown =
    (hand?.agendaPeek?.length ?? 0) > 0 ||
    (hand?.agendaPeekBottom?.length ?? 0) > 0 ||
    Object.keys(hand?.revealedSecrets ?? {}).length > 0 ||
    Boolean(mabanPeek);

  return (
    <>
    {hasKnown && (
      <section className={styles.panel} aria-label="What you know">
        <h3 className={styles.panelTitle}>What you know</h3>
        <KnownCards
          agendaTop={hand?.agendaPeek ?? []}
          agendaBottom={hand?.agendaPeekBottom ?? []}
          revealedSecrets={hand?.revealedSecrets ?? {}}
          maban={mabanPeek ?? null}
          players={players ?? []}
        />
      </section>
    )}
    <section className={styles.panel} aria-label="Hand cards">
      <h3 className={styles.panelTitle}>Your hand</h3>
      <p className={styles.hint}>Click a card to read it - play cards by dragging them from the hand bar on the map.</p>
      {isLoading && !hand ? <p className={styles.hint}>Loading hand…</p> : null}
      {GROUPS.map(({ tab, label }) => (
        <div key={tab} className={styles.handGroup}>
          <h4 className={styles.subTitle}>
            {label} <span>{ids[tab].length}</span>
          </h4>
          {ids[tab].length === 0 ? (
            <p className={styles.hint}>None.</p>
          ) : (
            <div className={styles.handGrid} role="list" aria-label={label}>
              {ids[tab].map((id, index) => (
                <div key={`${tab}-${id}-${index}`} role="listitem">
                  <HandCard tab={tab} id={id} frontier={tab === "actions" && frontier.includes(id)} />
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
    </>
  );
}

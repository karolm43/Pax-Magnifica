import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useActivityFeed } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { useGameData } from "@/state/useGameContext";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { useSettingsStore } from "@/state/appStore";
import { seatColorStyle } from "@/domains/game-shell/components/FactionsInGame/seatColor";
import { mainPhaseOf, phaseSweep, type Sweep } from "./keyMoments";
import styles from "./PhaseSweep.module.css";

/** Czas życia paska (ms) — zsynchronizowany z keyframes w CSS. */
const DURATION: Record<Sweep["variant"], number> = {
  round: 2100,
  strategy: 1600,
  action: 1600,
  status: 1600,
  agenda: 1600,
  turn: 2600,
};

/**
 * Kolor „mojego” miejsca: sieć — moje miejsce; lokalnie (jeden człowiek + boty, bez hot-seat)
 * — jedyny gracz-człowiek. `null`, gdy nie da się ustalić (np. sam host bez miejsca).
 */
function useMyColor(): string | null {
  const { data: feed } = useActivityFeed();
  const { data: me } = useNetworkMe();
  if (!feed || !me) return null;
  if (me.network) return me.player_id ? (feed.players[me.player_id]?.color ?? null) : null;
  const humans = Object.values(feed.players).filter((p) => !p.is_bot);
  return humans.length === 1 ? humans[0].color : null;
}

/**
 * Szybkie przejście między fazami (RULES.md 64.3) — zastępuje pełnoekranowe banery. Wąski
 * pasek nad mapą: nazwa fazy + runda (nowa runda = „ROUND N” z mocniejszym akcentem), oraz
 * „YOUR TURN”, gdy tura przechodzi do gracza tej przeglądarki. Czysta dekoracja:
 * `pointer-events: none`, `aria-hidden`; tryb `adminFastMode` go wyłącza.
 */
export function PhaseSweep() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const adminFastMode = useSettingsStore((s) => s.settings.adminFastMode);
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const round = gameData?.gameRound;
  const myColor = useMyColor();

  const phase = mainPhaseOf(gameState?.phase);
  const turnColor = gameState?.activeTurnPlayer ?? null;

  // Poprzedni widok; `null` = pierwszy render (stan przy otwarciu strony to nie przejście).
  const prev = useRef<{ phase: string; round: number | undefined; turn: string | null } | null>(
    null,
  );
  const [queue, setQueue] = useState<Sweep[]>([]);

  useEffect(() => {
    const before = prev.current;
    prev.current = { phase, round, turn: turnColor };
    if (before === null || !phase || adminFastMode) return;
    const next: Sweep[] = [];
    const sweep = phaseSweep(before, { phase, round });
    if (sweep) next.push(sweep);
    const turnArrived = turnColor !== null && turnColor !== before.turn;
    // Strategy phase (picking a card) is a turn too; agenda/status are skipped because the
    // active player falls back to the speaker between their steps (false "Your turn").
    if ((phase === "action" || phase === "strategy") && turnArrived && myColor !== null && turnColor === myColor) {
      const me = gameData?.playerData?.find((p) => p.color === myColor);
      const who = [me?.userName?.trim(), me ? getPlayerFactionDisplayName(me) : null]
        .filter((part): part is string => !!part && part.toLowerCase() !== "null")
        .join(" · ");
      next.push({
        id: `turn-${round ?? "?"}-${Date.now()}`,
        variant: "turn",
        title: "Your turn",
        subtitle: who || null,
      });
    }
    if (next.length > 0) setQueue((cur) => [...cur, ...next].slice(-3));
  }, [phase, round, turnColor, myColor, adminFastMode]);

  const current = queue[0];
  useEffect(() => {
    if (!current) return;
    const timer = window.setTimeout(() => setQueue((cur) => cur.slice(1)), DURATION[current.variant]);
    return () => window.clearTimeout(timer);
  }, [current]);

  if (!current) return null;
  const style = {
    "--sweep-ms": `${DURATION[current.variant]}ms`,
    ...(current.variant === "turn" && myColor ? seatColorStyle(myColor) : undefined),
  } as CSSProperties;
  return (
    <div className={styles.layer} aria-hidden="true">
      <div key={current.id} className={styles.band} data-variant={current.variant} style={style}>
        <span className={styles.line} />
        <div className={styles.text}>
          <span className={styles.title}>{current.title}</span>
          {current.subtitle && <span className={styles.subtitle}>{current.subtitle}</span>}
        </div>
        <span className={styles.line} data-bottom />
      </div>
    </div>
  );
}

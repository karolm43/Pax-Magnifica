import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { IconChevronDown, IconChevronUp, IconSparkles } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import type { ActiveEffectData, PlayerData } from "@/entities/data/types";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { playerRgb } from "@/domains/strategy/PlayerChip";
import styles from "./ActiveEffectsPanel.module.css";

const COLLAPSED_KEY = "activeEffects.collapsed.v1";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function writeCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
  } catch {
    /* brak localStorage - stan zwinięcia nie przetrwa przeładowania */
  }
}

function EffectRow({ effect, player }: { effect: ActiveEffectData; player: PlayerData | undefined }) {
  const [open, setOpen] = useState(false);
  return (
    <li
      className={styles.row}
      style={{ "--pc": playerRgb(player?.color) } as CSSProperties}
      data-open={open || undefined}
    >
      <button
        type="button"
        className={styles.rowBtn}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        title={effect.text || effect.name}
      >
        <span className={styles.icon} aria-hidden="true">
          {player?.faction ? (
            <CircularFactionIcon faction={player.faction} size={24} />
          ) : (
            <IconSparkles size={16} />
          )}
        </span>
        <span className={styles.body}>
          {effect.kind && <small className={styles.kind}>{effect.kind}</small>}
          <b className={styles.name}>{effect.name}</b>
          {effect.detail && <span className={styles.detail}>{effect.detail}</span>}
        </span>
        <span className={styles.until}>{effect.until}</span>
      </button>
      {open && effect.text && <p className={styles.text}>{effect.text}</p>}
    </li>
  );
}

/**
 * Efekty trwałe „położone obok planszy” (RULES.md 54): bohater Letnev do końca rundy, kość
 * agenta w tej rundzie walki, premie z kart itd. Pływająca karta po lewej stronie mapy —
 * zwijana do małej plakietki, widoczna tylko, gdy coś działa. Klik w wiersz pokazuje tekst karty.
 */
export function ActiveEffectsPanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const effects = gameState?.activeEffects ?? [];
  if (effects.length === 0) return null;

  const playerOf = (owner: string | null) =>
    owner ? gameData?.playerData.find((p) => p.faction === owner) : undefined;
  const toggle = () => {
    setCollapsed((c) => {
      writeCollapsed(!c);
      return !c;
    });
  };

  return (
    <aside className={styles.panel} aria-label="Active effects" data-collapsed={collapsed || undefined}>
      <button type="button" className={styles.head} onClick={toggle} aria-expanded={!collapsed}>
        <IconSparkles size={15} aria-hidden="true" />
        <span>Active effects</span>
        <b className={styles.count}>{effects.length}</b>
        {collapsed ? (
          <IconChevronDown size={14} aria-hidden="true" />
        ) : (
          <IconChevronUp size={14} aria-hidden="true" />
        )}
      </button>
      {!collapsed && (
        <ul className={styles.list}>
          {effects.map((effect) => (
            <EffectRow key={effect.id} effect={effect} player={playerOf(effect.owner)} />
          ))}
        </ul>
      )}
    </aside>
  );
}

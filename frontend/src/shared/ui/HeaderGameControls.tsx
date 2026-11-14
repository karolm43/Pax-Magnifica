import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Group, Popover, Switch } from "@/ds";
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconArrowsExchange,
  IconBolt,
  IconBook2,
  IconUserEdit,
} from "@tabler/icons-react";
import { useGameState } from "@/api/useGameState";
import { DEFAULT_GAME_ID } from "@/config";
import { useAppStore } from "@/state/appStore";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { PlayerEditorModal } from "@/domains/player/components/PlayerEditorModal";
import { BugReportButton } from "@/domains/bug-report/BugReportButton";
import hud from "./hudChrome.module.css";
import styles from "./HeaderGameControls.module.css";

/**
 * Nagłówek gry: Zasady, zgłoszenie błędu i — tylko dla hosta — menu God-Mode.
 *
 * God-Mode (RULES.md 44.1a, `HostOnly`) zbiera narzędzia operatora: Undo/Redo historii,
 * swobodny ruch jednostek, edytor graczy i wyłączenie limitu ręki kart akcji (RULES.md 53.8).
 * Gracze cofają własny ruch przyciskiem „Undo last move" w kroku ruchu (`/tactical/undo-move`).
 * Stan przychodzi przez WebSocket, więc ręczne odświeżanie nie jest potrzebne.
 */
export function HeaderGameControls() {
  const navigate = useNavigate();
  const { data: me } = useNetworkMe();
  const isHost = !me?.network || me.host;

  return (
    <Group gap={6} wrap="nowrap" visibleFrom="sm">
      {isHost && <GodModeMenu />}
      {/* Przeglądarka Zasad TI4; `from=game` daje w niej powrót „Wróć do gry". */}
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconBook2 size={14} />}
        onClick={() => navigate("/rules?from=game")}
        title="Open the Rules browser"
      >
        <span className={hud.hudLabel}>Rules</span>
      </Button>
      {/* Zgłoszenie błędu: zrzut widoku + opis → bug_reports/ na dysku hosta. */}
      <BugReportButton />
    </Group>
  );
}

function GodModeMenu() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const { undo, redo, setActionCardLimitDisabled } = useBoardEditor();
  const moveMode = useAppStore((s) => s.moveMode);
  const toggleMoveMode = useAppStore((s) => s.toggleMoveMode);
  const moveFrom = useAppStore((s) => s.moveFrom);
  const [opened, setOpened] = useState(false);
  const [busy, setBusy] = useState(false);
  const [playerEditorOpen, setPlayerEditorOpen] = useState(false);
  const limitDisabled = gameState?.actionCardLimitDisabled === true;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PlayerEditorModal
        opened={playerEditorOpen}
        onClose={() => setPlayerEditorOpen(false)}
      />
      <Popover
        opened={opened}
        onChange={setOpened}
        position="bottom-end"
        offset={6}
        zIndex="var(--z-header-menu)"
      >
        <Popover.Target>
          <Button
            variant={moveMode ? "filled" : "default"}
            size="xs"
            className={hud.hudButton}
            leftSection={<IconBolt size={14} />}
            aria-haspopup="menu"
            aria-expanded={opened}
            onClick={() => setOpened((o) => !o)}
            title="God-Mode tools (host only)"
          >
            <span className={moveMode ? undefined : hud.hudLabel}>
              {moveMode ? (moveFrom ? "Pick destination…" : "Pick source…") : "God-Mode"}
            </span>
          </Button>
        </Popover.Target>
        <Popover.Dropdown className={styles.menu} p={6}>
          <div role="menu" aria-label="God-Mode">
            <span className={styles.heading}>God-Mode · host only</span>
            <div className={styles.row}>
              <button
                type="button"
                role="menuitem"
                className={styles.item}
                disabled={busy}
                onClick={() => void run(undo)}
                title="Revert the most recent change in the game history"
              >
                <IconArrowBackUp size={14} aria-hidden="true" /> Undo
              </button>
              <button
                type="button"
                role="menuitem"
                className={styles.item}
                disabled={busy}
                onClick={() => void run(redo)}
                title="Re-apply the change that was undone"
              >
                <IconArrowForwardUp size={14} aria-hidden="true" /> Redo
              </button>
            </div>
            <button
              type="button"
              role="menuitem"
              className={styles.item}
              data-active={moveMode || undefined}
              onClick={() => {
                toggleMoveMode();
                setOpened(false);
              }}
              title="Move units freely: click the source system, then the destination"
            >
              <IconArrowsExchange size={14} aria-hidden="true" />
              {moveMode ? "Stop moving units" : "Move units (no rules)"}
            </button>
            <button
              type="button"
              role="menuitem"
              className={styles.item}
              onClick={() => {
                setPlayerEditorOpen(true);
                setOpened(false);
              }}
              title="Edit player data"
            >
              <IconUserEdit size={14} aria-hidden="true" /> Edit players
            </button>
            <div className={styles.switchRow}>
              <Switch
                size="sm"
                label="No action card hand limit"
                checked={limitDisabled}
                disabled={busy}
                onChange={(event) => {
                  const checked = event.currentTarget.checked;
                  void run(() => setActionCardLimitDisabled(checked));
                }}
              />
            </div>
          </div>
        </Popover.Dropdown>
      </Popover>
    </>
  );
}

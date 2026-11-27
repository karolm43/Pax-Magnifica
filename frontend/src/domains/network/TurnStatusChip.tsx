/*
 * Status tury w nagłówku gry sieciowej (RULES.md 44.5): „Your move - <co>" albo
 * „Waiting for - <gracze>: <co>", z listy `waitReasons` w web-data (`waitReasons.ts`).
 * Gracze to wspólne znaczniki `PlayerTag` (logo frakcji w kolorze gracza).
 *
 * Wcześniej był to pływający pasek `position: fixed` na środku nagłówka — przy każdej
 * szerokości nachodził na plakietkę „You play" (WhoAmIBadge). Teraz to element nagłówka,
 * tuż za „You play": przycina się wielokropkiem, pełny tekst jest w podpowiedzi.
 * Mój ruch = bursztynowy obrys + pulsująca kropka; zmiana stanu = jednorazowy błysk.
 */
import { Fragment } from "react";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { usePlayerData } from "@/api/usePlayerData";
import { DEFAULT_GAME_ID } from "@/config";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { useGameData } from "@/state/useGameContext";
import { useNetworkMe } from "./useNetworkMe";
import { waitStatus, waitText } from "./waitReasons";
import styles from "./TurnStatusChip.module.css";

export function TurnStatusChip() {
  const me = useNetworkMe();
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const active = me.data?.network === true && me.data.authenticated === true;
  const { data: reasons } = usePlayerData(gameId, {
    select: (doc) => doc.waitReasons ?? [],
  });
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  if (!active) return null;

  const myId = me.data?.player_id ?? null;
  // Host bez miejsca = tryb testowy: steruje każdym graczem (WhoAmIBadge).
  const controlAll = me.data?.host === true && !myId;
  // Własny pas w oknie reakcji (cudzych pasów projekcja nie wysyła).
  const passed = [gameState?.reactionPause, gameState?.heldPlay].some(
    (w) => myId !== null && w?.passed.includes(myId),
  );
  const status = waitStatus(reasons ?? [], myId, { controlAll, passed });
  // Pełne nazwy frakcji (jak w całym UI), nie nazwy miejsc „Player p4".
  const nameOf = (id: string) => {
    const player = gameData?.playerData?.find((p) => p.discordId === id);
    return player ? getPlayerFactionDisplayName(player) : id;
  };
  const text = waitText(status, nameOf, controlAll);
  if (!text) return null;
  const ownOnly = status.mine && !controlAll;
  return (
    <span
      // `key` = tekst: każda zmiana stanu odtwarza krótkie wejście (bez pętli).
      key={text}
      role="status"
      aria-live="polite"
      className={styles.chip}
      data-mine={status.mine || undefined}
      title={text}
    >
      <span className={styles.dot} aria-hidden="true" />
      <span className={styles.text}>
        {status.mine ? "Your move" : "Waiting for"}
        {" - "}
        {status.groups.map((group, index) => (
          <Fragment key={group.summary}>
            {index > 0 && (ownOnly ? ", " : "; ")}
            {!ownOnly && (
              <>
                {group.playerIds.map((id) => (
                  <Fragment key={id}>
                    <PlayerTag playerId={id} size={14} known={{ name: nameOf(id) }} />{" "}
                  </Fragment>
                ))}
              </>
            )}
            {group.summary}
          </Fragment>
        ))}
      </span>
    </span>
  );
}

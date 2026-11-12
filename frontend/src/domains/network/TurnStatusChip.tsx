/*
 * Status tury w nagłówku gry sieciowej (RULES.md 44.5): „Your move — <co>" albo
 * „Waiting for X (<co>)", z listy `awaiting` w web-data (backend: `core/actor.awaiting`).
 *
 * Wcześniej był to pływający pasek `position: fixed` na środku nagłówka — przy każdej
 * szerokości nachodził na plakietkę „You play" (WhoAmIBadge). Teraz to element nagłówka,
 * tuż za „You play": przycina się wielokropkiem, pełny tekst jest w podpowiedzi.
 * Mój ruch = bursztynowy obrys + pulsująca kropka; zmiana stanu = jednorazowy błysk.
 */
import { useParams } from "react-router-dom";
import { usePlayerData } from "@/api/usePlayerData";
import { DEFAULT_GAME_ID } from "@/config";
import { describeAwaiting, type Awaiting } from "./NetworkPanel";
import { useNetworkMe } from "./useNetworkMe";
import styles from "./TurnStatusChip.module.css";

export function TurnStatusChip() {
  const me = useNetworkMe();
  const params = useParams<{ mapid: string }>();
  const active = me.data?.network === true && me.data.authenticated === true;
  const { data: awaiting } = usePlayerData(params.mapid ?? DEFAULT_GAME_ID, {
    select: (doc) => (doc as { awaiting?: Awaiting[] }).awaiting ?? [],
  });
  if (!active) return null;
  const { mine, text } = describeAwaiting(awaiting ?? [], me.data?.player_id ?? null);
  if (!text) return null;
  return (
    <span
      // `key` = tekst: każda zmiana stanu odtwarza krótkie wejście (bez pętli).
      key={text}
      role="status"
      aria-live="polite"
      className={styles.chip}
      data-mine={mine || undefined}
      title={text}
    >
      <span className={styles.dot} aria-hidden="true" />
      <span className={styles.text}>{text}</span>
    </span>
  );
}

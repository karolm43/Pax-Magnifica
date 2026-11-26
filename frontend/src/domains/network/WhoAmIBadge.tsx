/*
 * „Kim gram" — plakietka w nagłówku gry (lewy górny róg, obok paska gry).
 *
 * - Network game: my seat from the token (`useDeskPlayer` = always my desk), shown as a
 *   faction banner: emblem, full faction name in the faction-scene font, player colour band.
 * - Host ma tu przełącznik TRYBU TESTOWEGO: „gram za wszystkich" (host-operator bez miejsca:
 *   biurko = gracz z turą, każda akcja dozwolona, widać wszystko) ⇄ powrót na swoje miejsce.
 *   Pod spodem `POST /network/host-seat` (RULES.md 44.2a).
 * - Tryb lokalny (jedno okno): gracz, którego biurko teraz obsługujesz (gracz z turą).
 */
import { useState, type CSSProperties } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FactionIcon } from "@/shared/ui/FactionIcon";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { getPlayerDisplayName } from "@/domains/game-shell/components/gameStatePlayers";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { NETWORK_ME_KEY, useNetworkMe } from "./useNetworkMe";
import styles from "./WhoAmIBadge.module.css";

type SeatsInfo = { host_seat: string | null; host_home: string | null };

function useHostSeats(enabled: boolean) {
  return useQuery({
    queryKey: ["network", "seats"],
    queryFn: async (): Promise<SeatsInfo> => {
      const res = await fetch("/bot/network/seats");
      if (!res.ok) throw new Error(`seats: ${res.status}`);
      return (await res.json()) as SeatsInfo;
    },
    enabled,
  });
}

export function WhoAmIBadge() {
  const { data: me } = useNetworkMe();
  const desk = useDeskPlayer();
  const network = me?.network === true;
  const host = network && me?.host === true;
  const { data: seats } = useHostSeats(host);
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);

  const testMode = host && !me?.player_id;
  const homeSeat = seats?.host_home ?? null;

  const switchMode = async () => {
    setBusy(true);
    try {
      await fetch("/bot/network/host-seat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: testMode ? homeSeat : null }),
      });
      await queryClient.invalidateQueries({ queryKey: NETWORK_ME_KEY });
      await queryClient.invalidateQueries();
    } finally {
      setBusy(false);
    }
  };

  const toggle = host && (testMode ? homeSeat !== null : true) && (
    <button
      type="button"
      style={toggleStyle(testMode)}
      disabled={busy}
      onClick={() => void switchMode()}
      title={
        testMode
          ? "Go back to your own seat - you see only your cards"
          : "Test mode: control whoever has the turn and see everything (host only)"
      }
    >
      {testMode ? "Back to my seat" : "Test: play for everyone"}
    </button>
  );

  if (!desk) {
    return toggle ? <span className={styles.bare}>{toggle}</span> : null;
  }
  const factionName = getPlayerFactionDisplayName(desk);
  const playerName = desk.playerName || desk.userName || getPlayerDisplayName(desk, "");
  const rgb = desk.color ? resolvePrimaryRgb(desk.color) : undefined;
  const bannerStyle = rgb
    ? ({ "--faction-rgb": `${rgb.red} ${rgb.green} ${rgb.blue}` } as CSSProperties)
    : undefined;
  const role = testMode ? "Test mode · controlling" : network ? null : "Local · controlling";
  return (
    <span
      className={styles.banner}
      style={bannerStyle}
      data-test-mode={testMode || undefined}
      title={
        testMode
          ? "Test mode: you act for whoever has the turn"
          : network
            ? "Your seat in this network game"
            : "Local game: you control whoever has the turn"
      }
    >
      <span className={styles.emblem}>
        <FactionIcon faction={desk.faction} w={34} h={34} alt="" />
      </span>
      <span className={styles.text}>
        <span className={styles.faction}>{factionName}</span>
        <span className={styles.sub}>
          {role && <span className={styles.role}>{role}</span>}
          {playerName && playerName !== factionName && <span>{playerName}</span>}
        </span>
      </span>
      {toggle}
    </span>
  );
}

function toggleStyle(active: boolean): CSSProperties {
  return {
    marginLeft: 6,
    padding: "1px 8px",
    borderRadius: 999,
    fontSize: 12,
    cursor: "pointer",
    color: "inherit",
    border: "1px solid var(--ds-accent)",
    background: active ? "var(--ds-accent)" : "transparent",
  };
}

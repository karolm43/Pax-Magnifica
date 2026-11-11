/*
 * „Kim gram" — plakietka w nagłówku gry (lewy górny róg, obok paska gry).
 *
 * - Gra sieciowa: moje miejsce z tokenu (`useDeskPlayer` = zawsze moje biurko) — ikona
 *   frakcji, kolor, nazwa.
 * - Host ma tu przełącznik TRYBU TESTOWEGO: „gram za wszystkich" (host-operator bez miejsca:
 *   biurko = gracz z turą, każda akcja dozwolona, widać wszystko) ⇄ powrót na swoje miejsce.
 *   Pod spodem `POST /network/host-seat` (RULES.md 44.2a).
 * - Tryb lokalny (jedno okno): gracz, którego biurko teraz obsługujesz (gracz z turą).
 */
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FactionIcon } from "@/shared/ui/FactionIcon";
import { PlayerColor } from "@/shared/ui/PlayerColor/PlayerColor";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { getPlayerDisplayName } from "@/domains/game-shell/components/gameStatePlayers";
import { NETWORK_ME_KEY, useNetworkMe } from "./useNetworkMe";

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
    return toggle ? <span style={badgeStyle}>{toggle}</span> : null;
  }
  const name = getPlayerDisplayName(desk, desk.faction);
  const label = testMode ? "Test mode - controlling" : network ? "You play" : "Controlling";
  return (
    <span
      style={badgeStyle}
      title={
        testMode
          ? "Test mode: you act for whoever has the turn"
          : network
            ? "Your seat in this network game"
            : "Local game: you control whoever has the turn"
      }
    >
      <span style={{ opacity: 0.7 }}>{label}:</span>
      <FactionIcon faction={desk.faction} w={20} h={20} alt="" />
      <b>{name}</b>
      {desk.color && <PlayerColor color={desk.color} size="sm" />}
      {toggle}
    </span>
  );
}

const badgeStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "2px 10px",
  borderRadius: 999,
  border: "1px solid var(--ds-edge-accent, rgba(255,255,255,0.2))",
  fontSize: 13,
  whiteSpace: "nowrap",
  flexShrink: 0,
};

function toggleStyle(active: boolean): React.CSSProperties {
  return {
    marginLeft: 4,
    padding: "1px 8px",
    borderRadius: 999,
    fontSize: 12,
    cursor: "pointer",
    color: "inherit",
    border: "1px solid var(--ds-accent)",
    background: active ? "var(--ds-accent)" : "transparent",
  };
}

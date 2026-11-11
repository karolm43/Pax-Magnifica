/*
 * „Kim gram" — plakietka w nagłówku gry (lewy górny róg, obok paska gry).
 *
 * - Gra sieciowa: moje miejsce z tokenu (`useDeskPlayer` = zawsze moje biurko) — ikona
 *   frakcji, kolor, nazwa; host bez miejsca: „Host (operator)".
 * - Tryb lokalny (jedno okno): gracz, którego biurko teraz obsługujesz (gracz z turą).
 */
import { FactionIcon } from "@/shared/ui/FactionIcon";
import { PlayerColor } from "@/shared/ui/PlayerColor/PlayerColor";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { getPlayerDisplayName } from "@/domains/game-shell/components/gameStatePlayers";
import { useNetworkMe } from "./useNetworkMe";

export function WhoAmIBadge() {
  const { data: me } = useNetworkMe();
  const desk = useDeskPlayer();
  const network = me?.network === true;

  if (network && me?.host && !me.player_id) {
    return <span style={badgeStyle}>Host (operator) - sees everything</span>;
  }
  if (!desk) return null;
  const name = getPlayerDisplayName(desk, desk.faction);
  const label = network ? "You play" : "Controlling";
  return (
    <span
      style={badgeStyle}
      title={
        network
          ? "Your seat in this network game"
          : "Local game: you control whoever has the turn"
      }
    >
      <span style={{ opacity: 0.7 }}>{label}:</span>
      <FactionIcon faction={desk.faction} w={20} h={20} alt="" />
      <b>{name}</b>
      {desk.color && <PlayerColor color={desk.color} size="sm" />}
      {network && me?.host && <span style={{ opacity: 0.7 }}>(host)</span>}
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

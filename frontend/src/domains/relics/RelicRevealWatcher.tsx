import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import { getPlanetData } from "@/entities/lookup/planets";
import { getExploration } from "@/entities/lookup/explorations";
import type { RelicReveal } from "@/entities/data/types";
import { RelicRevealScene } from "./RelicRevealScene";

/** Scena znika sama po tym czasie, gdy nikt nie kliknie OK. */
const AUTO_CLOSE_MS = 16000;

/**
 * Odsłonięcie reliktu u WSZYSTKICH graczy (RULES.md 59.8): silnik zapisuje każde dobranie
 * z talii reliktów w ``gameState.relicReveal`` (``core.relics.record_reveal``), a ten
 * komponent odtwarza scenę (fragmenty / The Fracture / eksploracja). Odsłonięcie, które już
 * było w stanie przy otwarciu strony, nie jest odtwarzane. Montowany raz na stronie gry.
 */
export function RelicRevealWatcher() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const look = usePlayerLook();
  const reveal = gameState?.relicReveal ?? null;
  const seq = reveal?.seq ?? 0;
  const seen = useRef<number | undefined>(undefined);
  const [shown, setShown] = useState<RelicReveal | null>(null);

  useEffect(() => {
    if (gameState === undefined) return;
    if (seen.current === undefined) {
      seen.current = seq; // pierwszy odczyt: stare odsłonięcie nie jest nowością
      return;
    }
    if (!reveal || seq <= seen.current) {
      // Licznik spadł (nowa gra, Undo): nowy punkt odniesienia.
      seen.current = seq;
      return;
    }
    seen.current = seq;
    setShown(reveal);
  }, [gameState, reveal, seq]);

  useEffect(() => {
    if (!shown) return;
    const timer = window.setTimeout(
      () => setShown((s) => (s?.seq === shown.seq ? null : s)),
      AUTO_CLOSE_MS,
    );
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShown(null);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, [shown]);

  if (!shown) return null;
  const faction =
    gameData?.playerData?.find((p) => p.discordId === shown.playerId)?.faction ??
    shown.playerId;
  const who = look(faction);
  return createPortal(
    <RelicRevealScene
      key={shown.seq}
      reveal={shown}
      who={who.name}
      rgb={who.rgb}
      names={{
        planet: shown.planet ? getPlanetData(shown.planet)?.name : undefined,
        card: shown.card ? getExploration(shown.card)?.name : undefined,
      }}
      onClose={() => setShown(null)}
    />,
    document.body,
  );
}

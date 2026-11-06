import type { GamePhase, GameState, PlayerData } from "@/entities/data/types";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";

/**
 * Model komunikatu prowadzącego gracza przez fazę (standaryzowany „wording stołu").
 *
 * ``tone`` steruje kolorem akcentu paska (spójnie z sygnałami fazy). ``phase`` niesie
 * główną fazę, by pasek mógł pokolorować akcent zgodnie z tonem fazy. ``title`` to
 * krótki nagłówek (co się dzieje), ``body`` — jedno zdanie instrukcji dla operatora.
 */
export type PhaseNotice = {
  tone: "strategy" | "action" | "status" | "agenda" | "neutral";
  title: string;
  body: string;
};

/** Główna faza (bez podfazy) z ``GamePhase`` ("status.scoring" → "status"). */
function mainPhase(phase: GamePhase): string {
  return phase.split(".")[0];
}

/** Gracz dopasowany po KOLORZE (kontrakt web-data adresuje graczy kolorem). */
function playerByColor(
  players: readonly PlayerData[],
  color: string | null | undefined,
): PlayerData | undefined {
  if (!color) return undefined;
  return players.find((p) => p.color === color);
}

/** Czytelna nazwa gracza (frakcja) albo fallback na kolor/„—". */
function nameOf(
  players: readonly PlayerData[],
  color: string | null | undefined,
): string {
  const player = playerByColor(players, color);
  if (player) return getPlayerFactionDisplayName(player);
  return color ?? "—";
}

/** Czy gracz jest „posadzony" (ma frakcję, nie jest talią/neutralny). */
function seated(players: readonly PlayerData[]): PlayerData[] {
  return players.filter((p) => p.faction && p.faction !== "neutral");
}

/**
 * Buduje kontekstowy komunikat fazy z bieżącego stanu gry. Zwraca ``null``, gdy nie
 * ma nic sensownego do pokazania (np. setup, koniec gry) — pasek się wtedy nie renderuje.
 *
 * Wording celowo prowadzi operatora: mówi, czyja kolej i co odblokowuje przejście
 * fazy (DECYZJA PROJEKTOWA 2026-11: „Next phase" dopiero po komplecie pasów/kroków).
 */
export function buildPhaseNotice(
  gameState: GameState | undefined,
  players: readonly PlayerData[],
): PhaseNotice | null {
  if (!gameState) return null;
  const phase = mainPhase(gameState.phase);
  const seatedPlayers = seated(players);
  const speakerName = nameOf(players, gameState.speaker);
  const activeName = nameOf(players, gameState.activePlayer);
  const canAdvance = gameState.canAdvancePhase ?? true;
  const allDone = gameState.allPassed ?? false;

  if (phase === "strategy") {
    const pickCount = gameState.strategyPickCount ?? null;
    // Ilu graczy skompletowało wybór (ma >= pickCount kart). Picker = aktywny.
    const everyonePicked = canAdvance;
    if (everyonePicked) {
      return {
        tone: "strategy",
        title: "Strategy phase — selection complete",
        body: `All players have chosen their Strategy Cards. ${speakerName} may advance to the Action Phase.`,
      };
    }
    const pickText =
      pickCount && pickCount > 1 ? `${pickCount} Strategy Cards` : "a Strategy Card";
    return {
      tone: "strategy",
      title: "Strategy phase — choosing cards",
      body: `${activeName} is picking. Every player must choose ${pickText} before the phase can end.`,
    };
  }

  if (phase === "action") {
    if (allDone) {
      return {
        tone: "action",
        title: "Action phase — everyone has passed",
        body: `All players have passed. ${speakerName} may end the Action Phase.`,
      };
    }
    const passedCount = seatedPlayers.filter((p) => p.passed).length;
    const total = seatedPlayers.length;
    const passTail =
      passedCount > 0 ? ` (${passedCount}/${total} passed)` : "";
    return {
      tone: "action",
      title: "Action phase",
      body: `${activeName} is active. Take an action, then End turn — or Pass, then End turn${passTail}.`,
    };
  }

  if (phase === "status") {
    if (allDone) {
      return {
        tone: "status",
        title: "Status phase — all steps done",
        body: `Every player has taken their Status step. ${speakerName} may advance to the Agenda Phase.`,
      };
    }
    return {
      tone: "status",
      title: "Status phase",
      body: `${activeName}'s step. Each player resolves their Status step in initiative order, then Next player.`,
    };
  }

  if (phase === "agenda") {
    return {
      tone: "agenda",
      title: "Agenda phase",
      body: `${activeName} may react or vote. Pass to decline, or Next player to pass the floor. ${speakerName} ends the phase.`,
    };
  }

  return null;
}

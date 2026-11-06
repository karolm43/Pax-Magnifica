import type { GamePhase, GameState, PlayerData } from "@/entities/data/types";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";

/**
 * Model komunikatu pokazywanego w panelu (osobny box u góry ekranu). ``tone`` steruje
 * kolorem akcentu (spójnie z sygnałami fazy). ``title`` — krótki nagłówek, ``body`` —
 * jedno zdanie. ``key`` identyfikuje komunikat, by nie pokazywać go dwa razy (ten sam
 * event przy kolejnych odświeżeniach stanu nie „mignie" ponownie).
 */
export type PhaseNotice = {
  key: string;
  tone: "strategy" | "action" | "status" | "agenda" | "neutral";
  title: string;
  body: string;
};

/** Główna faza (bez podfazy) z ``GamePhase`` ("status.scoring" → "status"). */
function mainPhase(phase: GamePhase): string {
  return phase.split(".")[0];
}

const PHASE_TONE: Record<string, PhaseNotice["tone"]> = {
  strategy: "strategy",
  action: "action",
  status: "status",
  agenda: "agenda",
};

const PHASE_LABEL: Record<string, string> = {
  strategy: "Strategy phase",
  action: "Action phase",
  status: "Status phase",
  agenda: "Agenda phase",
};

/** Czytelna nazwa gracza (frakcja) po KOLORZE albo fallback na kolor/„—". */
function nameOf(
  players: readonly PlayerData[],
  color: string | null | undefined,
): string {
  if (!color) return "The speaker";
  const player = players.find((p) => p.color === color);
  return player ? getPlayerFactionDisplayName(player) : color;
}

/**
 * Wyznacza komunikat NA PODSTAWIE ZMIANY STANU (prev → next). Panel ma być reaktywny
 * („coś się zmieniło / coś jest nie tak"), NIE stałym przypomnieniem — dlatego zwraca
 * komunikat tylko dla ZDARZEŃ wartych ogłoszenia (DECYZJA 2026-11, uwaga użytkownika):
 *
 *  1. zmiana głównej fazy (np. wejście w Action phase),
 *  2. moment „mówca może teraz zakończyć fazę" (canAdvancePhase: false → true w
 *     fazie akcji/statusu, albo wszyscy spasowali/zrobili krok).
 *
 * W pozostałych przypadkach (zwykły przebieg tury) zwraca ``null`` — panel milczy.
 * ``prev`` = ``null`` (pierwszy render) celowo NIE ogłasza nic, by nie „witać" gracza
 * banerem przy wejściu na mapę.
 */
export function announcementFor(
  prev: GameState | null,
  next: GameState | undefined,
  players: readonly PlayerData[],
): PhaseNotice | null {
  if (!next || !prev) return null;

  const prevPhase = mainPhase(prev.phase);
  const nextPhase = mainPhase(next.phase);

  // (1) Zmiana głównej fazy — krótkie „weszliśmy w fazę X".
  if (prevPhase !== nextPhase) {
    const label = PHASE_LABEL[nextPhase];
    if (label) {
      const roundTail =
        next.phase.startsWith("strategy") && prevPhase === "agenda"
          ? " A new round begins."
          : "";
      return {
        key: `phase:${nextPhase}:${next.turnStartedAt ?? ""}`,
        tone: PHASE_TONE[nextPhase] ?? "neutral",
        title: label,
        body: nextPhaseBody(nextPhase, next, players) + roundTail,
      };
    }
  }

  // (2) „Mówca może teraz zakończyć fazę" — tylko gdy brama właśnie się otworzyła
  //     (false → true) w fazie, gdzie to coś znaczy (akcja/status). Agenda/strategia
  //     nie ogłaszają tego osobno (strategia: wejście w akcję ogłosi punkt 1).
  const prevCan = prev.canAdvancePhase ?? false;
  const nextCan = next.canAdvancePhase ?? false;
  if (!prevCan && nextCan && (nextPhase === "action" || nextPhase === "status")) {
    const speakerName = nameOf(players, next.speaker);
    const what =
      nextPhase === "action"
        ? "All players have passed."
        : "Every player has taken their Status step.";
    const nextLabel = nextPhase === "action" ? "Status Phase" : "Agenda Phase";
    return {
      key: `advance:${nextPhase}`,
      tone: PHASE_TONE[nextPhase] ?? "neutral",
      title: "Ready to advance",
      body: `${what} ${speakerName} can now end the phase and move to the ${nextLabel}.`,
    };
  }

  return null;
}

/** Jedno zdanie opisujące, co robić po wejściu w daną fazę. */
function nextPhaseBody(
  phase: string,
  state: GameState,
  players: readonly PlayerData[],
): string {
  const activeName = nameOf(players, state.activePlayer);
  switch (phase) {
    case "strategy":
      return `${activeName} picks first. Each player chooses a Strategy Card.`;
    case "action":
      return `${activeName} goes first in initiative order.`;
    case "status":
      return "Each player resolves their Status step in initiative order.";
    case "agenda":
      return "Reveal and resolve the agenda. Players react and vote in order.";
    default:
      return "";
  }
}

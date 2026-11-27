/*
 * Status tury gry sieciowej (RULES.md 44.5): układa listę `waitReasons` z web-data (backend:
 * `core/actor.describe_wait_reasons`) w to, co pokazuje `TurnStatusChip`. Teksty powodów daje
 * silnik - tu tylko wybór „mój ruch / czekamy" i grupowanie graczy o tym samym powodzie.
 */
import type { WaitReason } from "@/entities/data/types";

export type WaitGroup = { summary: string; playerIds: string[] };

export type WaitStatus = { mine: boolean; groups: WaitGroup[] };

/**
 * Tylko powody blokujące (gracze „w kolejce” nie są jeszcze oczekiwani).
 *
 * `controlAll` = host w trybie testowym steruje każdym graczem - każda decyzja jest „moja".
 * `passed` = czy patrzący już spasował w oknie reakcji (wtedy „may react" to nie jego ruch).
 */
export function waitStatus(
  reasons: WaitReason[],
  me: string | null,
  { controlAll = false, passed = false }: { controlAll?: boolean; passed?: boolean } = {},
): WaitStatus {
  const blocking = reasons.filter((r) => r.blocking);
  const own = blocking.filter((r) => r.playerId === me && !(passed && r.reasonCode === "react"));
  const mine = controlAll ? blocking.length > 0 : own.length > 0;
  const shown = controlAll || !mine ? blocking : own;
  const groups: WaitGroup[] = [];
  for (const { playerId, summary } of shown) {
    const group = groups.find((g) => g.summary === summary);
    if (group) group.playerIds.push(playerId);
    else groups.push({ summary, playerIds: [playerId] });
  }
  return { mine, groups };
}

/** Pełny tekst do podpowiedzi (chip przycina się wielokropkiem). */
export function waitText(
  { mine, groups }: WaitStatus,
  nameOf: (playerId: string) => string,
  controlAll = false,
): string {
  if (groups.length === 0) return "";
  if (mine && !controlAll) return `Your move - ${groups.map((g) => g.summary).join(", ")}`;
  const who = groups
    .map((g) => `${g.playerIds.map(nameOf).join(", ")}: ${g.summary}`)
    .join("; ");
  return `${mine ? "Your move" : "Waiting for"} - ${who}`;
}

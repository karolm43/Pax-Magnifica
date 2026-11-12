import type { ActionCardPlayability } from "@/api/useActionCard";
import type { PromissoryPlayability } from "@/api/useFactionComponents";

/*
 * Karty reakcji zagrywalne TERAZ (RULES.md 54.8). Okno reakcji („after a system is activated”,
 * „at the start of a turn”…) mija z następnym krokiem gry, więc dok ręki musi je pokazać także
 * zwinięty albo na innej zakładce - inaczej karta „ucieka” graczowi. Karty ACTION w swojej turze
 * nie są tu liczone (gracz sam sięga po akcję).
 */

export type ReadyReaction = { tab: "actions" | "notes"; id: string };

export function readyReactions(
  actions: Record<string, ActionCardPlayability> | undefined,
  notes: Record<string, PromissoryPlayability> | undefined,
): ReadyReaction[] {
  const ready: ReadyReaction[] = [];
  for (const row of Object.values(actions ?? {})) {
    if (row.playable && row.reaction) ready.push({ tab: "actions", id: row.card_id });
  }
  for (const row of Object.values(notes ?? {})) {
    if (row.playable && row.reaction) ready.push({ tab: "notes", id: row.note_id });
  }
  return ready;
}

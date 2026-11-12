import type { Activity } from "@/api/useBoardEditor";
import type { NamedKind } from "./Named";

export type ActivitySubject = { kind: NamedKind; id: string };

/** Akcje, których ``subject`` to karta/zdolność z tekstem (to, co pokazuje podpowiedź nazwy). */
const ACTION_SUBJECT: Record<string, NamedKind> = {
  "tech.exhaust": "tech",
  "component.use": "leader",
  "leader.state": "leader",
  "promissory.play": "promissory",
  "strategy.play": "strategy",
  "objective.score": "objective",
  "explore.resolve": "explore",
};

/** Fakty niosące jawną kartę z tekstem (``core/activity.py``). */
const FACT_SUBJECT: Record<string, NamedKind> = {
  action_card: "actionCard",
  tech: "tech",
  explore_card: "explore",
  agenda: "agenda",
  promissory_in_play: "promissory",
  leader: "leader",
  objective_scored: "objective",
  secret_scored: "objective",
};

/**
 * Główna karta/technologia stojąca za wpisem feedu — jej tekst powiadomienie pokazuje od razu
 * (w panelu ten sam tekst jest w podpowiedzi po najechaniu na nazwę). ``null`` = brak.
 */
export function activitySubject(a: Activity): ActivitySubject | null {
  const byAction = ACTION_SUBJECT[a.action];
  if (byAction && a.subject) return { kind: byAction, id: a.subject };
  for (const fact of a.facts) {
    const kind = FACT_SUBJECT[fact.type];
    if (kind && fact.value) return { kind, id: fact.value };
  }
  return null;
}

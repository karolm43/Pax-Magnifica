/**
 * Zbieranie KOMPONENTÓW Z AKCJĄ (nagłówek „Action") dostępnych aktywnemu graczowi —
 * do listy „co zagrałeś?" w modalu akcji komponentu (RULES.md 31.8, R_component_action).
 *
 * Akcja komponentu bywa na: karcie akcji, zdolności frakcji, liderze, technologii,
 * relikcie (oraz karcie eksploracji / promissory note — tych gracz nie trzyma jako
 * listy posiadanych, więc pomijamy; łapie je opcja „Other" w modalu). Listujemy tylko
 * to, co gracz REALNIE ma — z web-data (``PlayerData``) + ręki (``actionCards``).
 *
 * Wykrywanie nagłówka „Action" czytamy WYŁĄCZNIE z danych (zero hardkodowania nazw):
 *  - karty akcji → ``actionCardTiming(id) === "Action"`` (pole ``window``);
 *  - zdolności → ``getAbilityKind(ability) === "action"`` (ACTION w window/effect);
 *  - liderzy → ``abilityWindow``/``abilityText`` zaczyna się od „ACTION";
 *  - techy/relikty → ``text`` zawiera nagłówek „ACTION".
 */

import type { PlayerData } from "@/entities/data/types";
import { getActionCard } from "@/entities/lookup/actionCards";
import { actionCardTiming } from "@/domains/game-shell/components/actionCardTiming";
import { getAbility, getAbilityKind } from "@/entities/lookup/abilities";
import { getLeaderById } from "@/entities/lookup/leaders";
import { getTechData } from "@/entities/lookup/tech";
import { getRelicData } from "@/entities/lookup/relics";
import { getBreakthroughData } from "@/entities/lookup/breakthroughs";

/** Rodzaj źródła akcji komponentu — steruje etykietą i ikoną w modalu. */
export type ComponentActionKind =
  | "action-card"
  | "ability"
  | "leader"
  | "technology"
  | "relic"
  | "legendary"
  | "breakthrough";

export type ComponentActionChoice = {
  id: string;
  name: string;
  kind: ComponentActionKind;
};

/** Czytelna etykieta kategorii (mały tag w wierszu listy). */
export const KIND_LABEL: Record<ComponentActionKind, string> = {
  "action-card": "Action card",
  ability: "Faction ability",
  leader: "Leader",
  technology: "Technology",
  relic: "Relic",
  legendary: "Legendary planet",
  breakthrough: "Breakthrough",
};

/** Nagłówek „Action" w dowolnym polu tekstowym komponentu (start linii lub „ACTION:"). */
const ACTION_HEADER = /^\s*ACTION\b|\bACTION:/;

function textHasAction(...texts: (string | undefined | null)[]): boolean {
  return texts.some((t) => !!t && ACTION_HEADER.test(t));
}

/**
 * Buduje listę komponentów z akcją dostępnych aktywnemu graczowi. ``hand`` to
 * identyfikatory kart akcji z ręki (z ``usePlayerHand``); reszta pochodzi z pól
 * ``PlayerData`` (``abilities``, ``leaderIDs``, ``techs``, ``relics``).
 *
 * Deduplikacja po (kind,id); nazwy z wbudowanych danych (fallback = id). Pozycje bez
 * danych albo bez nagłówka „Action" są pomijane.
 */
export function collectComponentActions(
  player: PlayerData | undefined,
  handActionCards: string[],
): ComponentActionChoice[] {
  const out: ComponentActionChoice[] = [];
  const seen = new Set<string>();
  const push = (kind: ComponentActionKind, id: string, name: string) => {
    const key = `${kind}:${id}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ id, name, kind });
  };

  // Karty akcji z ręki z oknem „Action".
  for (const id of handActionCards) {
    if (actionCardTiming(id) === "Action") {
      push("action-card", id, getActionCard(id)?.name ?? id);
    }
  }

  if (player) {
    // Zdolności frakcji typu „action".
    for (const id of player.abilities ?? []) {
      const ability = getAbility(id);
      if (ability && getAbilityKind(ability) === "action") {
        push("ability", id, ability.name ?? id);
      }
    }
    // Liderzy (agent/hero) z nagłówkiem „ACTION" w oknie lub tekście zdolności.
    for (const id of player.leaderIDs ?? []) {
      const leader = getLeaderById(id);
      if (leader && textHasAction(leader.abilityWindow, leader.abilityText)) {
        push("leader", id, leader.name ?? id);
      }
    }
    // Technologie z nagłówkiem „ACTION" w tekście.
    for (const id of player.techs ?? []) {
      const tech = getTechData(id);
      if (tech && textHasAction(tech.text)) {
        push("technology", id, tech.name ?? id);
      }
    }
    // Relikty z nagłówkiem „ACTION" w tekście.
    for (const id of player.relics ?? []) {
      const relic = getRelicData(id);
      if (relic && textHasAction(relic.text)) {
        push("relic", id, relic.name ?? id);
      }
    }
    // Przełom frakcji (Thunder's Edge) z „ACTION:" - tylko zdobyty (RULES.md 61.3).
    const bt = player.breakthrough;
    if (bt?.unlocked) {
      const data = getBreakthroughData(bt.breakthroughId);
      if (data && textHasAction(data.text)) push("breakthrough", bt.breakthroughId, data.name ?? bt.breakthroughId);
    }
    // Karty zdolności legendarnych planet z „ACTION:" (id = id planety; RULES.md 60).
    for (const ability of player.legendaryAbilities ?? []) {
      if (ability.kind === "action") push("legendary", ability.planet, ability.name);
    }
  }

  return out;
}

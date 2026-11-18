import { abilities } from "@/entities/data/abilities";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";
import type { Ability } from "@/entities/data/types";

const abilitiesMap = indexBy(abilities, (ability) => ability.id);

export function getAbility(abilityId: string): Ability | undefined {
  return withVariant("abilities", abilityId, abilitiesMap.get(abilityId));
}

export type AbilityKind = "action" | "triggered" | "passive";

const ACTION_PATTERN = /^ACTION\b|\bACTION:/;

/** How a faction ability is used: as an action, in a timing window, or always on. */
export function getAbilityKind(ability: Ability): AbilityKind {
  const texts = [ability.window, ability.windowEffect, ability.permanentEffect];
  if (texts.some((text) => text && ACTION_PATTERN.test(text))) return "action";
  if (ability.window) return "triggered";
  return "passive";
}

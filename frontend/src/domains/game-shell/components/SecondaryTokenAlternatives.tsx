import { Stack, Switch } from "@/ds";
import { useMapPick } from "@/domains/strategy/mapPick";
import { MapPickStatus } from "@/domains/offers/MapPickStatus";
import type { TokenAlternative } from "@/domains/strategy/strategyPrompt";

export type TokenAltChoice = { key: string; system: string | null };

/**
 * Other ways to pay a secondary's command token (Jae Mir Kan: "remove 1 of the active player's
 * command tokens from the board and use it instead", RULES.md 62.23). A switch per way; when on,
 * the token's system is picked ON THE MAP (glowing systems). No system clicked = "Auto" (the
 * engine takes the first one).
 */
export function SecondaryTokenAlternatives({
  alternatives,
  value,
  onChange,
}: {
  alternatives: TokenAlternative[];
  value: TokenAltChoice | null;
  onChange: (next: TokenAltChoice | null) => void;
}) {
  const current = alternatives.find((a) => a.key === value?.key) ?? null;
  const handle = useMapPick(
    "system",
    current?.systems ?? [],
    (position) => value && onChange({ key: value.key, system: position }),
    { enabled: !!current, selected: value?.system ?? null },
  );
  if (alternatives.length === 0) return null;
  return (
    <Stack gap="xs">
      {alternatives.map((alt) => (
        <Switch
          key={alt.key}
          checked={value?.key === alt.key}
          onChange={(e) => onChange(e.currentTarget.checked ? { key: alt.key, system: null } : null)}
          label={alt.label}
        />
      ))}
      {current && (
        <MapPickStatus
          targets={current.systems.map((id) => ({ kind: "system" as const, id }))}
          handle={handle}
          disabled={false}
        />
      )}
    </Stack>
  );
}

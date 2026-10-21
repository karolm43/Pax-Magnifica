import { useState } from "react";
import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  TextInput,
} from "@/ds";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, type PlayerEdit } from "@/api/useBoardEditor";
import type { PlayerData } from "@/entities/data/types";

type Props = {
  opened: boolean;
  onClose: () => void;
};

/** Pola liczbowe gracza edytowalne stepperem +/−. */
const NUMERIC_FIELDS: {
  key: keyof PlayerEdit;
  label: string;
  get: (p: PlayerData) => number;
  min?: number;
}[] = [
  { key: "victory_points", label: "Punkty zwycięstwa (VP)", get: (p) => p.totalVps, min: 0 },
  { key: "trade_goods", label: "Trade goods", get: (p) => p.tg, min: 0 },
  { key: "commodities", label: "Commodities", get: (p) => p.commodities, min: 0 },
  { key: "tactical_cc", label: "Żetony taktyczne", get: (p) => p.tacticalCC, min: 0 },
  { key: "fleet_cc", label: "Żetony floty", get: (p) => p.fleetCC, min: 0 },
  { key: "strategic_cc", label: "Żetony strategiczne", get: (p) => p.strategicCC, min: 0 },
  { key: "cc_reinf", label: "Żetony w rezerwie", get: (p) => p.ccReinf, min: 0 },
];

/**
 * Edytor stanu gracza (God-Mode). Wybierasz gracza i edytujesz wszystkie jego
 * wartości — bez sprawdzania zasad. Zmiany idą do backendu (z historią = Undo).
 * Styl spójny z resztą strony (komponenty ds).
 */
export function PlayerEditorModal({ opened, onClose }: Props) {
  const gameData = useGameData();
  const { editPlayer } = useBoardEditor();
  const players = gameData?.playerData ?? [];
  const [selected, setSelected] = useState<string>(players[0]?.discordId ?? "");
  const [busy, setBusy] = useState(false);

  const player =
    players.find((p) => p.discordId === selected) ?? players[0];

  const apply = async (edit: PlayerEdit) => {
    if (!player || busy) return;
    setBusy(true);
    try {
      await editPlayer(player.discordId, edit);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title="God-Mode · edycja gracza"
      size={520}
    >
      {players.length === 0 ? (
        <Text size="sm" c="dimmed">
          Brak graczy — najpierw utwórz grę.
        </Text>
      ) : (
        <Stack gap="md">
          <SegmentedControl
            size="xs"
            fullWidth
            value={player?.discordId}
            onChange={setSelected}
            data={players.map((p) => ({
              value: p.discordId,
              label: (p.flexibleDisplayName || p.faction).toUpperCase(),
            }))}
          />

          {player && (
            <>
              <Group gap="sm" grow>
                <TextInput
                  label="Frakcja"
                  defaultValue={player.faction}
                  onBlur={(e) => {
                    const v = e.currentTarget.value.trim();
                    if (v && v !== player.faction) void apply({ faction: v });
                  }}
                />
                <TextInput
                  label="Kolor"
                  defaultValue={player.color}
                  onBlur={(e) => {
                    const v = e.currentTarget.value.trim();
                    if (v && v !== player.color) void apply({ color: v });
                  }}
                />
              </Group>

              <Stack gap={6}>
                {NUMERIC_FIELDS.map(({ key, label, get, min }) => {
                  const value = get(player);
                  return (
                    <Group key={key} gap="sm" justify="space-between" wrap="nowrap">
                      <Text size="sm">{label}</Text>
                      <Group gap={4} wrap="nowrap">
                        <ActionIcon
                          size="sm"
                          variant="default"
                          disabled={busy || value <= (min ?? 0)}
                          onClick={() => void apply({ [key]: value - 1 })}
                          aria-label={`−1 ${label}`}
                        >
                          <IconMinus size={12} />
                        </ActionIcon>
                        <NumberInput
                          size="xs"
                          value={value}
                          min={min}
                          hideControls
                          w={64}
                          onChange={(v) => {
                            const n = typeof v === "number" ? v : Number(v);
                            if (!Number.isNaN(n) && n !== value) {
                              void apply({ [key]: n });
                            }
                          }}
                        />
                        <ActionIcon
                          size="sm"
                          variant="default"
                          disabled={busy}
                          onClick={() => void apply({ [key]: value + 1 })}
                          aria-label={`+1 ${label}`}
                        >
                          <IconPlus size={12} />
                        </ActionIcon>
                      </Group>
                    </Group>
                  );
                })}
              </Stack>

              <Switch
                label="Spasował (passed)"
                checked={player.passed}
                onChange={(e) =>
                  void apply({ passed: e.currentTarget.checked })
                }
              />

              <TextInput
                label="Technologie (ID po przecinku)"
                defaultValue={player.techs.join(", ")}
                onBlur={(e) => {
                  const techs = e.currentTarget.value
                    .split(",")
                    .map((t) => t.trim())
                    .filter(Boolean);
                  void apply({ technologies: techs });
                }}
              />

              <TextInput
                label="Kontrolowane planety (ID po przecinku)"
                defaultValue={player.planets.join(", ")}
                onBlur={(e) => {
                  const planets = e.currentTarget.value
                    .split(",")
                    .map((t) => t.trim())
                    .filter(Boolean);
                  void apply({ controlled_planets: planets });
                }}
              />

              <Group justify="flex-end">
                <Button variant="default" size="xs" onClick={onClose}>
                  Zamknij
                </Button>
              </Group>
            </>
          )}
        </Stack>
      )}
    </AppModal>
  );
}

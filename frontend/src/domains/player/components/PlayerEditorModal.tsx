import { useMemo, useState } from "react";
import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from "@/ds";
import { IconMinus, IconPlus, IconX } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, type PlayerEdit } from "@/api/useBoardEditor";
import { techs as ALL_TECHS } from "@/entities/data/tech";
import { getTechData } from "@/entities/lookup/tech";
import type { PlayerData } from "@/entities/data/types";
import styles from "./PlayerEditorModal.module.css";

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

const LEADER_STATE_LABEL: Record<string, string> = {
  locked: "🔒",
  unlocked: "✓",
  exhausted: "⟲",
};

/*
 * Oficjalne źródła (zgodne z assets/enabled_sources.json backendu). Dane
 * frontendu zawierają TĘ SAMĄ technologię z wielu źródeł homebrew (absol,
 * twilights_fall, …) pod różnymi aliasami — bez tego filtra lista dublowała
 * nazwy. Trzymamy oficjalne źródła + thunders_edge (aktywny zestaw).
 */
const OFFICIAL_TECH_SOURCES = new Set([
  "base",
  "pok",
  "codex1",
  "codex2",
  "codex3",
  "codex4",
  "thunders_edge",
]);

/*
 * Priorytet wersji karty (wyższa = nowsza). Oficjalne erraty: codex4 (ΩΩ) >
 * codex1 (Ω) > base. thunders_edge/pok to osobne karty (nie erraty) — dostają
 * neutralny priorytet. Przy duplikacie rodziny (ta sama karta w kilku wersjach)
 * zostaje najnowsza. Źródło: dane AsyncTI4 (sufiks Ω/ΩΩ = kolejna errata).
 */
const SOURCE_PRIORITY: Record<string, number> = {
  base: 0,
  pok: 1,
  thunders_edge: 1,
  codex1: 2,
  codex2: 3,
  codex3: 4,
  codex4: 5,
};

/**
 * Klucz rodziny karty: nazwa bez markera erraty (Ω/ΩΩ) i białych znaków. Dzięki
 * temu "X-89 Bacterial Weapon", "…Ω" i "…ΩΩ" trafiają do jednej rodziny i zostaje
 * tylko najnowszy wariant (inaczej lista dublowała wszystkie trzy).
 */
function techFamilyKey(name: string): string {
  return name.replace(/\u03a9+/g, "").replace(/\s+/g, " ").trim().toLowerCase();
}

/** Krótki kod technologii: litery wymagań (np. "BB") albo inicjał typu. */
function techCode(requirements: string | undefined, types: string[]): string {
  if (requirements) return requirements.toUpperCase();
  const t = types[0] ?? "";
  if (t === "UNITUPGRADE") return "U";
  return t ? t[0] : "?";
}

/**
 * Edytor stanu gracza (God-Mode). Wybierasz gracza i edytujesz wszystkie wartości:
 * liczby stepperem, liderów klikiem, technologie z listy (nazwa + skrót) — bez
 * wpisywania ID. Bez sprawdzania zasad. Zmiany idą do backendu (z historią = Undo).
 */
export function PlayerEditorModal({ opened, onClose }: Props) {
  const gameData = useGameData();
  const { editPlayer } = useBoardEditor();
  const players = gameData?.playerData ?? [];
  const [selected, setSelected] = useState<string>(players[0]?.discordId ?? "");
  const [busy, setBusy] = useState(false);
  const [techToAdd, setTechToAdd] = useState<string | null>(null);

  const player = players.find((p) => p.discordId === selected) ?? players[0];

  // Opcje technologii: TYLKO oficjalne źródła (+ thunders_edge). Dla każdej
  // RODZINY karty (nazwa bez Ω/ΩΩ) zostaje NAJNOWSZY wariant wg priorytetu źródła
  // — errata ΩΩ (codex4) wygrywa z Ω (codex1) i z base. Ogólne + frakcji gracza.
  const techOptions = useMemo(() => {
    // 1) Filtr źródeł i frakcji.
    const eligible = ALL_TECHS.filter((t) => {
      if (!OFFICIAL_TECH_SOURCES.has(t.source)) return false;
      // Frakcyjne: tylko bieżącego gracza; ogólne (bez faction) zawsze.
      if (t.faction && player && t.faction !== player.faction) return false;
      return true;
    });
    // 2) Dla każdej rodziny karty wybierz najnowszą wersję (najwyższy priorytet).
    const bestByFamily = new Map<string, (typeof eligible)[number]>();
    for (const t of eligible) {
      const key = `${t.faction ?? ""}|${techFamilyKey(t.name)}`;
      const current = bestByFamily.get(key);
      const rank = SOURCE_PRIORITY[t.source] ?? 1;
      const currentRank = current
        ? (SOURCE_PRIORITY[current.source] ?? 1)
        : -1;
      if (!current || rank > currentRank) bestByFamily.set(key, t);
    }
    // 3) Etykieta: nazwa + skrót; sortowanie alfabetyczne.
    return [...bestByFamily.values()]
      .map((t) => ({
        value: t.alias,
        label: `${t.name} · ${techCode(t.requirements, t.types)}`,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [player]);

  const apply = async (edit: PlayerEdit) => {
    if (!player || busy) return;
    setBusy(true);
    try {
      await editPlayer(player.discordId, edit);
    } finally {
      setBusy(false);
    }
  };

  const addTech = async (techId: string | null) => {
    if (!techId || !player) return;
    if (player.techs.includes(techId)) return;
    setTechToAdd(null);
    await apply({ technologies: [...player.techs, techId] });
  };

  const removeTech = async (techId: string) => {
    if (!player) return;
    await apply({ technologies: player.techs.filter((t) => t !== techId) });
  };

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title="God-Mode · edycja gracza"
      size={560}
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

              {/* Liczby: etykieta | [−] [input] [+] w stałej, wyrównanej kolumnie. */}
              <Stack gap={4}>
                {NUMERIC_FIELDS.map(({ key, label, get, min }) => {
                  const value = get(player);
                  return (
                    <div key={key} className={styles.numRow}>
                      <Text size="sm" className={styles.numLabel}>
                        {label}
                      </Text>
                      <div className={styles.numCtl}>
                        <ActionIcon
                          size="sm"
                          variant="subtle"
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
                          classNames={{ input: styles.numInput }}
                          onChange={(v) => {
                            const n = typeof v === "number" ? v : Number(v);
                            if (!Number.isNaN(n) && n !== value) {
                              void apply({ [key]: n });
                            }
                          }}
                        />
                        <ActionIcon
                          size="sm"
                          variant="subtle"
                          disabled={busy}
                          onClick={() => void apply({ [key]: value + 1 })}
                          aria-label={`+1 ${label}`}
                        >
                          <IconPlus size={12} />
                        </ActionIcon>
                      </div>
                    </div>
                  );
                })}
              </Stack>

              <Switch
                label="Spasował (passed)"
                checked={player.passed}
                onChange={(e) => void apply({ passed: e.currentTarget.checked })}
              />

              {player.leaders.length > 0 && (
                <Stack gap={4}>
                  <Text size="xs" c="dimmed">
                    Liderzy (klik: zablokowany → gotowy → wyczerpany)
                  </Text>
                  <Group gap={6} wrap="wrap">
                    {player.leaders.map((leader) => {
                      const state = leader.locked
                        ? "locked"
                        : leader.exhausted
                          ? "exhausted"
                          : "unlocked";
                      const next =
                        state === "locked"
                          ? "unlocked"
                          : state === "unlocked"
                            ? "exhausted"
                            : "locked";
                      return (
                        <Button
                          key={leader.id}
                          size="xs"
                          variant={state === "unlocked" ? "filled" : "default"}
                          disabled={busy}
                          onClick={() =>
                            void apply({ leader_states: { [leader.id]: next } })
                          }
                          title={`${leader.type}: ${state} → ${next}`}
                        >
                          {LEADER_STATE_LABEL[state]} {leader.type}
                        </Button>
                      );
                    })}
                  </Group>
                </Stack>
              )}

              {/* Technologie: lista z nazwą + skrótem (bez wpisywania ID). */}
              <Stack gap={6}>
                <Text size="xs" c="dimmed">
                  Technologie
                </Text>
                <Select
                  size="xs"
                  placeholder="Dodaj technologię (nazwa · skrót)…"
                  data={techOptions}
                  value={techToAdd}
                  onChange={(v) => void addTech(v)}
                  searchable
                  clearable
                />
                <Group gap={6} wrap="wrap">
                  {player.techs.map((techId) => {
                    const t = getTechData(techId);
                    return (
                      <Button
                        key={techId}
                        size="xs"
                        variant="default"
                        rightSection={<IconX size={11} />}
                        disabled={busy}
                        onClick={() => void removeTech(techId)}
                        title="Usuń technologię"
                      >
                        {t ? t.name : techId}
                      </Button>
                    );
                  })}
                  {player.techs.length === 0 && (
                    <Text size="xs" c="dimmed">
                      Brak technologii.
                    </Text>
                  )}
                </Group>
              </Stack>

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

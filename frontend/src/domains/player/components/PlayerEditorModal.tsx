import { useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
  ScrollArea,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Tabs,
  Text,
  TextInput,
} from "@/ds";
import {
  IconCards,
  IconCrown,
  IconMinus,
  IconPlanet,
  IconPlus,
  IconSettings,
  IconUsers,
  IconX,
} from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { useGameData } from "@/state/useGameContext";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import {
  useBoardEditor,
  useStrategyCards,
  type PlayerEdit,
} from "@/api/useBoardEditor";
import { techs as ALL_TECHS } from "@/entities/data/tech";
import { getTechData } from "@/entities/lookup/tech";
import { getPlanetData } from "@/entities/lookup/planets";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import type { PlayerData } from "@/entities/data/types";
import {
  actionCardOptions,
  promissoryNoteOptions,
  secretObjectiveOptions,
} from "./cardOptions";
import { CardListEditor } from "./CardListEditor";
import { usePlayerHandById } from "./usePlayerHandById";
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
  { key: "victory_points", label: "Victory points (VP)", get: (p) => p.totalVps, min: 0 },
  { key: "trade_goods", label: "Trade goods", get: (p) => p.tg, min: 0 },
  { key: "commodities", label: "Commodities", get: (p) => p.commodities, min: 0 },
  { key: "tactical_cc", label: "Tactical tokens", get: (p) => p.tacticalCC, min: 0 },
  { key: "fleet_cc", label: "Fleet tokens", get: (p) => p.fleetCC, min: 0 },
  { key: "strategic_cc", label: "Strategic tokens", get: (p) => p.strategicCC, min: 0 },
  { key: "cc_reinf", label: "Reinforcement tokens", get: (p) => p.ccReinf, min: 0 },
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
 * Edytor stanu gracza (God-Mode). Jeden panel na wszystko, co da się edytować bez
 * reguł: liczby i żetony, mówca, karty strategii, technologie (z wyczerpaniem),
 * planety (z wyczerpaniem), liderzy, prywatna ręka (karty akcji / tajne cele /
 * weksle) oraz weksle w strefie gry. Zmiany idą przez backend (z historią = Undo).
 */
export function PlayerEditorModal({ opened, onClose }: Props) {
  const gameData = useGameData();
  const {
    editPlayer,
    setSpeaker,
    toggleTechExhaust,
    togglePlanetExhaust,
    setLeaderState,
    setPlayerHand,
  } = useBoardEditor();
  const { data: strategyCards } = useStrategyCards();
  const deskPlayer = useDeskPlayer();
  const players = gameData?.playerData ?? [];
  const gameName = gameData?.gameName ?? "";
  const factionColorMap = gameData?.factionColorMap ?? {};

  // Domyślnie wybieramy GRACZA PULPITU (aktywny → mówca → pierwszy) — to jego
  // rękę pokazuje dok ręki na mapie. Dzięki temu karty dodane do ręki od razu
  // widać w doku (operator nie edytuje „po cichu" innego gracza). Można zmienić
  // gracza przełącznikiem — wtedy zmiany ręki widać dopiero po przełączeniu doku.
  const [selected, setSelected] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const player = players.find((p) => p.discordId === selected) ?? players[0];
  const playerId = player?.discordId ?? null;

  // Zasiej zaznaczenie graczem pulpitu (gdy jeszcze nie wybrano) — albo pierwszym
  // graczem, gdy pulpitu nie da się ustalić (pusty stan).
  useEffect(() => {
    if (selected) return;
    const seed = deskPlayer?.discordId ?? players[0]?.discordId;
    if (seed) setSelected(seed);
  }, [deskPlayer, players, selected]);

  const { data: hand } = usePlayerHandById(gameName, playerId);

  // Opcje technologii: TYLKO oficjalne źródła (+ thunders_edge). Dla każdej
  // RODZINY karty (nazwa bez Ω/ΩΩ) zostaje NAJNOWSZY wariant wg priorytetu źródła
  // — errata ΩΩ (codex4) wygrywa z Ω (codex1) i z base. Ogólne + frakcji gracza.
  const techOptions = useMemo(() => {
    const eligible = ALL_TECHS.filter((t) => {
      if (!OFFICIAL_TECH_SOURCES.has(t.source)) return false;
      if (t.faction && player && t.faction !== player.faction) return false;
      return true;
    });
    const bestByFamily = new Map<string, (typeof eligible)[number]>();
    for (const t of eligible) {
      const key = `${t.faction ?? ""}|${techFamilyKey(t.name)}`;
      const current = bestByFamily.get(key);
      const rank = SOURCE_PRIORITY[t.source] ?? 1;
      const currentRank = current ? (SOURCE_PRIORITY[current.source] ?? 1) : -1;
      if (!current || rank > currentRank) bestByFamily.set(key, t);
    }
    return [...bestByFamily.values()]
      .map((t) => ({
        value: t.alias,
        label: `${t.name} · ${techCode(t.requirements, t.types)}`,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [player]);

  const acOptions = useMemo(() => actionCardOptions(), []);
  const soOptions = useMemo(() => secretObjectiveOptions(), []);
  const pnOptions = useMemo(() => promissoryNoteOptions(), []);

  const apply = async (edit: PlayerEdit) => {
    if (!player || busy) return;
    setBusy(true);
    try {
      await editPlayer(player.discordId, edit);
    } finally {
      setBusy(false);
    }
  };

  const runBusy = async (fn: () => Promise<void>) => {
    if (!player || busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  // --- Technologie ---
  const addTech = (techId: string) => {
    if (!player || player.techs.includes(techId)) return;
    void apply({ technologies: [...player.techs, techId] });
  };
  const removeTech = (techId: string) =>
    player && void apply({ technologies: player.techs.filter((t) => t !== techId) });

  // --- Ręka (prywatna) ---
  const updateHand = (patch: {
    actionCards?: string[];
    secretObjectives?: string[];
    promissoryNotes?: string[];
  }) => playerId && void runBusy(() => setPlayerHand(playerId, patch));

  // --- Nazwy kart do chipów ---
  const acName = (id: string) => getActionCard(id)?.name ?? id;
  const soName = (id: string) => getSecretObjectiveData(id)?.name ?? id;
  const pnName = (id: string) =>
    getPromissoryNoteData(id, factionColorMap)?.displayName ?? id;

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title="God Mode · edit player"
      size={820}
    >
      {players.length === 0 ? (
        <Text size="sm" c="dimmed">
          No players - create a game first.
        </Text>
      ) : (
        <Stack gap="sm">
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
            <Tabs defaultValue="general" keepMounted={false}>
              <Tabs.List grow>
                <Tabs.Tab value="general" leftSection={<IconSettings size={14} />}>
                  General
                </Tabs.Tab>
                <Tabs.Tab value="tech" leftSection={<IconCards size={14} />}>
                  Tech
                </Tabs.Tab>
                <Tabs.Tab value="planets" leftSection={<IconPlanet size={14} />}>
                  Planets
                </Tabs.Tab>
                <Tabs.Tab value="leaders" leftSection={<IconCrown size={14} />}>
                  Leaders
                </Tabs.Tab>
                <Tabs.Tab value="hand" leftSection={<IconUsers size={14} />}>
                  Hand
                </Tabs.Tab>
              </Tabs.List>

              <ScrollArea mah="min(68vh, 620px)" offsetScrollbars>
                <div className={styles.tabBody}>
                  {/* === GENERAL === */}
                  <Tabs.Panel value="general">
                    <Stack gap="md">
                      <Group gap="sm" grow>
                        <TextInput
                          label="Faction"
                          defaultValue={player.faction}
                          key={`faction-${player.discordId}`}
                          onBlur={(e) => {
                            const v = e.currentTarget.value.trim();
                            if (v && v !== player.faction) void apply({ faction: v });
                          }}
                        />
                        <TextInput
                          label="Color"
                          defaultValue={player.color}
                          key={`color-${player.discordId}`}
                          onBlur={(e) => {
                            const v = e.currentTarget.value.trim();
                            if (v && v !== player.color) void apply({ color: v });
                          }}
                        />
                      </Group>

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

                      <Group justify="space-between">
                        <Switch
                          label="Passed"
                          checked={player.passed}
                          onChange={(e) =>
                            void apply({ passed: e.currentTarget.checked })
                          }
                        />
                        <Switch
                          label="Speaker"
                          checked={player.isSpeaker}
                          disabled={busy || player.isSpeaker}
                          onChange={() =>
                            void runBusy(() => setSpeaker(player.discordId))
                          }
                        />
                      </Group>

                      {/* Karty strategii (po numerze inicjatywy). */}
                      <Stack gap={6}>
                        <Text size="xs" c="dimmed">
                          Strategy cards (click to assign / unassign)
                        </Text>
                        <Group gap={6} wrap="wrap">
                          {(strategyCards ?? []).map((card) => {
                            const owned = player.scs.includes(card.initiative);
                            const takenByOther =
                              !owned && card.picked_by !== null;
                            return (
                              <Button
                                key={card.initiative}
                                size="xs"
                                variant={owned ? "filled" : "default"}
                                disabled={busy || takenByOther}
                                onClick={() => {
                                  const next = owned
                                    ? player.scs.filter((i) => i !== card.initiative)
                                    : [...player.scs, card.initiative];
                                  void apply({ strategy_cards: next });
                                }}
                                title={
                                  takenByOther
                                    ? `Taken by ${card.picked_by}`
                                    : card.name
                                }
                              >
                                {card.initiative}. {card.name}
                              </Button>
                            );
                          })}
                          {(strategyCards ?? []).length === 0 && (
                            <Text size="xs" c="dimmed">
                              No strategy card set loaded.
                            </Text>
                          )}
                        </Group>
                      </Stack>
                    </Stack>
                  </Tabs.Panel>

                  {/* === TECH === */}
                  <Tabs.Panel value="tech">
                    <Stack gap={8}>
                      <Text size="xs" c="dimmed">
                        Add a technology (name · prerequisite), then click a chip to
                        toggle exhausted (⟲) / ready, or the × to remove it.
                      </Text>
                      <Select
                        size="xs"
                        placeholder="Add technology…"
                        data={techOptions}
                        value={null}
                        onChange={(v) => {
                          if (v) addTech(v);
                        }}
                        searchable
                        clearable
                        disabled={busy}
                      />
                      <Group gap={6} wrap="wrap">
                        {player.techs.map((techId) => {
                          const t = getTechData(techId);
                          const exhausted = player.exhaustedTechs.includes(techId);
                          return (
                            <Group key={techId} gap={2} wrap="nowrap">
                              <Button
                                size="xs"
                                variant={exhausted ? "light" : "default"}
                                disabled={busy}
                                onClick={() =>
                                  void runBusy(() =>
                                    toggleTechExhaust(player.discordId, techId),
                                  )
                                }
                                title={
                                  exhausted
                                    ? "Exhausted — click to ready"
                                    : "Ready — click to exhaust"
                                }
                              >
                                {exhausted ? "⟲ " : ""}
                                {t ? t.name : techId}
                              </Button>
                              <ActionIcon
                                size="input-xs"
                                variant="default"
                                disabled={busy}
                                onClick={() => removeTech(techId)}
                                aria-label="Remove technology"
                              >
                                <IconX size={11} />
                              </ActionIcon>
                            </Group>
                          );
                        })}
                        {player.techs.length === 0 && (
                          <Text size="xs" c="dimmed">
                            No technologies.
                          </Text>
                        )}
                      </Group>
                    </Stack>
                  </Tabs.Panel>

                  {/* === PLANETS === */}
                  <Tabs.Panel value="planets">
                    <Stack gap={8}>
                      <Text size="xs" c="dimmed">
                        Click a planet to toggle exhausted (⟲) / ready. Edit the full
                        controlled set below (comma-separated planet IDs).
                      </Text>
                      <Group gap={6} wrap="wrap">
                        {player.planets.map((planetId) => {
                          const data = getPlanetData(planetId);
                          const exhausted =
                            player.exhaustedPlanets.includes(planetId);
                          return (
                            <Button
                              key={planetId}
                              size="xs"
                              variant={exhausted ? "light" : "default"}
                              disabled={busy}
                              onClick={() =>
                                void runBusy(() =>
                                  togglePlanetExhaust(player.discordId, planetId),
                                )
                              }
                              title={
                                exhausted
                                  ? "Exhausted — click to ready"
                                  : "Ready — click to exhaust"
                              }
                            >
                              {exhausted ? "⟲ " : ""}
                              {data?.name ?? planetId}
                            </Button>
                          );
                        })}
                        {player.planets.length === 0 && (
                          <Text size="xs" c="dimmed">
                            No controlled planets.
                          </Text>
                        )}
                      </Group>
                      <TextInput
                        label="Controlled planets (comma-separated IDs)"
                        defaultValue={player.planets.join(", ")}
                        key={`planets-${player.discordId}`}
                        onBlur={(e) => {
                          const planets = e.currentTarget.value
                            .split(",")
                            .map((t) => t.trim())
                            .filter(Boolean);
                          void apply({ controlled_planets: planets });
                        }}
                      />
                    </Stack>
                  </Tabs.Panel>

                  {/* === LEADERS === */}
                  <Tabs.Panel value="leaders">
                    {player.leaders.length > 0 ? (
                      <Stack gap={6}>
                        <Text size="xs" c="dimmed">
                          Click to cycle: locked 🔒 → ready ✓ → exhausted ⟲
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
                                  void runBusy(() =>
                                    setLeaderState(player.discordId, leader.id, next),
                                  )
                                }
                                title={`${leader.type}: ${state} → ${next}`}
                              >
                                {LEADER_STATE_LABEL[state]} {leader.type}
                              </Button>
                            );
                          })}
                        </Group>
                      </Stack>
                    ) : (
                      <Text size="xs" c="dimmed">
                        No leaders for this faction.
                      </Text>
                    )}
                  </Tabs.Panel>

                  {/* === HAND === */}
                  <Tabs.Panel value="hand">
                    <Stack gap="md">
                      {deskPlayer &&
                        player.discordId !== deskPlayer.discordId && (
                          <Text size="xs" c="var(--ds-sig-war)">
                            Heads up: the on-map hand dock only shows{" "}
                            {(
                              deskPlayer.flexibleDisplayName ||
                              deskPlayer.faction
                            ).toUpperCase()}
                            {" "}(the active / speaker player). Hand edits here go
                            to{" "}
                            {(
                              player.flexibleDisplayName || player.faction
                            ).toUpperCase()}
                            , so they won't appear in the dock until that player is
                            active.
                          </Text>
                        )}
                      <Stack gap={4}>
                        <Text size="sm" fw={600}>
                          Action cards
                        </Text>
                        <CardListEditor
                          ids={hand?.actionCards ?? []}
                          options={acOptions}
                          labelFor={acName}
                          placeholder="Add action card…"
                          emptyLabel="Empty hand."
                          disabled={busy || !hand}
                          onAdd={(id) =>
                            updateHand({
                              actionCards: [...(hand?.actionCards ?? []), id],
                            })
                          }
                          onRemove={(id) =>
                            updateHand({
                              actionCards: (hand?.actionCards ?? []).filter(
                                (x) => x !== id,
                              ),
                            })
                          }
                        />
                      </Stack>

                      <Stack gap={4}>
                        <Text size="sm" fw={600}>
                          Secret objectives
                        </Text>
                        <CardListEditor
                          ids={hand?.secretObjectives ?? []}
                          options={soOptions}
                          labelFor={soName}
                          placeholder="Add secret objective…"
                          emptyLabel="No secret objectives."
                          disabled={busy || !hand}
                          onAdd={(id) =>
                            updateHand({
                              secretObjectives: [
                                ...(hand?.secretObjectives ?? []),
                                id,
                              ],
                            })
                          }
                          onRemove={(id) =>
                            updateHand({
                              secretObjectives: (
                                hand?.secretObjectives ?? []
                              ).filter((x) => x !== id),
                            })
                          }
                        />
                      </Stack>

                      <Stack gap={4}>
                        <Text size="sm" fw={600}>
                          Promissory notes (hand)
                        </Text>
                        <CardListEditor
                          ids={hand?.promissoryNotes ?? []}
                          options={pnOptions}
                          labelFor={pnName}
                          placeholder="Add promissory note…"
                          emptyLabel="No promissory notes."
                          disabled={busy || !hand}
                          onAdd={(id) =>
                            updateHand({
                              promissoryNotes: [
                                ...(hand?.promissoryNotes ?? []),
                                id,
                              ],
                            })
                          }
                          onRemove={(id) =>
                            updateHand({
                              promissoryNotes: (
                                hand?.promissoryNotes ?? []
                              ).filter((x) => x !== id),
                            })
                          }
                        />
                      </Stack>

                      <Stack gap={4}>
                        <Text size="sm" fw={600}>
                          Promissory notes in play area
                        </Text>
                        <CardListEditor
                          ids={player.promissoryNotesInPlayArea ?? []}
                          options={pnOptions}
                          labelFor={pnName}
                          placeholder="Add note to play area…"
                          emptyLabel="Play area empty."
                          disabled={busy}
                          onAdd={(id) =>
                            void apply({
                              promissory_notes_in_play: [
                                ...(player.promissoryNotesInPlayArea ?? []),
                                id,
                              ],
                            })
                          }
                          onRemove={(id) =>
                            void apply({
                              promissory_notes_in_play: (
                                player.promissoryNotesInPlayArea ?? []
                              ).filter((x) => x !== id),
                            })
                          }
                        />
                      </Stack>
                    </Stack>
                  </Tabs.Panel>
                </div>
              </ScrollArea>
            </Tabs>
          )}

          <Group justify="flex-end">
            <Button variant="default" size="xs" onClick={onClose}>
              Close
            </Button>
          </Group>
        </Stack>
      )}
    </AppModal>
  );
}

import { useId, type ReactNode } from "react";
import { NumberInput, Switch, SegmentedControl, Tabs } from "@/ds";
import { useSettingsStore } from "@/state/appStore";
import { toggleVariant, variantModules } from "@/entities/data/officialSources";
import { AppModal } from "@/shared/ui/AppModal";
import type { ControlTokenDisplayMode } from "@/entities/game/controlTokenDisplay";
import { CurrentGameClockControls } from "@/domains/clock/CurrentGameClockControls";
import { CurrentGameReactionWindow } from "./CurrentGameReactionWindow";
import { AudioSettingsPanel } from "@/shared/audio/AudioSettingsPanel";
import styles from "./SettingsModal.module.css";

type PlayerAreaToggleKey =
  | "showPlayerAreaCommandTokens"
  | "showPlayerAreaArmyStrength"
  | "showPlayerAreaUnitUpgrades"
  | "showPlayerAreaTotalSpend"
  | "showPlayerAreaReinforcements"
  | "showPlayerAreaFactionAbilities"
  | "showPlayerAreaNeighborship";

const PLAYER_AREA_TOGGLES: { key: PlayerAreaToggleKey; label: string; description: string }[] = [
  {
    key: "showPlayerAreaCommandTokens",
    label: "Command Tokens",
    description: "Show tactical, fleet, and strategy command token counts.",
  },
  {
    key: "showPlayerAreaArmyStrength",
    label: "Army Strength",
    description: "Show the ground and space strength summary.",
  },
  {
    key: "showPlayerAreaUnitUpgrades",
    label: "Unit Upgrades",
    description: "Show upgraded-unit styling and upgrade faction badges.",
  },
  {
    key: "showPlayerAreaTotalSpend",
    label: "Total Spend",
    description: "Show the literal total resource and influence spend column. Optimal spend stays visible.",
  },
  {
    key: "showPlayerAreaReinforcements",
    label: "Reinforcements",
    description: "Show faction reinforcement tokens near planet cards, including sleepers, wormholes, breach, and galvanize tokens.",
  },
  {
    key: "showPlayerAreaFactionAbilities",
    label: "Faction Abilities",
    description: "Show faction abilities, faction tech, and related custom notes.",
  },
  {
    key: "showPlayerAreaNeighborship",
    label: "Neighborship",
    description: "Show neighbor faction icons.",
  },
];

/** Liczba całkowita z pola liczbowego w zakresie; puste/niepoprawne → `fallback`. */
function clampInt(value: number | string, min: number, max: number, fallback: number) {
  const n = typeof value === "number" ? value : Number.parseInt(value, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, Math.round(n)));
}

type SettingsModalProps = {
  opened: boolean;
  onClose: () => void;
  /** Bieżąca gra (w grze) — odblokowuje sterowanie zegarem trwającej partii. */
  gameId?: string;
};

function SettingGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className={styles.group}>
      <span className={styles.groupLabel}>{label}</span>
      {children}
    </section>
  );
}

/** Label and description on the left, the control on the right. */
function SettingRow({
  label,
  description,
  htmlFor,
  children,
}: {
  label: string;
  description?: ReactNode;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.row}>
      <label className={styles.label} htmlFor={htmlFor}>
        {label}
      </label>
      {description && <span className={styles.description}>{description}</span>}
      <span className={styles.control}>{children}</span>
    </div>
  );
}

function SwitchRow({
  label,
  description,
  checked,
  onToggle,
}: {
  label: string;
  description: string;
  checked: boolean;
  onToggle: (checked: boolean) => void;
}) {
  const id = useId();
  return (
    <SettingRow label={label} description={description} htmlFor={id}>
      <Switch
        id={id}
        checked={checked}
        onChange={(event) => onToggle(event.currentTarget.checked)}
        size="sm"
        aria-label={label}
      />
    </SettingRow>
  );
}

export function SettingsModal({ opened, onClose, gameId }: SettingsModalProps) {
  const settings = useSettingsStore((state) => state.settings);
  const handlers = useSettingsStore((state) => state.handlers);

  return (
    <AppModal opened={opened} onClose={onClose} title="Settings" size={620} centered>
      <Tabs defaultValue="general">
        <Tabs.List className={styles.tabList}>
          <Tabs.Tab value="general" className={styles.tab}>
            General
          </Tabs.Tab>
          <Tabs.Tab value="player-areas" className={styles.tab}>
            Player areas
          </Tabs.Tab>
          <Tabs.Tab value="sound" className={styles.tab}>
            Sound
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="general" className={styles.panel}>
          <SettingGroup label="Admin / testing">
            <SwitchRow
              label="Fast mode (skip intro & cinematics)"
              description="Skip the opening intro screen and full-screen phase transition banners for the quickest possible testing. Game rules are unaffected."
              checked={settings.adminFastMode}
              onToggle={(checked) =>
                handlers.updateSettings({ adminFastMode: checked })
              }
            />
            <SwitchRow
              label="Free unit dragging (God-Mode)"
              description="Allow dragging units anywhere on the map, ignoring the rules. When off, units can only be dragged into the active system as a validated tactical move."
              checked={settings.freeUnitDrag}
              onToggle={(checked) =>
                handlers.updateSettings({ freeUnitDrag: checked })
              }
            />
            <SwitchRow
              label="Skip phases button (God-Mode)"
              description="Show a Skip phase button in the turn panel. It jumps to the next phase ignoring passes, open windows and strategy card picks (missing cards are auto-picked). Normal Next phase is unchanged."
              checked={settings.skipPhases}
              onToggle={(checked) =>
                handlers.updateSettings({ skipPhases: checked })
              }
            />
          </SettingGroup>

          <SettingGroup label="Game variants">
            {variantModules().map((module) => (
              <SwitchRow
                key={module.id}
                label={module.name}
                description={`${module.description} Applies to the next new game; a game in progress keeps its decks.`}
                checked={settings.gameVariants.includes(module.id)}
                onToggle={(checked) =>
                  handlers.updateSettings({
                    gameVariants: toggleVariant(settings.gameVariants, module, checked),
                  })
                }
              />
            ))}
          </SettingGroup>

          <SettingGroup label="Chess clock">
            <SwitchRow
              label="Player clocks"
              description="Each player gets a time bank; only the player who is deciding right now (turn, vote, window response) uses it. Applies to new games; use Current game below to start it in a game in progress."
              checked={settings.chessClockEnabled}
              onToggle={(checked) =>
                handlers.updateSettings({ chessClockEnabled: checked })
              }
            />
            <SettingRow
              label="Time per player (minutes)"
              description="Total time bank for the whole game."
            >
              <NumberInput
                aria-label="Time per player in minutes"
                w={120}
                min={1}
                max={1440}
                disabled={!settings.chessClockEnabled}
                value={settings.chessClockMinutes}
                onChange={(value) =>
                  handlers.updateSettings({
                    chessClockMinutes: clampInt(value, 1, 1440, 120),
                  })
                }
              />
            </SettingRow>
            <SettingRow
              label="Bonus per turn (seconds)"
              description="Added to a player's bank each time their turn ends (like a chess increment). 0 = none."
            >
              <NumberInput
                aria-label="Bonus per turn in seconds"
                w={120}
                min={0}
                max={3600}
                step={5}
                disabled={!settings.chessClockEnabled}
                value={settings.chessClockIncrementSeconds}
                onChange={(value) =>
                  handlers.updateSettings({
                    chessClockIncrementSeconds: clampInt(value, 0, 3600, 0),
                  })
                }
              />
            </SettingRow>
            {gameId && (
              <SettingRow
                label="Current game"
                description="Start (or restart) the clock in this game with the values above. Every player gets a full bank from now."
              >
                <CurrentGameClockControls
                  gameId={gameId}
                  minutes={settings.chessClockMinutes}
                  incrementSeconds={settings.chessClockIncrementSeconds}
                />
              </SettingRow>
            )}
          </SettingGroup>

          <SettingGroup label="Reaction windows">
            <SettingRow
              label="Window length (seconds)"
              description="How long the game waits for reactions such as Sabotage, Coup d'Etat, agenda riders or Salvage. The window always lasts this long, so nobody can tell who holds a card; the game passes on its own for players who have nothing to play. Applies to new games; use the button below for a game in progress (host only)."
            >
              <NumberInput
                aria-label="Reaction window length in seconds"
                w={120}
                min={2}
                max={30}
                value={settings.reactionWindowSeconds}
                onChange={(value) =>
                  handlers.updateSettings({
                    reactionWindowSeconds: clampInt(value, 2, 30, 4),
                  })
                }
              />
            </SettingRow>
            {gameId && (
              <SettingRow
                label="Current game"
                description="Use this length in the game in progress, starting with the next reaction window."
              >
                <CurrentGameReactionWindow
                  gameId={gameId}
                  seconds={settings.reactionWindowSeconds}
                />
              </SettingRow>
            )}
          </SettingGroup>

          <SettingGroup label="Map display">
            <SwitchRow
              label="Ownership overlays"
              description="Tint systems by the player who controls them."
              checked={settings.overlaysEnabled}
              onToggle={() => handlers.toggleOverlays()}
            />
            <SettingRow
              label="Control tokens"
              description="Ambiguous planets are empty or hold ground forces from more than one faction."
            >
              <SegmentedControl
                aria-label="Control tokens"
                value={settings.controlTokenDisplayMode}
                onChange={(value) =>
                  handlers.updateSettings({
                    controlTokenDisplayMode: value as ControlTokenDisplayMode,
                  })
                }
                data={[
                  { label: "Always", value: "always" },
                  { label: "If ambiguous", value: "ambiguous" },
                  { label: "If empty", value: "empty" },
                ]}
              />
            </SettingRow>
            <SwitchRow
              label="Grey out exhausted planets"
              description="Exhausted planets dim on the map."
              checked={settings.showExhaustedPlanets}
              onToggle={() => handlers.toggleShowExhaustedPlanets()}
            />
            <SwitchRow
              label="Accessible colours"
              description="Blue, green, purple, yellow, red, pink, black, light gray, in seat order. Extra players keep their own colours."
              checked={settings.accessibleColors}
              onToggle={() => handlers.toggleAccessibleColors()}
            />
          </SettingGroup>


        </Tabs.Panel>

        <Tabs.Panel value="player-areas" className={styles.panel}>
          <SettingGroup label="Data groups">
            <p className={styles.intro}>
              Choose which data groups appear in player area cards.
            </p>
            {PLAYER_AREA_TOGGLES.map(({ key, label, description }) => (
              <SwitchRow
                key={key}
                label={label}
                description={description}
                checked={settings[key]}
                onToggle={(checked) => handlers.updateSettings({ [key]: checked })}
              />
            ))}
          </SettingGroup>
        </Tabs.Panel>

        <Tabs.Panel value="sound" className={styles.panel}>
          <SettingGroup label="Volume">
            <AudioSettingsPanel />
          </SettingGroup>
        </Tabs.Panel>
      </Tabs>
    </AppModal>
  );
}

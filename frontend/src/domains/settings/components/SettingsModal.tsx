import { useId, type ReactNode } from "react";
import { NumberInput, Switch, SegmentedControl, Tabs } from "@/ds";
import { useSettingsStore } from "@/state/appStore";
import { toggleVariant, variantModules } from "@/entities/data/officialSources";
import { AppModal } from "@/shared/ui/AppModal";
import type { ControlTokenDisplayMode } from "@/entities/game/controlTokenDisplay";
import { CurrentGameClockControls } from "@/domains/clock/CurrentGameClockControls";
import {
  CurrentGameQuickJitter,
  CurrentGameQuickWindows,
  CurrentGameReactionWindow,
} from "./CurrentGameReactionWindow";
import { AudioSettingsPanel } from "@/shared/audio/AudioSettingsPanel";
import styles from "./SettingsModal.module.css";

/*
 * Ustawienia w pięciu zakładkach:
 *   - Game: to, co idzie do backendu przy tworzeniu NOWEJ partii (zegar, okna reakcji)
 *     + wiersze „Current game” dla trwającej partii (host);
 *   - Variants: moduły fanowskich talii i errat (też dla nowej partii);
 *   - Display: mapa i karty graczy (tylko ten komputer);
 *   - Sound: głośność;
 *   - Testing: przyspieszenia i gesty God-Mode omijające reguły.
 */

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
    label: "Command tokens",
    description: "Tactic, fleet and strategy pool counts.",
  },
  {
    key: "showPlayerAreaArmyStrength",
    label: "Army strength",
    description: "Space and ground strength summary with the player's rank at the table.",
  },
  {
    key: "showPlayerAreaUnitUpgrades",
    label: "Unit upgrades",
    description: "Mark units the player has already upgraded (II versions).",
  },
  {
    key: "showPlayerAreaTotalSpend",
    label: "Total resources and influence",
    description: "Add a column with the plain sum of all planets. The optimal split is always shown.",
  },
  {
    key: "showPlayerAreaReinforcements",
    label: "Faction tokens in reinforcements",
    description: "Sleeper, wormhole, breach and galvanize tokens the player can still place.",
  },
  {
    key: "showPlayerAreaFactionAbilities",
    label: "Faction abilities",
    description: "Faction abilities, faction technologies not yet researched and faction promissory notes.",
  },
  {
    key: "showPlayerAreaNeighborship",
    label: "Neighbours",
    description: "Icons of the factions this player is adjacent to (only neighbours can trade).",
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
    <AppModal opened={opened} onClose={onClose} title="Settings" size={660} centered>
      <Tabs defaultValue="game">
        <Tabs.List className={styles.tabList}>
          <Tabs.Tab value="game" className={styles.tab}>
            Game
          </Tabs.Tab>
          <Tabs.Tab value="variants" className={styles.tab}>
            Variants
          </Tabs.Tab>
          <Tabs.Tab value="display" className={styles.tab}>
            Display
          </Tabs.Tab>
          <Tabs.Tab value="sound" className={styles.tab}>
            Sound
          </Tabs.Tab>
          <Tabs.Tab value="testing" className={styles.tab}>
            Testing
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="game" className={styles.panel}>
          <p className={styles.intro}>
            Used when a new game is created. A game in progress keeps its own setup; where it
            can still be changed, use the Current game rows (host only).
          </p>

          <SettingGroup label="Chess clock">
            <SwitchRow
              label="Player clocks"
              description="Each player gets a time bank. Only the player who has to decide right now (their turn, a vote, a reaction) spends it."
              checked={settings.chessClockEnabled}
              onToggle={(checked) =>
                handlers.updateSettings({ chessClockEnabled: checked })
              }
            />
            <SettingRow
              label="Time per player (minutes)"
              description="Time bank for the whole game."
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
              description="Added to the bank whenever the player ends a turn, like a chess increment. 0 = no bonus."
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
                description="Start or restart the clock in this game with the values above. Every player gets a full bank from now."
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
              description="How long everyone gets to react (Sabotage, agenda riders, Salvage…). Every window lasts the full time, so waiting never reveals who holds a card; players with nothing to play pass automatically."
            >
              <NumberInput
                aria-label="Reaction window length in seconds"
                w={120}
                min={2}
                max={60}
                value={settings.reactionWindowSeconds}
                onChange={(value) =>
                  handlers.updateSettings({
                    reactionWindowSeconds: clampInt(value, 2, 60, 20),
                  })
                }
              />
            </SettingRow>
            {gameId && (
              <SettingRow
                label="Current game"
                description="Use this length in this game, starting with the next reaction window."
              >
                <CurrentGameReactionWindow
                  gameId={gameId}
                  seconds={settings.reactionWindowSeconds}
                />
              </SettingRow>
            )}
            {gameId && (
              <SettingRow
                label="Quick windows"
                description="End a window once everyone has passed. With a bluff range the end comes at a random moment, so an early end does not show that nobody had a fitting card. New games start with it on."
              >
                <CurrentGameQuickWindows gameId={gameId} />
              </SettingRow>
            )}
            {gameId && (
              <SettingRow
                label="Bluff range"
                description="With Quick windows on, every automatic pass lands at a random private moment between 25% and 100% of this range, and the window ends at the last one - never instantly."
              >
                <CurrentGameQuickJitter gameId={gameId} />
              </SettingRow>
            )}
          </SettingGroup>
        </Tabs.Panel>

        <Tabs.Panel value="variants" className={styles.panel}>
          <p className={styles.intro}>
            Optional fan-made decks and errata. Chosen modules apply to the next new game; a game
            in progress keeps its decks. Two modules that replace the same deck cannot be on at
            once.
          </p>
          <SettingGroup label="Fan decks and errata">
            {variantModules().map((module) => (
              <SwitchRow
                key={module.id}
                label={module.name}
                description={module.description}
                checked={settings.gameVariants.includes(module.id)}
                onToggle={(checked) =>
                  handlers.updateSettings({
                    gameVariants: toggleVariant(settings.gameVariants, module, checked),
                  })
                }
              />
            ))}
          </SettingGroup>
        </Tabs.Panel>

        <Tabs.Panel value="display" className={styles.panel}>
          <SettingGroup label="Map">
            <SwitchRow
              label="Controller colours"
              description="Tint each system in the colour of the player who controls it."
              checked={settings.overlaysEnabled}
              onToggle={() => handlers.toggleOverlays()}
            />
            <SettingRow
              label="Control tokens"
              description="When to draw control tokens on planets. Ambiguous = the planet is empty or holds ground forces of more than one player."
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
              label="Dim exhausted planets"
              description="Exhausted planets are greyed out on the map."
              checked={settings.showExhaustedPlanets}
              onToggle={() => handlers.toggleShowExhaustedPlanets()}
            />
            <SwitchRow
              label="Colour-blind friendly colours"
              description="Swap player colours for an easy-to-tell set (blue, green, purple, yellow, red, pink, black, light grey) in seat order. Players beyond eight keep their own colours."
              checked={settings.accessibleColors}
              onToggle={() => handlers.toggleAccessibleColors()}
            />
          </SettingGroup>

          <SettingGroup label="Player cards">
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

        <Tabs.Panel value="testing" className={styles.panel}>
          <p className={styles.intro}>
            For testing and fixing a game. God-Mode options bypass the rules — keep them off in
            a normal game.
          </p>
          <SettingGroup label="Speed">
            <SwitchRow
              label="Fast mode"
              description="Skip the opening intro, the phase transition sweep and key-moment cinematics. Rules are unaffected."
              checked={settings.adminFastMode}
              onToggle={(checked) =>
                handlers.updateSettings({ adminFastMode: checked })
              }
            />
          </SettingGroup>
          <SettingGroup label="God-Mode">
            <SwitchRow
              label="Free unit dragging"
              description="Drag units anywhere on the map. When off, units can only be dragged into the active system as a checked tactical move."
              checked={settings.freeUnitDrag}
              onToggle={(checked) =>
                handlers.updateSettings({ freeUnitDrag: checked })
              }
            />
            <SwitchRow
              label="Look inside decks"
              description="Clicking a face-down deck (action cards, agendas, exploration, objectives, relics) shows the cards in it. When off, a deck only shows how many cards are left; discard piles are always open."
              checked={settings.browseDecks}
              onToggle={(checked) =>
                handlers.updateSettings({ browseDecks: checked })
              }
            />
            <SwitchRow
              label="Skip buttons"
              description="Adds Skip phase to the turn panel (moves on, ignoring passes, open windows and strategy card picks) and Skip setup (random secret objectives) to the setup screen."
              checked={settings.skipPhases}
              onToggle={(checked) =>
                handlers.updateSettings({ skipPhases: checked })
              }
            />
          </SettingGroup>
        </Tabs.Panel>
      </Tabs>
    </AppModal>
  );
}

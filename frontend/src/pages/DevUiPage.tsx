/**
 * /dev/ui — Galeria komponentów i okien do inspekcji wizualnej.
 *
 * Otwórz: http://localhost:5173/dev/ui (w trybie dev bez backendu).
 * Cel: wyłapać brzydkie okna, niespójności UI i interakcje komponentów
 * BEZ ręcznego grania w całą partię.
 *
 * Wszystkie propsy z lokalnych makiet — zero importu stanu gry / API.
 */

import { useState } from "react";
import {
  Button,
  ActionIcon,
  Stack,
  Group,
  Text,
  Title,
  Paper,
  Alert,
  Divider,
  Modal,
  Tooltip,
  Select,
  TextInput,
  NumberInput,
  Switch,
  Tabs,
  Loader,
} from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { DecisionFrame } from "@/shared/ui/DecisionFrame";
import { Surface } from "@/shared/ui/Surface";
import { StatusInfo } from "@/shared/ui/StatusInfo/StatusInfo";
import {
  IconAlertTriangle,
  IconInfoCircle,
  IconX,
  IconSword,
  IconCards,
  IconBolt,
  IconCrown,
  IconFlask,
  IconTarget,
  IconArrowsExchange,
  IconUserStar,
  IconHourglass,
  IconSettings,
  IconBug,
  IconEye,
  IconChevronsRight,
  IconHandStop,
  IconStar,
} from "@tabler/icons-react";
import styles from "./DevUiPage.module.css";

// ─── Mock helper badge (ds doesn't export Badge, so a simple span) ─────────
function Chip({
  children,
  color = "default",
}: {
  children: React.ReactNode;
  color?: "default" | "blue" | "green" | "red" | "yellow" | "violet";
}) {
  const colors: Record<string, string> = {
    default: "var(--ds-h22)",
    blue: "rgba(34,139,230,.25)",
    green: "rgba(64,192,87,.25)",
    red: "rgba(250,82,82,.25)",
    yellow: "rgba(252,196,25,.2)",
    violet: "rgba(121,80,242,.25)",
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: "var(--ds-ink)",
        background: colors[color],
        border: "1px solid var(--ds-h22)",
        borderRadius: 4,
        padding: "2px 8px",
      }}
    >
      {children}
    </span>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────
function Section({
  id,
  title,
  note,
  children,
}: {
  id: string;
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className={styles.section}>
      <div className={styles.sectionHead}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        {note && <span className={styles.sectionNote}>{note}</span>}
      </div>
      {children}
    </section>
  );
}

function Tile({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.tile}>
      <div className={styles.tileLabel}>{label}</div>
      {children}
    </div>
  );
}

// ─── Modal launcher (opens AppModal on click) ────────────────────────────
function ModalLauncher({
  label,
  icon,
  children,
}: {
  label: string;
  icon?: React.ReactNode;
  children: (opened: boolean, onClose: () => void) => React.ReactNode;
}) {
  const [opened, setOpened] = useState(false);
  return (
    <>
      <Button
        variant="default"
        size="sm"
        leftSection={icon}
        onClick={() => setOpened(true)}
        style={{ minWidth: 160 }}
      >
        {label}
      </Button>
      {children(opened, () => setOpened(false))}
    </>
  );
}

// ─── Inline notice banner (static) ───────────────────────────────────────
function NoticeBanner({
  kind,
  title,
  body,
}: {
  kind: "error" | "info";
  title: string;
  body: string;
}) {
  const isError = kind === "error";
  const accent = isError ? "239, 83, 80" : "100, 181, 246";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 15,
        padding: "13px 18px 13px 20px",
        border: "1px solid rgba(255,255,255,0.1)",
        borderLeft: `4px solid rgb(${accent} / 0.9)`,
        borderRadius: "var(--ds-radius-overlay, 8px)",
        background: `linear-gradient(180deg, rgb(${accent} / 0.08), transparent 60%), rgb(12 12 14 / 0.94)`,
        backdropFilter: "blur(7px)",
        maxWidth: 580,
      }}
    >
      <span style={{ color: `rgb(${accent} / 0.9)`, display: "flex", flexShrink: 0 }}>
        {isError ? <IconAlertTriangle size={20} /> : <IconInfoCircle size={20} />}
      </span>
      <span style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
        <b
          style={{
            fontFamily: "var(--ds-font-display)",
            fontSize: "var(--ds-fz-md)",
            fontWeight: 600,
            color: "var(--ds-ink-hi)",
          }}
        >
          {title}
        </b>
        <span style={{ fontSize: "var(--ds-fz-sm)", color: "var(--ds-ink)" }}>{body}</span>
      </span>
      <button
        type="button"
        style={{
          marginLeft: "auto",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 28,
          height: 28,
          border: "1px solid transparent",
          borderRadius: 6,
          background: "transparent",
          color: "var(--ds-ink-lo)",
          cursor: "pointer",
        }}
        aria-label="Dismiss"
      >
        <IconX size={18} />
      </button>
    </div>
  );
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────
const SECTIONS = [
  { id: "ds-tokens", label: "Design Tokens" },
  { id: "ds-buttons", label: "Buttons" },
  { id: "ds-forms", label: "Forms" },
  { id: "ds-surfaces", label: "Surfaces" },
  { id: "ds-overlays", label: "Overlays / Modals" },
  { id: "game-decision", label: "Decision Frames" },
  { id: "game-notices", label: "Notices & Alerts" },
  { id: "game-status", label: "Status Chips" },
  { id: "game-modals", label: "Game Modals" },
  { id: "game-tabs", label: "Tabs & Nav" },
  { id: "edge-cases", label: "Edge Cases" },
];

export function DevUiPage() {
  return (
    <div className={styles.root}>
      {/* ── Sticky header ── */}
      <header className={styles.header}>
        <span className={styles.logo}>Custodian Engine</span>
        <span className={styles.badge}>DEV / UI</span>
        <nav className={styles.nav} aria-label="Sections">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              className={styles.navLink}
              onClick={() =>
                document.getElementById(s.id)?.scrollIntoView({ behavior: "smooth" })
              }
            >
              {s.label}
            </button>
          ))}
        </nav>
      </header>

      <main className={styles.content}>
        {/* ══════════════════════════════════════════════════════════════
            1. DESIGN TOKENS
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="ds-tokens"
          title="Design Tokens"
          note="Palette, ink, surfaces, signals — tokens.css"
        >
          <div className={styles.grid}>
            <Tile label="Ink steps">
              <Group gap="sm">
                {(
                  [
                    ["var(--ds-ink-hi)", "ink-hi (titles)"],
                    ["var(--ds-ink)", "ink (default)"],
                    ["var(--ds-ink-lo)", "ink-lo (labels)"],
                  ] as const
                ).map(([c, l]) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        display: "inline-block",
                        width: 16,
                        height: 16,
                        borderRadius: 3,
                        background: c,
                      }}
                    />
                    <Text size="sm" style={{ color: c }}>
                      {l}
                    </Text>
                  </div>
                ))}
              </Group>
            </Tile>

            <Tile label="Surfaces">
              {(
                [
                  ["var(--ds-page)", "--ds-page"],
                  ["var(--ds-deck)", "--ds-deck"],
                  ["var(--ds-field)", "--ds-field"],
                  ["var(--ds-socket)", "--ds-socket"],
                ] as const
              ).map(([c, l]) => (
                <div
                  key={l}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      display: "inline-block",
                      width: 32,
                      height: 20,
                      borderRadius: 4,
                      background: c,
                      border: "1px solid rgba(255,255,255,0.08)",
                    }}
                  />
                  <Text size="xs" c="dimmed">
                    {l}
                  </Text>
                </div>
              ))}
            </Tile>

            <Tile label="Signal colours">
              {(
                [
                  ["rgb(var(--ds-sig-danger))", "danger"],
                  ["rgb(var(--ds-sig-warn))", "warn"],
                  ["rgb(var(--ds-sig-ok))", "ok"],
                  ["rgb(var(--ds-sig-prop))", "prop"],
                  ["rgb(var(--ds-sig-tech))", "tech"],
                ] as const
              ).map(([c, l]) => (
                <div
                  key={l}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      display: "inline-block",
                      width: 32,
                      height: 20,
                      borderRadius: 4,
                      background: c,
                    }}
                  />
                  <Text size="xs" c="dimmed">
                    {l}
                  </Text>
                </div>
              ))}
            </Tile>

            <Tile label="Radius ladder">
              <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
                {(["xs", "sm", "md", "lg", "xl"] as const).map((r) => (
                  <div
                    key={r}
                    style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}
                  >
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        background: "var(--ds-field)",
                        border: "1px solid var(--ds-h22)",
                        borderRadius: `var(--ds-radius-${r})`,
                      }}
                    />
                    <Text size="xs" c="dimmed">
                      {r}
                    </Text>
                  </div>
                ))}
              </div>
            </Tile>

            <Tile label="Hairline alpha ladder">
              <div style={{ display: "flex", gap: 8 }}>
                {(["h08", "h14", "h22", "h36", "h56"] as const).map((h) => (
                  <div
                    key={h}
                    style={{
                      width: 36,
                      height: 36,
                      background: `var(--ds-${h})`,
                      border: "1px solid rgba(255,255,255,0.3)",
                      borderRadius: 4,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Text size="xs" c="dimmed" style={{ fontSize: 9 }}>
                      {h}
                    </Text>
                  </div>
                ))}
              </div>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            2. BUTTONS
        ══════════════════════════════════════════════════════════════ */}
        <Section id="ds-buttons" title="Buttons" note="All variants, sizes, states">
          <div className={styles.grid}>
            <Tile label="Variants">
              <Group gap="sm" wrap="wrap">
                <Button variant="filled">Filled</Button>
                <Button variant="light">Light</Button>
                <Button variant="default">Default</Button>
                <Button variant="subtle">Subtle</Button>
              </Group>
            </Tile>

            <Tile label="Sizes">
              <Group gap="sm" align="center" wrap="wrap">
                <Button size="xs">xs</Button>
                <Button size="sm">sm</Button>
                <Button size="md">md</Button>
                <Button size="lg">lg</Button>
                <Button size="compact-xs">compact-xs</Button>
                <Button size="compact-sm">compact-sm</Button>
              </Group>
            </Tile>

            <Tile label="States">
              <Group gap="sm" wrap="wrap">
                <Button disabled>Disabled</Button>
                <Button loading>Loading</Button>
                <Button variant="filled" color="red">
                  Danger
                </Button>
                <Button variant="filled" color="green">
                  Success
                </Button>
                <Button variant="filled" color="yellow">
                  Warning
                </Button>
              </Group>
            </Tile>

            <Tile label="With icons">
              <Group gap="sm" wrap="wrap">
                <Button leftSection={<IconSword size={14} />}>Attack</Button>
                <Button leftSection={<IconFlask size={14} />} variant="light">
                  Research
                </Button>
                <Button
                  leftSection={<IconHandStop size={14} />}
                  rightSection={<IconChevronsRight size={14} />}
                  variant="default"
                >
                  Pass
                </Button>
              </Group>
            </Tile>

            <Tile label="Action icons">
              <Group gap="sm">
                <Tooltip label="Settings">
                  <ActionIcon variant="subtle" aria-label="Settings">
                    <IconSettings size={18} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Info">
                  <ActionIcon variant="light" aria-label="Info">
                    <IconInfoCircle size={18} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Delete">
                  <ActionIcon variant="filled" color="red" aria-label="Delete">
                    <IconX size={18} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            3. FORMS
        ══════════════════════════════════════════════════════════════ */}
        <Section id="ds-forms" title="Forms" note="Inputs, selects, switches">
          <div className={styles.grid}>
            <Tile label="TextInput">
              <Stack gap="xs" style={{ width: 240 }}>
                <TextInput label="Player name" placeholder="e.g. Sarween Tools" />
                <TextInput label="With error" error="This field is required" placeholder="…" />
                <TextInput label="Disabled" disabled defaultValue="Locked value" />
              </Stack>
            </Tile>

            <Tile label="NumberInput">
              <Stack gap="xs" style={{ width: 160 }}>
                <NumberInput label="Trade goods" defaultValue={3} min={0} max={10} />
                <NumberInput label="Command tokens" defaultValue={0} min={0} max={16} />
              </Stack>
            </Tile>

            <Tile label="Select">
              <Stack gap="xs" style={{ width: 220 }}>
                <Select
                  label="Faction"
                  placeholder="Pick one"
                  data={[
                    "Arborec",
                    "Barony of Letnev",
                    "Clan of Saar",
                    "Embers of Muaat",
                    "Emirates of Hacan",
                    "Federation of Sol",
                    "Ghosts of Creuss",
                    "L1Z1X Mindnet",
                    "Mentak Coalition",
                    "Naalu Collective",
                  ]}
                />
                <Select
                  label="Phase"
                  defaultValue="action"
                  data={[
                    { value: "strategy", label: "Strategy Phase" },
                    { value: "action", label: "Action Phase" },
                    { value: "status", label: "Status Phase" },
                    { value: "agenda", label: "Agenda Phase" },
                  ]}
                />
              </Stack>
            </Tile>

            <Tile label="Switches">
              <Stack gap="sm">
                <Switch label="God Mode" defaultChecked />
                <Switch label="Reaction notifications" />
                <Switch label="Disabled option" disabled />
              </Stack>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            4. SURFACES
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="ds-surfaces"
          title="Surfaces"
          note="Paper, Surface (grid/circle patterns, corner accents)"
        >
          <div className={styles.grid}>
            <Tile label="Paper">
              <Paper p="md" withBorder style={{ width: 200 }}>
                <Text size="sm">Standard paper with border</Text>
              </Paper>
            </Tile>

            <Tile label="Paper — shadow">
              <Paper p="md" shadow="lg" style={{ width: 200 }}>
                <Text size="sm">Paper with lg shadow</Text>
              </Paper>
            </Tile>

            <Tile label="Surface — no pattern">
              <Surface p="md" style={{ width: 200 }}>
                <Text size="sm">Plain surface</Text>
              </Surface>
            </Tile>

            <Tile label="Surface — grid pattern">
              <Surface pattern="grid" p="md" style={{ width: 200, minHeight: 80 }}>
                <Text size="sm">Grid background</Text>
              </Surface>
            </Tile>

            <Tile label="Surface — circle pattern">
              <Surface pattern="circle" p="md" style={{ width: 200, minHeight: 80 }}>
                <Text size="sm">Circle background</Text>
              </Surface>
            </Tile>

            <Tile label="Surface — corner accents">
              <Surface
                cornerAccents
                p="md"
                style={{ width: 200, minHeight: 100, position: "relative" }}
              >
                <Text size="sm">Corner accents</Text>
              </Surface>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            5. OVERLAYS / MODALS (DS layer)
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="ds-overlays"
          title="Overlays & Modals (DS)"
          note="Modal, Drawer, Tooltip, Popover — base primitives"
        >
          <div className={styles.launchGrid}>
            <ModalLauncher label="Modal — small" icon={<IconEye size={14} />}>
              {(opened, onClose) => (
                <Modal opened={opened} onClose={onClose} title="Small modal" size="sm">
                  <Stack gap="sm">
                    <Text size="sm">Basic ds Modal at size="sm".</Text>
                    <Text size="sm" c="dimmed">
                      Body text with a secondary line.
                    </Text>
                    <Group justify="flex-end">
                      <Button variant="default" onClick={onClose}>
                        Close
                      </Button>
                      <Button>Confirm</Button>
                    </Group>
                  </Stack>
                </Modal>
              )}
            </ModalLauncher>

            <ModalLauncher label="Modal — large" icon={<IconEye size={14} />}>
              {(opened, onClose) => (
                <Modal opened={opened} onClose={onClose} title="Large modal (800 px)" size={800}>
                  <Stack gap="sm">
                    <Text size="sm">
                      This tests layout at wider widths, e.g. the transaction or battle overlay.
                    </Text>
                    <Divider />
                    <Text size="sm" c="dimmed">
                      Left column content / right column content can be placed side-by-side.
                    </Text>
                    <Group justify="flex-end">
                      <Button variant="default" onClick={onClose}>
                        Close
                      </Button>
                    </Group>
                  </Stack>
                </Modal>
              )}
            </ModalLauncher>

            <ModalLauncher label="AppModal — minimizable" icon={<IconStar size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title="Minimizable window"
                  minimizable="Demo window"
                  floating
                  size={480}
                >
                  <Stack gap="sm">
                    <Text size="sm">
                      Click the minus icon (top-right of the title bar) to minimise. A pill
                      appears at the bottom; click to restore.
                    </Text>
                    <Group justify="flex-end">
                      <Button variant="default" onClick={onClose}>
                        Close
                      </Button>
                    </Group>
                  </Stack>
                </AppModal>
              )}
            </ModalLauncher>

            <ModalLauncher label="AppModal — long content" icon={<IconEye size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title="Scrollable body"
                  floating
                  size={440}
                >
                  <Stack gap="xs" style={{ padding: "0 0 8px" }}>
                    {Array.from({ length: 30 }, (_, i) => (
                      <Text key={i} size="sm">
                        Line {i + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                      </Text>
                    ))}
                    <Group justify="flex-end" mt="sm">
                      <Button variant="default" onClick={onClose}>
                        Close
                      </Button>
                    </Group>
                  </Stack>
                </AppModal>
              )}
            </ModalLauncher>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            6. DECISION FRAMES
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="game-decision"
          title="Decision Frames"
          note="DecisionFrame — the universal player-decision widget"
        >
          <div className={styles.grid}>
            <Tile label="Standalone — Skip/Use">
              <div className={styles.frame} style={{ width: 380 }}>
                <DecisionFrame
                  ariaLabel="Action card: Tactical Bombardment"
                  kind="Action card"
                  title="Tactical Bombardment"
                  text="After another player's ground forces are destroyed during an invasion combat on a planet that contains a space dock, you may destroy that space dock."
                  onUse={() => alert("Used!")}
                  useLabel="Play card"
                  onSkip={() => alert("Skipped!")}
                />
              </div>
            </Tile>

            <Tile label="Required — no skip">
              <div className={styles.frame} style={{ width: 340 }}>
                <DecisionFrame
                  ariaLabel="Choose target"
                  kind="Tactical"
                  title="Choose system to activate"
                  required
                  text="You must choose a system to activate. Click a highlighted system on the map."
                  onUse={() => alert("Confirmed!")}
                  useLabel="Confirm"
                  canUse={false}
                />
              </div>
            </Tile>

            <Tile label="With warnings & notes">
              <div className={styles.frame} style={{ width: 360 }}>
                <DecisionFrame
                  ariaLabel="Technology research"
                  kind="Technology"
                  title="Neural Motivator"
                  text="At the start of the strategy phase, draw 1 action card."
                  notes={["Costs 1 technology prerequisite (Biotic).", "Auto: skip if already researched."]}
                  warnings={["You are exhausted. This action is not available this round."]}
                  onUse={() => alert("Research!")}
                  useLabel="Research"
                  canUse={false}
                  onSkip={() => alert("Pass!")}
                />
              </div>
            </Tile>

            <Tile label="Queue counter (+3 more)">
              <div className={styles.frame} style={{ width: 340 }}>
                <DecisionFrame
                  ariaLabel="Reaction: Gravity Drive"
                  kind="Faction ability"
                  title="Gravity Drive"
                  queued={3}
                  text="During the movement step of your tactical action, apply +1 to the move value of 1 of your ships."
                  onUse={() => alert("Use!")}
                  onSkip={() => alert("Skip!")}
                />
              </div>
            </Tile>

            <Tile label="Long text (collapsed)">
              <div className={styles.frame} style={{ width: 360 }}>
                <DecisionFrame
                  ariaLabel="Long text test"
                  kind="Relic"
                  title="Shard of the Throne"
                  text={
                    "VICTORY POINT\n\n" +
                    "When you gain this card, gain 1 victory point. While you have 1 or more victory points from this card, " +
                    "other players can steal this card during their tactical actions. If this card is stolen, " +
                    "the new owner gains 1 victory point and you lose 1 victory point. " +
                    "At the end of the game, if you hold this card, gain 1 additional victory point for each " +
                    "time the card has changed hands (maximum of 3). " +
                    "This is a very long card text to test the more/less toggle behaviour. " +
                    "Make sure the collapse works without clipping content and that the button is accessible. " +
                    "The measurement threshold is LONG_TEXT = 420 characters."
                  }
                  onUse={() => alert("Claim!")}
                  useLabel="Claim relic"
                  onSkip={() => alert("Skip!")}
                />
              </div>
            </Tile>

            <Tile label="Embedded (inside AppModal)">
              <ModalLauncher label="Open embedded frame" icon={<IconBolt size={14} />}>
                {(opened, onClose) => (
                  <AppModal
                    opened={opened}
                    onClose={onClose}
                    title={undefined}
                    floating
                    withCloseButton={false}
                    size={460}
                  >
                    <DecisionFrame
                      embedded
                      ariaLabel="Action card: Reflections"
                      kind="Action card"
                      title="Reflections"
                      text="At the end of the status phase, you may redistribute your command tokens."
                      onUse={() => { alert("Played!"); onClose(); }}
                      useLabel="Play card"
                      onSkip={onClose}
                      skipLabel="Cancel"
                    />
                  </AppModal>
                )}
              </ModalLauncher>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            7. NOTICES & ALERTS
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="game-notices"
          title="Notices & Alerts"
          note="PhaseNoticePanel styles, ds Alert variants"
        >
          <Stack gap="md">
            <div className={styles.noticePreview}>
              <NoticeBanner
                kind="error"
                title="Action not allowed"
                body="You cannot pass before playing your strategy card this action phase."
              />
              <NoticeBanner
                kind="info"
                title="Notice"
                body="All players must resolve secondary before the active player can proceed."
              />
            </div>

            <Divider />
            <Text size="sm" fw={500} c="dimmed" mt={-6} mb={4}>ds Alert</Text>

            <div className={styles.grid}>
              {(
                [
                  ["info", "Info alert — neutral notification"],
                  ["warning", "Warning — important caution"],
                  ["error", "Error — invalid state or failed action"],
                  ["success", "Success — action resolved correctly"],
                ] as const
              ).map(([color, msg]) => (
                <Alert key={color} color={color} title={color} style={{ maxWidth: 320 }}>
                  {msg}
                </Alert>
              ))}
            </div>
          </Stack>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            8. STATUS CHIPS
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="game-status"
          title="Status Chips"
          note="StatusInfo wrapper — click to open details card"
        >
          <div className={styles.grid}>
            <Tile label="Speaker (clickable)">
              <StatusInfo status="speaker">
                <Chip color="yellow">
                  <IconCrown size={12} />
                  Speaker
                </Chip>
              </StatusInfo>
            </Tile>

            <Tile label="Active (clickable)">
              <StatusInfo status="active">
                <Chip color="green">
                  <IconBolt size={12} />
                  Active
                </Chip>
              </StatusInfo>
            </Tile>

            <Tile label="Passed (clickable)">
              <StatusInfo status="passed">
                <Chip color="default">
                  <IconHandStop size={12} />
                  Passed
                </Chip>
              </StatusInfo>
            </Tile>

            <Tile label="Tyrant (clickable)">
              <StatusInfo status="tyrant">
                <Chip color="red">
                  <IconUserStar size={12} />
                  Tyrant
                </Chip>
              </StatusInfo>
            </Tile>

            <Tile label="Naalu 0-token (clickable)">
              <StatusInfo status="initiativeZero">
                <Chip color="violet">0</Chip>
              </StatusInfo>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            9. GAME MODALS (launcher gallery)
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="game-modals"
          title="Game Modals"
          note="Real game windows rendered with static mock data"
        >
          <div className={styles.launchGrid}>
            {/* ── ComponentUseModal mock ── */}
            <ModalLauncher label="Action card window" icon={<IconCards size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title={undefined}
                  floating
                  withCloseButton={false}
                  size={480}
                >
                  <DecisionFrame
                    embedded
                    ariaLabel="Action card: Cyber Refit"
                    kind="Action card"
                    title="Cyber Refit"
                    text="Choose 1 of your non-fighter ships. Place 1 mech unit from your reinforcements on a planet you control in that ship's system."
                    notes={["Auto: selects largest capacity ship."]}
                    onUse={() => { alert("Card played!"); onClose(); }}
                    useLabel="Play"
                    onSkip={onClose}
                    skipLabel="Cancel"
                  />
                </AppModal>
              )}
            </ModalLauncher>

            {/* ── Technology window ── */}
            <ModalLauncher label="Technology window" icon={<IconFlask size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title={undefined}
                  floating
                  withCloseButton={false}
                  size={480}
                >
                  <DecisionFrame
                    embedded
                    ariaLabel="Technology: Sling Relay"
                    kind="Technology"
                    title="Sling Relay"
                    text="At the start of your turn, you may produce 1 unit using your space dock in any system."
                    notes={["Passive — no activation required."]}
                    warnings={["Already researched. This technology is inactive."]}
                    canUse={false}
                    onUse={() => { alert("Tech used!"); onClose(); }}
                    useLabel="Activate"
                    onSkip={onClose}
                    skipLabel="Close"
                  />
                </AppModal>
              )}
            </ModalLauncher>

            {/* ── Leader / Agent window ── */}
            <ModalLauncher label="Leader window" icon={<IconUserStar size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title={undefined}
                  floating
                  withCloseButton={false}
                  size={480}
                >
                  <DecisionFrame
                    embedded
                    ariaLabel="Leader: Magmus (Agent)"
                    kind="Leader · Agent"
                    title="Magmus"
                    text="At the start of your turn: You may exhaust this card to allow a friendly space dock to produce units regardless of the fleet pool limit."
                    notes={["AGENT — usable once per round.", "Auto: exhausts immediately."]}
                    onUse={() => { alert("Agent used!"); onClose(); }}
                    useLabel="Use agent"
                    onSkip={onClose}
                    skipLabel="Cancel"
                    secondary={{ label: "Unlock", onClick: () => alert("Unlocked!") }}
                  />
                </AppModal>
              )}
            </ModalLauncher>

            {/* ── Strategic action window ── */}
            <ModalLauncher label="Strategy primary" icon={<IconTarget size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title="Imperial — Primary"
                  floating
                  minimizable="Imperial Primary"
                  size={520}
                >
                  <Stack gap="sm">
                    <Text size="sm">
                      Score 1 public objective if you meet its requirements. Reveal a public
                      objective from the deck and place it face-up in the common play area.
                    </Text>
                    <Divider />
                    <Text size="sm" c="dimmed">
                      If you have Imperial Rider, you gain 1 VP automatically.
                    </Text>
                    <Group justify="flex-end" mt="xs">
                      <Button variant="default" onClick={onClose}>
                        Skip secondary
                      </Button>
                      <Button onClick={() => { alert("Imperial resolved!"); onClose(); }}>
                        Resolve
                      </Button>
                    </Group>
                  </Stack>
                </AppModal>
              )}
            </ModalLauncher>

            {/* ── Transaction window ── */}
            <ModalLauncher label="Transaction window" icon={<IconArrowsExchange size={14} />}>
              {(opened, onClose) => (
                <AppModal
                  opened={opened}
                  onClose={onClose}
                  title="Transaction"
                  floating
                  minimizable
                  size={1080}
                >
                  <Stack gap="md">
                    <Text size="sm" c="dimmed">
                      Sit down at the table with another player. Each of you puts down only your
                      own things — you see theirs once they put them on the table. The deal happens
                      when both of you are Ready.
                    </Text>
                    <div
                      style={{
                        display: "flex",
                        gap: 10,
                        flexWrap: "wrap",
                      }}
                    >
                      {["Sol", "Hacan", "Letnev", "Saar"].map((name) => (
                        <button
                          key={name}
                          type="button"
                          style={{
                            padding: "8px 16px",
                            border: "1px solid var(--ds-h22)",
                            borderRadius: 6,
                            background: "var(--ds-field)",
                            color: "var(--ds-ink)",
                            cursor: "pointer",
                            fontSize: 13,
                          }}
                        >
                          {name}
                        </button>
                      ))}
                    </div>
                    <Paper withBorder p="md">
                      <Text size="sm" c="dimmed">
                        [Trading table will appear here when a partner is selected]
                      </Text>
                    </Paper>
                    <Group justify="flex-end">
                      <Button variant="default" onClick={onClose}>
                        Close
                      </Button>
                    </Group>
                  </Stack>
                </AppModal>
              )}
            </ModalLauncher>

            {/* ── KeyboardShortcuts ── */}
            <ModalLauncher label="Keyboard shortcuts" icon={<IconSettings size={14} />}>
              {(opened, onClose) => (
                <Modal opened={opened} onClose={onClose} title="Keyboard shortcuts" size={560}>
                  <Stack gap="xs">
                    {[
                      ["M", "Toggle map fullscreen"],
                      ["T", "Open Technology overlay"],
                      ["Escape", "Close current overlay / deselect"],
                      ["Enter", "Confirm decision"],
                      ["Space", "Pass turn (action phase)"],
                      ["/", "Open search"],
                      ["G", "Toggle God Mode panel"],
                    ].map(([key, desc]) => (
                      <Group key={key} justify="space-between">
                        <Text size="sm">{desc}</Text>
                        <kbd
                          style={{
                            fontFamily: "var(--ds-font-data)",
                            fontSize: 12,
                            background: "var(--ds-field)",
                            border: "1px solid var(--ds-h22)",
                            borderRadius: 4,
                            padding: "2px 7px",
                            color: "var(--ds-ink-hi)",
                          }}
                        >
                          {key}
                        </kbd>
                      </Group>
                    ))}
                    <Group justify="flex-end" mt="sm">
                      <Button variant="default" onClick={onClose}>
                        Close
                      </Button>
                    </Group>
                  </Stack>
                </Modal>
              )}
            </ModalLauncher>

            {/* ── Bug report ── */}
            <ModalLauncher label="Bug report modal" icon={<IconBug size={14} />}>
              {(opened, onClose) => (
                <Modal opened={opened} onClose={onClose} title="Report a bug" size={520}>
                  <Stack gap="sm">
                    <TextInput label="Short description" placeholder="What went wrong?" />
                    <Select
                      label="Category"
                      defaultValue="ui"
                      data={[
                        { value: "ui", label: "UI / visual" },
                        { value: "rules", label: "Rules engine" },
                        { value: "network", label: "Network / sync" },
                        { value: "other", label: "Other" },
                      ]}
                    />
                    <Alert color="info" title="Console log">
                      Last 10 console entries will be attached automatically.
                    </Alert>
                    <Group justify="flex-end">
                      <Button variant="default" onClick={onClose}>
                        Cancel
                      </Button>
                      <Button
                        leftSection={<IconBug size={14} />}
                        onClick={() => { alert("Report sent!"); onClose(); }}
                      >
                        Send report
                      </Button>
                    </Group>
                  </Stack>
                </Modal>
              )}
            </ModalLauncher>

            {/* ── Victory screen preview ── */}
            <ModalLauncher label="Victory screen" icon={<IconCrown size={14} />}>
              {(opened, onClose) => (
                <Modal
                  opened={opened}
                  onClose={onClose}
                  title="Game over"
                  size={700}
                  withCloseButton
                >
                  <Stack gap="md" align="center" py="xl">
                    <IconCrown size={64} color="var(--ds-yellow-5)" />
                    <Title order={2} style={{ color: "var(--ds-ink-hi)" }}>
                      Federation of Sol wins!
                    </Title>
                    <Text c="dimmed">10 Victory Points — Round 6</Text>
                    <Divider style={{ width: "100%" }} />
                    <Text size="sm" c="dimmed">
                      Final scoreboard and epilogue chronicle appear here.
                    </Text>
                    <Group>
                      <Button variant="default" onClick={onClose}>
                        Back to menu
                      </Button>
                      <Button leftSection={<IconStar size={14} />}>View Chronicle</Button>
                    </Group>
                  </Stack>
                </Modal>
              )}
            </ModalLauncher>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            10. TABS & NAV
        ══════════════════════════════════════════════════════════════ */}
        <Section id="game-tabs" title="Tabs & Navigation" note="ds Tabs component, various configs">
          <div className={styles.grid}>
            <Tile label="Default tabs">
              <Tabs defaultValue="players" style={{ width: 500 }}>
                <Tabs.List>
                  <Tabs.Tab value="players">Players</Tabs.Tab>
                  <Tabs.Tab value="objectives">Objectives</Tabs.Tab>
                  <Tabs.Tab value="laws">Laws</Tabs.Tab>
                  <Tabs.Tab value="rules">Rules</Tabs.Tab>
                </Tabs.List>
                <Tabs.Panel value="players" pt="md">
                  <Text size="sm" c="dimmed">
                    Player list / initiative order goes here.
                  </Text>
                </Tabs.Panel>
                <Tabs.Panel value="objectives" pt="md">
                  <Text size="sm" c="dimmed">
                    Public objectives panel.
                  </Text>
                </Tabs.Panel>
                <Tabs.Panel value="laws" pt="md">
                  <Text size="sm" c="dimmed">
                    Active laws from agenda phase.
                  </Text>
                </Tabs.Panel>
                <Tabs.Panel value="rules" pt="md">
                  <Text size="sm" c="dimmed">
                    Rules browser embed.
                  </Text>
                </Tabs.Panel>
              </Tabs>
            </Tile>

            <Tile label="Phase stepper">
              <div
                style={{
                  display: "flex",
                  gap: 0,
                  borderRadius: 8,
                  overflow: "hidden",
                  border: "1px solid var(--ds-h22)",
                  width: "fit-content",
                }}
              >
                {["Strategy", "Action", "Status", "Agenda"].map((phase, i, arr) => (
                  <button
                    key={phase}
                    type="button"
                    style={{
                      padding: "8px 18px",
                      background: phase === "Action" ? "var(--ds-field)" : "var(--ds-deck)",
                      border: "none",
                      borderRight: i < arr.length - 1 ? "1px solid var(--ds-h14)" : "none",
                      color: phase === "Action" ? "var(--ds-ink-hi)" : "var(--ds-ink-lo)",
                      fontSize: 13,
                      fontWeight: phase === "Action" ? 600 : 400,
                      cursor: "pointer",
                    }}
                  >
                    {phase}
                  </button>
                ))}
              </div>
            </Tile>
          </div>
        </Section>

        {/* ══════════════════════════════════════════════════════════════
            11. EDGE CASES
        ══════════════════════════════════════════════════════════════ */}
        <Section
          id="edge-cases"
          title="Edge Cases"
          note="Long strings, 0 values, overflow, empty states"
        >
          <div className={styles.grid}>
            <Tile label="Very long faction name">
              <Paper p="sm" withBorder style={{ width: 220 }}>
                <Text size="sm" style={{ wordBreak: "break-word" }}>
                  Xxcha Kingdom of the Galactic Sovereignty Conclave of Eternal Council
                </Text>
              </Paper>
            </Tile>

            <Tile label="Zero-value resources">
              <Paper p="sm" withBorder>
                <Stack gap="xs">
                  {[
                    ["Trade Goods", 0],
                    ["Commodities", 0],
                    ["Command Tokens", 0],
                    ["Victory Points", 0],
                  ].map(([label, val]) => (
                    <Group key={String(label)} justify="space-between" style={{ width: 200 }}>
                      <Text size="sm" c="dimmed">
                        {label}
                      </Text>
                      <Text
                        size="sm"
                        style={{
                          color: val === 0 ? "var(--ds-ink-lo)" : "var(--ds-ink-hi)",
                          fontFamily: "var(--ds-font-data)",
                        }}
                      >
                        {val}
                      </Text>
                    </Group>
                  ))}
                </Stack>
              </Paper>
            </Tile>

            <Tile label="Max resources">
              <Paper p="sm" withBorder>
                <Stack gap="xs">
                  {[
                    ["Trade Goods", 10],
                    ["Commodities", 4],
                    ["Command Tokens", 16],
                    ["Victory Points", 14],
                  ].map(([label, val]) => (
                    <Group key={String(label)} justify="space-between" style={{ width: 200 }}>
                      <Text size="sm" c="dimmed">
                        {label}
                      </Text>
                      <Text
                        size="sm"
                        style={{
                          color: "var(--ds-ink-hi)",
                          fontFamily: "var(--ds-font-data)",
                        }}
                      >
                        {val}
                      </Text>
                    </Group>
                  ))}
                </Stack>
              </Paper>
            </Tile>

            <Tile label="Empty state">
              <Paper
                p="md"
                withBorder
                style={{
                  width: 280,
                  minHeight: 100,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Stack align="center" gap="xs">
                  <IconHourglass size={28} color="var(--ds-ink-lo)" />
                  <Text size="sm" c="dimmed">
                    No items yet
                  </Text>
                </Stack>
              </Paper>
            </Tile>

            <Tile label="Loader states">
              <Group gap="lg" align="center">
                <Stack align="center" gap="xs">
                  <Loader size="xs" />
                  <Text size="xs" c="dimmed">xs</Text>
                </Stack>
                <Stack align="center" gap="xs">
                  <Loader size="sm" />
                  <Text size="xs" c="dimmed">sm</Text>
                </Stack>
                <Stack align="center" gap="xs">
                  <Loader size="md" />
                  <Text size="xs" c="dimmed">md</Text>
                </Stack>
                <Stack align="center" gap="xs">
                  <Loader size="lg" />
                  <Text size="xs" c="dimmed">lg</Text>
                </Stack>
              </Group>
            </Tile>

            <Tile label="Button overflow (narrow container)">
              <div style={{ width: 140, overflow: "hidden", border: "1px dashed var(--ds-h22)", padding: 8, borderRadius: 6 }}>
                <Button fullWidth>Very long button label text</Button>
              </div>
            </Tile>

            <Tile label="Modal with no title">
              <ModalLauncher label="No-title modal">
                {(opened, onClose) => (
                  <AppModal
                    opened={opened}
                    onClose={onClose}
                    title={undefined}
                    floating
                    withCloseButton
                    size={360}
                  >
                    <Stack gap="sm">
                      <Alert color="warning" title="No title bar">
                        This modal has no title — only a close button.
                      </Alert>
                      <Group justify="flex-end">
                        <Button variant="default" onClick={onClose}>OK</Button>
                      </Group>
                    </Stack>
                  </AppModal>
                )}
              </ModalLauncher>
            </Tile>
          </div>
        </Section>
      </main>
    </div>
  );
}

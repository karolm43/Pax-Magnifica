/*
 * Ekrany lobby i zapisów na ekranie startowym (RULES.md 44.4, 44.6).
 *
 * - `JoinScreen` — gość z innego komputera: wpisuje imię i czeka, aż host wystartuje grę
 *   (dostaje miejsce → wejście do gry). Gdy nikt nie hostuje — informacja.
 * - `LobbyScreen` — host po „Play": link dla znajomych (np. ZeroTier), kto dołączył, boty,
 *   „Start" → wybór frakcji (miejsca przypisane automatycznie: host 1., dołączeni kolejno).
 * - `LoadGameModal` — lista zapisanych partii i wczytanie.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Group, Modal, Paper, Stack, Text, TextInput } from "@/ds";
import { MAX_PLAYERS, MIN_PLAYERS, useSetupStore } from "@/domains/setup/useSetupStore";
import { useLobby, useLobbyActions, useLobbyAssignments, useSaves } from "./useLobby";
import { useNetworkMe } from "./useNetworkMe";

const panelStyle: React.CSSProperties = { maxWidth: 460, width: "100%" };

/** Gość: dołączenie imieniem + poczekalnia do startu gry. */
export function JoinScreen() {
  const navigate = useNavigate();
  const { data: me } = useNetworkMe();
  const { data: lobby } = useLobby(me?.network === true);
  const actions = useLobbyActions();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const seated = me?.player_id != null;

  // Host przypisał mi miejsce → do gry.
  useEffect(() => {
    if (seated && lobby?.game_started) navigate("/game");
  }, [seated, lobby?.game_started, navigate]);

  if (!me) return null;

  if (!me.network) {
    return (
      <Paper p="xl" style={panelStyle}>
        <Stack gap="sm">
          <Text fw={700} size="lg">No network game right now</Text>
          <Text size="sm">
            The host has not opened the lobby yet. Ask them to click &quot;Play&quot; and
            refresh this page.
          </Text>
        </Stack>
      </Paper>
    );
  }

  if (!me.authenticated) {
    const submit = async () => {
      setBusy(true);
      setError(null);
      try {
        await actions.join(name);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    };
    return (
      <Paper p="xl" style={panelStyle}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <Stack gap="md">
            <Text fw={700} size="lg">Join the game</Text>
            <TextInput
              label="Your name"
              value={name}
              maxLength={40}
              autoFocus
              onChange={(e) => setName(e.currentTarget.value)}
              error={error ?? undefined}
            />
            <Button type="submit" loading={busy} disabled={!name.trim()}>
              Join lobby
            </Button>
          </Stack>
        </form>
      </Paper>
    );
  }

  return (
    <Paper p="xl" style={panelStyle}>
      <Stack gap="sm">
        <Text fw={700} size="lg">
          {seated ? "You have a seat" : `In the lobby as ${me.name ?? "player"}`}
        </Text>
        <Text size="sm">
          {seated
            ? "The game is ready."
            : "Waiting for the host to pick factions and start the game…"}
        </Text>
        <Text size="sm" fw={600}>Players in the lobby:</Text>
        {(lobby?.members ?? []).map((m) => (
          <Text key={m.member_id} size="sm">
            • {m.name}
            {m.member_id === me.member_id ? " (you)" : ""}
          </Text>
        ))}
        {seated && <Button onClick={() => navigate("/game")}>Enter the game</Button>}
      </Stack>
    </Paper>
  );
}

/**
 * Lobby hosta — pierwszy ekran po „Play". Pusta lista + link do skopiowania; kto wejdzie pod
 * link i wpisze imię, pojawia się tu na żywo. Host może dołożyć boty. „Start" ustawia graczy
 * w kreatorze (host = miejsce 1, dołączeni kolejno, potem boty) i przechodzi do wyboru frakcji.
 */
export function LobbyScreen({ onStart, onBack }: { onStart: () => void; onBack: () => void }) {
  const { data: lobby } = useLobby();
  const actions = useLobbyActions();
  const [hostName, setHostName] = useState(() => readHostName());
  const [bots, setBots] = useState(0);
  const [copied, setCopied] = useState<string | null>(null);
  const members = lobby?.members ?? [];
  const total = 1 + members.length + bots;
  const port = window.location.port ? `:${window.location.port}` : "";
  const links = (lobby?.addresses ?? []).map((ip) => `http://${ip}${port}`);

  const copy = async (link: string) => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(link);
    } catch {
      window.prompt("Copy this link:", link);
    }
  };

  const start = () => {
    saveHostName(hostName);
    const players = [
      { name: hostName.trim(), bot: false, who: "host" },
      ...members.map((m) => ({ name: m.name, bot: false, who: m.member_id })),
      ...Array.from({ length: bots }, () => ({ name: "", bot: true, who: "" })),
    ].slice(0, MAX_PLAYERS);
    const setup = useSetupStore.getState();
    setup.reset();
    setup.setPlayerCount(players.length);
    const bySlot: Record<number, string> = {};
    players.forEach((p, i) => {
      setup.setControlType(i, p.bot ? "BOT" : "HUMAN");
      setup.updateSlot(i, { name: p.name });
      if (p.who) bySlot[i] = p.who;
    });
    useLobbyAssignments.setState({ bySlot });
    setup.goToStep(1); // wybór frakcji (mapę można zmienić krokiem „Back")
    onStart();
  };

  return (
    <div style={{ minHeight: "100%", display: "grid", placeItems: "center", padding: 16 }}>
      <Paper p="xl" shadow="lg" withBorder style={{ maxWidth: 520, width: "100%" }}>
        <Stack gap="md">
          <Text fw={700} size="xl">Lobby</Text>
          <Stack gap={6}>
            <Text size="sm">Send this link to friends (ZeroTier / LAN) - they enter their name and appear below:</Text>
            {links.length === 0 && (
              <Text size="sm" c="dimmed">No network address found - is ZeroTier connected?</Text>
            )}
            {links.map((link) => (
              <Group key={link} gap="xs" wrap="nowrap">
                <Text size="sm" fw={600} style={{ userSelect: "all", flex: 1 }}>{link}</Text>
                <Button size="compact-sm" variant="default" onClick={() => void copy(link)}>
                  {copied === link ? "Copied" : "Copy"}
                </Button>
              </Group>
            ))}
          </Stack>
          <Stack gap={6}>
            <Text size="sm" fw={600}>Players ({Math.min(total, MAX_PLAYERS)}/{MAX_PLAYERS})</Text>
            <TextInput
              label="You (host)"
              placeholder="Your name"
              value={hostName}
              maxLength={40}
              onChange={(e) => setHostName(e.currentTarget.value)}
            />
            {members.map((m) => (
              <Group key={m.member_id} justify="space-between" wrap="nowrap">
                <Text size="sm">{m.name}</Text>
                <Button size="compact-xs" variant="subtle" onClick={() => void actions.kick(m.member_id)}>
                  Remove
                </Button>
              </Group>
            ))}
            {Array.from({ length: bots }, (_, i) => (
              <Group key={`bot-${i}`} justify="space-between" wrap="nowrap">
                <Text size="sm" c="dimmed">Bot {i + 1}</Text>
                <Button size="compact-xs" variant="subtle" onClick={() => setBots((b) => b - 1)}>
                  Remove
                </Button>
              </Group>
            ))}
            {members.length === 0 && bots === 0 && (
              <Text size="sm" c="dimmed">Waiting for players to join…</Text>
            )}
          </Stack>
          <Group justify="space-between">
            <Button variant="subtle" onClick={onBack}>Back</Button>
            <Group gap="xs">
              <Button
                variant="default"
                disabled={total >= MAX_PLAYERS}
                onClick={() => setBots((b) => b + 1)}
              >
                Add bot
              </Button>
              <Button disabled={total < MIN_PLAYERS} onClick={start}>
                Start
              </Button>
            </Group>
          </Group>
          {total < MIN_PLAYERS && (
            <Text size="xs" c="dimmed">At least {MIN_PLAYERS} players - wait for friends or add a bot.</Text>
          )}
        </Stack>
      </Paper>
    </div>
  );
}

const HOST_NAME_KEY = "custodian.hostName";

function readHostName(): string {
  try {
    return localStorage.getItem(HOST_NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveHostName(name: string): void {
  try {
    localStorage.setItem(HOST_NAME_KEY, name.trim());
  } catch {
    // brak storage — imię nie zostanie zapamiętane
  }
}

/** Lista zapisów + wczytanie. */
export function LoadGameModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { data, isLoading, error } = useSaves(opened);
  const actions = useLobbyActions();
  const [loading, setLoading] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = async (name: string) => {
    setLoading(name);
    setLoadError(null);
    try {
      await actions.loadSave(name);
      onClose();
      navigate("/game");
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Load game" size="lg">
      <Stack gap="sm">
        {isLoading && <Text size="sm">Loading saves…</Text>}
        {error && <Text size="sm">Could not list saves: {String(error)}</Text>}
        {data && !data.enabled && <Text size="sm">Saves are disabled on this server.</Text>}
        {data?.enabled && data.saves.length === 0 && <Text size="sm">No saved games yet.</Text>}
        {loadError && <Text size="sm">{loadError}</Text>}
        {data?.saves.map((s) => (
          <Paper key={s.name} p="sm" withBorder>
            <Group justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Text fw={600}>
                  {s.players.length > 0 ? s.players.join(", ") : "Empty game"}
                  {s.current ? " (current)" : ""}
                </Text>
                <Text size="xs" c="dimmed">
                  {s.broken
                    ? "Cannot be read"
                    : `Round ${s.round_number ?? "-"} · ${s.phase ?? "-"} · `}
                  {new Date(s.modified * 1000).toLocaleString()}
                </Text>
              </Stack>
              <Button
                size="compact-sm"
                disabled={s.broken}
                loading={loading === s.name}
                onClick={() => void load(s.name)}
              >
                {s.current ? "Continue" : "Load"}
              </Button>
            </Group>
          </Paper>
        ))}
      </Stack>
    </Modal>
  );
}

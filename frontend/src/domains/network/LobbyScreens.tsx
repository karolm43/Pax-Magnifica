/*
 * Ekrany lobby i zapisów na ekranie startowym (RULES.md 44.4, 44.6).
 *
 * - `JoinScreen` — gość z innego komputera: wpisuje imię i czeka, aż host wystartuje grę
 *   (dostaje miejsce → wejście do gry). Gdy nikt nie hostuje — informacja.
 * - `LobbyHostPanel` — host w kreatorze: adres do podania znajomym (np. ZeroTier), kto
 *   dołączył, kto siedzi na którym miejscu (przypisanie trafia do backendu po starcie gry).
 * - `LoadGameModal` — lista zapisanych partii i wczytanie.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Group, Modal, Paper, Select, Stack, Text, TextInput } from "@/ds";
import { useSetupStore } from "@/domains/setup/useSetupStore";
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
            The host has not opened a lobby on this computer yet. Ask them to choose
            &quot;Host online game&quot; and refresh this page.
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

/** Host w kreatorze: adres, dołączeni, przypisanie miejsc. */
export function LobbyHostPanel() {
  const { data: lobby } = useLobby();
  const actions = useLobbyActions();
  const slots = useSetupStore((s) => s.slots);
  const updateSlot = useSetupStore((s) => s.updateSlot);
  const { bySlot, setSlot } = useLobbyAssignments();
  if (!lobby?.open) return null;

  const port = window.location.port ? `:${window.location.port}` : "";
  const memberName = (id: string) => lobby.members.find((m) => m.member_id === id)?.name;
  const options = [
    { value: "", label: "Nobody (local / bot)" },
    { value: "host", label: "Me (host)" },
    ...lobby.members.map((m) => ({ value: m.member_id, label: m.name })),
  ];

  return (
    <div style={{ position: "fixed", right: 16, top: 72, zIndex: 950, width: 320 }}>
      <Paper p="md" shadow="lg" withBorder>
        <Stack gap="sm">
          <Group justify="space-between" wrap="nowrap">
            <Text fw={700}>Online lobby</Text>
            <Button size="compact-sm" variant="subtle" onClick={() => void actions.close()}>
              Close lobby
            </Button>
          </Group>
          <Text size="xs">Friends open this address (ZeroTier / LAN) and enter their name:</Text>
          {lobby.addresses.length === 0 && (
            <Text size="xs">No network address found - check ZeroTier is connected.</Text>
          )}
          {lobby.addresses.map((ip) => (
            <Text key={ip} size="sm" fw={600} style={{ userSelect: "all" }}>
              http://{ip}
              {port}
            </Text>
          ))}
          <Text size="sm" fw={600}>Joined ({lobby.members.length}):</Text>
          {lobby.members.length === 0 && <Text size="xs">Nobody yet…</Text>}
          {lobby.members.map((m) => (
            <Group key={m.member_id} justify="space-between" wrap="nowrap">
              <Text size="sm">{m.name}</Text>
              <Button size="compact-xs" variant="subtle" onClick={() => void actions.kick(m.member_id)}>
                Remove
              </Button>
            </Group>
          ))}
          <Text size="sm" fw={600}>Who plays which seat:</Text>
          {slots.map((slot, i) =>
            slot.controlType === "HUMAN" ? (
              <Select
                key={i}
                label={`Seat ${i + 1}${slot.name ? ` - ${slot.name}` : ""}`}
                data={options}
                value={bySlot[i] ?? ""}
                onChange={(v) => {
                  setSlot(i, v || null);
                  const n = v && v !== "host" ? memberName(v) : undefined;
                  if (n) updateSlot(i, { name: n });
                }}
              />
            ) : null,
          )}
        </Stack>
      </Paper>
    </div>
  );
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

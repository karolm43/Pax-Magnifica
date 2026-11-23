/*
 * Ekrany lobby i zapisów na ekranie startowym (RULES.md 44.4, 44.6).
 *
 * - `JoinScreen` — gość z innego komputera: wpisuje imię i czeka, aż host wystartuje grę
 *   (dostaje miejsce → wejście do gry). Gdy nikt nie hostuje — informacja.
 * - Lobby hosta to krok „Players & map" kreatora (wspólny na żywo — `setupSync.ts`).
 * - `LoadGameModal` — lista zapisanych partii i wczytanie.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Group, Modal, Paper, Stack, Text, TextInput } from "@/ds";
import { type SaveEntry, useLobby, useLobbyActions, useSaves } from "./useLobby";
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

  // Bez automatycznego przejścia do gry: dołączony gość siedzi w kreatorze, a start gry
  // (intro, potem plansza) obsługuje `useSetupSync` — inaczej ten ukryty pod kreatorem ekran
  // przeskakiwał intro. Zostaje przycisk „Enter the game" poniżej.

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

/** Faza z zapisu (`action`, `strategy`…) → „Action phase". */
export function formatSavePhase(phase: string | null): string {
  if (!phase) return "-";
  const words = phase.replace(/[_-]+/g, " ").toLowerCase();
  return `${words.charAt(0).toUpperCase()}${words.slice(1)} phase`;
}

/** Jednolinijkowy opis zapisu: „Round 3 · Action phase" (albo informacja o uszkodzeniu). */
export function describeSave(s: SaveEntry): string {
  if (s.broken) return "Cannot be read";
  return `Round ${s.round_number ?? "-"} · ${formatSavePhase(s.phase)}`;
}

/**
 * Wczytanie zapisu i przejście do gry — wspólne dla okna „Load game" i panelu
 * „Recent games" w menu głównym (jedno miejsce logiki, ten sam komunikat błędu).
 */
export function useLoadSave(onLoaded?: () => void) {
  const navigate = useNavigate();
  const actions = useLobbyActions();
  const [loading, setLoading] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const load = async (name: string) => {
    setLoading(name);
    setLoadError(null);
    try {
      await actions.loadSave(name);
      onLoaded?.();
      navigate("/game");
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };
  return { load, loading, loadError };
}

/** Lista zapisów + wczytanie. */
export function LoadGameModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const { data, isLoading, error } = useSaves(opened);
  const { load, loading, loadError } = useLoadSave(onClose);

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
                  {describeSave(s)} · {new Date(s.modified * 1000).toLocaleString()}
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

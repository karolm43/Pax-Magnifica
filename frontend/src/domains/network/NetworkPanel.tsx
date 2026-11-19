/*
 * Panel gry sieciowej (RULES.md 44.2): kim jestem + zaproszenia dla hosta.
 *
 * - Tryb lokalny: nic nie renderuje.
 * - Brak/nieważny token: zasłona „otwórz grę ze swojego linku" (backend i tak odpowie 401).
 * - Gracz: plakietka „You: <miejsce>". Host: przycisk „Invites" — linki miejsc (kopiuj,
 *   unieważnij) i wybór, czy host sam siedzi przy stole (wtedy widzi tylko swoje).
 * - Status tury (RULES.md 44.5) — `describeAwaiting` stąd, wyświetla go `TurnStatusChip`
 *   w nagłówku (obok „You play").
 * - Odmowa serwera (403 — nie twój ruch / nie host) pokazuje się jako krótki komunikat
 *   zamiast surowego błędu (zdarzenie `FORBIDDEN_EVENT` z `actorIdentity`).
 * Push stanu (WebSocket) włącza się tu, bo tylko gra sieciowa go potrzebuje.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Group, Modal, Paper, Select, Stack, Text } from "@/ds";
import { FORBIDDEN_EVENT } from "@/api/actorIdentity";
import { useAppStore } from "@/state/appStore";
import { useBackendPush } from "./useBackendPush";
import { NETWORK_ME_KEY, useNetworkMe } from "./useNetworkMe";
import { useLobby } from "./useLobby";
import { inviteOrigins } from "./inviteOrigin";

type SeatInvite = {
  player_id: string;
  name: string;
  faction: string | null;
  color: string | null;
  token: string;
  is_host_seat: boolean;
};

type SeatsResponse = { network: boolean; host_seat: string | null; seats: SeatInvite[] };

const SEATS_KEY = ["network", "seats"] as const;

export type Awaiting = {
  playerId: string;
  name: string;
  faction: string | null;
  color: string | null;
  reason: string;
};

/** Co gracz ma teraz zrobić (kody z `core/actor.awaiting`). */
const REASON: Record<string, string> = {
  respond: "respond in the timing window",
  decide: "make a decision",
  assign_hits: "assign hits",
  combat: "resolve combat",
  invasion: "resolve the invasion",
  explore: "explore",
  strategy: "resolve a strategy card",
  turn: "take a turn",
  speaker: "advance the phase (speaker)",
  secret: "choose a secret objective",
  setup: "finish the game setup (speaker)",
};

/**
 * Tekst chipa tury. ``controlAll`` = host w trybie testowym steruje każdym graczem — wtedy
 * każda czekająca decyzja jest „moja" (nie „Waiting for <gracz, którym właśnie gram>").
 */
export function describeAwaiting(
  list: Awaiting[],
  me: string | null,
  controlAll = false,
): {
  mine: boolean;
  text: string;
} {
  const reason = (a: Awaiting) => REASON[a.reason] ?? a.reason;
  if (controlAll && list.length > 0) {
    return {
      mine: true,
      text: `Your move - ${list.map((a) => `${a.name}: ${reason(a)}`).join(", ")}`,
    };
  }
  const own = list.find((a) => a.playerId === me);
  if (own) return { mine: true, text: `Your move - ${reason(own)}` };
  if (list.length === 0) return { mine: false, text: "" };
  const who = list.map((a) => `${a.name} (${reason(a)})`).join(", ");
  return { mine: false, text: `Waiting for ${who}` };
}

/**
 * Odmowa serwera (403, „nie twój ruch") trafia do wspólnej strefy komunikatów — ten sam panel
 * co odrzucone akcje (422), zamiast osobnego dymka.
 */
function ForbiddenNotices() {
  useEffect(() => {
    const onForbidden = (event: Event) => {
      useAppStore
        .getState()
        .setNotice(`Not your move: ${String((event as CustomEvent<string>).detail)}`, "error");
    };
    window.addEventListener(FORBIDDEN_EVENT, onForbidden);
    return () => window.removeEventListener(FORBIDDEN_EVENT, onForbidden);
  }, []);
  return null;
}
const OPERATOR = "__operator__";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/bot${path}`, init);
  if (!res.ok) throw new Error((await res.text().catch(() => "")) || `Error ${res.status}`);
  return (await res.json()) as T;
}

export function inviteLink(token: string, origin: string = window.location.origin): string {
  return `${origin}/game?token=${encodeURIComponent(token)}`;
}

function InvitesModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState<string | null>(null);
  const seats = useQuery({
    queryKey: SEATS_KEY,
    queryFn: () => call<SeatsResponse>("/network/seats"),
    enabled: opened,
  });
  // Adres w linkach: zamiast „localhost” adres tego komputera w sieci (LAN / ZeroTier).
  const lobby = useLobby(opened);
  const origins = inviteOrigins(lobby.data?.addresses ?? [], window.location);
  const [picked, setPicked] = useState<string | null>(null);
  const origin = picked && origins.includes(picked) ? picked : origins[0];
  const update = (data: SeatsResponse) => {
    queryClient.setQueryData(SEATS_KEY, data);
    void queryClient.invalidateQueries({ queryKey: NETWORK_ME_KEY });
    void queryClient.invalidateQueries({ refetchType: "active" });
  };
  const rotate = useMutation({
    mutationFn: (playerId: string) =>
      call<SeatsResponse>(`/network/seats/${encodeURIComponent(playerId)}/rotate`, { method: "POST" }),
    onSuccess: update,
  });
  const hostSeat = useMutation({
    mutationFn: (playerId: string | null) =>
      call<SeatsResponse>("/network/host-seat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId }),
      }),
    onSuccess: update,
  });

  const copy = async (seat: SeatInvite) => {
    try {
      await navigator.clipboard.writeText(inviteLink(seat.token, origin));
      setCopied(seat.player_id);
    } catch {
      window.prompt("Copy this invite link:", inviteLink(seat.token, origin));
    }
  };

  const data = seats.data;
  return (
    <Modal opened={opened} onClose={onClose} title="Network game - invites" size="lg">
      <Stack gap="md">
        <Text size="sm">
          Send each player their own link. Whoever opens a link plays that seat, and the server
          shows them only their own cards. Do not share your host link.
        </Text>
        {origins.length > 1 && (
          <Select
            label="Friends connect through"
            description="Same home network: the 192.168… address. Over the internet: your ZeroTier / VPN address."
            data={origins.map((o) => ({ value: o, label: o.replace(/^https?:\/\//, "") }))}
            value={origin}
            onChange={(v) => v && setPicked(v)}
          />
        )}
        {seats.isLoading && <Text size="sm">Loading seats…</Text>}
        {seats.error && <Text size="sm">Could not load seats: {String(seats.error)}</Text>}
        {data && data.seats.length === 0 && (
          <Text size="sm">No players yet - create the game first.</Text>
        )}
        {data && data.seats.length > 0 && (
          <>
            <Select
              label="You (the host) play as"
              data={[
                { value: OPERATOR, label: "Nobody - operator, sees everything" },
                ...data.seats.map((s) => ({ value: s.player_id, label: s.name })),
              ]}
              value={data.host_seat ?? OPERATOR}
              onChange={(v) => hostSeat.mutate(v && v !== OPERATOR ? v : null)}
            />
            {data.seats.map((seat) => (
              <Paper key={seat.player_id} p="sm" withBorder>
                <Group justify="space-between" wrap="nowrap">
                  <Stack gap={2}>
                    <Text fw={600}>
                      {seat.name}
                      {seat.is_host_seat ? " (you)" : ""}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {seat.faction ?? "-"} · {seat.color ?? "-"} · {seat.player_id}
                    </Text>
                  </Stack>
                  <Group gap="xs" wrap="nowrap">
                    <Button size="compact-sm" onClick={() => void copy(seat)}>
                      {copied === seat.player_id ? "Copied" : "Copy link"}
                    </Button>
                    <Button
                      size="compact-sm"
                      variant="subtle"
                      onClick={() => rotate.mutate(seat.player_id)}
                    >
                      New link
                    </Button>
                  </Group>
                </Group>
              </Paper>
            ))}
          </>
        )}
      </Stack>
    </Modal>
  );
}

export function NetworkPanel() {
  const me = useNetworkMe();
  const [open, setOpen] = useState(false);
  const network = me.data?.network === true;
  useBackendPush(network && me.data?.authenticated === true);

  if (!network || !me.data) return null;

  if (!me.data.authenticated) {
    return (
      <div
        role="alert"
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 10000,
          display: "grid",
          placeItems: "center",
          background: "rgba(0, 0, 0, 0.82)",
        }}
      >
        <Paper p="xl" maw={440}>
          <Stack gap="sm">
            <Text fw={700} size="lg">
              This is a network game
            </Text>
            <Text size="sm">
              Join from the start page (enter your name in the lobby), or open the personal
              invite link the host sent you.
            </Text>
            <Button component="a" href="/">
              Go to the lobby
            </Button>
          </Stack>
        </Paper>
      </div>
    );
  }

  return (
    <>
      <ForbiddenNotices />
      {/* „Kim gram" jest w nagłówku (WhoAmIBadge); tu tylko zaproszenia hosta. */}
      {me.data.host && (
        <div style={{ position: "fixed", left: 12, bottom: 12, zIndex: 900 }}>
          <Button size="compact-sm" onClick={() => setOpen(true)}>
            Invites
          </Button>
        </div>
      )}
      {me.data.host && <InvitesModal opened={open} onClose={() => setOpen(false)} />}
    </>
  );
}

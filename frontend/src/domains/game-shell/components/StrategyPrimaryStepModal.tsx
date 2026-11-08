import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Switch, Text } from "@/ds";
import { IconCheck } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor } from "@/api/useBoardEditor";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import { getPlayerDisplayName, type GameStatePlayer } from "./gameStatePlayers";

type SeatPlayer = GameStatePlayer & { discordId: string };

/**
 * Szkielet kroku WIELOETAPOWEGO primary karty strategii (RULES.md 30.5).
 *
 * Gdy karta wymaga wyboru aktywnego gracza, silnik ustawia ``pendingStrategy`` (krok +
 * szkic) i blokuje End turn. Ten modal renderuje bieżący ``step`` i wysyła wybór
 * (``/strategy/primary-step``). Obsługiwany krok: ``choose_free_players`` (Trade — kogo
 * wskazać do DARMOWEGO, obowiązkowego secondary). Kolejne karty dołożą własne kroki
 * w ``renderStep`` (docelowo: panele w stylu akcji taktycznej / statusu).
 *
 * Modal jest NIEODRZUCALNY — zniknie, gdy backend zastosuje primary i otworzy okno
 * secondary. Odpowiedzi waliduje serwer (tylko właściciel karty), więc w sieci inni
 * gracze zobaczą ten sam stan, ale nie mogą go rozstrzygnąć.
 */
export function StrategyPrimaryStepModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { strategyPrimaryStep } = useBoardEditor();
  const [chosen, setChosen] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const pending = gameState?.pendingStrategy ?? null;
  const players = (gameData?.playerData ?? []) as SeatPlayer[];
  const owner = players.find((p) => p.discordId === pending?.ownerId);
  const ownerName = owner
    ? getPlayerDisplayName(owner, owner.color)
    : (pending?.ownerId ?? "");
  const cardName = pending
    ? (gameData?.strategyCards?.find((c) => c.initiative === pending.initiative)
        ?.name ?? SC_NAMES[pending.initiative] ?? `Strategy Card ${pending.initiative}`)
    : "";

  const submit = (payload: Record<string, unknown>) => {
    if (!pending || busy) return;
    setBusy(true);
    void strategyPrimaryStep(pending.ownerId, payload).finally(() => {
      setBusy(false);
      setChosen([]);
    });
  };

  const toggle = (id: string, on: boolean) =>
    setChosen((cur) => (on ? [...cur, id] : cur.filter((x) => x !== id)));

  const renderStep = () => {
    if (!pending) return null;
    if (pending.step === "choose_free_players") {
      const others = players.filter((p) => p.discordId !== pending.ownerId);
      return (
        <Stack gap="sm">
          <Text size="sm">
            Choose the players who will resolve the <b>secondary</b> ability{" "}
            <b>for free</b>. They <b>must</b> resolve it and spend no command token.
          </Text>
          <Stack gap={6}>
            {others.map((p) => (
              <Switch
                key={p.discordId}
                label={getPlayerDisplayName(p, p.color)}
                checked={chosen.includes(p.discordId)}
                onChange={(e) => toggle(p.discordId, e.currentTarget.checked)}
                disabled={busy}
              />
            ))}
          </Stack>
          <Group justify="flex-end">
            <Button
              disabled={busy}
              leftSection={<IconCheck size={16} />}
              onClick={() => submit({ players: chosen })}
            >
              {chosen.length === 0 ? "Choose nobody" : "Confirm"}
            </Button>
          </Group>
        </Stack>
      );
    }
    return (
      <Text size="sm" c="dimmed">
        Unsupported step: {pending.step}
      </Text>
    );
  };

  return (
    <AppModal
      opened={pending != null}
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title={`${cardName} — primary ability`}
      size={440}
    >
      <Stack gap="md">
        <Text size="xs" c="dimmed">
          {ownerName} is resolving the primary ability.
        </Text>
        {renderStep()}
      </Stack>
    </AppModal>
  );
}

export default StrategyPrimaryStepModal;

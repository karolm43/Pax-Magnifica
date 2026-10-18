import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Center,
  Loader,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from "@/ds";
import { useFactions, createNewGame } from "@/api/useNewGame";
import { usePageThemeClass } from "@/hooks/usePageThemeClass";

/** Maksymalna liczba graczy (układ 6-osobowy — sloty domowe na rogach pierścienia 3). */
const MAX_PLAYERS = 6;
const MIN_PLAYERS = 2;

/** Kolory przydzielane automatycznie wg kolejności graczy (podgląd dla UI). */
const AUTO_COLORS = ["red", "green", "white", "blue", "purple", "yellow"];

/**
 * Ekran startowy Custodian Engine. Konfigurujesz grę: liczba graczy, frakcje
 * i (opcjonalnie) map string, po czym jednym żądaniem tworzysz grę w backendzie
 * i przechodzisz do widoku planszy. Kolory i sloty domowe przydzielane są
 * automatycznie wg kolejności (gracz 1 → red, 2 → green, ...).
 */
export default function StartScreen() {
  const themeClassName = usePageThemeClass();
  const navigate = useNavigate();
  const { data: factions, isLoading, isError } = useFactions();

  const [playerCount, setPlayerCount] = useState(MIN_PLAYERS);
  const [factionByPlayer, setFactionByPlayer] = useState<Record<number, string>>(
    {},
  );
  const [mapString, setMapString] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const factionOptions = useMemo(
    () =>
      (factions ?? [])
        .map((f) => ({ value: f.id, label: f.name }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    [factions],
  );

  const playerIndexes = Array.from({ length: playerCount }, (_, i) => i);
  const allChosen = playerIndexes.every((i) => factionByPlayer[i]);

  const handleStart = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await createNewGame({
        players: playerIndexes.map((i) => ({ faction_id: factionByPlayer[i] })),
        map_string: mapString.trim() || undefined,
      });
      navigate("/game");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nieznany błąd przy tworzeniu gry.");
      setSubmitting(false);
    }
  };

  return (
    <Box className={themeClassName} style={{ minHeight: "100vh" }}>
      <Center style={{ minHeight: "100vh", padding: 24 }}>
        <Paper
          radius="md"
          style={{ width: "100%", maxWidth: 560, padding: 28 }}
        >
          <Stack gap="lg">
            <Stack gap={4}>
              <Title order={1} size="h2">
                Custodian Engine
              </Title>
              <Text size="sm" c="dimmed">
                Nowa gra Twilight Imperium 4 — wybierz graczy i frakcje, a potem graj.
              </Text>
            </Stack>

            {isLoading && (
              <Center style={{ padding: 24 }}>
                <Loader />
              </Center>
            )}

            {isError && (
              <Text c="red" size="sm">
                Nie udało się pobrać listy frakcji. Czy backend działa (port 8000)?
              </Text>
            )}

            {factions && (
              <>
                <NumberInput
                  label="Liczba graczy"
                  value={playerCount}
                  min={MIN_PLAYERS}
                  max={MAX_PLAYERS}
                  onChange={(v) => {
                    const n = typeof v === "number" ? v : Number(v) || MIN_PLAYERS;
                    setPlayerCount(Math.min(MAX_PLAYERS, Math.max(MIN_PLAYERS, n)));
                  }}
                />

                <Stack gap="sm">
                  {playerIndexes.map((i) => (
                    <Select
                      key={i}
                      label={`Gracz ${i + 1} · ${AUTO_COLORS[i]}`}
                      placeholder="Wybierz frakcję"
                      data={factionOptions}
                      value={factionByPlayer[i] ?? null}
                      onChange={(v) =>
                        setFactionByPlayer((prev) => ({ ...prev, [i]: v }))
                      }
                    />
                  ))}
                </Stack>

                <TextInput
                  label="Map string (opcjonalnie)"
                  placeholder="Puste = mapa testowa"
                  value={mapString}
                  onChange={(e) => setMapString(e.target.value)}
                />

                {error && (
                  <Text c="red" size="sm">
                    {error}
                  </Text>
                )}

                <Button
                  size="md"
                  disabled={!allChosen || submitting}
                  loading={submitting}
                  onClick={() => void handleStart()}
                >
                  Generuj i graj
                </Button>
              </>
            )}
          </Stack>
        </Paper>
      </Center>
    </Box>
  );
}

import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Center,
  Group,
  Loader,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@/ds";
import { useFactions, createNewGame, type FactionInfo } from "@/api/useNewGame";
import { usePageThemeClass } from "@/hooks/usePageThemeClass";

/** Układ 6-osobowy: sloty domowe na rogach pierścienia 3. */
const MAX_PLAYERS = 6;
const MIN_PLAYERS = 2;
const DEFAULT_PLAYERS = 6;

/** Kolory przydzielane automatycznie wg kolejności graczy (zgodne z backendem). */
const AUTO_COLORS = ["red", "green", "white", "blue", "purple", "yellow"];

/** Mapowanie koloru gracza na realny kolor CSS kropki w UI. */
const COLOR_SWATCH: Record<string, string> = {
  red: "#f00606",
  green: "#2fb344",
  white: "#cecece",
  blue: "#2f6fed",
  purple: "#8b5cf6",
  yellow: "#f5f506",
};

/** Specjalna wartość w Selectcie oznaczająca „losowa frakcja". */
const RANDOM = "__random__";

function pickRandom<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

/**
 * Ekran startowy Custodian Engine. Konfigurujesz grę: liczba graczy, frakcje
 * i (opcjonalnie) map string, po czym jednym żądaniem tworzysz grę w backendzie
 * i przechodzisz do widoku planszy. Nie wybrana frakcja = losowa (bez powtórzeń).
 * Kolory i sloty domowe przydzielane automatycznie wg kolejności (red, green, ...).
 */
export default function StartScreen() {
  const themeClassName = usePageThemeClass();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: factions, isLoading, isError } = useFactions();

  const [playerCount, setPlayerCount] = useState(DEFAULT_PLAYERS);
  // Domyślnie każdy slot = "losowa"; użytkownik może nadpisać wyborem frakcji.
  const [factionByPlayer, setFactionByPlayer] = useState<Record<number, string>>(
    {},
  );
  const [mapString, setMapString] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Opcje do Selecta: „losowa" na górze, potem frakcje alfabetycznie.
  const factionOptions = useMemo(
    () => [
      { value: RANDOM, label: "🎲 Losowa" },
      ...(factions ?? [])
        .map((f) => ({ value: f.id, label: f.name }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    ],
    [factions],
  );

  const playerIndexes = Array.from({ length: playerCount }, (_, i) => i);

  /** Rozwiązuje wybory graczy na konkretne frakcje; „losowa"/brak → losowanie bez powtórzeń. */
  const resolveFactions = (all: FactionInfo[]): string[] => {
    const chosen = playerIndexes.map((i) => factionByPlayer[i]);
    const taken = new Set(
      chosen.filter((id): id is string => !!id && id !== RANDOM),
    );
    const pool = all.map((f) => f.id).filter((id) => !taken.has(id));
    return chosen.map((id) => {
      if (id && id !== RANDOM) return id;
      const pick = pickRandom(pool);
      pool.splice(pool.indexOf(pick), 1); // bez powtórzeń
      return pick;
    });
  };

  const handleStart = async () => {
    if (!factions) return;
    setError(null);
    setSubmitting(true);
    try {
      const resolved = resolveFactions(factions);
      await createNewGame({
        players: resolved.map((faction_id) => ({ faction_id })),
        map_string: mapString.trim() || undefined,
      });
      // Nowa gra = nowy stan; wymuś świeży fetch web-data (staleTime: Infinity).
      await queryClient.invalidateQueries({ queryKey: ["playerData"] });
      navigate("/game");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nieznany błąd przy tworzeniu gry.");
      setSubmitting(false);
    }
  };

  return (
    <Box className={themeClassName} style={{ minHeight: "100vh" }}>
      <Center style={{ minHeight: "100vh", padding: 24 }}>
        <Paper radius="lg" style={{ width: "100%", maxWidth: 640, padding: 32 }}>
          <Stack gap="xl">
            <Stack gap={6}>
              <Title order={1} size="h2">
                Custodian Engine
              </Title>
              <Text size="sm" c="dimmed">
                Nowa gra Twilight Imperium 4. Wybierz liczbę graczy i frakcje
                (lub zostaw losowe), opcjonalnie wklej map string i zaczynaj.
              </Text>
            </Stack>

            {isLoading && (
              <Center style={{ padding: 32 }}>
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
                    const n =
                      typeof v === "number" ? v : Number(v) || DEFAULT_PLAYERS;
                    setPlayerCount(Math.min(MAX_PLAYERS, Math.max(MIN_PLAYERS, n)));
                  }}
                />

                {/* Stały 2-kolumnowy układ — zmiana liczby graczy dokłada wiersze
                    w dół zamiast przestawiać całość. */}
                <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                  {playerIndexes.map((i) => (
                    <Group key={i} gap="xs" wrap="nowrap" align="flex-end">
                      <Box
                        style={{
                          width: 14,
                          height: 14,
                          borderRadius: "50%",
                          marginBottom: 8,
                          flexShrink: 0,
                          background: COLOR_SWATCH[AUTO_COLORS[i]],
                          boxShadow: "0 0 0 1px rgba(255,255,255,0.2)",
                        }}
                        title={AUTO_COLORS[i]}
                      />
                      <Box style={{ flex: 1, minWidth: 0 }}>
                        <Select
                          label={`Gracz ${i + 1}`}
                          placeholder="🎲 Losowa"
                          data={factionOptions}
                          value={factionByPlayer[i] ?? RANDOM}
                          onChange={(v) =>
                            setFactionByPlayer((prev) => ({ ...prev, [i]: v }))
                          }
                        />
                      </Box>
                    </Group>
                  ))}
                </SimpleGrid>

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

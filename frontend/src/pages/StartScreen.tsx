import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Modal,
  NumberInput,
  Paper,
  Stack,
  Text,
  TextInput,
} from "@/ds";
import { useFactions, createNewGame, type FactionInfo } from "@/api/useNewGame";
import { FactionItem } from "@/domains/setup/FactionList";
import StartingTechPicker from "@/domains/setup/StartingTechPicker";
import { usePageThemeClass } from "@/hooks/usePageThemeClass";
import styles from "./StartScreen.module.css";

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

/** Specjalna wartość oznaczająca „losowa frakcja". */
const RANDOM = "__random__";

function pickRandom<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

/**
 * Pełnoekranowy ekran rozruchu — pokazywany, dopóki ładujemy dane gry (frakcje)
 * z backendu, oraz gdy ładowanie się nie powiedzie. Trzyma ten sam ciemny klimat
 * co menu (to samo tło, mocno przyciemnione), logo i animowany pasek postępu —
 * żeby start aplikacji wyglądał jak rozruch prawdziwej gry, nie jak pusty ekran
 * z kręciołkiem.
 */
function BootScreen({
  state,
  onRetry,
}: {
  state: "loading" | "error";
  onRetry?: () => void;
}) {
  const themeClassName = usePageThemeClass();
  return (
    <div className={`${themeClassName} ${styles.boot}`}>
      <div className={styles.bootInner}>
        <div className={styles.menuTitleWrap}>
          <h1 className={`${styles.menuTitle} ${styles.bootTitle}`}>
            Custodian Engine
          </h1>
          <span className={styles.titleRule} aria-hidden />
        </div>

        {state === "loading" ? (
          <div className={styles.bootStatus}>
            <div
              className={styles.progressTrack}
              role="progressbar"
              aria-label="Ładowanie zasobów gry"
            >
              <span className={styles.progressBar} />
            </div>
            <p className={styles.bootLabel}>Ładowanie zasobów gry…</p>
          </div>
        ) : (
          <div className={styles.bootStatus}>
            <p className={styles.bootError}>
              Nie udało się pobrać danych gry. Sprawdź, czy backend działa
              (port 8000), i spróbuj ponownie.
            </p>
            {onRetry && (
              <Button variant="default" onClick={onRetry}>
                Spróbuj ponownie
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Ekran startowy Custodian Engine. Konfigurujesz grę: liczba graczy, nazwy,
 * frakcje i (opcjonalnie) map string, po czym jednym żądaniem tworzysz grę
 * w backendzie i przechodzisz do widoku planszy. Nie wybrana frakcja = losowa
 * (bez powtórzeń). Kolory i sloty domowe przydzielane automatycznie wg kolejności
 * (red, green, ...).
 */
export default function StartScreen() {
  const themeClassName = usePageThemeClass();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: factions, isLoading, isError, refetch } = useFactions();

  // Minimalny czas pokazania ekranu rozruchu. Lokalny backend odpowiada niemal
  // natychmiast, więc bez tego BootScreen tylko by „mignął". Dzięki temu rozruch
  // jest widoczny i płynnie znika, zamiast przeskakiwać od razu do menu.
  const MIN_BOOT_MS = 1100;
  const [bootMinElapsed, setBootMinElapsed] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setBootMinElapsed(true), MIN_BOOT_MS);
    return () => window.clearTimeout(t);
  }, []);

  const [playerCount, setPlayerCount] = useState(DEFAULT_PLAYERS);
  // Domyślnie każdy slot = "losowa"; użytkownik może nadpisać wyborem frakcji.
  const [factionByPlayer, setFactionByPlayer] = useState<Record<number, string>>(
    {},
  );
  // Wybrane technologie startowe per gracz (dla frakcji z wyborem, np. Winnu/Argent).
  const [techByPlayer, setTechByPlayer] = useState<Record<number, string[]>>({});
  // Nazwy graczy per slot (opcjonalne; pusta = auto po stronie backendu).
  const [nameByPlayer, setNameByPlayer] = useState<Record<number, string>>({});
  // Która frakcja ma pokazany podgląd quick reference w danym slocie (id) albo
  // null. Stan trzymamy w slocie (nie w pojedynczym FactionItem), więc naraz
  // widać najwyżej jeden podgląd, a wyjście myszą poza listę zawsze go chowa —
  // to likwiduje „zacinający się" hover, gdy mouseleave pojedynczego elementu
  // się zgubi przy szybkim przeskakiwaniu.
  const [hoveredByPlayer, setHoveredByPlayer] = useState<
    Record<number, string | null>
  >({});
  const [mapString, setMapString] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Widok ekranu startowego: "menu" (ekran tytułowy z 3 przyciskami) lub "setup"
  // (konfiguracja nowej gry). Oba leżą w jednym pionowym „decku" wysokim na dwa
  // ekrany; zmiana widoku PRZEWIJA deck w pionie (translateY) z animacją, więc
  // klik „Graj" wygląda jak zjechanie strony w dół do listy wyboru.
  const [view, setView] = useState<"menu" | "setup">("menu");
  // Okno szkieletowe — na razie placeholder, wypełnimy je później.
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Szybki dostęp do danych frakcji po id (do menu wyboru technologii).
  const factionById = useMemo(() => {
    const map = new Map<string, FactionInfo>();
    for (const f of factions ?? []) map.set(f.id, f);
    return map;
  }, [factions]);

  // Frakcje do listy wyboru, posortowane alfabetycznie po nazwie.
  const sortedFactions = useMemo(
    () => [...(factions ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
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

    // Walidacja unikalności nazw: `player_id` to klucz gracza, więc niepuste
    // nazwy nie mogą się powtarzać. Puste pola = auto (bez kontroli unikalności).
    const names = playerIndexes
      .map((i) => (nameByPlayer[i] ?? "").trim())
      .filter((name) => name.length > 0);
    if (new Set(names).size !== names.length) {
      setError("Nazwy graczy muszą być unikalne.");
      return;
    }

    setSubmitting(true);
    try {
      const resolved = resolveFactions(factions);
      await createNewGame({
        players: resolved.map((faction_id, i) => {
          const info = factionById.get(faction_id);
          // Wybór tech tylko dla frakcji z wyborem i tylko gdy gracz jawnie wybrał
          // tę frakcję (dla losowej zostawiamy fallback backendu = pierwsze N opcji).
          const chosen = techByPlayer[i];
          const needsChoice = (info?.starting_tech_amount ?? 0) > 0;
          const explicit = factionByPlayer[i] && factionByPlayer[i] !== RANDOM;
          // Nazwa jako player_id; pusta → undefined (auto przez backend).
          const player_id = (nameByPlayer[i] ?? "").trim() || undefined;
          return needsChoice && explicit && chosen?.length
            ? { faction_id, player_id, starting_tech: chosen }
            : { faction_id, player_id };
        }),
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

  // Dopóki ładujemy frakcje (lub gdy się nie powiodło) — pełnoekranowy rozruch,
  // zamiast migać pustym menu bez danych. Boot utrzymujemy też przez minimalne
  // okno czasu, żeby przy błyskawicznym backendzie nie „mignął".
  if (isError) return <BootScreen state="error" onRetry={() => void refetch()} />;
  if (isLoading || !bootMinElapsed) return <BootScreen state="loading" />;

  return (
    <Box className={`${themeClassName} ${styles.root}`}>
      {/*
       * Pionowy „deck" wysoki na dwa ekrany. Klasa `deckSetup` przesuwa go w
       * górę o 50% (translateY) z animacją, odsłaniając ekran konfiguracji —
       * efekt „strona zjeżdża w dół do listy".
       */}
      <div
        className={`${styles.deck} ${
          view === "setup" ? styles.deckSetup : ""
        }`}
      >
        {/* ── Ekran tytułowy (menu główne) ──────────────────────────────── */}
        <div
          className={styles.menuScreen}
          aria-hidden={view === "setup"}
          inert={view === "setup"}
        >
          <div className={styles.menuTitleWrap}>
            <h1 className={styles.menuTitle}>Custodian Engine</h1>
            <span className={styles.titleRule} aria-hidden />
            <p className={styles.menuTagline}>Twilight Imperium 4 — web game</p>
          </div>

          <nav className={styles.menuButtons} aria-label="Menu główne">
            <Button
              size="xl"
              fullWidth
              className={styles.menuButton}
              onClick={() => setView("setup")}
            >
              Graj
            </Button>
            <Button
              size="xl"
              fullWidth
              variant="default"
              className={styles.menuButton}
              onClick={() => setSettingsOpen(true)}
            >
              Ustawienia
            </Button>
            <Button
              size="xl"
              fullWidth
              variant="default"
              className={styles.menuButton}
              onClick={() => navigate("/rules")}
            >
              Zasady
            </Button>
          </nav>

         

          
        </div>

        {/* ── Ekran konfiguracji nowej gry (wybór graczy/frakcji) ───────── */}
        <div
          className={styles.setupScreen}
          aria-hidden={view === "menu"}
          inert={view === "menu"}
        >
          <Paper radius="lg" withBorder shadow="xl" className={styles.panel}>
            <Stack gap="xl">
                <header className={styles.header}>
                  <button
                    type="button"
                    className={styles.backButton}
                    onClick={() => setView("menu")}
                  >
                    ← Menu główne
                  </button>
                  <h1 className={styles.title}>Nowa gra</h1>
                  <p className={styles.subtitle}>
                    Wybierz liczbę graczy, nazwij ich i dobierz frakcje (lub
                    zostaw losowe). Najedź na frakcję, by zobaczyć jej quick
                    reference.
                  </p>
                </header>

                {factions && (
                  <>
                    {/* ── Ustawienia gry ── */}
              <section>
                <p className={styles.sectionLabel}>Ustawienia</p>
                <div className={styles.settingsRow}>
                  <NumberInput
                    label="Liczba graczy"
                    value={playerCount}
                    min={MIN_PLAYERS}
                    max={MAX_PLAYERS}
                    onChange={(v) => {
                      const n =
                        typeof v === "number" ? v : Number(v) || DEFAULT_PLAYERS;
                      setPlayerCount(
                        Math.min(MAX_PLAYERS, Math.max(MIN_PLAYERS, n)),
                      );
                    }}
                  />
                  <TextInput
                    label="Map string (opcjonalnie)"
                    placeholder="Puste = mapa testowa"
                    value={mapString}
                    onChange={(e) => setMapString(e.target.value)}
                  />
                </div>
              </section>

              {/* ── Sloty graczy ── */}
              <section>
                <p className={styles.sectionLabel}>Gracze</p>
                <div className={styles.playersGrid}>
                  {playerIndexes.map((i) => {
                    const selectedId = factionByPlayer[i] ?? RANDOM;
                    const slotColor = COLOR_SWATCH[AUTO_COLORS[i]];
                    return (
                      <div
                        key={i}
                        className={styles.playerSlot}
                        style={{ ["--slot-color" as string]: slotColor }}
                      >
                        <div className={styles.playerSlotHead}>
                          <span className={styles.colorDot} title={AUTO_COLORS[i]} />
                          <span className={styles.slotTitle}>Gracz {i + 1}</span>
                        </div>

                        <TextInput
                          label="Nazwa gracza"
                          placeholder="Auto"
                          value={nameByPlayer[i] ?? ""}
                          onChange={(e) =>
                            setNameByPlayer((prev) => ({
                              ...prev,
                              [i]: e.target.value,
                            }))
                          }
                        />

                        {/* Przewijalna lista frakcji z „Losową" na górze. */}
                        <div
                          className={styles.factionList}
                          role="listbox"
                          aria-label={`Frakcja gracza ${i + 1}`}
                          // Wyjście myszą poza listę zawsze chowa podgląd slotu.
                          onMouseLeave={() =>
                            setHoveredByPlayer((prev) => ({ ...prev, [i]: null }))
                          }
                          // Scroll listy chowa podgląd — inaczej karta „odjeżdża"
                          // od swojej pozycji i zostaje wisieć (popover nie nadąża
                          // za przewijanym kontenerem).
                          onScroll={() =>
                            setHoveredByPlayer((prev) =>
                              prev[i] == null ? prev : { ...prev, [i]: null },
                            )
                          }
                        >
                          <button
                            type="button"
                            className={`${styles.factionItem} ${
                              selectedId === RANDOM ? styles.factionItemActive : ""
                            }`}
                            aria-pressed={selectedId === RANDOM}
                            onClick={() => {
                              setFactionByPlayer((prev) => ({ ...prev, [i]: RANDOM }));
                              setTechByPlayer((prev) => ({ ...prev, [i]: [] }));
                            }}
                          >
                            <span className={styles.randomIcon} aria-hidden>
                              🎲
                            </span>
                            <span className={styles.factionItemLabel}>Losowa</span>
                          </button>

                          {sortedFactions.map((f) => (
                            <FactionItem
                              key={f.id}
                              faction={f}
                              active={selectedId === f.id}
                              opened={(hoveredByPlayer[i] ?? null) === f.id}
                              onHover={(id) =>
                                setHoveredByPlayer((prev) => ({ ...prev, [i]: id }))
                              }
                              onPick={() => {
                                setFactionByPlayer((prev) => ({ ...prev, [i]: f.id }));
                                // Zmiana frakcji kasuje poprzedni wybór technologii.
                                setTechByPlayer((prev) => ({ ...prev, [i]: [] }));
                              }}
                            />
                          ))}
                        </div>

                        <StartingTechPicker
                          faction={
                            selectedId !== RANDOM
                              ? factionById.get(selectedId)
                              : undefined
                          }
                          value={techByPlayer[i] ?? []}
                          onChange={(techs) =>
                            setTechByPlayer((prev) => ({ ...prev, [i]: techs }))
                          }
                        />
                      </div>
                    );
                  })}
                </div>
              </section>

              {error && (
                <Text c="red" size="sm">
                  {error}
                </Text>
              )}

              <div className={styles.footer}>
                <Button
                  size="md"
                  loading={submitting}
                  onClick={() => void handleStart()}
                >
                  Generuj i graj
                </Button>
              </div>
                  </>
                )}
              </Stack>
            </Paper>
          </div>
      </div>

      {/* ── Okno szkieletowe: Ustawienia (do wypełnienia później) ───────── */}
      <Modal
        opened={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="Ustawienia"
        size="md"
      >
        <Stack gap="md">
          <Text c="dimmed" size="sm">
            Ustawienia gry pojawią się tutaj. Na razie to szkielet — wypełnimy
            go kolejnymi opcjami (np. motyw, dźwięk, warianty reguł).
          </Text>
          <div className={styles.modalActions}>
            <Button variant="default" onClick={() => setSettingsOpen(false)}>
              Zamknij
            </Button>
          </div>
        </Stack>
      </Modal>

    </Box>
  );
}

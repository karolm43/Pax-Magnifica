// Kontener kreatora setupu (Setup_Wizard).
//
// Odpowiedzialności (zadanie 11.3):
//  1. Renderuje BIEŻĄCY krok wg uporządkowanej sekwencji `SETUP_STEPS` (R14.1). Mapowanie
//     „id kroku → komponent" trzyma lekki rejestr `STEP_COMPONENTS` (Step_NameColor —
//     nazwa/kolor/sterowanie, Step_Faction — pełnoekranowa scena). Wybór technologii startowych NIE jest już osobnym
//     krokiem — jest wbudowany w panel podglądu frakcji (`FactionSummary`) w kroku frakcji.
//  2. Blokuje „Dalej"/„Generuj" przy niespełnionej walidacji (R7.4–R7.6, R9.2/R9.5, R10.2)
//     — logika w czystej funkcji `validateSetup` ze store'a.
//  3. Mapuje stan store'a na `NewGameRequest` (`toNewGameRequest`) i wysyła `/game/new`.
//
// Kontener jest celowo „cienki": cała walidacja i mapowanie żyją w `useSetupStore.ts`
// (testowalne bez Reacta), tu zostaje tylko spięcie stanu z UI i obsługa wysyłki.

import { useMemo, useState, type ComponentType } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Group, NumberInput, Paper, Stack, Text, TextInput } from "@/ds";
import { useFactions, createNewGame, type FactionInfo } from "@/api/useNewGame";
import { SETUP_STEPS, type SetupStepId } from "./setupSteps";
import {
  currentStep,
  MAX_PLAYERS,
  MIN_PLAYERS,
  toNewGameRequest,
  useSetupStore,
  validateSetup,
  validateStep,
} from "./useSetupStore";
import Step_NameColor from "./steps/Step_NameColor";
import Step_Faction from "./steps/Step_Faction";

/**
 * Propsy współdzielone przez komponenty kroków. Każdy krok dostaje listę frakcji
 * (z `/factions`) i mapę po id — reszta danych (sloty, akcje) pochodzi bezpośrednio ze
 * store'a przez `useSetupStore`, więc kroki nie potrzebują prop-drillingu stanu.
 */
export interface SetupStepProps {
  factions: FactionInfo[];
  factionById: Map<string, FactionInfo>;
  /** Akcje nawigacji — przekazywane tylko krokom pełnoekranowym (scena frakcji). */
  stage?: StageActions;
}

/**
 * Akcje paska górnego sceny pełnoekranowej (krok frakcji nie ma ramki kreatora, więc
 * „Wstecz" i „Generuj i graj" renderuje sam w swoim pasku).
 */
export interface StageActions {
  onBack: () => void;
  onSubmit: () => void;
  submitting: boolean;
  /** Czy konfiguracja przeszła walidację (przycisk startu aktywny). */
  canSubmit: boolean;
  /** Komunikat walidacji / błąd wysyłki (albo `null`). */
  message: string | null;
}

/** Kroki rysowane na całym ekranie, poza ramką kreatora (scena). */
export const STAGE_STEP_IDS: ReadonlySet<SetupStepId> = new Set(["faction"]);

/**
 * Rejestr „id kroku → komponent". Każdy krok kreatora ma tu swój komponent; dodanie
 * nowego kroku (np. przyszły draft slice) = nowy wpis bez zmian w samym kontenerze.
 */
const STEP_COMPONENTS: Record<SetupStepId, ComponentType<SetupStepProps>> = {
  "name-color": Step_NameColor,
  faction: Step_Faction,
};

/**
 * Kreator setupu nowej gry. Steruje nawigacją po krokach (`SETUP_STEPS`) i — na ostatnim
 * kroku — wysyła konfigurację do backendu, po czym przechodzi do widoku planszy.
 */
export default function SetupWizard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: factions } = useFactions();

  const slots = useSetupStore((s) => s.slots);
  const mapString = useSetupStore((s) => s.mapString);
  const playerCount = useSetupStore((s) => s.playerCount);
  const setPlayerCount = useSetupStore((s) => s.setPlayerCount);
  const setMapString = useSetupStore((s) => s.setMapString);
  const currentStepIndex = useSetupStore((s) => s.currentStepIndex);
  const nextStep = useSetupStore((s) => s.nextStep);
  const prevStep = useSetupStore((s) => s.prevStep);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mapa frakcji po id — do walidacji (liczba wymaganych tech) i mapowania żądania.
  const factionById = useMemo(() => {
    const map = new Map<string, FactionInfo>();
    for (const f of factions ?? []) map.set(f.id, f);
    return map;
  }, [factions]);

  const step = currentStep(currentStepIndex);
  const isLastStep = currentStepIndex >= SETUP_STEPS.length - 1;

  // Walidacja bieżącego kroku — blokuje „Dalej". Sprawdza TYLKO reguły tego kroku,
  // więc np. brak wyboru technologii (krok późniejszy) nie blokuje wyjścia z kroku
  // frakcji. To była przyczyna „nie da się przejść dalej" dla frakcji z wyborem tech.
  const stepError = useMemo(
    () => validateStep(step.id, slots, factionById),
    [step.id, slots, factionById],
  );

  // Pełna walidacja — wymagana dopiero przy „Generuj" (ostatni krok): komplet reguł.
  const fullError = useMemo(
    () => validateSetup(slots, factionById),
    [slots, factionById],
  );

  // Komunikat pod krokiem: na ostatnim kroku pokazuje pełny błąd (co jeszcze brakuje),
  // na wcześniejszych — błąd bieżącego kroku.
  const validationError = isLastStep ? fullError : stepError;

  const StepComponent = STEP_COMPONENTS[step.id];
  const isStage = STAGE_STEP_IDS.has(step.id);

  const handleSubmit = async () => {
    if (!factions || validationError) return;
    setError(null);
    setSubmitting(true);
    try {
      const request = toNewGameRequest(slots, mapString, factionById);
      await createNewGame(request);
      // Nowa gra = nowy stan; wymuś świeży fetch web-data (staleTime: Infinity).
      await queryClient.invalidateQueries({ queryKey: ["playerData"] });
      navigate("/game");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error while creating the game.");
      setSubmitting(false);
    }
  };

  // Scena pełnoekranowa (frakcja): bez ramki kreatora, własny pasek górny z akcjami.
  if (isStage) {
    return (
      <StepComponent
        factions={factions ?? []}
        factionById={factionById}
        stage={{
          onBack: prevStep,
          onSubmit: () => void handleSubmit(),
          submitting,
          canSubmit: validationError === null && !!factions,
          message: error ?? validationError,
        }}
      />
    );
  }

  return (
    <Paper radius="lg" withBorder shadow="xl" p="xl">
      <Stack gap="xl">
        {/* Pasek postępu kroków — prosty wskaźnik „krok N z M" + etykieta. */}
        <Stack gap={4}>
          <Text size="sm" c="dimmed">
            Step {currentStepIndex + 1} of {SETUP_STEPS.length}
          </Text>
          <Text fw={700} size="lg">
            {step.label}
          </Text>
        </Stack>

        {/*
         * Ustawienia gry (liczba graczy + map string) — pokazywane tylko na PIERWSZYM
         * kroku, bo zmiana liczby graczy PRZEBUDOWUJE sloty wszystkich kroków
         * (`setPlayerCount` → `resizeSlots`). Dzięki temu konfigurujesz liczbę graczy,
         * zanim zaczniesz wypełniać ich dane. Oba pola są w `useSetupStore`.
         */}
        {currentStepIndex === 0 && (
          <Group grow align="flex-start">
            <NumberInput
              label="Number of players"
              value={playerCount}
              min={MIN_PLAYERS}
              max={MAX_PLAYERS}
              onChange={(v) => {
                const n = typeof v === "number" ? v : Number(v);
                if (Number.isFinite(n)) setPlayerCount(n);
              }}
            />
            <TextInput
              label="Map string (optional)"
              placeholder="Empty = test map"
              value={mapString}
              onChange={(e) => setMapString(e.currentTarget.value)}
            />
          </Group>
        )}

        {/* Bieżący krok (stub lub realny komponent z 12.x). */}
        <StepComponent factions={factions ?? []} factionById={factionById} />

        {/* Komunikat walidacji/wysyłki — wskazuje slot i powód blokady. */}
        {(validationError || error) && (
          <Text c="red" size="sm">
            {error ?? validationError}
          </Text>
        )}

        {/* Nawigacja: „Wstecz", oraz „Dalej" / „Generuj i graj" na ostatnim kroku. */}
        <Group justify="space-between">
          <Button
            variant="default"
            onClick={prevStep}
            disabled={currentStepIndex === 0 || submitting}
          >
            Back
          </Button>

          {isLastStep ? (
            <Button
              loading={submitting}
              // „Generuj" zablokowane, dopóki konfiguracja nie przejdzie walidacji (R7–R10).
              disabled={validationError !== null || !factions}
              onClick={() => void handleSubmit()}
            >
              Generate and play
            </Button>
          ) : (
            <Button
              // „Dalej" zablokowane przy niespełnionej walidacji bieżącej konfiguracji.
              disabled={validationError !== null}
              onClick={nextStep}
            >
              Next
            </Button>
          )}
        </Group>
      </Stack>
    </Paper>
  );
}

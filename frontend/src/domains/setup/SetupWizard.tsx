// Kontener kreatora setupu (Setup_Wizard).
//
// Odpowiedzialności (zadanie 11.3):
//  1. Renderuje BIEŻĄCY krok wg uporządkowanej sekwencji `SETUP_STEPS` (R14.1). Mapowanie
//     „id kroku → komponent" trzyma lekki rejestr `STEP_COMPONENTS`; właściwe kroki
//     (Step_NameColor, Step_Faction, Step_StartingTech, Step_Control) to osobne zadania
//     12.x — do tego czasu pod ich identyfikatorami renderują się STUBY (placeholdery),
//     które podmienimy bez dotykania kontenera ani nawigacji.
//  2. Blokuje „Dalej"/„Generuj" przy niespełnionej walidacji (R7.4–R7.6, R9.2/R9.5, R10.2)
//     — logika w czystej funkcji `validateSetup` ze store'a.
//  3. Mapuje stan store'a na `NewGameRequest` (`toNewGameRequest`) i wysyła `/game/new`.
//
// Kontener jest celowo „cienki": cała walidacja i mapowanie żyją w `useSetupStore.ts`
// (testowalne bez Reacta), tu zostaje tylko spięcie stanu z UI i obsługa wysyłki.

import { useMemo, useState, type ComponentType } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Group, Paper, Stack, Text } from "@/ds";
import { useFactions, createNewGame, type FactionInfo } from "@/api/useNewGame";
import { SETUP_STEPS, type SetupStepId } from "./setupSteps";
import StepControl from "./steps/Step_Control";
import {
  currentStep,
  toNewGameRequest,
  useSetupStore,
  validateSetup,
} from "./useSetupStore";
import Step_NameColor from "./steps/Step_NameColor";
import Step_Faction from "./steps/Step_Faction";
import Step_StartingTech from "./steps/Step_StartingTech";

/**
 * Propsy współdzielone przez komponenty kroków. Każdy krok dostaje listę frakcji
 * (z `/factions`) i mapę po id — reszta danych (sloty, akcje) pochodzi bezpośrednio ze
 * store'a przez `useSetupStore`, więc kroki nie potrzebują prop-drillingu stanu.
 */
export interface SetupStepProps {
  factions: FactionInfo[];
  factionById: Map<string, FactionInfo>;
}

/**
 * Rejestr „id kroku → komponent". Każdy krok kreatora ma tu swój komponent; dodanie
 * nowego kroku (np. przyszły draft slice) = nowy wpis bez zmian w samym kontenerze.
 */
const STEP_COMPONENTS: Record<SetupStepId, ComponentType<SetupStepProps>> = {
  "name-color": Step_NameColor,
  faction: Step_Faction,
  "starting-tech": Step_StartingTech,
  control: StepControl,
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

  // Komunikat walidacji (null = konfiguracja OK). Blokuje „Dalej"/„Generuj", gdy ustawiony.
  const validationError = useMemo(
    () => validateSetup(slots, factionById),
    [slots, factionById],
  );

  const StepComponent = STEP_COMPONENTS[step.id];

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
      setError(e instanceof Error ? e.message : "Nieznany błąd przy tworzeniu gry.");
      setSubmitting(false);
    }
  };

  return (
    <Paper radius="lg" withBorder shadow="xl" p="xl">
      <Stack gap="xl">
        {/* Pasek postępu kroków — prosty wskaźnik „krok N z M" + etykieta. */}
        <Stack gap={4}>
          <Text size="sm" c="dimmed">
            Krok {currentStepIndex + 1} z {SETUP_STEPS.length}
          </Text>
          <Text fw={700} size="lg">
            {step.label}
          </Text>
        </Stack>

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
            Wstecz
          </Button>

          {isLastStep ? (
            <Button
              loading={submitting}
              // „Generuj" zablokowane, dopóki konfiguracja nie przejdzie walidacji (R7–R10).
              disabled={validationError !== null || !factions}
              onClick={() => void handleSubmit()}
            >
              Generuj i graj
            </Button>
          ) : (
            <Button
              // „Dalej" zablokowane przy niespełnionej walidacji bieżącej konfiguracji.
              disabled={validationError !== null}
              onClick={nextStep}
            >
              Dalej
            </Button>
          )}
        </Group>
      </Stack>
    </Paper>
  );
}
